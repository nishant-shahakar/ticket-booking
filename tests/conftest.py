"""
Test configuration and fixtures for ticket booking system.
"""

import pytest
import os
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.models import Base, Event, Hold, Booking, HoldStatus, BookingStatus
from app.settings import settings


# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def engine():
    """Create fresh in-memory database engine for each test."""
    test_db_url = "sqlite:///:memory:"
    engine = create_engine(
        test_db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Enable foreign keys in SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def db(engine):
    """Create fresh session for each test.
    
    Services use with session.begin_nested() for transactions.
    Tests run against in-memory database that's recreated per test.
    """
    session = sessionmaker(bind=engine)()
    
    yield session
    
    session.close()


@pytest.fixture
def sample_event(db: Session) -> Event:
    """Create a sample event for testing."""
    event = Event(
        name="Test Concert",
        date=datetime.now(timezone.utc) + timedelta(days=30),
        location="Test Venue",
        total_seats=100,
    )
    db.add(event)
    db.commit()
    return event


@pytest.fixture
def sample_user_id() -> str:
    """Generate a sample user ID."""
    return str(uuid4())


@pytest.fixture
def sample_event_id() -> str:
    """Generate a sample event ID."""
    return str(uuid4())


@pytest.fixture
def sample_hold(db: Session, sample_event: Event) -> Hold:
    """Create a sample active hold."""
    hold = Hold(
        event_id=sample_event.id,
        user_id=uuid4(),
        seat_count=5,
        status=HoldStatus.ACTIVE,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    db.add(hold)
    db.commit()
    return hold


@pytest.fixture
def sample_booking(db: Session, sample_event: Event, sample_hold: Hold) -> Booking:
    """Create a sample confirmed booking."""
    booking = Booking(
        event_id=sample_event.id,
        user_id=sample_hold.user_id,
        seat_count=5,
        status=BookingStatus.CONFIRMED,
        hold_id=sample_hold.id,
    )
    db.add(booking)
    db.commit()
    return booking
