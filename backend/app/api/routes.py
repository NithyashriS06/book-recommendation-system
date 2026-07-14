"""
API route handlers.

Endpoints:
  GET  /api/users              — list all users
  GET  /api/users/{id}/profile — genre profile (RL state)
  GET  /api/users/{id}/ratings — rated books
  GET  /api/users/{id}/recommendations — get DQN recommendations
  GET  /api/books              — search/list books
  GET  /api/books/{id}         — book detail
  GET  /api/metrics            — training metrics for charts
  GET  /api/metrics/precision  — Precision@K evaluation
  GET  /api/health             — health check
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

from app.db.database import get_db
from app.db import models
from app.ml import inference
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


# ─────────────────────────── Health ───────────────────────────

@router.get("/health")
def health():
    return {"status": "ok"}


# ─────────────────────────── Users ────────────────────────────

@router.get("/users")
def list_users(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    users = db.query(models.User).limit(limit).all()
    return [{"id": u.id, "goodreads_user_id": u.goodreads_user_id} for u in users]


@router.get("/users/{user_id}/profile")
def user_genre_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    ratings = {r.book_id: r.rating for r in user.ratings}
    profile = inference.build_genre_profile(ratings)
    return {
        "user_id": user_id,
        "genre_profile": profile,
        "total_ratings": len(ratings),
    }


@router.get("/users/{user_id}/ratings")
def user_ratings(
    user_id: int,
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    rated = (
        db.query(models.Rating, models.Book)
        .join(models.Book, models.Rating.book_id == models.Book.id)
        .filter(models.Rating.user_id == user_id)
        .order_by(models.Rating.rating.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "book_id": book.id,
            "title": book.title,
            "authors": book.authors,
            "rating": r.rating,
            "image_url": book.small_image_url,
        }
        for r, book in rated
    ]


# ─────────────────────── Recommendations ──────────────────────

@router.get("/users/{user_id}/recommendations")
def get_recommendations(
    user_id: int,
    top_k: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_ratings_dict = {r.book_id: r.rating for r in user.ratings}

    try:
        recs = inference.get_recommendations(
            user_ratings=user_ratings_dict,
            top_k=top_k,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    # Enrich with book metadata
    result = []
    for rec in recs:
        book = db.query(models.Book).filter(models.Book.id == rec["book_id"]).first()
        if book:
            actual_rating = user_ratings_dict.get(book.id)
            result.append({
                "rank": rec["rank"],
                "book_id": book.id,
                "title": book.title,
                "authors": book.authors,
                "average_rating": book.average_rating,
                "image_url": book.small_image_url,
                "q_value": rec["q_value"],
                "actual_user_rating": actual_rating,  # None if unread
            })

    # Log recommendations to DB
    episode = (
        db.query(models.Recommendation)
        .filter(models.Recommendation.user_id == user_id)
        .count()
    ) // top_k + 1

    for i, rec in enumerate(result):
        db.add(models.Recommendation(
            user_id=user_id,
            book_id=rec["book_id"],
            q_value=rec["q_value"],
            actual_rating=rec["actual_user_rating"],
            episode=episode,
            step=i + 1,
        ))
    db.commit()

    return {"user_id": user_id, "recommendations": result}


# ─────────────────────────── Books ────────────────────────────

@router.get("/books")
def list_books(
    q: Optional[str] = Query(None, description="Search by title or author"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(models.Book)
    if q:
        like = f"%{q}%"
        query = query.filter(
            models.Book.title.ilike(like) | models.Book.authors.ilike(like)
        )
    books = query.offset(offset).limit(limit).all()
    return [
        {
            "id": b.id,
            "title": b.title,
            "authors": b.authors,
            "average_rating": b.average_rating,
            "image_url": b.small_image_url,
        }
        for b in books
    ]


@router.get("/books/{book_id}")
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Get top tags for this book
    tags = (
        db.query(models.Tag.tag_name, models.BookTag.count)
        .join(models.BookTag, models.Tag.id == models.BookTag.tag_id)
        .filter(models.BookTag.book_id == book_id)
        .order_by(models.BookTag.count.desc())
        .limit(10)
        .all()
    )

    return {
        "id": book.id,
        "goodreads_book_id": book.goodreads_book_id,
        "title": book.title,
        "authors": book.authors,
        "average_rating": book.average_rating,
        "ratings_count": book.ratings_count,
        "image_url": book.image_url,
        "tags": [{"name": t.tag_name, "count": t.count} for t in tags],
    }


# ─────────────────────────── Metrics ──────────────────────────

@router.get("/metrics")
def training_metrics(
    limit: int = Query(500, ge=10, le=5000),
    db: Session = Depends(get_db),
):
    metrics = (
        db.query(models.TrainingMetric)
        .order_by(models.TrainingMetric.episode)
        .limit(limit)
        .all()
    )
    return [
        {
            "episode": m.episode,
            "cumulative_reward": m.cumulative_reward,
            "epsilon": m.epsilon,
            "loss": m.loss,
            "precision_at_k": m.precision_at_k,
        }
        for m in metrics
    ]


@router.get("/metrics/precision")
def precision_at_k(
    k: int = Query(10, ge=1, le=50),
    threshold: float = Query(4.0, ge=1.0, le=5.0),
    db: Session = Depends(get_db),
):
    """
    Compute Precision@K across all logged recommendations.
    Precision@K = fraction of top-K recs that user rated >= threshold.
    Only considers recommendations where actual_rating is known.
    """
    recs = (
        db.query(models.Recommendation)
        .filter(models.Recommendation.actual_rating.isnot(None))
        .filter(models.Recommendation.step <= k)
        .all()
    )

    if not recs:
        return {"precision_at_k": None, "k": k, "threshold": threshold, "sample_size": 0}

    hits = sum(1 for r in recs if r.actual_rating >= threshold)
    precision = hits / len(recs)

    return {
        "precision_at_k": round(precision, 4),
        "k": k,
        "threshold": threshold,
        "sample_size": len(recs),
        "hits": hits,
    }
