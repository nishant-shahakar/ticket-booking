# Docker Setup Guide

## Quick Start

Run the entire system with a single command:

```bash
docker-compose up
```

This will:
1. Build the FastAPI application image
2. Start PostgreSQL container (port 5432)
3. Start API service (port 8000)
4. Run database migrations automatically
5. Start the background scheduler

## Accessing the API

Once running, access the API at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Base URL**: http://localhost:8000

## Docker Compose Services

### PostgreSQL Service
- **Container Name**: `ticket_booking_db`
- **Port**: `5432`
- **Username**: `ticket_user`
- **Password**: `ticket_password`
- **Database**: `ticket_booking`
- **Storage**: Persistent volume (`postgres_data`)

### API Service
- **Container Name**: `ticket_booking_api`
- **Port**: `8000`
- **Depends on**: PostgreSQL (waits for health check)
- **Auto-reload**: Enabled for development

## Common Commands

### Start Services
```bash
# Start in foreground (see logs)
docker-compose up

# Start in background
docker-compose up -d

# Start with build (rebuilds images)
docker-compose up --build
```

### Stop Services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes database)
docker-compose down -v
```

### View Logs
```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs api
docker-compose logs postgres

# Follow logs in real-time
docker-compose logs -f api

# View last 100 lines
docker-compose logs --tail=100 api
```

### Execute Commands

#### Run migrations manually
```bash
docker-compose exec api alembic upgrade head
```

#### Access PostgreSQL CLI
```bash
docker-compose exec postgres psql -U ticket_user -d ticket_booking
```

#### Run tests inside container
```bash
docker-compose exec api pytest tests/ -v
```

#### Access API container shell
```bash
docker-compose exec api /bin/bash
```

## Environment Configuration

### Development (docker-compose.yml)
- **Database**: PostgreSQL in container
- **API Host**: 0.0.0.0 (accessible from host)
- **Debug**: True
- **Auto-reload**: Enabled

### Production Deployment

To deploy to production, create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: ${DB_NAME}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - ticket_network

  api:
    image: ticket-booking-api:latest  # Use pre-built image
    depends_on:
      - postgres
    environment:
      DATABASE_URL: postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      DEBUG: "False"
    ports:
      - "8000:8000"
    networks:
      - ticket_network
    command: gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

volumes:
  postgres_data:

networks:
  ticket_network:
```

Then run with:
```bash
docker-compose -f docker-compose.prod.yml up
```

## Troubleshooting

### Port Already in Use
```bash
# Find what's using port 8000
lsof -i :8000

# Use different port
docker-compose up -p myapp  # Prefixes container names
```

Or modify `docker-compose.yml`:
```yaml
ports:
  - "9000:8000"  # Use 9000 instead
```

### Database Connection Issues
```bash
# Check PostgreSQL is healthy
docker-compose ps

# View PostgreSQL logs
docker-compose logs postgres

# Test connection from API container
docker-compose exec api pg_isready -h postgres -U ticket_user -d ticket_booking
```

### API Not Starting
```bash
# View API logs
docker-compose logs api

# Check for errors
docker-compose logs api | grep ERROR
```

### Rebuild Images
```bash
# Force rebuild (without cache)
docker-compose build --no-cache

# Then start
docker-compose up
```

## Health Checks

Both services have health checks configured:

```bash
# Check service status
docker-compose ps

# Example output:
# NAME                    STATUS
# ticket_booking_db       Up X minutes (healthy)
# ticket_booking_api      Up X minutes (healthy)
```

## Testing with Docker

### Run Unit Tests
```bash
docker-compose exec api pytest tests/ -v
```

### Run with Coverage
```bash
docker-compose exec api pytest tests/ --cov=app --cov-report=html
```

### Run Specific Test
```bash
docker-compose exec api pytest tests/test_booking_service.py -v
```

## Database Persistence

The PostgreSQL data is stored in a Docker volume (`postgres_data`). This means:

- **Data persists** between `docker-compose down` and `docker-compose up`
- **Data is lost** only when running `docker-compose down -v`

### Backup Database
```bash
docker-compose exec postgres pg_dump -U ticket_user ticket_booking > backup.sql
```

### Restore Database
```bash
docker-compose exec -T postgres psql -U ticket_user ticket_booking < backup.sql
```

## Multi-Environment Setup

### Development
```bash
docker-compose -f docker-compose.yml up
```

### Staging
```bash
docker-compose -f docker-compose.staging.yml up
```

### Production
```bash
docker-compose -f docker-compose.prod.yml up
```

## Docker Networking

The services communicate via a custom bridge network (`ticket_network`):

- **API → PostgreSQL**: Uses hostname `postgres` (internal DNS)
- **Host → API**: Uses `localhost:8000`
- **Host → PostgreSQL**: Uses `localhost:5432`

## Building for Different Architectures

### Build for specific architecture
```bash
# For ARM64 (M1/M2 Mac)
docker buildx build --platform linux/arm64 -t ticket-booking-api:latest .

# For AMD64 (Linux/Intel)
docker buildx build --platform linux/amd64 -t ticket-booking-api:latest .

# Multi-platform
docker buildx build --platform linux/amd64,linux/arm64 -t ticket-booking-api:latest .
```

## Performance Optimization

### Production Image Size
Current image size: ~150MB

To reduce further:
1. Use `python:3.9-slim-bullseye` instead of `-slim`
2. Remove development dependencies
3. Use multi-stage build (already implemented)

### Database Performance
Add PostgreSQL optimizations to `docker-compose.yml`:

```yaml
postgres:
  environment:
    POSTGRES_INITDB_ARGS: "-c shared_buffers=256MB -c max_connections=200"
```

## CI/CD Integration

### GitHub Actions Example
```yaml
services:
  postgres:
    image: postgres:15-alpine
    env:
      POSTGRES_PASSWORD: postgres
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5

- name: Run tests
  run: |
    docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## Monitoring

### Container Resource Usage
```bash
docker stats ticket_booking_api ticket_booking_db
```

### View Image Sizes
```bash
docker images ticket-booking-api
```

### Inspect Container
```bash
docker inspect ticket_booking_api
```

## Cleanup

### Remove unused resources
```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Remove unused volumes (WARNING: loses data)
docker volume prune

# Remove everything (containers, images, volumes)
docker system prune -a --volumes
```

## Next Steps

1. **Run the system**: `docker-compose up`
2. **Access API**: http://localhost:8000/docs
3. **Run tests**: `docker-compose exec api pytest tests/ -v`
4. **Create events**: Use Swagger UI to test endpoints
5. **Monitor logs**: `docker-compose logs -f api`
