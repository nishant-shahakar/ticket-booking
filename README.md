# Ticket Booking System

A production-ready ticket booking system built with FastAPI, SQLAlchemy, and PostgreSQL. Features concurrency-safe Hold → Confirm architecture with automatic expiry management.

## 🚀 Quick Start with Docker

```bash
# Start everything with one command
docker-compose up

# API available at: http://localhost:8000/docs
# PostgreSQL at: localhost:5432
```

That's it! Both services will be running with automatic migrations.

## ✨ Features

- **Hold System**: Reserve seats for 5 minutes with automatic expiry
- **Two-Phase Commit**: Hold → Confirm booking workflow
- **Concurrency Safe**: Row-level locking prevents race conditions
- **Duplicate Prevention**: Database unique constraint enforces single booking per user
- **Soft Deletes**: Full audit trail with soft-delete pattern
- **Background Jobs**: Automatic hold expiry cleanup
- **Production Ready**: Docker, Docker Compose, comprehensive tests
- **Full Test Coverage**: 39 unit tests, all passing ✅

## 📋 API Endpoints

### Events
```
POST   /v1/events              - Create event
GET    /v1/events/{id}         - Get event details
PUT    /v1/events/{id}         - Update event
DELETE /v1/events/{id}         - Delete event
GET    /v1/events/{id}/availability - Check available seats
```

### Holds
```
POST /v1/holds     - Create 5-minute hold (reserve seats)
GET  /v1/holds/{id} - Get hold details
```

### Bookings
```
POST   /v1/bookings/confirm    - Confirm booking from hold
GET    /v1/bookings/{id}       - Get booking details
DELETE /v1/bookings/{id}       - Cancel booking
```

## 🐳 Docker Setup

### Using Docker Compose

```bash
# Start services
docker-compose up

# View logs
docker-compose logs -f api

# Run tests
docker-compose exec api pytest tests/ -v

# Access PostgreSQL
docker-compose exec postgres psql -U ticket_user -d ticket_booking

# Stop services
docker-compose down
```

### Using Helper Script (macOS/Linux)

```bash
./docker-helper.sh start          # Start services
./docker-helper.sh logs api       # View logs
./docker-helper.sh test tests/    # Run tests
./docker-helper.sh bash           # Access container shell
./docker-helper.sh psql           # Access PostgreSQL
./docker-helper.sh stop           # Stop services
./docker-helper.sh help           # Show all commands
```

See [DOCKER_SETUP.md](DOCKER_SETUP.md) for complete Docker documentation.

## 💻 Local Development Setup

### Prerequisites
- Python 3.9+
- PostgreSQL 12+
- pip

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your PostgreSQL connection

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

API available at: http://localhost:8000/docs

## 🧪 Testing

### With Docker
```bash
docker-compose exec api pytest tests/ -v
```

### Local Development
```bash
pytest tests/ -v
```

**Test Results:** 39/39 tests passing ✅

See [RUNNING_TESTS.md](RUNNING_TESTS.md) for detailed testing guide.

## 🏗️ Architecture

```
Controller Layer (FastAPI Routes)
           ↓
Service Layer (Business Logic, Transactions)
           ↓
Repository Layer (Data Access)
           ↓
Database Layer (SQLAlchemy Models + PostgreSQL)
           ↓
Background Jobs (APScheduler - Hold Expiry Cleanup)
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation.

## 📚 Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design and patterns
- [DOCKER_SETUP.md](DOCKER_SETUP.md) - Docker/Docker Compose setup
- [RUNNING_TESTS.md](RUNNING_TESTS.md) - Testing guide
- [TESTING_RESULTS.md](TESTING_RESULTS.md) - Test analysis and results
- [STARTUP_GUIDE.md](STARTUP_GUIDE.md) - Development startup guide

## 🔑 Key Design Patterns

### 1. Hold → Confirm Two-Phase Commit
- Create hold to reserve seats for 5 minutes
- Confirm hold to create permanent booking
- Prevents overbooking through atomic transactions

### 2. Row-Level Locking
- `FOR UPDATE` locks prevent concurrent reads of stale data
- Serializes competing requests automatically
- Critical for availability calculations

### 3. Soft Delete Pattern
- Records marked with `deleted_at` instead of physically deleted
- Maintains complete audit trail
- Automatic filtering in all queries

### 4. Unique Constraints
- Database enforces: `UNIQUE(event_id, user_id) WHERE status='CONFIRMED'`
- Prevents duplicate bookings even with race conditions
- Complements application-level validation
