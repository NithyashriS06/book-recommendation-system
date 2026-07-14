"""
Deep Q-Network (DQN) for book recommendation.

Architecture:
  Input:  Genre profile vector (state_dim = number of genres)
  Hidden: Two FC layers with ReLU + BatchNorm + Dropout
  Output: Q-value for each candidate book (action_dim = candidate pool size)

The network approximates Q(s, a) — the expected cumulative reward
for recommending book 'a' given the user's current genre profile 's'.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class DQNNetwork(nn.Module):
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 256):
        """
        Args:
            state_dim:   Number of genre dimensions in the state vector.
            action_dim:  Number of candidate books (action space size).
            hidden_dim:  Size of hidden layers.
        """
        super(DQNNetwork, self).__init__()

        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),

            nn.Linear(hidden_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),

            nn.Linear(hidden_dim, action_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: State tensor of shape (batch_size, state_dim)
        Returns:
            Q-values tensor of shape (batch_size, action_dim)
        """
        return self.net(x)


class ReplayBuffer:
    """
    Experience replay buffer storing (state, action, reward, next_state, done) tuples.
    Randomly sampling from this buffer breaks temporal correlations in training.
    """

    def __init__(self, capacity: int = 10_000):
        self.capacity = capacity
        self.buffer = []
        self.position = 0

    def push(self, state, action, reward, next_state, done):
        if len(self.buffer) < self.capacity:
            self.buffer.append(None)
        self.buffer[self.position] = (state, action, reward, next_state, done)
        self.position = (self.position + 1) % self.capacity

    def sample(self, batch_size: int):
        import random
        batch = random.sample(self.buffer, batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        return (
            torch.tensor(states, dtype=torch.float32),
            torch.tensor(actions, dtype=torch.long),
            torch.tensor(rewards, dtype=torch.float32),
            torch.tensor(next_states, dtype=torch.float32),
            torch.tensor(dones, dtype=torch.float32),
        )

    def __len__(self):
        return len(self.buffer)
