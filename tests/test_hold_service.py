"""
Tests for HoldService - Hold (temporary reservation) operations.
**CRITICAL**: Tests for concurrency control and row-level locking.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from app.services import HoldService
from app.exceptions import (
    EventNotFound, SeatsUnavailable, InvalidSeatCount,
    HoldNotFound, HoldExpired
)
from app.models import Hold, HoldStatus


class TestHoldServiceCreateBasic:
    """Test basic hold creation."""
    
    def test_create_hold_success(self, db, sample_event):
        """Test successful hold creation."""
        service = HoldService(db)
        user_id = uuid4()
        
        hold = service.create_hold(
            event_id=sample_event.id,
            user_id=user_id,
            seat_count=5,
        )
        
        assert hold.id is not None
        assert hold.event_id == sample_event.id
        assert hold.user_id == user_id
        assert hold.seat_count == 5
        assert hold.status == HoldStatus.ACTIVE
        assert hold.expires_at is not None
        
        # Check expiry is ~5 minutes
        expiry_delta = (hold.expires_at - datetime.now(timezone.utc)).total_seconds()
        assert 290 < expiry_delta < 310  # ~5 minutes
    
    def test_create_hold_event_not_found(self, db):
        """Test hold creation fails when event doesn't exist."""
        service = HoldService(db)
        
        with pytest.raises(EventNotFound):
            service.create_hold(
                event_id=uuid4(),
                user_id=uuid4(),
                seat_count=5,
            )
    
    def test_create_hold_invalid_seat_count(self, db, sample_event):
        """Test hold creation fails with invalid seat count."""
        service = HoldService(db)
        
        with pytest.raises(InvalidSeatCount):
            service.create_hold(
                event_id=sample_event.id,
                user_id=uuid4(),
                seat_count=0,
            )
        
        with pytest.raises(InvalidSeatCount):
            service.create_hold(
                event_id=sample_event.id,
                user_id=uuid4(),
                seat_count=-5,
            )


class TestHoldServiceAvailability:
    """Test availability calculation during holds."""
    
    def test_create_hold_insufficient_seats(self, db, sample_event):
        """Test hold creation fails when insufficient seats."""
        service = HoldService(db)
        
        # Try to hold 150 seats but only 100 available
        with pytest.raises(SeatsUnavailable):
            service.create_hold(
                event_id=sample_event.id,
                user_id=uuid4(),
                seat_count=150,
            )
    
    def test_create_hold_exactly_available(self, db, sample_event):
        """Test hold succeeds when requesting exactly available seats."""
        service = HoldService(db)
        
        hold = service.create_hold(
            event_id=sample_event.id,
            user_id=uuid4(),
            seat_count=100,  # Exactly total_seats
        )
        
        assert hold.seat_count == 100
        
        # Second hold should fail (no seats left)
        with pytest.raises(SeatsUnavailable):
            service.create_hold(
                event_id=sample_event.id,
                user_id=uuid4(),
                seat_count=1,
            )
    
    def test_create_hold_respects_existing_bookings(self, db, sample_event, sample_booking):
        """Test hold respects existing confirmed bookings.
        
        Event: 100 total seats
        Booking: 5 seats (confirmed)
        Hold (from sample_booking fixture): 5 seats (held)
        Available: 90 seats (100 - 5 confirmed - 5 held)
        
        Hold attempt: 91 seats → FAIL
        Hold attempt: 90 seats → SUCCESS
        """
        service = HoldService(db)
        
        # Should fail: only 90 available (100 - 5 booked - 5 held)
        with pytest.raises(SeatsUnavailable):
            service.create_hold(
                event_id=sample_event.id,
                user_id=uuid4(),
                seat_count=91,
            )
        
        # Should succeed
        hold = service.create_hold(
            event_id=sample_event.id,
            user_id=uuid4(),
            seat_count=90,
        )
        
        assert hold.seat_count == 90


class TestHoldServiceGet:
    """Test hold retrieval."""
    
    def test_get_hold_success(self, db, sample_hold):
        """Test successful hold retrieval."""
        service = HoldService(db)
        
        hold = service.get_hold(sample_hold.id)
        
        assert hold.id == sample_hold.id
        assert hold.status == HoldStatus.ACTIVE
    
    def test_get_hold_not_found(self, db):
        """Test retrieval of non-existent hold."""
        service = HoldService(db)
        
        with pytest.raises(HoldNotFound):
            service.get_hold(uuid4())
    
    def test_get_expired_hold(self, db, sample_event):
        """Test retrieval of expired hold fails.
        
        Lazy expiry: If expires_at <= now, should raise HoldExpired.
        """
        from app.repositories import HoldRepository
        
        # Create expired hold (manually in DB)
        repo = HoldRepository(db)
        hold = Hold(
            event_id=sample_event.id,
            user_id=uuid4(),
            seat_count=5,
            status=HoldStatus.ACTIVE,
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),  # Already expired
        )
        repo.save(hold)
        db.commit()
        
        # Try to get it → should fail
        service = HoldService(db)
        with pytest.raises(HoldExpired):
            service.get_hold(hold.id)


class TestHoldServiceValidation:
    """Test hold validation for booking confirmation."""
    
    def test_validate_hold_success(self, db, sample_hold):
        """Test valid hold passes validation."""
        service = HoldService(db)
        
        validated = service.validate_hold(sample_hold.id)
        
        assert validated.id == sample_hold.id
        assert validated.status == HoldStatus.ACTIVE
    
    def test_validate_hold_expired(self, db, sample_event):
        """Test expired hold fails validation."""
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
        
        service = HoldService(db)
        with pytest.raises(HoldExpired):
            service.validate_hold(hold.id)
    
    def test_validate_hold_already_confirmed(self, db, sample_event):
        """Test confirmed hold fails validation."""
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
        
        service = HoldService(db)
        with pytest.raises(HoldExpired):
            service.validate_hold(hold.id)
