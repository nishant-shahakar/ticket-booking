# 🐳 Docker Setup Complete - Ready to Use

## ✅ What's Been Set Up

Your ticket booking system is now fully dockerized with PostgreSQL. Everything is configured and ready to go.

## 🚀 Start Using It Right Now

### Option 1: Simple (Recommended)
```bash
cd /Users/nishantshahakar/Documents/projects/Spry\ Health\ Assignment/ticket-booking

docker-compose up
```

That's it! Both PostgreSQL and the API will start automatically.

### Option 2: Using Helper Script (macOS/Linux)
```bash
./docker-helper.sh start
```

### Option 3: Detached Mode (Run in Background)
```bash
docker-compose up -d
```

## 📍 Access Points

Once running, everything is available at:

- **Swagger API Docs**: http://localhost:8000/docs ⭐ (Best for testing)
- **ReDoc**: http://localhost:8000/redoc
- **Base API**: http://localhost:8000
- **PostgreSQL**: localhost:5432 (user: `ticket_user`, password: `ticket_password`)

## 🧪 Test It Out

### Create an Event
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

### Or Use Swagger UI
1. Open http://localhost:8000/docs
2. Click on POST /v1/events
3. Click "Try it out"
4. Fill in the data
5. Click "Execute"

## 📋 What's Running

### PostgreSQL Container
- Name: `ticket_booking_db`
- Port: 5432
- Database: `ticket_booking`
- Data: Persists in Docker volume

### API Container
- Name: `ticket_booking_api`
- Port: 8000
- Framework: FastAPI
- Auto-reload: Enabled (changes reflected immediately)

### Shared Network
- Services communicate automatically
- Both exposed to your machine

## 🔧 Common Commands

```bash
# View logs
docker-compose logs -f api

# Stop everything (data persists)
docker-compose down

# Stop and remove data
docker-compose down -v

# View status
docker-compose ps

# Run tests
docker-compose exec api pytest tests/ -v

# Access database
docker-compose exec postgres psql -U ticket_user -d ticket_booking

# Access API container shell
docker-compose exec api /bin/bash
```

## 📁 Files Created

```
✓ Dockerfile                  - Container image definition
✓ docker-compose.yml          - Multi-container setup
✓ .dockerignore               - Build optimization
✓ docker-helper.sh            - Convenience commands
✓ .env.docker                 - Environment config
✓ DOCKER_SETUP.md             - Complete guide (50+ commands)
✓ GETTING_STARTED.md          - 5-minute quick start
✓ DOCKER_COMPLETE.md          - Setup summary
✓ README.md                   - Updated with Docker info
```

## 🎯 Next Steps

### 1. Start the System
```bash
docker-compose up
```

### 2. Open Browser
http://localhost:8000/docs

### 3. Play with API
- Create events
- Create holds
- Confirm bookings
- Check availability

### 4. Run Tests (verify everything works)
```bash
docker-compose exec api pytest tests/ -v
```

### 5. Explore Code
- `app/main.py` - Main FastAPI app
- `app/routes/` - API endpoints
- `app/services/` - Business logic
- `app/repositories/` - Data access

## ❓ FAQ

**Q: Do I need to install PostgreSQL?**
A: No! PostgreSQL runs in Docker.

**Q: Will I lose data when I stop the containers?**
A: No! Data persists in Docker volume. It's only lost if you run `docker-compose down -v`.

**Q: Can I change the port?**
A: Yes, edit `docker-compose.yml` line `- "8000:8000"` to `- "9000:8000"` etc.

**Q: How do I use the database?**
A: Run `docker-compose exec postgres psql -U ticket_user -d ticket_booking`

**Q: What if a port is already in use?**
A: Change the port in docker-compose.yml or stop the other service.

**Q: Can I deploy this to production?**
A: Yes! See DOCKER_SETUP.md for production setup.

## 📊 System Architecture

```
┌─────────────────────────────────────────────────┐
│            Docker Environment                  │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────────────┐  ┌────────────────┐  │
│  │   FastAPI (8000)     │  │  PostgreSQL    │  │
│  │   - Swagger UI       │  │   (5432)       │  │
│  │   - REST APIs        │  │   - Data       │  │
│  │   - Business Logic   │  │   - Persistence│  │
│  └──────────────────────┘  └────────────────┘  │
│           ↓                       ↑             │
│     Communicates via Docker Network             │
│           ↓                       ↑             │
│  ┌──────────────────────────────────────────┐  │
│  │      Docker Bridge Network                │  │
│  │   (ticket_network)                       │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
└─────────────────────────────────────────────────┘
        ↓
   ┌──────────────┐
   │  Your Machine│
   │  localhost   │
   └──────────────┘
```

## 🚨 Troubleshooting

### Services won't start
```bash
# Check logs
docker-compose logs

# Rebuild
docker-compose build --no-cache
docker-compose up
```

### Port already in use
```bash
# Find what's using port 8000
lsof -i :8000

# Edit docker-compose.yml to use different port
```

### Database won't connect
```bash
# Check database is healthy
docker-compose ps

# View database logs
docker-compose logs postgres
```

### Permission errors
```bash
# Make script executable
chmod +x docker-helper.sh
```

## 📚 Documentation

- **Quick Start**: GETTING_STARTED.md (5-minute walkthrough)
- **Docker Guide**: DOCKER_SETUP.md (comprehensive Docker reference)
- **Architecture**: ARCHITECTURE.md (system design)
- **Testing**: RUNNING_TESTS.md (how to run tests)
- **Setup Complete**: DOCKER_COMPLETE.md (this file)

## 🎉 You're All Set!

Everything is ready. Just run:

```bash
docker-compose up
```

Then open: http://localhost:8000/docs

Enjoy your fully functional ticket booking system! 🚀

---

**Need help?** Check the documentation files or examine the code in the `app/` directory.
