"""
Event service - Event management business logic.
"""

from uuid import UUID
from sqlalchemy.orm import Session

from app.models import Event
from app.repositories import EventRepository
from app.exceptions import EventNotFound


class EventService:
    """Service for event operations."""
    
    def __init__(self, session: Session):
        """Initialize with session.
        
        Args:
            session: SQLAlchemy session
        """
        self.session = session
        self.event_repo = EventRepository(session)
    
    def create_event(self, name: str, date, location: str, total_seats: int) -> Event:
        """Create a new event.
        
        Args:
            name: Event name
            date: Event date
            location: Event location
            total_seats: Total seats available
            
        Returns:
            Created event
            
        Raises:
            ValueError: If total_seats <= 0
        """
        if total_seats <= 0:
            raise ValueError("total_seats must be positive")
        
        event = Event(
            name=name,
            date=date,
            location=location,
            total_seats=total_seats,
        )
        
        self.event_repo.save(event)
        return event
    
    def get_event(self, event_id: UUID) -> Event:
        """Get event by ID.
        
        Args:
            event_id: Event UUID
            
        Returns:
            Event
            
        Raises:
            EventNotFound: If event doesn't exist
        """
        event = self.event_repo.get_by_id(event_id)
        if not event:
            raise EventNotFound()
        return event
    
    def update_event(self, event_id: UUID, **kwargs) -> Event:
        """Update event fields.
        
        Args:
            event_id: Event UUID
            **kwargs: Fields to update (name, date, location, total_seats)
            
        Returns:
            Updated event
            
        Raises:
            EventNotFound: If event doesn't exist
        """
        event = self.get_event(event_id)
        
        # Validate total_seats if provided
        if 'total_seats' in kwargs and kwargs['total_seats'] <= 0:
            raise ValueError("total_seats must be positive")
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(event, key) and value is not None:
                setattr(event, key, value)
        
        self.event_repo.update(event)
        return event
    
    def delete_event(self, event_id: UUID) -> Event:
        """Soft delete event.
        
        Args:
            event_id: Event UUID
            
        Returns:
            Soft-deleted event
            
        Raises:
            EventNotFound: If event doesn't exist
        """
        event = self.get_event(event_id)
        self.event_repo.soft_delete(event)
        return event
    
    def get_availability(self, event_id: UUID) -> dict:
        """Get seat availability for an event.
        
        Args:
            event_id: Event UUID
            
        Returns:
            Availability details:
            {
                "event_id": UUID,
                "total_seats": int,
                "confirmed_seats": int,
                "held_seats": int,
                "available_seats": int
            }
            
        Raises:
            EventNotFound: If event doesn't exist
        """
        event = self.get_event(event_id)  # Validate exists
        
        availability = self.event_repo.get_availability_details(event_id)
        if not availability:
            raise EventNotFound()
        
        return availability
    
    def list_events(self, limit: int = 100, offset: int = 0) -> list[Event]:
        """List all events with pagination.
        
        Args:
            limit: Max results
            offset: Skip count
            
        Returns:
            List of events
        """
        return self.event_repo.get_all(limit=limit, offset=offset)
