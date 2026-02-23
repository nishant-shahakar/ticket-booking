"""
Booking routes - POST confirm, GET, DELETE bookings.
"""

from uuid import UUID
from fastapi import APIRouter, Depends

from app.database import get_db
from app.services import BookingService
from app.schemas import BookingConfirmRequest, BookingResponse, BookingCancelRequest
from app.exceptions import (
    HoldNotFound, HoldExpired, DuplicateBooking, InvalidHoldStatus,
    BookingNotFound, BookingAlreadyCanceled
)


router = APIRouter(prefix="/v1/bookings", tags=["bookings"])


@router.post("/confirm", response_model=BookingResponse, status_code=201)
def confirm_booking(
    request: BookingConfirmRequest,
    db = Depends(get_db),
):
    """Confirm booking from a hold (complete the purchase).
    
    **Critical Operation**: Two-phase commit with row-level locking.
    
    Flow:
        1. Validate hold exists and is ACTIVE
        2. Check hold not expired (5-minute window)
        3. Check user doesn't already have confirmed booking
        4. Create booking
        5. Mark hold as CONFIRMED
    
    Request:
        {
            "hold_id": "uuid",
            "user_id": "uuid"
        }
    
    Success Response (201):
        {
            "id": "uuid",
            "event_id": "uuid",
            "user_id": "uuid",
            "seat_count": 5,
            "status": "CONFIRMED",
            "hold_id": "uuid",
            "created_at": "2026-02-23T12:00:30Z",
            "canceled_at": null
        }
    
    Errors:
        - 404: Hold not found
        - 409: Hold expired
        - 409: Hold already confirmed or invalid status
        - 409: User already has confirmed booking for this event
    
    Args:
        request: Booking confirmation request
        db: Database session (dependency)
        
    Returns:
        Confirmed booking
        
    Raises:
        HoldNotFound: If hold doesn't exist (404)
        HoldExpired: If hold expired or invalid status (409)
        InvalidHoldStatus: If hold already confirmed (409)
        DuplicateBooking: If user already has confirmed booking (409)
    """
    service = BookingService(db)
    
    booking = service.confirm_booking(
        hold_id=request.hold_id,
        user_id=request.user_id,
    )
    
    db.commit()
    return booking


@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(
    booking_id: UUID,
    db = Depends(get_db),
):
    """Get booking by ID.
    
    Args:
        booking_id: Booking UUID
        db: Database session (dependency)
        
    Returns:
        Booking details
        
    Raises:
        BookingNotFound: If booking doesn't exist (404)
    """
    service = BookingService(db)
    return service.get_booking(booking_id)


@router.delete("/{booking_id}", response_model=BookingResponse)
def cancel_booking(
    booking_id: UUID,
    request: BookingCancelRequest,
    db = Depends(get_db),
):
    """Cancel (soft delete) a booking - seats become available.
    
    Soft delete means:
    - Booking marked as CANCELED (not deleted)
    - canceled_at timestamp recorded
    - Full audit trail maintained
    - Seats automatically available again (only CONFIRMED counted)
    
    Request:
        {
            "user_id": "uuid"
        }
    
    Success Response (200):
        {
            "id": "uuid",
            "event_id": "uuid",
            "user_id": "uuid",
            "seat_count": 5,
            "status": "CANCELED",
            "hold_id": "uuid",
            "created_at": "2026-02-23T12:00:30Z",
            "canceled_at": "2026-02-23T12:10:00Z"
        }
    
    Errors:
        - 404: Booking not found
        - 403: User doesn't own this booking
        - 409: Booking already canceled
    
    Args:
        booking_id: Booking UUID
        request: Cancellation request with user_id
        db: Database session (dependency)
        
    Returns:
        Canceled booking
        
    Raises:
        BookingNotFound: If booking doesn't exist (404)
        ApplicationException: If unauthorized (403)
        BookingAlreadyCanceled: If already canceled (409)
    """
    service = BookingService(db)
    
    booking = service.cancel_booking(
        booking_id=booking_id,
        user_id=request.user_id,
    )
    
    db.commit()
    return booking
