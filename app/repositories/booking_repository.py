"""
Booking repository - handles booking queries.
"""

from typing import Optional
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import and_

from app.models import Booking, BookingStatus
from app.repositories.base_repository import BaseRepository


class BookingRepository(BaseRepository):
    """Repository for Booking model."""
    
    def __init__(self, session):
        """Initialize with session."""
        super().__init__(session, Booking)
    
    def get_for_update(self, id: UUID) -> Optional[Booking]:
        """Get booking with row-level lock (FOR UPDATE).
        
        Args:
            id: Booking UUID
            
        Returns:
            Booking with lock acquired or None
        """
        return self._base_query().filter(Booking.id == id).with_for_update().first()
    
    def get_confirmed_booking(self, event_id: UUID, user_id: UUID) -> Optional[Booking]:
        """Get user's confirmed booking for an event.
        
        Critical check during booking confirmation to prevent double booking.
        
        Args:
            event_id: Event UUID
            user_id: User UUID
            
        Returns:
            Confirmed booking or None
        """
        return self._base_query().filter(
            Booking.event_id == event_id,
            Booking.user_id == user_id,
            Booking.status == BookingStatus.CONFIRMED,
        ).first()
    
    def get_bookings_by_event(self, event_id: UUID, status: Optional[str] = None) -> list[Booking]:
        """Get bookings for an event.
        
        Args:
            event_id: Event UUID
            status: Optional status filter (CONFIRMED or CANCELED)
            
        Returns:
            List of bookings
        """
        query = self._base_query().filter(Booking.event_id == event_id)
        
        if status:
            query = query.filter(Booking.status == status)
        
        return query.all()
    
    def get_bookings_by_user(self, user_id: UUID) -> list[Booking]:
        """Get all bookings for a user.
        
        Args:
            user_id: User UUID
            
        Returns:
            List of bookings
        """
        return self._base_query().filter(Booking.user_id == user_id).all()
    
    def get_confirmed_bookings_by_user(self, user_id: UUID) -> list[Booking]:
        """Get confirmed bookings for a user.
        
        Args:
            user_id: User UUID
            
        Returns:
            List of confirmed bookings
        """
        return self._base_query().filter(
            Booking.user_id == user_id,
            Booking.status == BookingStatus.CONFIRMED,
        ).all()
    
    def mark_canceled(self, booking: Booking) -> Booking:
        """Mark booking as CANCELED (soft delete).
        
        Args:
            booking: Booking to cancel
            
        Returns:
            Updated booking
        """
        booking.status = BookingStatus.CANCELED
        booking.canceled_at = datetime.now(timezone.utc)
        return self.update(booking)
    
    def is_user_has_confirmed_booking(self, event_id: UUID, user_id: UUID) -> bool:
        """Check if user has confirmed booking for event.
        
        Args:
            event_id: Event UUID
            user_id: User UUID
            
        Returns:
            True if confirmed booking exists
        """
        booking = self.get_confirmed_booking(event_id, user_id)
        return booking is not None
