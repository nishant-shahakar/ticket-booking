"""
Tests for BookingService - Booking confirmation and cancellation.
**CRITICAL**: Tests for preventing double booking and soft deletes.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from app.services import BookingService
from app.exceptions import (
    HoldNotFound, HoldExpired, InvalidHoldStatus, DuplicateBooking,
    BookingNotFound, BookingAlreadyCanceled, ApplicationException
)
from app.models import BookingStatus, Hold, HoldStatus


class TestBookingServiceConfirmBasic:
    """Test basic booking confirmation."""
    
    def test_confirm_booking_success(self, db, sample_hold):
        """Test successful booking confirmation."""
        service = BookingService(db)
        
        booking = service.confirm_booking(
            hold_id=sample_hold.id,
            user_id=sample_hold.user_id,
        )
        
        assert booking.id is not None
        assert booking.event_id == sample_hold.event_id
        assert booking.user_id == sample_hold.user_id
        assert booking.seat_count == sample_hold.seat_count
        assert booking.status == BookingStatus.CONFIRMED
        assert booking.hold_id == sample_hold.id
        assert booking.created_at is not None
        
        # Verify hold was marked confirmed
        db.refresh(sample_hold)
        assert sample_hold.status == HoldStatus.CONFIRMED
    
    def test_confirm_booking_hold_not_found(self, db, sample_hold):
        """Test confirmation fails when hold doesn't exist."""
        service = BookingService(db)
        
        with pytest.raises(HoldNotFound):
            service.confirm_booking(
                hold_id=uuid4(),
                user_id=uuid4(),
            )


class TestBookingServiceValidation:
    """Test booking confirmation validation."""
    
    def test_confirm_booking_expired_hold(self, db, sample_event):
        """Test confirmation fails for expired hold."""
        from app.repositories import HoldRepository
        
        repo = HoldRepository(db)
        hold = Hold(
            event_id=sample_event.id,
            user_id=uuid4(),
            seat_count=5,
            status=HoldStatus.ACTIVE,
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        repo.save(hold)
        db.commit()
        
        service = BookingService(db)
        with pytest.raises(HoldExpired):
            service.confirm_booking(hold_id=hold.id, user_id=hold.user_id)
    
    def test_confirm_booking_already_confirmed(self, db, sample_event):
        """Test confirmation fails for already confirmed hold."""
        from app.repositories import HoldRepository
        
        repo = HoldRepository(db)
        hold = Hold(
            event_id=sample_event.id,
            user_id=uuid4(),
            seat_count=5,
            status=HoldStatus.CONFIRMED,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        repo.save(hold)
        db.commit()
        
        service = BookingService(db)
        with pytest.raises(InvalidHoldStatus):
            service.confirm_booking(hold_id=hold.id, user_id=hold.user_id)
    
    def test_confirm_booking_expired_status(self, db, sample_event):
        """Test confirmation fails for expired-status hold."""
        from app.repositories import HoldRepository
        
        repo = HoldRepository(db)
        hold = Hold(
            event_id=sample_event.id,
            user_id=uuid4(),
            seat_count=5,
            status=HoldStatus.EXPIRED,
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        repo.save(hold)
        db.commit()
        
        service = BookingService(db)
        with pytest.raises(InvalidHoldStatus):
            service.confirm_booking(hold_id=hold.id, user_id=hold.user_id)


class TestBookingServiceDuplicatePrevention:
    """Test prevention of duplicate bookings.
    **CRITICAL**: Ensures user can only have one confirmed booking per event.
    """
    
    def test_confirm_booking_duplicate_fails(self, db, sample_event, sample_booking):
        """Test confirmation fails when user already has confirmed booking.
        
        This is the critical duplicate prevention test.
        Database unique constraint: UNIQUE(event_id, user_id) WHERE status='CONFIRMED'
        """
        from app.repositories import HoldRepository
        
        # Create second hold for same user, same event
        repo = HoldRepository(db)
        hold2 = Hold(
            event_id=sample_event.id,
            user_id=sample_booking.user_id,  # SAME USER
            seat_count=5,
            status=HoldStatus.ACTIVE,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        repo.save(hold2)
        db.commit()
        
        # Try to confirm second booking → should fail
        service = BookingService(db)
        with pytest.raises(DuplicateBooking):
            service.confirm_booking(
                hold_id=hold2.id,
                user_id=sample_booking.user_id,
            )
    
    def test_confirm_booking_different_users_allowed(self, db, sample_event):
        """Test different users can both book same event."""
        from app.repositories import HoldRepository
        
        repo = HoldRepository(db)
        service = BookingService(db)
        
        # User 1 creates and confirms booking
        user1_id = uuid4()
        hold1 = Hold(
            event_id=sample_event.id,
            user_id=user1_id,
            seat_count=5,
            status=HoldStatus.ACTIVE,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        repo.save(hold1)
        db.commit()
        
        booking1 = service.confirm_booking(hold_id=hold1.id, user_id=user1_id)
        db.commit()
        
        # User 2 creates and confirms booking (should succeed)
        user2_id = uuid4()
        hold2 = Hold(
            event_id=sample_event.id,
            user_id=user2_id,
            seat_count=5,
            status=HoldStatus.ACTIVE,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
        )
        repo.save(hold2)
        db.commit()
        
        booking2 = service.confirm_booking(hold_id=hold2.id, user_id=user2_id)
        
        assert booking1.user_id != booking2.user_id
        assert booking1.event_id == booking2.event_id


class TestBookingServiceGet:
    """Test booking retrieval."""
    
    def test_get_booking_success(self, db, sample_booking):
        """Test successful booking retrieval."""
        service = BookingService(db)
        
        booking = service.get_booking(sample_booking.id)
        
        assert booking.id == sample_booking.id
        assert booking.status == BookingStatus.CONFIRMED
    
    def test_get_booking_not_found(self, db):
        """Test retrieval of non-existent booking."""
        service = BookingService(db)
        
        with pytest.raises(BookingNotFound):
            service.get_booking(uuid4())


class TestBookingServiceCancellation:
    """Test booking cancellation (soft delete)."""
    
    def test_cancel_booking_success(self, db, sample_booking):
        """Test successful booking cancellation."""
        service = BookingService(db)
        
        canceled = service.cancel_booking(
            booking_id=sample_booking.id,
            user_id=sample_booking.user_id,
        )
        
        assert canceled.status == BookingStatus.CANCELED
        assert canceled.canceled_at is not None
    
    def test_cancel_booking_not_found(self, db):
        """Test cancellation of non-existent booking."""
        service = BookingService(db)
        
        with pytest.raises(BookingNotFound):
            service.cancel_booking(booking_id=uuid4(), user_id=uuid4())
    
    def test_cancel_booking_unauthorized(self, db, sample_booking):
        """Test cancellation fails for different user."""
        service = BookingService(db)
        
        with pytest.raises(ApplicationException):
            service.cancel_booking(
                booking_id=sample_booking.id,
                user_id=uuid4(),  # Different user
            )
    
    def test_cancel_booking_already_canceled(self, db, sample_booking):
        """Test cancellation fails when already canceled."""
        from app.repositories import BookingRepository
        
        repo = BookingRepository(db)
        sample_booking = repo.get_for_update(sample_booking.id)
        repo.mark_canceled(sample_booking)
        db.commit()
        
        service = BookingService(db)
        with pytest.raises(BookingAlreadyCanceled):
            service.cancel_booking(
                booking_id=sample_booking.id,
                user_id=sample_booking.user_id,
            )
