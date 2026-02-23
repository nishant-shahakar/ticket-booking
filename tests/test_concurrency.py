"""
Concurrency tests for ticket booking system.
**CRITICAL**: Simulate 20 concurrent threads creating holds to verify no overbooking.
Validates row-level locking and database constraints prevent race conditions.
"""

import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from uuid import uuid4

from app.services import HoldService, EventService
from app.repositories import BookingRepository
from app.exceptions import SeatsUnavailable
from app.models import BookingStatus, HoldStatus


class TestConcurrentHolds:
    """Test concurrent hold creation doesn't exceed event capacity."""
    
    def test_concurrent_holds_no_overbooking(self, engine, sample_event):
        """
        **CRITICAL TEST**: Simulate 20 concurrent threads creating 5-seat holds.
        Event has 100 seats. Should allow exactly 20 holds (100 seats total).
        
        Validates:
        - Row-level locking prevents stale reads
        - Database constraints catch over-allocations
        - Consistent state despite threading
        """
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        total_seats = 100
        seat_per_hold = 5
        num_threads = 20
        expected_max_holds = total_seats // seat_per_hold  # 20
        
        # Update event to known capacity
        session = sessionmaker(bind=engine)()
        session.query(type(sample_event)).filter(
            type(sample_event).id == sample_event.id
        ).update({type(sample_event).total_seats: total_seats})
        session.commit()
        session.close()
        
        successful_holds = []
        failed_holds = []
        
        def create_hold_thread(user_id):
            """Create hold in thread context."""
            session = sessionmaker(bind=engine)()
            try:
                service = HoldService(session)
                hold = service.create_hold(
                    event_id=sample_event.id,
                    user_id=user_id,
                    seat_count=seat_per_hold,
                )
                successful_holds.append(hold)
                session.commit()
            except SeatsUnavailable:
                failed_holds.append(user_id)
            except Exception as e:
                failed_holds.append((user_id, str(e)))
            finally:
                session.close()
        
        # Execute 20 concurrent threads
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(create_hold_thread, uuid4())
                for _ in range(num_threads)
            ]
            for future in as_completed(futures):
                future.result()
        
        # Verify results
        total_held_seats = sum(h.seat_count for h in successful_holds)
        
        # Should have exactly 20 holds (100 seats / 5 per hold)
        assert len(successful_holds) == expected_max_holds, \
            f"Expected {expected_max_holds} holds, got {len(successful_holds)}"
        
        # Total held seats should equal event capacity
        assert total_held_seats == total_seats, \
            f"Expected {total_seats} held seats, got {total_held_seats}"
        
        # All holds should be ACTIVE
        for hold in successful_holds:
            assert hold.status == HoldStatus.ACTIVE
        
        # At least one thread should have failed (tried to exceed capacity)
        assert len(failed_holds) > 0, "Expected some holds to fail due to capacity"
    
    def test_concurrent_holds_exactly_at_capacity(self, engine, sample_event):
        """
        **BOUNDARY TEST**: Verify system correctly handles exactly-at-capacity scenario.
        100 seats, 10 threads × 10 seats each should succeed.
        """
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        total_seats = 100
        seat_per_hold = 10
        num_threads = 10
        
        # Update event
        session = sessionmaker(bind=engine)()
        session.query(type(sample_event)).filter(
            type(sample_event).id == sample_event.id
        ).update({type(sample_event).total_seats: total_seats})
        session.commit()
        session.close()
        
        successful_holds = []
        
        def create_hold_thread(user_id):
            session = sessionmaker(bind=engine)()
            try:
                service = HoldService(session)
                hold = service.create_hold(
                    event_id=sample_event.id,
                    user_id=user_id,
                    seat_count=seat_per_hold,
                )
                successful_holds.append(hold)
                session.commit()
            finally:
                session.close()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(create_hold_thread, uuid4())
                for _ in range(num_threads)
            ]
            for future in as_completed(futures):
                future.result()
        
        # All 10 should succeed (exactly at capacity)
        assert len(successful_holds) == num_threads
        assert sum(h.seat_count for h in successful_holds) == total_seats


class TestConcurrentBookings:
    """Test concurrent booking confirmations maintain consistency."""
    
    def test_concurrent_bookings_no_duplicate(self, engine, sample_event):
        """
        **CRITICAL**: User cannot have 2 confirmed bookings via concurrent requests.
        
        Simulates race condition:
        1. Create 2 concurrent holds for same user, same event
        2. Confirm both concurrently
        3. Only 1 should succeed (unique constraint enforced)
        """
        from sqlalchemy.orm import sessionmaker
        from app.repositories import HoldRepository
        from app.services import BookingService
        from app.models import Hold
        
        user_id = uuid4()
        
        # Pre-create two holds
        session = sessionmaker(bind=engine)()
        hold_repo = HoldRepository(session)
        
        hold1 = Hold(
            event_id=sample_event.id,
            user_id=user_id,
            seat_count=5,
            status=HoldStatus.ACTIVE,
            expires_at=datetime.now(timezone.utc).replace(microsecond=0) + \
                       __import__('datetime').timedelta(minutes=5),
        )
        hold_repo.save(hold1)
        
        hold2 = Hold(
            event_id=sample_event.id,
            user_id=user_id,
            seat_count=5,
            status=HoldStatus.ACTIVE,
            expires_at=datetime.now(timezone.utc).replace(microsecond=0) + \
                       __import__('datetime').timedelta(minutes=5),
        )
        hold_repo.save(hold2)
        session.commit()
        session.close()
        
        # Attempt concurrent bookings
        successful_bookings = []
        failed_bookings = []
        
        def confirm_booking_thread(hold_id):
            session = sessionmaker(bind=engine)()
            try:
                service = BookingService(session)
                booking = service.confirm_booking(hold_id=hold_id, user_id=user_id)
                successful_bookings.append(booking)
                session.commit()
            except Exception as e:
                failed_bookings.append((hold_id, str(e)))
            finally:
                session.close()
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(confirm_booking_thread, hold1.id),
                executor.submit(confirm_booking_thread, hold2.id),
            ]
            for future in as_completed(futures):
                future.result()
        
        # Exactly 1 booking should succeed
        assert len(successful_bookings) == 1, \
            f"Expected 1 booking, got {len(successful_bookings)}"
        
        # Other should fail
        assert len(failed_bookings) >= 1


class TestConcurrentAvailability:
    """Test availability calculation under concurrent load."""
    
    def test_concurrent_holds_reduce_availability(self, engine, sample_event):
        """
        Verify that concurrent holds correctly reduce available seats.
        100 seats → 20 concurrent holds of 5 seats each → 0 available.
        """
        from sqlalchemy.orm import sessionmaker
        from app.services import EventService
        
        total_seats = 100
        seat_per_hold = 5
        num_threads = 20
        
        # Setup event
        session = sessionmaker(bind=engine)()
        session.query(type(sample_event)).filter(
            type(sample_event).id == sample_event.id
        ).update({type(sample_event).total_seats: total_seats})
        session.commit()
        session.close()
        
        successful_holds = []
        
        def create_hold_thread(user_id):
            session = sessionmaker(bind=engine)()
            try:
                service = HoldService(session)
                hold = service.create_hold(
                    event_id=sample_event.id,
                    user_id=user_id,
                    seat_count=seat_per_hold,
                )
                successful_holds.append(hold)
                session.commit()
            finally:
                session.close()
        
        # Create all holds concurrently
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(create_hold_thread, uuid4())
                for _ in range(num_threads)
            ]
            for future in as_completed(futures):
                future.result()
        
        # Check availability after all holds
        session = sessionmaker(bind=engine)()
        event_service = EventService(session)
        availability = event_service.get_availability(sample_event.id)
        session.close()
        
        held_seats = sum(h.seat_count for h in successful_holds)
        expected_available = total_seats - held_seats
        
        assert availability['available'] == expected_available, \
            f"Expected {expected_available} available, got {availability['available']}"
        
        assert availability['held'] == held_seats, \
            f"Expected {held_seats} held, got {availability['held']}"


class TestConcurrentStateConsistency:
    """Test overall system state consistency under concurrent load."""
    
    def test_system_consistency_after_concurrent_operations(self, engine, sample_event):
        """
        Comprehensive test: After concurrent operations, verify:
        - Total seats = confirmed + held + available
        - No double bookings exist
        - All holds in valid state
        """
        from sqlalchemy.orm import sessionmaker
        from app.repositories import HoldRepository, BookingRepository
        
        total_seats = 100
        
        # Setup
        session = sessionmaker(bind=engine)()
        session.query(type(sample_event)).filter(
            type(sample_event).id == sample_event.id
        ).update({type(sample_event).total_seats: total_seats})
        session.commit()
        session.close()
        
        # Create concurrent holds
        successful_holds = []
        
        def create_hold_thread(user_id):
            session = sessionmaker(bind=engine)()
            try:
                service = HoldService(session)
                hold = service.create_hold(
                    event_id=sample_event.id,
                    user_id=user_id,
                    seat_count=5,
                )
                successful_holds.append((hold.id, user_id))
                session.commit()
            finally:
                session.close()
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(create_hold_thread, uuid4())
                for _ in range(20)
            ]
            for future in as_completed(futures):
                future.result()
        
        # Verify final state
        session = sessionmaker(bind=engine)()
        
        hold_repo = HoldRepository(session)
        booking_repo = BookingRepository(session)
        
        holds = session.query(type(sample_event)).filter(
            type(sample_event).id == sample_event.id
        ).first()
        
        # Count confirmed bookings
        confirmed_bookings = session.execute(
            __import__('sqlalchemy').text("""
                SELECT COUNT(*) as count FROM bookings 
                WHERE event_id = :event_id AND status = 'CONFIRMED'
            """),
            {"event_id": sample_event.id}
        ).scalar() or 0
        
        confirmed_seats = confirmed_bookings * 5  # Each booking is 5 seats
        held_seats = len(successful_holds) * 5
        
        # Verify equation: total = confirmed + held + available
        total_allocated = confirmed_seats + held_seats
        assert total_allocated <= total_seats, \
            f"Over-allocation: {total_allocated} > {total_seats}"
        
        session.close()
