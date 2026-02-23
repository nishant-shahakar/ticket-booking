"""
Event routes - POST, GET, PUT, DELETE events.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, Query
from datetime import datetime

from app.database import get_db
from app.services import EventService
from app.schemas import EventCreateRequest, EventUpdateRequest, EventResponse, AvailabilityResponse
from app.exceptions import EventNotFound


router = APIRouter(prefix="/v1/events", tags=["events"])


@router.post("", response_model=EventResponse, status_code=201)
def create_event(
    request: EventCreateRequest,
    db = Depends(get_db),
):
    """Create a new event.
    
    Args:
        request: Event creation request
        db: Database session (dependency)
        
    Returns:
        Created event
        
    Raises:
        ValueError: If total_seats <= 0
    """
    service = EventService(db)
    event = service.create_event(
        name=request.name,
        date=request.date,
        location=request.location,
        total_seats=request.total_seats,
    )
    db.commit()
    return event


@router.get("/{event_id}", response_model=EventResponse)
def get_event(
    event_id: UUID,
    db = Depends(get_db),
):
    """Get event by ID.
    
    Args:
        event_id: Event UUID
        db: Database session (dependency)
        
    Returns:
        Event details
        
    Raises:
        EventNotFound: If event doesn't exist (404)
    """
    service = EventService(db)
    return service.get_event(event_id)


@router.put("/{event_id}", response_model=EventResponse)
def update_event(
    event_id: UUID,
    request: EventUpdateRequest,
    db = Depends(get_db),
):
    """Update event.
    
    Args:
        event_id: Event UUID
        request: Update request (partial)
        db: Database session (dependency)
        
    Returns:
        Updated event
        
    Raises:
        EventNotFound: If event doesn't exist (404)
        ValueError: If total_seats <= 0
    """
    service = EventService(db)
    
    # Filter out None values from request
    update_data = {k: v for k, v in request.dict().items() if v is not None}
    
    event = service.update_event(event_id, **update_data)
    db.commit()
    return event


@router.delete("/{event_id}", response_model=EventResponse)
def delete_event(
    event_id: UUID,
    db = Depends(get_db),
):
    """Delete (soft delete) event.
    
    Args:
        event_id: Event UUID
        db: Database session (dependency)
        
    Returns:
        Soft-deleted event
        
    Raises:
        EventNotFound: If event doesn't exist (404)
    """
    service = EventService(db)
    event = service.delete_event(event_id)
    db.commit()
    return event


@router.get("", response_model=list[EventResponse])
def list_events(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db = Depends(get_db),
):
    """List all events with pagination.
    
    Args:
        limit: Max results (1-1000, default 100)
        offset: Skip count (default 0)
        db: Database session (dependency)
        
    Returns:
        List of events
    """
    service = EventService(db)
    return service.list_events(limit=limit, offset=offset)


@router.get("/{event_id}/availability", response_model=AvailabilityResponse)
def get_availability(
    event_id: UUID,
    db = Depends(get_db),
):
    """Get seat availability for an event.
    
    Returns detailed availability:
    - total_seats: Event capacity
    - confirmed_seats: Booked seats
    - held_seats: Temporary hold seats (< 5 min)
    - available_seats: Free seats
    
    Args:
        event_id: Event UUID
        db: Database session (dependency)
        
    Returns:
        Availability details
        
    Raises:
        EventNotFound: If event doesn't exist (404)
    """
    service = EventService(db)
    return service.get_availability(event_id)
