"""
Hold routes - POST, GET holds (temporary seat reservations).
"""

from uuid import UUID
from fastapi import APIRouter, Depends

from app.database import get_db
from app.services import HoldService
from app.schemas import HoldCreateRequest, HoldResponse
from app.exceptions import InvalidSeatCount, SeatsUnavailable, EventNotFound, HoldNotFound


router = APIRouter(prefix="/v1/holds", tags=["holds"])


@router.post("", response_model=HoldResponse, status_code=201)
def create_hold(
    request: HoldCreateRequest,
    db = Depends(get_db),
):
    """Create a hold (temporary seat reservation - 5 minutes).
    
    **Critical Operation**: Uses row-level locking to prevent overbooking.
    
    Request:
        {
            "event_id": "uuid",
            "user_id": "uuid",
            "seat_count": 5
        }
    
    Success Response (201):
        {
            "id": "uuid",
            "event_id": "uuid",
            "user_id": "uuid",
            "seat_count": 5,
            "status": "ACTIVE",
            "expires_at": "2026-02-23T12:05:00Z",
            "created_at": "2026-02-23T12:00:00Z"
        }
    
    Errors:
        - 400: seat_count <= 0
        - 404: Event not found
        - 409: Not enough seats available
    
    Args:
        request: Hold creation request
        db: Database session (dependency)
        
    Returns:
        Created hold with expiry time
        
    Raises:
        InvalidSeatCount: If seat_count <= 0 (400)
        EventNotFound: If event doesn't exist (404)
        SeatsUnavailable: If not enough seats (409)
    """
    service = HoldService(db)
    
    hold = service.create_hold(
        event_id=request.event_id,
        user_id=request.user_id,
        seat_count=request.seat_count,
    )
    
    db.commit()
    return hold


@router.get("/{hold_id}", response_model=HoldResponse)
def get_hold(
    hold_id: UUID,
    db = Depends(get_db),
):
    """Get hold by ID.
    
    Args:
        hold_id: Hold UUID
        db: Database session (dependency)
        
    Returns:
        Hold details
        
    Raises:
        HoldNotFound: If hold doesn't exist (404)
        HoldExpired: If hold has expired (409)
    """
    service = HoldService(db)
    return service.get_hold(hold_id)
