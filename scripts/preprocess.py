"""
Preprocess Goodreads CSVs and load into MySQL.

Input files (in ./data/):
  - books.csv
  - ratings.csv
  - book_tags.csv
  - tags.csv

Run from project root:
  python scripts/preprocess.py
"""

import sys
import os
from pathlib import Path

# Add backend to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
os.chdir(Path(__file__).parent.parent / "backend")

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import engine, create_tables, SessionLocal
from app.db.models import Book, Tag, BookTag, User, Rating

DATA_DIR = Path(__file__).parent.parent / "data"

# Genre-related tag names we care about (maps to GENRE_LIST in environment.py)
GENRE_TAGS = {
    "fiction", "fantasy", "mystery", "romance", "science-fiction",
    "historical-fiction", "thriller", "young-adult", "nonfiction",
    "biography", "self-help", "horror", "graphic-novels", "poetry",
    "humor", "children", "religion", "philosophy", "science", "travel",
    # Common aliases
    "sci-fi", "ya", "biography-memoir", "historical", "non-fiction",
    "graphic-novel", "childrens",
}


def load_books(db: Session, df: pd.DataFrame):
    print(f"Loading {len(df)} books...")
    for _, row in df.iterrows():
        book = Book(
            goodreads_book_id=int(row["book_id"]),
            title=str(row.get("title", ""))[:512],
            authors=str(row.get("authors", ""))[:512],
            average_rating=float(row.get("average_rating", 0)) if pd.notna(row.get("average_rating")) else None,
            ratings_count=int(row.get("ratings_count", 0)) if pd.notna(row.get("ratings_count")) else None,
            image_url=str(row.get("image_url", ""))[:1024] if pd.notna(row.get("image_url")) else None,
            small_image_url=str(row.get("small_image_url", ""))[:1024] if pd.notna(row.get("small_image_url")) else None,
        )
        db.merge(book)
    db.commit()
    print(f"  ✓ Books loaded")


def load_tags(db: Session, df: pd.DataFrame):
    print(f"Loading {len(df)} tags...")
    for _, row in df.iterrows():
        tag = Tag(
            tag_id=int(row["tag_id"]),
            tag_name=str(row["tag_name"])[:256],
        )
        db.merge(tag)
    db.commit()
    print(f"  ✓ Tags loaded")


def load_book_tags(db: Session, bt_df: pd.DataFrame, tags_df: pd.DataFrame, books_df: pd.DataFrame):
    """Only load book tags that correspond to genre-related tags."""
    print("Loading book_tags (genre tags only)...")

    # Build lookup: goodreads tag_id → DB tag id
    genre_tag_names = tags_df[
        tags_df["tag_name"].str.lower().isin(GENRE_TAGS)
    ]
    genre_tag_ids = set(genre_tag_names["tag_id"].astype(int))

    # Build book lookup: goodreads book_id → DB book id
    book_gid_to_id = {int(row["book_id"]): idx + 1 for idx, row in books_df.iterrows()}
    tag_gid_to_id = {int(row["tag_id"]): idx + 1 for idx, row in tags_df.iterrows()}

    filtered = bt_df[bt_df["tag_id"].astype(int).isin(genre_tag_ids)]
    count = 0
    for _, row in filtered.iterrows():
        gbook_id = int(row["goodreads_book_id"])
        gtag_id = int(row["tag_id"])
        db_book_id = book_gid_to_id.get(gbook_id)
        db_tag_id = tag_gid_to_id.get(gtag_id)
        if db_book_id and db_tag_id:
            bt = BookTag(
                book_id=db_book_id,
                tag_id=db_tag_id,
                count=int(row.get("count", 0)),
            )
            db.merge(bt)
            count += 1
    db.commit()
    print(f"  ✓ {count} book-tag links loaded")


def load_users_and_ratings(db: Session, ratings_df: pd.DataFrame, books_df: pd.DataFrame):
    print(f"Loading users and {len(ratings_df)} ratings (this may take a few minutes)...")

    book_gid_to_db_id = {}
    for idx, row in books_df.iterrows():
        book_gid_to_db_id[int(row["book_id"])] = idx + 1

    before = len(ratings_df)
    ratings_df = ratings_df.drop_duplicates(subset=["user_id", "book_id"], keep="last")
    print(f"  Deduplicated {before} → {len(ratings_df)} ratings")

    user_gid_to_db_id = {}
    batch_size = 5000
    batch = []

    insert_sql = text(
        "INSERT IGNORE INTO ratings (user_id, book_id, rating) "
        "VALUES (:user_id, :book_id, :rating)"
    )

    for i, (_, row) in enumerate(ratings_df.iterrows()):
        guser_id = int(row["user_id"])
        gbook_id = int(row["book_id"])
        rating = float(row["rating"])

        if guser_id not in user_gid_to_db_id:
            user = User(goodreads_user_id=guser_id)
            db.add(user)
            db.flush()
            user_gid_to_db_id[guser_id] = user.id

        db_user_id = user_gid_to_db_id[guser_id]
        db_book_id = book_gid_to_db_id.get(gbook_id)

        if db_book_id and rating > 0:
            batch.append({
                "user_id": db_user_id,
                "book_id": db_book_id,
                "rating": rating,
            })

        if len(batch) >= batch_size:
            db.execute(insert_sql, batch)
            db.commit()
            batch = []
            print(f"  Processed {i+1} ratings...")

    if batch:
        db.execute(insert_sql, batch)
        db.commit()

    print(f"  ✓ {len(user_gid_to_db_id)} users and ratings loaded")

def main():
    print("=== Goodreads Data Preprocessing ===\n")

    # Check files exist
    required = ["books.csv", "ratings.csv", "book_tags.csv", "tags.csv"]
    for fname in required:
        path = DATA_DIR / fname
        if not path.exists():
            print(f"ERROR: {path} not found. Run `python scripts/download_data.py` first.")
            sys.exit(1)

    print("Reading CSV files...")
    books_df = pd.read_csv(DATA_DIR / "books.csv", on_bad_lines="skip")
    ratings_df = pd.read_csv(DATA_DIR / "ratings.csv", on_bad_lines="skip")
    book_tags_df = pd.read_csv(DATA_DIR / "book_tags.csv", on_bad_lines="skip")
    tags_df = pd.read_csv(DATA_DIR / "tags.csv", on_bad_lines="skip")

    print(f"  books: {len(books_df)} rows")
    print(f"  ratings: {len(ratings_df)} rows")
    print(f"  book_tags: {len(book_tags_df)} rows")
    print(f"  tags: {len(tags_df)} rows\n")

    print("Creating database tables...")
    create_tables()

    db = SessionLocal()
    try:
        load_books(db, books_df)
        load_tags(db, tags_df)
        load_book_tags(db, book_tags_df, tags_df, books_df)
        load_users_and_ratings(db, ratings_df, books_df)
    finally:
        db.close()

    print("\n✅ Preprocessing complete! Run `python scripts/train.py` next.")


if __name__ == "__main__":
    main()
