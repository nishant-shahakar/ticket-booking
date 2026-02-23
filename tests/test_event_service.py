"""
Tests for EventService - Event management operations.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from app.services import EventService
from app.exceptions import EventNotFound
from app.models import Event


class TestEventServiceCreate:
    """Test event creation."""
    
    def test_create_event_success(self, db):
        """Test successful event creation."""
        service = EventService(db)
        
        event = service.create_event(
            name="Concert",
            date=datetime.now(timezone.utc) + timedelta(days=30),
            location="Madison Square Garden",
            total_seats=100,
        )
        db.flush()  # Flush to ensure ID is generated
        
        assert event.id is not None
        assert event.name == "Concert"
        assert event.total_seats == 100
        assert event.created_at is not None
    
    def test_create_event_invalid_seat_count(self, db):
        """Test creation fails with invalid seat count."""
        service = EventService(db)
        
        with pytest.raises(ValueError, match="total_seats must be positive"):
            service.create_event(
                name="Concert",
                date=datetime.now(timezone.utc),
                location="Venue",
                total_seats=-10,
            )
    
    def test_create_event_zero_seats(self, db):
        """Test creation fails with zero seats."""
        service = EventService(db)
        
        with pytest.raises(ValueError):
            service.create_event(
                name="Concert",
                date=datetime.now(timezone.utc),
                location="Venue",
                total_seats=0,
            )


class TestEventServiceGet:
    """Test event retrieval."""
    
    def test_get_event_success(self, db, sample_event):
        """Test successful event retrieval."""
        service = EventService(db)
        
        event = service.get_event(sample_event.id)
        
        assert event.id == sample_event.id
        assert event.name == sample_event.name
    
    def test_get_event_not_found(self, db):
        """Test retrieval of non-existent event."""
        service = EventService(db)
        
        with pytest.raises(EventNotFound):
            service.get_event(uuid4())


class TestEventServiceUpdate:
    """Test event updates."""
    
    def test_update_event_success(self, db, sample_event):
        """Test successful event update."""
        service = EventService(db)
        
        updated = service.update_event(
            sample_event.id,
            name="Updated Concert",
            total_seats=200,
        )
        
        assert updated.name == "Updated Concert"
        assert updated.total_seats == 200
    
    def test_update_event_partial(self, db, sample_event):
        """Test partial event update."""
        service = EventService(db)
        
        updated = service.update_event(
            sample_event.id,
            name="New Name",
        )
        
        assert updated.name == "New Name"
        assert updated.total_seats == sample_event.total_seats
    
    def test_update_event_invalid_seats(self, db, sample_event):
        """Test update fails with invalid seat count."""
        service = EventService(db)
        
        with pytest.raises(ValueError):
            service.update_event(sample_event.id, total_seats=0)


class TestEventServiceDelete:
    """Test event soft deletion."""
    
    def test_delete_event_success(self, db, sample_event):
        """Test successful event soft deletion."""
        service = EventService(db)
        
        deleted = service.delete_event(sample_event.id)
        
        assert deleted.deleted_at is not None
    
    def test_delete_event_not_found(self, db):
        """Test deletion of non-existent event."""
        service = EventService(db)
        
        with pytest.raises(EventNotFound):
            service.delete_event(uuid4())


class TestEventServiceAvailability:
    """Test seat availability calculation."""
    
    def test_availability_all_seats_free(self, db, sample_event):
        """Test availability when all seats are free."""
        service = EventService(db)
        
        availability = service.get_availability(sample_event.id)
        
        assert availability["total_seats"] == 100
        assert availability["confirmed_seats"] == 0
        assert availability["held_seats"] == 0
        assert availability["available_seats"] == 100
    
    def test_availability_with_bookings(self, db, sample_event, sample_booking):
        """Test availability with confirmed bookings.
        
        Note: sample_booking also creates sample_hold (5 held seats).
        Total used: 5 booked + 5 held = 10, available: 90
        """
        service = EventService(db)
        
        availability = service.get_availability(sample_event.id)
        
        assert availability["confirmed_seats"] == 5
        assert availability["held_seats"] == 5  # From sample_hold dependency
        assert availability["available_seats"] == 90  # 100 - 5 - 5
    
    def test_availability_with_holds(self, db, sample_event, sample_hold):
        """Test availability with active holds."""
        service = EventService(db)
        
        availability = service.get_availability(sample_event.id)
        
        assert availability["held_seats"] == 5
        assert availability["available_seats"] == 95
    
    def test_availability_event_not_found(self, db):
        """Test availability for non-existent event."""
        service = EventService(db)
        
        with pytest.raises(EventNotFound):
            service.get_availability(uuid4())
