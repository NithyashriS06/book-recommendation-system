"""
Inference engine for the trained DQN model.

Loads the saved .pt model once at startup (via FastAPI lifespan),
then uses it to generate top-K book recommendations for a given user
without any training/backpropagation.
"""

import torch
import numpy as np
from typing import Optional
from pathlib import Path

from app.ml.dqn import DQNNetwork
from app.ml.environment import (
    RecommendationEnv, GENRE_LIST, STATE_DIM, GENRE_TO_IDX, normalize_reward
)
from app.core.config import get_settings

settings = get_settings()

# Global model instance (loaded once at startup)
_model: Optional[DQNNetwork] = None
_candidate_books: Optional[list] = None  # Global candidate book IDs
_book_genres: Optional[dict] = None      # {book_id: [genres]}


def load_model(
    candidate_books: list,
    book_genres: dict,
    model_path: Optional[str] = None,
):
    """
    Load the trained DQN model into memory.
    Called once during FastAPI startup.

    Args:
        candidate_books: Ordered list of all book IDs in the action space.
        book_genres:     Dict mapping book_id -> list of genre strings.
        model_path:      Path to the .pt file. Defaults to settings.MODEL_PATH.
    """
    global _model, _candidate_books, _book_genres

    _candidate_books = candidate_books
    _book_genres = book_genres
    path = Path(model_path or settings.MODEL_PATH)

    if not path.exists():
        raise FileNotFoundError(
            f"Model file not found at {path}. "
            "Run `python scripts/train.py` first to train the model."
        )

    import random
    # Read saved weights first to detect action_dim from the model itself
    state_dict = torch.load(str(path), map_location="cpu")
    action_dim = state_dict["net.8.weight"].shape[0]

    # Trim candidate pool to match what the model was trained with
    if len(candidate_books) > action_dim:
        _candidate_books = random.sample(candidate_books, action_dim)
    else:
        _candidate_books = candidate_books

    _model = DQNNetwork(state_dim=STATE_DIM, action_dim=action_dim)
    _model.load_state_dict(state_dict)
    _model.eval()
    print(f"[Inference] DQN model loaded from {path} | actions={action_dim}")


def get_recommendations(
    user_ratings: dict,   # {book_id: rating}
    top_k: int = 10,
    exclude_read: bool = True,
) -> list[dict]:
    """
    Generate top-K book recommendations for a user.

    Args:
        user_ratings:  The user's known ratings {book_id: rating}.
        top_k:         Number of recommendations to return.
        exclude_read:  Whether to exclude already-rated books.

    Returns:
        List of dicts: [{book_id, q_value, rank}, ...]
    """
    if _model is None:
        raise RuntimeError("Model not loaded. Call load_model() first.")

    # Build state vector from user's genre profile
    env = RecommendationEnv(
        user_ratings=user_ratings,
        book_genres=_book_genres,
        candidate_books=_candidate_books,
        episode_length=settings.EPISODE_LENGTH,
    )
    state = env.reset()

    # Filter candidate pool
    if exclude_read:
        candidates = [
            (i, book_id)
            for i, book_id in enumerate(_candidate_books)
            if book_id not in user_ratings
        ]
    else:
        candidates = list(enumerate(_candidate_books))

    if not candidates:
        return []

    # Run forward pass — no gradient needed
    state_tensor = torch.tensor(state, dtype=torch.float32).unsqueeze(0)  # (1, state_dim)
    with torch.no_grad():
        q_values = _model(state_tensor).squeeze(0).numpy()  # (action_dim,)

    # Rank candidates by Q-value
    candidate_indices, candidate_book_ids = zip(*candidates)
    candidate_q_values = [float(q_values[i]) for i in candidate_indices]

    ranked = sorted(
        zip(candidate_book_ids, candidate_q_values),
        key=lambda x: x[1],
        reverse=True,
    )[:top_k]

    return [
        {"book_id": book_id, "q_value": round(q_val, 4), "rank": rank + 1}
        for rank, (book_id, q_val) in enumerate(ranked)
    ]


def build_genre_profile(user_ratings: dict) -> dict:
    """Return user's genre profile as {genre: avg_rating} for display."""
    if _book_genres is None:
        return {}

    genre_ratings: dict[str, list] = {g: [] for g in GENRE_LIST}
    for book_id, rating in user_ratings.items():
        for genre in _book_genres.get(book_id, []):
            if genre in genre_ratings:
                genre_ratings[genre].append(rating)

    return {
        genre: round(float(np.mean(ratings)), 2)
        for genre, ratings in genre_ratings.items()
        if ratings
    }
