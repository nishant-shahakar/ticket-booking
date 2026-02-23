"""
Domain models for the ticket booking system.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, UniqueConstraint,
    CheckConstraint, Index, func, TypeDecorator
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, relationship


# Custom UUID type that works with both PostgreSQL and SQLite
class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL UUID type for native databases,
    falls back to CHAR(32) for SQLite.
    """
    impl = String(32)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value
        if not isinstance(value, uuid.UUID):
            return str(uuid.UUID(value))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return uuid.UUID(value) if not isinstance(value, uuid.UUID) else value


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


# Enums
class HoldStatus(str, Enum):
    """Hold status enumeration."""
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CONFIRMED = "CONFIRMED"


class BookingStatus(str, Enum):
    """Booking status enumeration."""
    CONFIRMED = "CONFIRMED"
    CANCELED = "CANCELED"


# Models
class Event(Base):
    """Event model - represents an event with seat capacity."""
    
    __tablename__ = "events"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    location = Column(String(255), nullable=False)
    total_seats = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    # Relationships
    holds = relationship("Hold", back_populates="event", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="event", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("total_seats > 0", name="check_event_total_seats_positive"),
        Index("idx_events_deleted_at", "deleted_at"),
    )
    
    def __repr__(self):
        return f"<Event(id={self.id}, name={self.name}, total_seats={self.total_seats})>"


class Hold(Base):
    """Hold model - temporary 5-minute seat reservation."""
    
    __tablename__ = "holds"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    event_id = Column(GUID(), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID(), nullable=False)
    seat_count = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default=HoldStatus.ACTIVE)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    event = relationship("Event", back_populates="holds")
    booking = relationship("Booking", back_populates="hold", uselist=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint("seat_count > 0", name="check_hold_seat_count_positive"),
        CheckConstraint("status IN ('ACTIVE', 'EXPIRED', 'CONFIRMED')", name="check_hold_status_valid"),
        # Index for fast availability calculation (active holds not expired)
        Index("idx_holds_event_active", "event_id", "status", "expires_at"),
        Index("idx_holds_expires_at", "expires_at"),
        Index("idx_holds_deleted_at", "deleted_at"),
    )
    
    def __repr__(self):
        return f"<Hold(id={self.id}, event_id={self.event_id}, user_id={self.user_id}, status={self.status})>"


class Booking(Base):
    """Booking model - permanent seat purchase."""
    
    __tablename__ = "bookings"
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    event_id = Column(GUID(), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(GUID(), nullable=False)
    seat_count = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default=BookingStatus.CONFIRMED)
    hold_id = Column(GUID(), ForeignKey("holds.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    event = relationship("Event", back_populates="bookings")
    hold = relationship("Hold", back_populates="booking")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("seat_count > 0", name="check_booking_seat_count_positive"),
        CheckConstraint("status IN ('CONFIRMED', 'CANCELED')", name="check_booking_status_valid"),
        # CRITICAL: Unique constraint to prevent double booking (only for confirmed)
        UniqueConstraint("event_id", "user_id", name="uq_booking_event_user"),
        # Index for fast booking lookups by event and status
        Index("idx_bookings_event_status", "event_id", "status"),
        Index("idx_bookings_user_id", "user_id"),
        Index("idx_bookings_deleted_at", "deleted_at"),
    )
    
    def __repr__(self):
        return f"<Booking(id={self.id}, event_id={self.event_id}, user_id={self.user_id}, status={self.status})>"
