"""
Request and response schemas (Data Transfer Objects).
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Event Schemas
# ============================================================================

class EventCreateRequest(BaseModel):
    """Request to create an event."""
    
    name: str = Field(..., min_length=1, max_length=255)
    date: datetime
    location: str = Field(..., min_length=1, max_length=255)
    total_seats: int = Field(..., gt=0)


class EventUpdateRequest(BaseModel):
    """Request to update an event."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    date: Optional[datetime] = None
    location: Optional[str] = Field(None, min_length=1, max_length=255)
    total_seats: Optional[int] = Field(None, gt=0)


class EventResponse(BaseModel):
    """Response containing event data."""
    
    id: UUID
    name: str
    date: datetime
    location: str
    total_seats: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Hold Schemas
# ============================================================================

class HoldCreateRequest(BaseModel):
    """Request to create a hold (reserve seats)."""
    
    event_id: UUID
    user_id: UUID
    seat_count: int = Field(..., gt=0)


class HoldResponse(BaseModel):
    """Response containing hold data."""
    
    id: UUID
    event_id: UUID
    user_id: UUID
    seat_count: int
    status: str
    expires_at: datetime
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# Booking Schemas
# ============================================================================

class BookingConfirmRequest(BaseModel):
    """Request to confirm a booking from a hold."""
    
    hold_id: UUID
    user_id: UUID


class BookingResponse(BaseModel):
    """Response containing booking data."""
    
    id: UUID
    event_id: UUID
    user_id: UUID
    seat_count: int
    status: str
    hold_id: Optional[UUID] = None
    created_at: datetime
    canceled_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class BookingCancelRequest(BaseModel):
    """Request to cancel a booking."""
    
    user_id: UUID


# ============================================================================
# Availability Schemas
# ============================================================================

class AvailabilityResponse(BaseModel):
    """Response containing seat availability for an event."""
    
    event_id: UUID
    total_seats: int
    confirmed_seats: int
    held_seats: int
    available_seats: int


# ============================================================================
# Error Response Schema
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response format."""
    
    message: str
    code: str
    status: str = "error"
