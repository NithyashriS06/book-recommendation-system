from sqlalchemy import (
    Column, Integer, String, Float, Text,
    ForeignKey, DateTime, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    goodreads_book_id = Column(Integer, unique=True, nullable=False)
    title = Column(String(512), nullable=False)
    authors = Column(String(512))
    average_rating = Column(Float)
    ratings_count = Column(Integer)
    image_url = Column(String(1024))
    small_image_url = Column(String(1024))

    tags = relationship("BookTag", back_populates="book")
    ratings = relationship("Rating", back_populates="book")
    recommendations = relationship("Recommendation", back_populates="book")


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    tag_id = Column(Integer, unique=True, nullable=False)
    tag_name = Column(String(256), nullable=False)

    book_tags = relationship("BookTag", back_populates="tag")


class BookTag(Base):
    __tablename__ = "book_tags"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"))
    tag_id = Column(Integer, ForeignKey("tags.id"))
    count = Column(Integer, default=0)

    book = relationship("Book", back_populates="tags")
    tag = relationship("Tag", back_populates="book_tags")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    goodreads_user_id = Column(Integer, unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    ratings = relationship("Rating", back_populates="user")
    recommendations = relationship("Recommendation", back_populates="user")
    genre_profiles = relationship("UserGenreProfile", back_populates="user")


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    book_id = Column(Integer, ForeignKey("books.id"))
    rating = Column(Float, nullable=False)  # 1-5 stars
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (UniqueConstraint("user_id", "book_id"),)

    user = relationship("User", back_populates="ratings")
    book = relationship("Book", back_populates="ratings")


class UserGenreProfile(Base):
    """Stores a user's average rating per genre (the RL state)."""
    __tablename__ = "user_genre_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    genre = Column(String(256), nullable=False)
    avg_rating = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (UniqueConstraint("user_id", "genre"),)

    user = relationship("User", back_populates="genre_profiles")


class Recommendation(Base):
    """Stores each recommendation made by the agent (for logging & evaluation)."""
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    book_id = Column(Integer, ForeignKey("books.id"))
    q_value = Column(Float)           # Q-value the agent assigned
    actual_rating = Column(Float)     # Rating if user has rated it (for Precision@K)
    episode = Column(Integer)
    step = Column(Integer)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="recommendations")
    book = relationship("Book", back_populates="recommendations")


class TrainingMetric(Base):
    """Stores training metrics for plotting learning curves."""
    __tablename__ = "training_metrics"

    id = Column(Integer, primary_key=True, index=True)
    episode = Column(Integer, nullable=False)
    cumulative_reward = Column(Float)
    epsilon = Column(Float)
    loss = Column(Float)
    precision_at_k = Column(Float)
    created_at = Column(DateTime, server_default=func.now())
