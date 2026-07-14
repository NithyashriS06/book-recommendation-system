# 📚 Goodreads Q-Learning Recommendation System

A research-grade book recommendation system using Deep Q-Networks (DQN), built with FastAPI + React + MySQL.

---

## Project Structure

```
goodreads-rl/
├── backend/               # FastAPI Python backend
│   ├── app/
│   │   ├── api/           # Route handlers
│   │   ├── core/          # Config, settings
│   │   ├── ml/            # Q-Learning / DQN model
│   │   └── db/            # MySQL connection & queries
│   ├── models/            # Saved .pt model files (after training)
│   └── requirements.txt
├── frontend/              # React (Vite) frontend
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── hooks/
│       └── services/
├── scripts/
│   ├── download_data.py   # Downloads Goodreads dataset
│   ├── preprocess.py      # Cleans & loads data into MySQL
│   └── train.py           # Trains the DQN offline
└── data/                  # Raw CSV files go here
```

---

## Prerequisites

- Python 3.11 (specifically — 3.12+ causes package compatibility issues)
- Node.js 18+
- MySQL 8.0+ (running locally)
- Git

---

## Step-by-Step Setup (Windows)

### 1. Clone & navigate
```bash
cd goodreads-rl
```

### 2. Set up MySQL
Open MySQL Workbench or MySQL Shell and run:
```sql
CREATE DATABASE goodreads_rl;
CREATE USER 'rl_user'@'localhost' IDENTIFIED BY 'rl_password';
GRANT ALL PRIVILEGES ON goodreads_rl.* TO 'rl_user'@'localhost';
FLUSH PRIVILEGES;
```

### 3. Set up Python backend
```bash
cd backend
py -3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

On Git Bash, activate with:
```bash
source venv/Scripts/activate
```

Copy `.env.example` to `.env` and confirm your MySQL credentials match.

### 4. Download the dataset

Dataset: **goodbooks-10k** by Zygmunt Zając
https://www.kaggle.com/datasets/zygmunt/goodbooks-10k

Download and unzip into the `data/` folder. You need these 4 files:
```
data/books.csv
data/ratings.csv
data/book_tags.csv
data/tags.csv
```

### 5. Preprocess data into MySQL

Make sure MySQL is running first:
```bash
net start MySQL80
```

Then:
```bash
python scripts/preprocess.py
```

This loads books, tags, users, and ~980k ratings into MySQL. Takes a few minutes.

> If you need to re-run preprocess, clear the DB first:
> ```sql
> USE goodreads_rl;
> SET FOREIGN_KEY_CHECKS = 0;
> TRUNCATE TABLE recommendations;
> TRUNCATE TABLE ratings;
> TRUNCATE TABLE user_genre_profiles;
> TRUNCATE TABLE users;
> TRUNCATE TABLE book_tags;
> TRUNCATE TABLE books;
> TRUNCATE TABLE tags;
> SET FOREIGN_KEY_CHECKS = 1;
> ```

### 6. Train the DQN model (offline, one-time)
```bash
python scripts/train.py
```
Saves the trained model to `backend/models/dqn_model.pt`. Takes ~10–15 minutes.

### 7. Start the backend (keep this terminal open)
```bash
cd backend
source venv/Scripts/activate
uvicorn app.main:app --reload --port 8000
```

### 8. Start the frontend (new terminal)
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

> **Note:** You only need to run preprocess and train once. After that, just start MySQL, activate the venv, and run uvicorn + npm dev each session.

---

## How It Works

### Recommendation Algorithm

The system uses a **Deep Q-Network (DQN)** — a neural network that learns to predict which book will earn the highest long-term reward (user rating) for a given user.

#### State
Each user is represented as a **genre profile vector** — a fixed array of 20 numbers, one per genre:

```
[fiction, fantasy, mystery, romance, science-fiction,
 historical-fiction, thriller, young-adult, nonfiction,
 biography, self-help, horror, graphic-novels, poetry,
 humor, children, religion, philosophy, science, travel]
```

Each value is the user's **average star rating (1.0–5.0)** across all books they've rated in that genre. A value of 0.0 means they haven't rated any books in that genre. This vector is the RL "state" — it tells the agent what kind of reader this user is.

Example for a user who likes fantasy and sci-fi:
```
[3.3, 4.2, 3.5, 0.0, 4.5, 3.4, 3.5, 3.7, 3.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.7, 0.0]
```

#### Action
Each action = recommending one book from a **candidate pool** of 500 randomly sampled unread books.

#### Reward
The reward signal is the user's actual star rating, normalized to the range **[-1, +1]**:

```
reward = (rating - 3) / 2
```

| Star Rating | Reward |
|-------------|--------|
| 5★          | +1.0   |
| 4★          | +0.5   |
| 3★          | 0.0    |
| 2★          | -0.5   |
| 1★          | -1.0   |

#### Q-Value Formula

The Q-value represents the **expected cumulative discounted reward** of recommending book `a` to a user in state `s`. It is computed via the Bellman equation:

```
Q(s, a) = r + γ · max_a' Q(s', a')
```

Where:
- `r` = immediate reward (normalized rating)
- `γ` = discount factor (0.95) — how much future rewards are valued
- `s'` = next state (updated genre profile after the recommendation)
- `max_a' Q(s', a')` = best Q-value achievable from the next state

The DQN neural network approximates Q(s, a) directly. Higher Q-value = the agent predicts this book will lead to higher ratings over the episode.

> **Note:** Q-values are not bounded to [-1, +1]. Because they accumulate discounted future rewards over a 10-step episode, they can range roughly from **-5 to +5** in practice.

#### Episode Structure
- One episode = one simulated user session (10 recommendation steps)
- Training is done **offline** by replaying historical rating data
- Exploration uses **ε-greedy**: starts fully random (ε=1.0), decays to 10% random (ε=0.1) over 2000 episodes

#### Inference (at recommendation time)
1. Build the user's genre profile vector (state) from their ratings
2. Feed the vector into the trained DQN
3. The network outputs a Q-value for each of the 500 candidate books
4. Rank by Q-value descending → return top K

---

## Evaluation Metrics

- **Precision@K**: Fraction of top-K recommendations the user actually rated ≥ 4★
- **Cumulative Reward**: Total reward per episode over training — shows the learning curve

---

## API — Testing with curl

Start the backend first, then open a second terminal and run these:

**Health check**
```bash
curl http://localhost:8000/api/health
```

**List first 10 users**
```bash
curl "http://localhost:8000/api/users?limit=10"
```

**Get a user's genre profile (state vector)**
```bash
curl http://localhost:8000/api/users/1/profile
```
Returns the 20-genre vector with each genre's average rating. Genres not rated show as absent (0.0 internally).

**Get a user's rated books**
```bash
curl http://localhost:8000/api/users/1/ratings
```

**Browse books**
```bash
curl "http://localhost:8000/api/books?limit=5"
```

**Search books by title or author**
```bash
curl "http://localhost:8000/api/books?q=hunger+games"
```

**Get DQN recommendations for a user**
```bash
curl "http://localhost:8000/api/users/1/recommendations?top_k=5"
```
Returns top-K books ranked by Q-value. Requires the model to be trained first.

---

## Troubleshooting

**MySQL not running**: Run `net start MySQL80` (or find the service name in `services.msc`).

**Duplicate entry errors during preprocess**: Truncate all tables (see step 5 above) then re-run.

**torch install fails**: Make sure you're using Python 3.11 (`py -3.11 -m venv venv`). Python 3.12+ is not supported by all dependencies.

**Model size mismatch on startup**: The saved model's action dimension doesn't match. The backend now auto-detects this from the saved weights. If it still fails, delete `backend/models/dqn_model.pt` and retrain.

**uvicorn: command not found**: Your venv isn't activated. Run `source venv/Scripts/activate` first.

---

## Tech Stack

| Layer     | Technology              |
|-----------|--------------------------|
| Frontend  | React 18 + Vite + Axios |
| Backend   | FastAPI + Uvicorn       |
| ML        | PyTorch (DQN)           |
| Database  | MySQL 8 (local)         |
| ORM       | SQLAlchemy              |