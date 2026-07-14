"""
Recommendation Environment for offline RL simulation.

Simulates a user session by replaying historical rating data.
The agent interacts with this environment during both training and inference.

State:  Genre profile vector — avg rating per genre for the current user.
Action: Index into the candidate book pool.
Reward: Normalized actual rating = (rating - 3) / 2  → range [-1, +1]
Done:   True after EPISODE_LENGTH steps.
"""

import numpy as np
from typing import Optional


GENRE_LIST = [
    "fiction", "fantasy", "mystery", "romance", "science-fiction",
    "historical-fiction", "thriller", "young-adult", "nonfiction",
    "biography", "self-help", "horror", "graphic-novels", "poetry",
    "humor", "children", "religion", "philosophy", "science", "travel"
]
STATE_DIM = len(GENRE_LIST)
GENRE_TO_IDX = {g: i for i, g in enumerate(GENRE_LIST)}


def normalize_reward(rating: float) -> float:
    """Maps 1-5 star rating to [-1, +1]."""
    return (rating - 3.0) / 2.0


class RecommendationEnv:
    def __init__(
        self,
        user_ratings: dict,          # {book_id: rating}
        book_genres: dict,           # {book_id: [genre_str, ...]}
        candidate_books: list,       # [book_id, ...] — filtered candidate pool
        episode_length: int = 10,
    ):
        """
        Args:
            user_ratings:    All ratings this user has given {book_id: rating}.
            book_genres:     Genre tags for each book {book_id: [genres]}.
            candidate_books: Subset of unread books the agent can recommend.
            episode_length:  Max steps per episode.
        """
        self.user_ratings = user_ratings
        self.book_genres = book_genres
        self.candidate_books = candidate_books
        self.episode_length = episode_length

        self.state: Optional[np.ndarray] = None
        self.step_count = 0
        self.recommended = set()

    def reset(self) -> np.ndarray:
        """Reset environment and compute initial genre profile from early ratings."""
        self.step_count = 0
        self.recommended = set()
        self.state = self._build_genre_profile()
        return self.state.copy()

    def step(self, action_idx: int):
        """
        Take one recommendation step.

        Args:
            action_idx: Index into candidate_books list.
        Returns:
            (next_state, reward, done, info)
        """
        book_id = self.candidate_books[action_idx]
        self.recommended.add(book_id)

        # Reward: actual rating if available, else slightly negative (unknown)
        if book_id in self.user_ratings:
            rating = self.user_ratings[book_id]
            reward = normalize_reward(rating)
        else:
            reward = -0.5  # Penalize recommending books with no known rating

        # Update genre profile state with this book's genres
        genres = self.book_genres.get(book_id, [])
        if book_id in self.user_ratings and genres:
            rating = self.user_ratings[book_id]
            for genre in genres:
                idx = GENRE_TO_IDX.get(genre)
                if idx is not None:
                    # Incremental running average update
                    old_avg = self.state[idx]
                    # Track count via a small heuristic (simplified)
                    self.state[idx] = old_avg * 0.9 + rating * 0.1

        self.step_count += 1
        done = self.step_count >= self.episode_length

        info = {
            "book_id": book_id,
            "reward": reward,
            "has_rating": book_id in self.user_ratings,
        }

        return self.state.copy(), reward, done, info

    def _build_genre_profile(self) -> np.ndarray:
        """Build state vector: avg rating per genre across all rated books."""
        genre_ratings = {g: [] for g in GENRE_LIST}

        for book_id, rating in self.user_ratings.items():
            genres = self.book_genres.get(book_id, [])
            for genre in genres:
                if genre in genre_ratings:
                    genre_ratings[genre].append(rating)

        profile = np.zeros(STATE_DIM, dtype=np.float32)
        for genre, ratings in genre_ratings.items():
            if ratings:
                profile[GENRE_TO_IDX[genre]] = np.mean(ratings)

        return profile

    @property
    def state_dim(self) -> int:
        return STATE_DIM

    @property
    def action_dim(self) -> int:
        return len(self.candidate_books)
