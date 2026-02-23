# Running Tests

## Unit Tests (39 tests - All Passing ✅)

Run all unit tests:
```bash
pytest tests/test_booking_service.py tests/test_event_service.py tests/test_hold_service.py -v
```

Run specific test class:
```bash
pytest tests/test_booking_service.py::TestBookingServiceConfirmBasic -v
```

Run with coverage:
```bash
pytest tests/test_booking_service.py tests/test_event_service.py tests/test_hold_service.py --cov=app --cov-report=html
```

## Test Results Summary

| Test File | Tests | Status |
|-----------|-------|--------|
| test_booking_service.py | 13 | ✅ All passing |
| test_event_service.py | 13 | ✅ All passing |
| test_hold_service.py | 13 | ✅ All passing |
| **Total** | **39** | **✅ All passing** |

## Critical Tests to Understand

### Duplicate Booking Prevention
```bash
pytest tests/test_booking_service.py::TestBookingServiceDuplicatePrevention::test_confirm_booking_duplicate_fails -v
```
Validates that a user cannot have 2 confirmed bookings for the same event, enforced by:
- Service-layer validation
- Database UNIQUE constraint

### Availability Calculation
```bash
pytest tests/test_event_service.py::TestEventServiceAvailability -v
```
Validates that available seats = total - confirmed - held_not_expired

### Concurrency Tests (PostgreSQL Required)
```bash
pytest tests/test_concurrency.py -v  # Requires PostgreSQL, not SQLite
```
**Note**: Concurrency tests are in the repository but require PostgreSQL due to SQLite threading limitations. When running with PostgreSQL, these tests validate:
- 20 concurrent threads cannot exceed event capacity
- Row-level locking prevents race conditions
- Database constraints enforce seat availability

## Setup for Testing

### 1. Install Dependencies
```bash
cd ticket-booking
pip install -r requirements.txt
```

### 2. Configure Database
Testing uses SQLite in-memory by default (no setup needed):
```bash
# Default .env configuration for testing
DATABASE_URL=sqlite:///ticket_booking.db
```

### 3. Run Tests
```bash
pytest tests/ -v
```

## Debugging Failed Tests

### View full error with traceback:
```bash
pytest tests/test_booking_service.py::TestBookingServiceConfirmBasic::test_confirm_booking_success -xvs
```

### Print debug statements:
```bash
pytest tests/test_booking_service.py -xvs --log-cli-level=DEBUG
```

### Stop at first failure:
```bash
pytest tests/ -x
```

## Test Structure

Each test file follows this pattern:

```python
# Test fixtures provide pre-created domain objects
def test_example(self, db, sample_event, sample_booking):
    # Arrange: Create service with test session
    service = BookingService(db)
    
    # Act: Call service method
    result = service.some_operation(sample_booking.id)
    
    # Assert: Verify result
    assert result.status == "SUCCESS"
```

## Key Test Patterns

### Testing Exception Cases
```python
def test_confirm_booking_expired_hold(self, db, sample_event):
    service = BookingService(db)
    
    # Create an expired hold
    expired_hold = Hold(
        event_id=sample_event.id,
        user_id=uuid4(),
        seat_count=5,
        status=HoldStatus.ACTIVE,
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    db.add(expired_hold)
    db.commit()
    
    # Assert exception raised
    with pytest.raises(HoldExpired):
        service.confirm_booking(hold_id=expired_hold.id, user_id=expired_hold.user_id)
```

### Testing Database Constraints
```python
def test_confirm_booking_duplicate_fails(self, db, sample_event, sample_booking):
    """Validates UNIQUE(event_id, user_id) WHERE status='CONFIRMED'"""
    service = BookingService(db)
    
    # Second booking should fail (unique constraint)
    with pytest.raises(DuplicateBooking):
        service.confirm_booking(hold_id=hold2.id, user_id=sample_booking.user_id)
```

## Common Issues & Solutions

### Issue: "can't compare offset-naive and offset-aware datetimes"
**Cause**: SQLite returns naive datetimes  
**Solution**: Tests handle timezone conversions automatically in service layer

### Issue: "ambiguous column name" in availability query
**Cause**: Multiple joins without explicit FROM clause  
**Solution**: Fixed in EventRepository with `.select_from(Event)`

### Issue: Test database not isolated
**Cause**: Previous test data persists  
**Solution**: Each test gets fresh in-memory SQLite database

## Performance

All 39 tests complete in < 1 second:
```
======================== 39 passed in 0.18s =========================
```

## Continuous Integration

For CI/CD pipelines, run:
```bash
pytest tests/ -v --junitxml=test-results.xml --cov=app --cov-report=xml
```
