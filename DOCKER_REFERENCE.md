# Docker Setup - Quick Reference

## What's Included

Your ticket booking system is now fully Dockerized with:

- ✅ **Dockerfile** - Multi-stage build for optimized image
- ✅ **docker-compose.yml** - PostgreSQL + FastAPI orchestration
- ✅ **docker-helper.sh** - Convenience script with 13 commands
- ✅ **Comprehensive Documentation** - 5 guides for all use cases

## One-Command Startup

```bash
docker-compose up
```

That's it! The system will:
1. Start PostgreSQL database (port 5432)
2. Run database migrations automatically
3. Start FastAPI server (port 8000)
4. Enable background scheduler for hold expiry
5. Be ready to accept API requests

## Verify It's Working

Open in your browser:
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## Common Tasks

### Start Services
```bash
docker-compose up                  # Start in foreground (shows logs)
docker-compose up -d               # Start in background
```

### View Logs
```bash
docker-compose logs -f api         # FastAPI logs (follow)
docker-compose logs -f postgres    # PostgreSQL logs
docker-compose logs                # All logs (one-time)
```

### Run Tests
```bash
docker-compose exec api pytest tests/ -v
```

### Access Database Directly
```bash
docker-compose exec postgres psql -U ticket_user -d ticket_booking
```

### Stop Services
```bash
docker-compose down                # Stop and keep data
docker-compose down -v             # Stop and delete all data
```

## Using the Helper Script

Alternatively, use the convenience script:

```bash
./docker-helper.sh start           # Start services
./docker-helper.sh stop            # Stop services
./docker-helper.sh restart         # Restart services
./docker-helper.sh logs api        # View logs
./docker-helper.sh test            # Run tests
./docker-helper.sh bash api        # Shell into API container
./docker-helper.sh psql            # Connect to database
./docker-helper.sh reset-db        # Reset database (with prompt)
./docker-helper.sh help            # Show all commands
```

## Key Ports

| Service      | Port | URL/Connection                          |
|-------------|------|----------------------------------------|
| FastAPI    | 8000 | http://localhost:8000/docs             |
| PostgreSQL | 5432 | postgresql://user:pass@localhost:5432  |

## Architecture

```
Your Computer
    ├── Port 8000 → FastAPI Container
    │   ├── Routes (create, read, hold, book)
    │   ├── Services (business logic)
    │   ├── Scheduler (hold expiry cleanup)
    │   └── Talks to PostgreSQL
    │
    └── Port 5432 → PostgreSQL Container
        ├── Events table
        ├── Holds table (auto-expires)
        └── Bookings table (soft deletes)
        
Data persists in "postgres_data" volume
(survives container restarts)
```

## Important Notes

### Data Persistence
- **With `docker-compose down`**: Data persists (good for development)
- **With `docker-compose down -v`**: Data deleted (resets everything)

### Environment Configuration
All settings are in `.env.docker`:
```
DATABASE_URL=postgresql://ticket_user:ticket_password@postgres:5432/ticket_booking
DEBUG=True
HOLD_EXPIRY_MINUTES=5
SCHEDULER_ENABLED=True
```

### Health Checks
Services have health checks configured:
- PostgreSQL: Ready when `pg_isready` succeeds
- FastAPI: Waits for database to be healthy before starting
- This ensures reliable startup sequence

## Documentation Files

- **QUICK_START.md** - 2-minute quick reference
- **GETTING_STARTED.md** - 5-minute walkthrough with examples
- **DOCKER_SETUP.md** - 50+ commands reference & production setup
- **DOCKER_COMPLETE.md** - Comprehensive setup summary
- **DOCKER_SUMMARY.md** - Visual diagrams and quick reference

## Testing Examples

### Create Event
```bash
curl -X POST http://localhost:8000/v1/events \
  -H "Content-Type: application/json" \
  -d '{"name":"Concert","total_seats":100}'
```

### Create Hold
```bash
curl -X POST http://localhost:8000/v1/events/1/holds \
  -H "Content-Type: application/json" \
  -d '{"num_seats":5}'
```

### Create Booking
```bash
curl -X POST http://localhost:8000/v1/bookings \
  -H "Content-Type: application/json" \
  -d '{"hold_id":1}'
```

## Troubleshooting

**Services won't start?**
```bash
docker-compose logs   # Check what's wrong
docker-compose down -v  # Clean reset
docker-compose up       # Try again
```

**Port already in use?**
```bash
# Change port in docker-compose.yml
# Line: ports: ["8000:8000"]  → ports: ["8001:8000"]
docker-compose up
```

**Want fresh database?**
```bash
docker-compose down -v
docker-compose up
# This recreates empty database with migrations
```

## Production Notes

For production deployment:
1. See DOCKER_SETUP.md "Production Deployment" section
2. Use environment-specific docker-compose files
3. Enable TLS/HTTPS
4. Configure proper database backups
5. Use Gunicorn instead of uvicorn
6. Set DEBUG=False
7. Configure proper logging

## Next Steps

1. ✅ Run: `docker-compose up`
2. ✅ Visit: http://localhost:8000/docs
3. ✅ Try creating events/holds/bookings
4. ✅ Read GETTING_STARTED.md for detailed walkthrough
5. ✅ Run tests: `docker-compose exec api pytest tests/ -v`

---

**Questions?** Check the relevant documentation file or run:
```bash
./docker-helper.sh help
```
