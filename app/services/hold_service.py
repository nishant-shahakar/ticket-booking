"""
Hold service - Hold (temporary reservation) business logic.
Critical for concurrency control and seat availability.
"""

from uuid import UUID
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.models import Hold, HoldStatus
from app.repositories import EventRepository, HoldRepository
from app.exceptions import (
    EventNotFound, HoldNotFound, SeatsUnavailable, InvalidSeatCount,
    HoldExpired
)
from app.settings import settings


class HoldService:
    """Service for hold operations (temporary seat reservations)."""
    
    def __init__(self, session: Session):
        """Initialize with session.
        
        Args:
            session: SQLAlchemy session
        """
        self.session = session
        self.event_repo = EventRepository(session)
        self.hold_repo = HoldRepository(session)
    
    def create_hold(self, event_id: UUID, user_id: UUID, seat_count: int) -> Hold:
        """Create a hold (temporary seat reservation).
        
        **CRITICAL OPERATION**: Uses row-level locking to prevent overbooking.
        
        Flow:
            1. BEGIN TRANSACTION
            2. Lock event row (FOR UPDATE)
            3. Calculate available seats
            4. Validate seat count
            5. Create hold with 5-minute expiry
            6. COMMIT
        
        Args:
            event_id: Event UUID
            user_id: User UUID
            seat_count: Number of seats to hold
            
        Returns:
            Created hold
            
        Raises:
            EventNotFound: If event doesn't exist
            InvalidSeatCount: If seat_count <= 0
            SeatsUnavailable: If not enough seats available
        """
        if seat_count <= 0:
            raise InvalidSeatCount()
        
        # TRANSACTION BOUNDARY - all or nothing
        with self.session.begin_nested():
            # CRITICAL: Lock event row to serialize concurrent requests
            event = self.event_repo.get_for_update(event_id)
            if not event:
                raise EventNotFound()
            
            # Calculate available seats within transaction
            available = self.event_repo.calculate_available(event_id)
            
            # Check if enough seats
            if available < seat_count:
                raise SeatsUnavailable()
            
            # Create hold with expiry
            expires_at = datetime.now(timezone.utc) + timedelta(
                minutes=settings.hold_expiry_minutes
            )
            
            hold = Hold(
                event_id=event_id,
                user_id=user_id,
                seat_count=seat_count,
                status=HoldStatus.ACTIVE,
                expires_at=expires_at,
            )
            
            self.hold_repo.save(hold)
        
        # Transaction committed, lock released
        return hold
    
    def get_hold(self, hold_id: UUID) -> Hold:
        """Get hold by ID.
        
        Args:
            hold_id: Hold UUID
            
        Returns:
            Hold
            
        Raises:
            HoldNotFound: If hold doesn't exist
        """
        hold = self.hold_repo.get_by_id(hold_id)
        if not hold:
            raise HoldNotFound()
        
        # Check if expired (lazy expiry)
        expires_at = hold.expires_at
        # Ensure timezone-aware comparison (SQLite returns naive)
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if hold.status == HoldStatus.ACTIVE and expires_at <= datetime.now(timezone.utc):
            raise HoldExpired()
        
        return hold
    
    def validate_hold(self, hold_id: UUID) -> Hold:
        """Validate hold is active and not expired.
        
        Used before confirming booking.
        
        Args:
            hold_id: Hold UUID
            
        Returns:
            Valid hold
            
        Raises:
            HoldNotFound: If hold doesn't exist
            HoldExpired: If hold has expired
        """
        hold = self.hold_repo.get_by_id(hold_id)
        if not hold:
            raise HoldNotFound()
        
        # Check status
        if hold.status != HoldStatus.ACTIVE:
            raise HoldExpired()  # Already confirmed or expired
        
        # Check expiry
        expires_at = hold.expires_at
        # Ensure timezone-aware comparison (SQLite returns naive)
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            raise HoldExpired()
        
        return hold
    
    def get_user_hold(self, event_id: UUID, user_id: UUID) -> Hold:
        """Get user's active hold on an event.
        
        Args:
            event_id: Event UUID
            user_id: User UUID
            
        Returns:
            User's active hold or None
            
        Raises:
            HoldNotFound: If no active hold exists
        """
        hold = self.hold_repo.get_by_event_and_user(event_id, user_id)
        if not hold:
            raise HoldNotFound()
        
        return hold
