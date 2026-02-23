"""
Database connection and session management.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from app.settings import settings


# Create engine with connection pool
engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
    poolclass=NullPool,  # Disable connection pooling for testing simplicity
)


# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_session() -> Session:
    """Get a new database session."""
    return SessionLocal()


def get_db():
    """Dependency injection for FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
