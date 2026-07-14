"""
Offline DQN Training Script.

Trains the book recommendation agent by replaying historical user ratings.

Algorithm:
  1. For each user (episode):
     a. Build initial state from their genre profile
     b. For each step (up to EPISODE_LENGTH):
        - Agent picks best book (ε-greedy)
        - Receives reward = normalized actual rating
        - Stores (s, a, r, s', done) in replay buffer
        - Updates state with book's genres
     c. Every N steps: sample batch, compute TD loss, backpropagate
  2. Target network updated every TARGET_UPDATE episodes (stabilizes training)
  3. ε decays from 1.0 → 0.1 over training

Outputs:
  - backend/models/dqn_model.pt   (trained weights)
  - Metrics saved to DB for plotting
"""

import sys
import os
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
os.chdir(Path(__file__).parent.parent / "backend")

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from copy import deepcopy

from app.db.database import SessionLocal, create_tables
from app.db import models
from app.ml.dqn import DQNNetwork, ReplayBuffer
from app.ml.environment import RecommendationEnv, STATE_DIM, GENRE_TO_IDX
from app.core.config import get_settings

settings = get_settings()

# ─────────────────── Hyperparameters ───────────────────
EPISODES = 2000            # Total training episodes (users)
EPISODE_LENGTH = 10        # Steps per episode
BATCH_SIZE = 64
GAMMA = 0.95               # Discount factor
LR = 1e-3                  # Learning rate
EPSILON_START = 1.0
EPSILON_END = 0.1
EPSILON_DECAY = 0.995
TARGET_UPDATE = 50         # Update target network every N episodes
REPLAY_MIN = 500           # Min samples in buffer before training starts
REPLAY_CAPACITY = 20_000
CANDIDATE_POOL = 500       # Books to sample per user as action space
TOP_K = 10
HIDDEN_DIM = 256
SAVE_PATH = Path("models/dqn_model.pt")
METRICS_EVERY = 10         # Log metrics every N episodes
# ───────────────────────────────────────────────────────


def precision_at_k(recommendations: list, user_ratings: dict, k: int = 10, threshold: float = 4.0) -> float:
    top_k = recommendations[:k]
    hits = sum(1 for b in top_k if user_ratings.get(b, 0) >= threshold)
    return hits / k if k > 0 else 0.0


def compute_td_loss(
    policy_net: DQNNetwork,
    target_net: DQNNetwork,
    buffer: ReplayBuffer,
    optimizer: optim.Optimizer,
    device: torch.device,
) -> float:
    states, actions, rewards, next_states, dones = buffer.sample(BATCH_SIZE)
    states = states.to(device)
    actions = actions.to(device)
    rewards = rewards.to(device)
    next_states = next_states.to(device)
    dones = dones.to(device)

    # Q(s, a) from policy network
    q_values = policy_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)

    # max Q(s', a') from target network (no gradient)
    with torch.no_grad():
        next_q = target_net(next_states).max(1)[0]
        target_q = rewards + GAMMA * next_q * (1 - dones)

    loss = nn.MSELoss()(q_values, target_q)
    optimizer.zero_grad()
    loss.backward()
    nn.utils.clip_grad_norm_(policy_net.parameters(), max_norm=1.0)
    optimizer.step()

    return loss.item()


def main():
    print("=== DQN Training ===\n")
    create_tables()
    SAVE_PATH.parent.mkdir(exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    db = SessionLocal()
    try:
        print("Loading data from MySQL...")
        all_books = db.query(models.Book).all()
        all_book_ids = [b.id for b in all_books]

        # Build book_genres dict
        book_tags = (
            db.query(models.BookTag, models.Tag)
            .join(models.Tag, models.BookTag.tag_id == models.Tag.id)
            .filter(models.BookTag.count > 10)
            .all()
        )
        book_genres: dict[int, list[str]] = {}
        for bt, tag in book_tags:
            book_genres.setdefault(bt.book_id, []).append(tag.tag_name.lower())

        # Load users with enough ratings
        users_with_ratings = (
            db.query(models.User)
            .join(models.Rating)
            .group_by(models.User.id)
            .having(db.query(models.Rating).filter(
                models.Rating.user_id == models.User.id
            ).count() >= 5)
            .limit(EPISODES * 2)  # Get more than needed for variety
            .all()
        )

        if not users_with_ratings:
            print("ERROR: No users found in DB. Run preprocess.py first.")
            sys.exit(1)

        print(f"Found {len(users_with_ratings)} eligible users")
        print(f"Books: {len(all_book_ids)} | Episode length: {EPISODE_LENGTH}\n")

    except Exception as e:
        print(f"DB Error: {e}")
        db.close()
        sys.exit(1)

    # Use a fixed candidate pool size for consistent action_dim across all users
    action_dim = min(CANDIDATE_POOL, len(all_book_ids))
    policy_net = DQNNetwork(STATE_DIM, action_dim, HIDDEN_DIM).to(device)
    target_net = deepcopy(policy_net).to(device)
    target_net.eval()

    optimizer = optim.Adam(policy_net.parameters(), lr=LR)
    buffer = ReplayBuffer(REPLAY_CAPACITY)

    epsilon = EPSILON_START
    total_loss = 0.0
    loss_count = 0

    print("Starting training...\n")

    for episode in range(1, EPISODES + 1):
        # Sample a random user
        user = random.choice(users_with_ratings)
        user_ratings = {r.book_id: r.rating for r in db.query(models.Rating).filter(
            models.Rating.user_id == user.id
        ).all()}

        # Sample candidate pool (unread books for this user)
        unread = [b for b in all_book_ids if b not in user_ratings]
        candidate_books = random.sample(unread, min(action_dim, len(unread)))

        # Pad if needed to keep action_dim consistent
        while len(candidate_books) < action_dim:
            candidate_books.append(random.choice(all_book_ids))

        env = RecommendationEnv(
            user_ratings=user_ratings,
            book_genres=book_genres,
            candidate_books=candidate_books,
            episode_length=EPISODE_LENGTH,
        )

        state = env.reset()
        cumulative_reward = 0.0
        recommended_books = []

        for step in range(EPISODE_LENGTH):
            state_tensor = torch.tensor(state, dtype=torch.float32).unsqueeze(0).to(device)

            # ε-greedy action selection
            if random.random() < epsilon:
                action = random.randint(0, action_dim - 1)
            else:
                policy_net.eval()
                with torch.no_grad():
                    action = policy_net(state_tensor).argmax(dim=1).item()
                policy_net.train()

            next_state, reward, done, info = env.step(action)
            cumulative_reward += reward
            recommended_books.append(candidate_books[action])

            buffer.push(state, action, reward, next_state, float(done))
            state = next_state

            # Train when buffer has enough samples
            if len(buffer) >= REPLAY_MIN:
                loss = compute_td_loss(policy_net, target_net, buffer, optimizer, device)
                total_loss += loss
                loss_count += 1

            if done:
                break

        # Decay epsilon
        epsilon = max(EPSILON_END, epsilon * EPSILON_DECAY)

        # Update target network
        if episode % TARGET_UPDATE == 0:
            target_net.load_state_dict(policy_net.state_dict())

        # Log metrics
        if episode % METRICS_EVERY == 0:
            avg_loss = total_loss / max(loss_count, 1)
            prec = precision_at_k(recommended_books, user_ratings, k=TOP_K)

            db.add(models.TrainingMetric(
                episode=episode,
                cumulative_reward=round(cumulative_reward, 4),
                epsilon=round(epsilon, 4),
                loss=round(avg_loss, 6),
                precision_at_k=round(prec, 4),
            ))
            db.commit()

            print(
                f"Episode {episode:4d}/{EPISODES} | "
                f"Reward: {cumulative_reward:+.2f} | "
                f"Precision@{TOP_K}: {prec:.2%} | "
                f"ε: {epsilon:.3f} | "
                f"Loss: {avg_loss:.5f}"
            )

            total_loss = 0.0
            loss_count = 0

    # Save trained model
    torch.save(policy_net.state_dict(), str(SAVE_PATH))
    print(f"\n✅ Model saved to {SAVE_PATH}")
    print("Run the FastAPI backend to start serving recommendations.")
    db.close()


if __name__ == "__main__":
    main()
