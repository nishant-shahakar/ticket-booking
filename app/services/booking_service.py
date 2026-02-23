"""
Booking service - Booking confirmation and cancellation logic.
Critical for preventing double booking and managing soft deletes.
"""

from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import Booking, BookingStatus
from app.repositories import BookingRepository, HoldRepository, EventRepository
from app.exceptions import (
    BookingNotFound, HoldNotFound, HoldExpired, DuplicateBooking,
    InvalidHoldStatus, BookingAlreadyCanceled
)


class BookingService:
    """Service for booking operations."""
    
    def __init__(self, session: Session):
        """Initialize with session.
        
        Args:
            session: SQLAlchemy session
        """
        self.session = session
        self.booking_repo = BookingRepository(session)
        self.hold_repo = HoldRepository(session)
        self.event_repo = EventRepository(session)
    
    def confirm_booking(self, hold_id: UUID, user_id: UUID) -> Booking:
        """Confirm booking from an active hold.
        
        **CRITICAL OPERATION**: Two-phase commit with row-level locking.
        
        Flow:
            1. BEGIN TRANSACTION
            2. Lock hold row (FOR UPDATE)
            3. Validate hold (exists, not expired, not already confirmed)
            4. Check user doesn't already have confirmed booking
            5. Create booking
            6. Mark hold as CONFIRMED
            7. COMMIT
            8. Unique constraint on (event_id, user_id, status='CONFIRMED') prevents double-insert
        
        Args:
            hold_id: Hold UUID to confirm
            user_id: User UUID confirming
            
        Returns:
            Created booking
            
        Raises:
            HoldNotFound: If hold doesn't exist
            InvalidHoldStatus: If hold is not ACTIVE
            HoldExpired: If hold has expired
            DuplicateBooking: If user already has confirmed booking
        """
        # TRANSACTION BOUNDARY - use nested for testing compatibility
        with self.session.begin_nested():
            # Lock hold to prevent concurrent confirmation
            hold = self.hold_repo.get_for_update(hold_id)
            if not hold:
                raise HoldNotFound()
            
            # Validate hold state
            if hold.status != 'ACTIVE':
                raise InvalidHoldStatus()
            
            # Check not expired
            expires_at = hold.expires_at
            # Ensure timezone-aware comparison (SQLite returns naive)
            if expires_at and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at <= datetime.now(timezone.utc):
                raise HoldExpired()
            
            # Critical: Check user doesn't already have confirmed booking
            existing = self.booking_repo.get_confirmed_booking(
                hold.event_id,
                user_id
            )
            if existing:
                raise DuplicateBooking()
            
            # Create booking
            booking = Booking(
                event_id=hold.event_id,
                user_id=user_id,
                seat_count=hold.seat_count,
                status=BookingStatus.CONFIRMED,
                hold_id=hold_id,
            )
            
            self.booking_repo.save(booking)
            
            # Mark hold as confirmed
            hold.status = 'CONFIRMED'
            self.hold_repo.update(hold)
        
        # Transaction committed
        # Unique index on (event_id, user_id, status='CONFIRMED') now enforced
        return booking
    
    def get_booking(self, booking_id: UUID) -> Booking:
        """Get booking by ID.
        
        Args:
            booking_id: Booking UUID
            
        Returns:
            Booking
            
        Raises:
            BookingNotFound: If booking doesn't exist
        """
        booking = self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise BookingNotFound()
        return booking
    
    def cancel_booking(self, booking_id: UUID, user_id: UUID) -> Booking:
        """Cancel (soft delete) a booking.
        
        Flow:
            1. BEGIN TRANSACTION
            2. Lock booking row (FOR UPDATE)
            3. Validate ownership (user_id matches)
            4. Check not already canceled
            5. Set status = CANCELED, canceled_at = now
            6. COMMIT
        
        Seats automatically become available since availability only counts CONFIRMED.
        
        Args:
            booking_id: Booking UUID
            user_id: User UUID requesting cancellation
            
        Returns:
            Canceled booking
            
        Raises:
            BookingNotFound: If booking doesn't exist
            Unauthorized: If user doesn't own booking
            BookingAlreadyCanceled: If already canceled
        """
        with self.session.begin_nested():
            booking = self.booking_repo.get_for_update(booking_id)
            if not booking:
                raise BookingNotFound()
            
            # Verify ownership
            if booking.user_id != user_id:
                from app.exceptions import ApplicationException
                raise ApplicationException(
                    "Unauthorized to cancel this booking",
                    "UNAUTHORIZED",
                    403
                )
            
            # Check not already canceled
            if booking.status == BookingStatus.CANCELED:
                raise BookingAlreadyCanceled()
            
            # Soft delete
            self.booking_repo.mark_canceled(booking)
        
        return booking
    
    def get_user_bookings(self, user_id: UUID) -> list[Booking]:
        """Get all bookings for a user.
        
        Args:
            user_id: User UUID
            
        Returns:
            List of bookings
        """
        return self.booking_repo.get_bookings_by_user(user_id)
    
    def get_confirmed_bookings(self, user_id: UUID) -> list[Booking]:
        """Get confirmed bookings for a user.
        
        Args:
            user_id: User UUID
            
        Returns:
            List of confirmed bookings
        """
        return self.booking_repo.get_confirmed_bookings_by_user(user_id)
    
    def has_confirmed_booking(self, event_id: UUID, user_id: UUID) -> bool:
        """Check if user has confirmed booking for event.
        
        Args:
            event_id: Event UUID
            user_id: User UUID
            
        Returns:
            True if confirmed booking exists
        """
        return self.booking_repo.is_user_has_confirmed_booking(event_id, user_id)
