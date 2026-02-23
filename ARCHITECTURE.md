# Ticket Booking System - Architecture Documentation

## 1. System Philosophy

This is a **consistency-first system**, not CRUD. The core requirement is **never oversell seats**.

### Core Guarantees
- ✅ Concurrency safe
- ✅ No seat overbooking (serialized at event level)
- ✅ Temporary seat reservation (5 minutes with auto-expiry)
- ✅ Prevent duplicate bookings per user
- ✅ Full audit trail (soft deletes, immutable history)
- ✅ Business rules enforced at both application and DB level

---

## 2. Layered Architecture (MANDATORY)

```
┌─────────────────────────────────────┐
│   Controller Layer (FastAPI Routes) │  ← HTTP requests, validation, mapping
├─────────────────────────────────────┤
│   Service Layer                     │  ← Business logic, transactions, rules
├─────────────────────────────────────┤
│   DAO Layer (Repositories)          │  ← Query abstractions, no logic
├─────────────────────────────────────┤
│   Database (PostgreSQL + SQLAlchemy)│  ← Constraints, locking, indexes
└─────────────────────────────────────┘
```

### Responsibility Boundaries

#### Controller Layer
- **Only**: HTTP request validation, mapping to/from DTOs
- **Never**: Business logic, transactions, database calls
- Returns proper HTTP status codes

#### Service Layer
- **Only**: Business logic, transaction boundaries, concurrency control
- Manages session lifecycle
- Applies business rules (availability, expiry, duplicates)
- Throws domain exceptions

#### DAO Layer (Repositories)
- **Only**: Pure query abstractions
- No business logic
- Handles `FOR UPDATE` locking when needed
- Returns domain objects

#### Database Layer
- Enforces constraints (unique indexes, foreign keys)
- Provides row-level locking
- Aggregation queries optimized

---

## 3. Core Domain Model

### Event
```
id (UUID, PK)
name (str)
date (datetime)
location (str)
total_seats (int)
created_at (timestamp)
updated_at (timestamp)
```

**Role**: Represents an event with total seat capacity. Locked during availability calculations.

---

### Hold
```
id (UUID, PK)
event_id (UUID, FK)
user_id (UUID)
seat_count (int)
status (ACTIVE | EXPIRED | CONFIRMED)
expires_at (timestamp)
created_at (timestamp)
```

**Role**: Temporary seat reservation lasting 5 minutes.

**States**:
- `ACTIVE` → Hold is valid, not yet expired
- `EXPIRED` → Hold exceeded 5 minutes (marked by scheduler)
- `CONFIRMED` → Hold converted to booking

**Critical Index**:
```sql
CREATE INDEX idx_holds_event_active
ON holds(event_id, status, expires_at)
WHERE status = 'ACTIVE'
```

---

### Booking
```
id (UUID, PK)
event_id (UUID, FK)
user_id (UUID)
seat_count (int)
status (CONFIRMED | CANCELED)
hold_id (UUID, FK, nullable)
created_at (timestamp)
canceled_at (timestamp, nullable)
```

**Role**: Permanent seat booking.

**States**:
- `CONFIRMED` → Seats are sold
- `CANCELED` → Soft-deleted, seats become available

**Critical Constraint** (UNIQUE partial index):
```sql
CREATE UNIQUE INDEX idx_bookings_user_event_confirmed
ON bookings(event_id, user_id)
WHERE status = 'CONFIRMED'
```

Why? Prevents user from having multiple confirmed bookings for same event.

---

## 4. Critical Concurrency Pattern: Hold → Confirm

### Why This Pattern?

**Problem**: Two users simultaneously trying to book last 50 seats.
```
User A: "I want 40 seats"
User B: "I want 40 seats"
(Both see 80 seats available due to race condition)
Result: OVERBOOKING ❌
```

**Solution**: Two-phase commit with row-level locking.

### Phase 1: HOLD Seats (POST /v1/holds)

```python
def create_hold(user_id, event_id, seats):
    with session.begin():  # Begin transaction
        event = event_repo.get_for_update(event_id)  # Lock event row
        
        available = event_repo.calculate_available(event_id)
        if available < seats:
            raise SeatsUnavailable()
        
        hold = Hold(
            event_id=event_id,
            user_id=user_id,
            seat_count=seats,
            status='ACTIVE',
            expires_at=now() + 5min
        )
        
        hold_repo.save(hold)
    # Transaction commits, lock releases
    
    return hold
```

**Key Points**:
- `FOR UPDATE` lock prevents other transactions from reading stale availability
- Availability = `total_seats - SUM(confirmed bookings) - SUM(active holds)`
- Lock held only during calculation
- Hold expires in 5 minutes (lazy expiry + scheduler cleanup)

### Phase 2: CONFIRM Booking (POST /v1/bookings/confirm)

```python
def confirm_booking(hold_id, user_id):
    with session.begin():  # Begin transaction
        hold = hold_repo.get_for_update(hold_id)  # Lock hold row
        
        # Validate hold
        if hold.status != 'ACTIVE':
            raise InvalidHoldStatus()
        if hold.expires_at <= now():
            raise HoldExpired()
        
        # Check no existing confirmed booking
        existing = booking_repo.get_confirmed(hold.event_id, user_id)
        if existing:
            raise DuplicateBooking()
        
        # Create booking
        booking = Booking(
            event_id=hold.event_id,
            user_id=user_id,
            seat_count=hold.seat_count,
            status='CONFIRMED',
            hold_id=hold_id
        )
        
        # Mark hold as confirmed
        hold.status = 'CONFIRMED'
        
        booking_repo.save(booking)
        hold_repo.update(hold)
    # Unique constraint on (event_id, user_id, status='CONFIRMED') prevents double-insert
    
    return booking
```

**Key Points**:
- Duplicate booking prevented by unique index + transaction
- Hold automatically not available for other users (status = CONFIRMED)
- Booking row is immutable once created (no updates except cancellation)

---

## 5. Availability Calculation

**Formula**:
```
available_seats = total_seats - confirmed_seats - active_holds
```

**Query** (single roundtrip, optimized):
```sql
SELECT 
    e.total_seats,
    COALESCE(SUM(CASE WHEN b.status = 'CONFIRMED' THEN b.seat_count ELSE 0 END), 0) as confirmed_seats,
    COALESCE(SUM(CASE WHEN h.status = 'ACTIVE' AND h.expires_at > NOW() THEN h.seat_count ELSE 0 END), 0) as held_seats
FROM events e
LEFT JOIN bookings b ON b.event_id = e.id
LEFT JOIN holds h ON h.event_id = e.id
WHERE e.id = ?
GROUP BY e.id, e.total_seats
```

**Must return**:
```json
{
    "eventId": "...",
    "totalSeats": 100,
    "confirmedSeats": 60,
    "heldSeats": 20,
    "availableSeats": 20
}
```

---

## 6. Hold Expiry (Two-Layer Safety)

### Layer 1: Lazy Expiration (Mandatory)

During any hold-related query:
```sql
WHERE status = 'ACTIVE'
AND expires_at > NOW()
```

Expired holds are automatically ignored.

### Layer 2: Background Cleanup Job (Required)

**What**: APScheduler job runs every 60 seconds

**Why**: Keeps data clean, auditable, and optimizes queries

**Job Logic**:
```python
def expire_old_holds():
    """Mark holds as EXPIRED if past expiry time."""
    with session.begin():
        expired_count = db.query(Hold)\
            .filter(Hold.status == 'ACTIVE')\
            .filter(Hold.expires_at <= func.now())\
            .update({Hold.status: 'EXPIRED'})
        
        session.commit()
        logger.info(f"Expired {expired_count} holds")
```

**Result**: `available_seats` automatically increases as holds expire.

---

## 7. Booking Cancellation (Soft Delete)

### Why Soft Delete?

1. **Audit Trail**: Never lose data
2. **Reconciliation**: Can trace who canceled and when
3. **Analytics**: Track cancellation patterns

### Flow

```python
def cancel_booking(booking_id, user_id):
    with session.begin():
        booking = booking_repo.get_for_update(booking_id)
        
        if booking.user_id != user_id:
            raise Unauthorized()
        
        if booking.status == 'CANCELED':
            raise BookingAlreadyCanceled()
        
        booking.status = 'CANCELED'
        booking.canceled_at = now()
        
        booking_repo.update(booking)
    
    return booking
```

**Important**: Availability calculation only counts `status = 'CONFIRMED'` bookings, so canceling a booking automatically frees seats.

---

## 8. Database Constraints (CRITICAL - NOT Optional)

### Constraint 1: Prevent Double Booking

```sql
CREATE UNIQUE INDEX idx_bookings_user_event_confirmed
ON bookings(event_id, user_id)
WHERE status = 'CONFIRMED'
```

**Why Unique Index?**
- Enforces at DB level (not application level)
- Concurrent transactions cannot bypass this
- Prevents race conditions

### Constraint 2: Prevent Negative Total Seats

```sql
ALTER TABLE events
ADD CONSTRAINT check_total_seats_positive
CHECK (total_seats > 0)
```

### Constraint 3: Foreign Key Integrity

```sql
ALTER TABLE holds
ADD CONSTRAINT fk_holds_event
FOREIGN KEY (event_id) REFERENCES events(id)

ALTER TABLE bookings
ADD CONSTRAINT fk_bookings_event
FOREIGN KEY (event_id) REFERENCES events(id)

ALTER TABLE bookings
ADD CONSTRAINT fk_bookings_hold
FOREIGN KEY (hold_id) REFERENCES holds(id)
```

---

## 9. Performance Optimization

### Indexes (MANDATORY)

```sql
-- Fast hold lookups by event
CREATE INDEX idx_holds_event_active
ON holds(event_id, status, expires_at)
WHERE status = 'ACTIVE'

-- Fast booking lookups by event
CREATE INDEX idx_bookings_event_status
ON bookings(event_id, status)

-- Fast availability calculations
CREATE INDEX idx_holds_expires_at
ON holds(expires_at)
WHERE status = 'ACTIVE'
```

### Query Optimization

- **Availability**: Single aggregation query (no N+1)
- **Hold Check**: PK lookup + expiry filter
- **Booking Check**: Unique index lookup

---

## 10. Exception Hierarchy

All exceptions extend `ApplicationException` with:
- `message`: Human-readable error
- `code`: Machine-readable code
- `status_code`: HTTP status

### Key Exceptions

| Exception | HTTP Status | Meaning |
|-----------|-------------|---------|
| `SeatsUnavailable` | 409 | Not enough seats available |
| `HoldExpired` | 409 | Hold exceeded 5 minutes |
| `DuplicateBooking` | 409 | User already booked event |
| `EventNotFound` | 404 | Event doesn't exist |
| `HoldNotFound` | 404 | Hold doesn't exist |
| `BookingNotFound` | 404 | Booking doesn't exist |
| `InvalidSeatCount` | 400 | Seat count ≤ 0 |

---

## 11. Transaction Boundaries (CRITICAL)

**Rule**: Transaction begins in Service, committed by SQLAlchemy context manager.

**Pattern**:
```python
def service_method(self):
    with self.session.begin():  # BEGIN TRANSACTION
        # Acquire locks
        # Read/write operations
        # Raise exceptions if needed
        pass  # COMMIT automatically
    # Session released by caller (Controller dependency injection)
```

**Why**?
- Atomic operations
- Row locks held for minimal time
- Automatic rollback on exception

---

## 12. API Response Format

### Success Response
```json
{
    "data": { ... },
    "status": "success"
}
```

### Error Response
```json
{
    "error": {
        "message": "...",
        "code": "ERROR_CODE",
        "status": "error"
    }
}
```

---

## 13. Testing Strategy

### Unit Tests (Mock DAO)
- Expiry logic
- Overbooking prevention
- Duplicate booking prevention
- Edge cases (0 seats, negative seats, etc.)

### Integration Tests (Real DB)
- Transaction boundaries
- Constraint enforcement
- Availability calculations

### Concurrency Tests (Thread Pool)
- Simulate 20 threads
- 100 seats available
- 20 users × 10-seat requests
- Assert: `confirmed + held ≤ total`

---

## 14. Deployment Checklist

- [ ] PostgreSQL 12+ running
- [ ] `.env` configured with `DATABASE_URL`
- [ ] `pip install -r requirements.txt`
- [ ] `alembic upgrade head` (run migrations)
- [ ] `python -m pytest tests/` (run tests)
- [ ] `uvicorn app.main:app --host 0.0.0.0 --port 8000`

---

## 15. Key Design Principles (Why This Architecture?)

| Principle | Implementation | Benefit |
|-----------|----------------|---------|
| **Consistency First** | Transaction + row locking | No overbooking |
| **Fail Fast** | Explicit exceptions | Clear error handling |
| **Audit Trail** | Soft deletes | Complete history |
| **Scalability** | Indexed queries | O(log n) lookups |
| **Concurrency Safe** | DB constraints + app logic | Race condition proof |
| **Testable** | Dependency injection | Mock-friendly |
| **Maintainable** | Layered architecture | Clear separation |

---

## 16. Common Pitfalls (DO NOT DO)

❌ **Delete booking rows** → Use soft delete
❌ **Update seat availability after booking** → Calculate dynamically
❌ **Hold expiry in service without scheduler** → Data becomes stale
❌ **Lock entire table** → Lock only event row
❌ **Trust application-only validation** → Enforce at DB level
❌ **N+1 queries** → Use aggregation, single query
❌ **Transaction after service** → Begin in service, end in context manager

---

## 17. Future Improvements (Staff-Level Bonus)

- **Redis Hold TTL**: Move hold expiry to Redis with automatic TTL
- **Distributed Locking**: Use Redlock for multi-instance deployments
- **Event Sourcing**: Immutable event log for audit
- **CQRS**: Separate read/write models for availability
- **Partitioning**: Shard events by date range
- **Async Confirmation**: Publish booking confirmed event to message queue

---

## 18. Glossary

- **Hold**: Temporary 5-minute seat reservation
- **Booking**: Permanent seat purchase
- **Availability**: Seats not confirmed or held (with valid expiry)
- **FOR UPDATE**: Row-level lock in SQL to prevent race conditions
- **Soft Delete**: Mark row as deleted (status = CANCELED) instead of removing
- **Lazy Expiry**: Check expiry at query time
- **Eager Cleanup**: Background job updates status to EXPIRED

---

**Last Updated**: 23 February 2026
**Status**: Ready for Layer 2 (Database Models)
