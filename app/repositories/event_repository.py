"""
Event repository - handles event queries.
"""

from typing import Optional
from uuid import UUID
from sqlalchemy import func

from app.models import Event, Booking, Hold, HoldStatus, BookingStatus
from app.repositories.base_repository import BaseRepository


class EventRepository(BaseRepository):
    """Repository for Event model."""
    
    def __init__(self, session):
        """Initialize with session."""
        super().__init__(session, Event)
    
    def get_for_update(self, id: UUID) -> Optional[Event]:
        """Get event with row-level lock (FOR UPDATE).
        
        Critical for concurrency control during hold/booking operations.
        
        Args:
            id: Event UUID
            
        Returns:
            Event with lock acquired or None
        """
        return self._base_query().filter(Event.id == id).with_for_update().first()
    
    def calculate_available(self, event_id: UUID) -> int:
        """Calculate available seats for an event.
        
        Formula:
            available = total_seats - confirmed_bookings - active_holds
        
        MUST be called within transaction after acquiring lock on event.
        
        Args:
            event_id: Event UUID
            
        Returns:
            Number of available seats
        """
        event = self.get_by_id(event_id)
        if not event:
            return 0
        
        # Sum confirmed bookings
        confirmed_seats = self.session.query(
            func.coalesce(func.sum(Booking.seat_count), 0)
        ).filter(
            Booking.event_id == event_id,
            Booking.status == BookingStatus.CONFIRMED,
            Booking.deleted_at.is_(None)
        ).scalar()
        
        # Sum active holds (not expired)
        from sqlalchemy import and_
        from datetime import datetime, timezone
        
        held_seats = self.session.query(
            func.coalesce(func.sum(Hold.seat_count), 0)
        ).filter(
            Hold.event_id == event_id,
            Hold.status == HoldStatus.ACTIVE,
            Hold.expires_at > datetime.now(timezone.utc),
            Hold.deleted_at.is_(None)
        ).scalar()
        
        available = event.total_seats - confirmed_seats - held_seats
        return max(0, available)  # Never return negative
    
    def get_availability_details(self, event_id: UUID) -> dict:
        """Get detailed availability information for an event.
        
        Returns:
            {
                "event_id": UUID,
                "total_seats": int,
                "confirmed_seats": int,
                "held_seats": int,
                "available_seats": int
            }
        """
        event = self.get_by_id(event_id)
        if not event:
            return None
        
        from sqlalchemy import and_
        from datetime import datetime, timezone
        
        # Single query for all stats
        from sqlalchemy import and_
        from datetime import datetime, timezone
        
        result = self.session.query(
            func.coalesce(func.sum(Booking.seat_count), 0).label('confirmed_seats'),
            func.coalesce(
                func.sum(Hold.seat_count), 0
            ).label('held_seats')
        ).select_from(Event).outerjoin(
            Booking,
            and_(
                Booking.event_id == Event.id,
                Booking.status == BookingStatus.CONFIRMED,
                Booking.deleted_at.is_(None)
            )
        ).outerjoin(
            Hold,
            and_(
                Hold.event_id == Event.id,
                Hold.status == HoldStatus.ACTIVE,
                Hold.expires_at > datetime.now(timezone.utc),
                Hold.deleted_at.is_(None)
            )
        ).filter(Event.id == event_id).first()
        
        confirmed_seats, held_seats = result
        available_seats = event.total_seats - confirmed_seats - held_seats
        
        return {
            "event_id": event_id,
            "total_seats": event.total_seats,
            "confirmed_seats": confirmed_seats,
            "held_seats": held_seats,
            "available_seats": max(0, available_seats),
        }
    
    def get_all(self, limit: int = 100, offset: int = 0) -> list[Event]:
        """Get all events with pagination.
        
        Args:
            limit: Max results
            offset: Skip count
            
        Returns:
            List of events
        """
        return self._base_query().limit(limit).offset(offset).all()
