# Getting Started with Ticket Booking System

## 🚀 Fastest Way to Get Started (5 minutes)

### Prerequisites
- Docker and Docker Compose installed on your system

### Step 1: Start the System
```bash
cd ticket-booking
docker-compose up
```

Wait for both services to show "healthy" status.

### Step 2: Access the API
Open your browser and go to: **http://localhost:8000/docs**

You'll see the Swagger UI with all API endpoints.

### Step 3: Try the API

#### Create an Event
```bash
curl -X POST "http://localhost:8000/v1/events" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Summer Concert",
    "date": "2026-06-15T19:00:00Z",
    "location": "Central Park",
    "total_seats": 100
  }'
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Summer Concert",
  "total_seats": 100,
  ...
}
```

Save the `id` for next steps.

#### Check Availability
```bash
curl "http://localhost:8000/v1/events/{event_id}/availability"
```

Response:
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "total_seats": 100,
  "confirmed_seats": 0,
  "held_seats": 0,
  "available_seats": 100
}
```

#### Create a Hold (Reserve Seats)
```bash
curl -X POST "http://localhost:8000/v1/holds" \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "{event_id}",
    "user_id": "123e4567-e89b-12d3-a456-426614174000",
    "seat_count": 5
  }'
```

Response:
```json
{
  "id": "hold_id_here",
  "status": "ACTIVE",
  "expires_at": "2026-02-23T22:30:00Z",
  ...
}
```

Save the `hold_id`.

#### Confirm Booking (From Hold)
```bash
curl -X POST "http://localhost:8000/v1/bookings/confirm" \
  -H "Content-Type: application/json" \
  -d '{
    "hold_id": "{hold_id}",
    "user_id": "123e4567-e89b-12d3-a456-426614174000"
  }'
```

Response:
```json
{
  "id": "booking_id_here",
  "status": "CONFIRMED",
  ...
}
```

**That's it!** You've created an event, held seats, and confirmed a booking.

## 📊 System Status

Check if everything is running:
```bash
docker-compose ps
```

Expected output:
```
NAME                    STATUS
ticket_booking_db       Up X minutes (healthy)
ticket_booking_api      Up X minutes (healthy)
```

## 🔍 Useful Docker Commands

### View Logs
```bash
# API logs
docker-compose logs -f api

# Database logs
docker-compose logs -f postgres

# Last 100 lines
docker-compose logs --tail=100 api
```

### Access Services

#### PostgreSQL CLI
```bash
docker-compose exec postgres psql -U ticket_user -d ticket_booking
```

Inside psql:
```sql
-- View events
SELECT * FROM events;

-- View holds
SELECT * FROM holds;

-- View bookings
SELECT * FROM bookings;

-- Exit
\q
```

#### API Container Shell
```bash
docker-compose exec api /bin/bash
```

### Run Tests
```bash
# All tests
docker-compose exec api pytest tests/ -v

# Specific test
docker-compose exec api pytest tests/test_booking_service.py::TestBookingServiceConfirmBasic -v

# With coverage
docker-compose exec api pytest tests/ --cov=app
```

## 🛑 Stopping Services

```bash
# Stop services (data persists)
docker-compose down

# Stop and remove data
docker-compose down -v

# Restart
docker-compose restart
```

## 🔧 Helper Script (macOS/Linux)

For convenience, use the included helper script:

```bash
./docker-helper.sh start    # Start services
./docker-helper.sh logs api # View API logs
./docker-helper.sh test     # Run tests
./docker-helper.sh psql     # Access database
./docker-helper.sh bash     # Shell in API
./docker-helper.sh stop     # Stop services
./docker-helper.sh help     # Show all commands
```

## 💡 Understanding the System

### Three-Component Architecture

1. **PostgreSQL Database** (port 5432)
   - Stores events, holds, bookings
   - Enforces data integrity
   - Persistent volume keeps data between restarts

2. **FastAPI Application** (port 8000)
   - REST API for all operations
   - Business logic layer
   - Automatic migrations on startup
   - Background scheduler for hold cleanup

3. **Networking**
   - Services communicate via Docker network
   - API connects to database using hostname `postgres`
   - Both exposed to host machine

### Key Workflows

#### Booking Flow
```
1. Create Event (100 seats)
2. Create Hold (5 seats reserved for 5 minutes)
3. Confirm Booking (from hold, permanent)
4. Available = 100 - 5 confirmed - 0 held = 95 seats
5. Hold expires after 5 minutes (automatic cleanup)
```

#### Safety Mechanisms
- **Row-level locking**: Prevents overbooking
- **Unique constraint**: Prevents duplicate bookings
- **Transaction boundaries**: Atomic operations
- **Background cleanup**: Automatic hold expiry

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Check what's using port 8000
lsof -i :8000

# If needed, change port in docker-compose.yml
# Change: "8000:8000" to "9000:8000"
```

### Services Won't Start
```bash
# Check logs
docker-compose logs

# Rebuild images
docker-compose build --no-cache

# Start again
docker-compose up
```

### Database Connection Error
```bash
# Make sure database is healthy
docker-compose ps

# View database logs
docker-compose logs postgres

# Restart database
docker-compose restart postgres
```

### Permission Errors
```bash
# Make helper script executable
chmod +x docker-helper.sh
```

## 📖 Next Steps

1. **Explore the Swagger UI**: http://localhost:8000/docs
2. **Read Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
3. **Run Tests**: `docker-compose exec api pytest tests/ -v`
4. **Check the Code**: Browse `app/` directory
5. **Read Docker Setup**: [DOCKER_SETUP.md](DOCKER_SETUP.md)

## 🎓 Learning Resources

### Understand the System
- **ARCHITECTURE.md**: Complete system design
- **RUNNING_TESTS.md**: How tests work
- **TESTING_RESULTS.md**: Test analysis

### API Documentation
- **Swagger UI**: Interactive docs at http://localhost:8000/docs
- **ReDoc**: Alternative view at http://localhost:8000/redoc

### Database
- Run `docker-compose exec postgres psql ...` to interact with database
- See sample queries in DOCKER_SETUP.md

## 💬 Common Questions

**Q: Where is the data stored?**
A: In Docker volume `postgres_data`. Persists until you run `docker-compose down -v`.

**Q: Can I change the database port?**
A: Yes, edit `docker-compose.yml` line `- "5432:5432"` to any port you want.

**Q: How do I connect to database from my app?**
A: Use connection string: `postgresql://ticket_user:ticket_password@localhost:5432/ticket_booking`

**Q: Can I run this on a different machine?**
A: Yes, just need Docker and Docker Compose. The entire setup is self-contained.

**Q: How do I deploy to production?**
A: See "Production Deployment" section in DOCKER_SETUP.md

## ✅ Verification Checklist

After starting the system, verify:

- [ ] Both containers are "healthy" (`docker-compose ps`)
- [ ] API responds (`curl http://localhost:8000/docs`)
- [ ] Can create event (test via Swagger UI)
- [ ] Can create hold (test via Swagger UI)
- [ ] Can confirm booking (test via Swagger UI)
- [ ] Tests pass (`docker-compose exec api pytest tests/ -v`)

## 🎉 You're Ready!

You now have a fully functional ticket booking system running in Docker. Start creating events and bookings!

**Need help?** Check the documentation files or look at the code comments.
