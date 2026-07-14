"""
FastAPI application entry point.

Startup sequence:
  1. Create DB tables (if not exists)
  2. Load books + genres from DB into memory
  3. Load trained DQN model from disk
  4. Serve API endpoints
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.db.database import create_tables, SessionLocal
from app.db import models
from app.ml import inference
from app.core.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup tasks before accepting requests."""
    print("[Startup] Creating database tables...")
    create_tables()

    print("[Startup] Loading books and genres from DB...")
    db = SessionLocal()
    try:
        # Load all books into memory for the candidate pool
        books = db.query(models.Book).all()
        candidate_books = [b.id for b in books]

        # Build book_genres dict: {book_id: [genre_strings]}
        book_tags = (
            db.query(models.BookTag, models.Tag)
            .join(models.Tag, models.BookTag.tag_id == models.Tag.id)
            .filter(models.BookTag.count > 10)  # Only significant tags
            .all()
        )

        book_genres: dict[int, list[str]] = {}
        for bt, tag in book_tags:
            book_genres.setdefault(bt.book_id, []).append(tag.tag_name.lower())

        print(f"[Startup] Loaded {len(candidate_books)} books, {len(book_genres)} with genres")

        print("[Startup] Loading DQN model...")
        try:
            inference.load_model(
                candidate_books=candidate_books,
                book_genres=book_genres,
            )
            print("[Startup] Model loaded successfully.")
        except FileNotFoundError as e:
            print(f"[Startup] WARNING: {e}")
            print("[Startup] API will start but /recommendations will return 503 until model is trained.")

    finally:
        db.close()

    yield  # App is running
    print("[Shutdown] Cleaning up...")


app = FastAPI(
    title="Goodreads Q-Learning Recommender",
    version="1.0.0",
    description="Book recommendation system using Deep Q-Networks",
    lifespan=lifespan,
)

# Allow React dev server to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/")
def root():
    return {
        "message": "Goodreads RL Recommender API",
        "docs": "http://localhost:8000/docs",
    }
