#!/bin/bash

# Ticket Booking System - Docker Helper Script
# This script provides convenient commands for Docker operations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# Main commands
case "$1" in
    start)
        print_info "Starting Ticket Booking System..."
        docker-compose up -d
        print_success "Services started successfully"
        print_info "API available at: http://localhost:8000/docs"
        print_info "PostgreSQL available at: localhost:5432"
        ;;

    stop)
        print_info "Stopping Ticket Booking System..."
        docker-compose down
        print_success "Services stopped successfully"
        ;;

    restart)
        print_info "Restarting Ticket Booking System..."
        docker-compose restart
        print_success "Services restarted successfully"
        ;;

    logs)
        print_info "Displaying logs (press Ctrl+C to exit)..."
        docker-compose logs -f "${2:-api}"
        ;;

    bash)
        print_info "Opening shell in API container..."
        docker-compose exec api /bin/bash
        ;;

    psql)
        print_info "Opening PostgreSQL CLI..."
        docker-compose exec postgres psql -U ticket_user -d ticket_booking
        ;;

    test)
        print_info "Running tests..."
        docker-compose exec api pytest tests/ -v "${@:2}"
        ;;

    migrate)
        print_info "Running database migrations..."
        docker-compose exec api alembic upgrade head
        print_success "Migrations completed"
        ;;

    reset-db)
        print_info "⚠️  This will delete all database data. Continue? (y/N)"
        read -r response
        if [ "$response" = "y" ]; then
            print_info "Resetting database..."
            docker-compose down -v
            docker-compose up -d
            print_success "Database reset completed"
        else
            print_info "Reset cancelled"
        fi
        ;;

    build)
        print_info "Building Docker images..."
        docker-compose build "${@:2}"
        print_success "Build completed"
        ;;

    ps)
        print_info "Checking service status..."
        docker-compose ps
        ;;

    stats)
        print_info "Displaying resource usage..."
        docker stats ticket_booking_api ticket_booking_db
        ;;

    clean)
        print_info "Cleaning up Docker resources..."
        docker container prune -f
        docker image prune -f
        print_success "Cleanup completed"
        ;;

    help)
        echo "Ticket Booking System - Docker Helper"
        echo ""
        echo "Usage: ./docker-helper.sh [command] [options]"
        echo ""
        echo "Commands:"
        echo "  start              Start all services"
        echo "  stop               Stop all services"
        echo "  restart            Restart all services"
        echo "  logs [service]     View logs (default: api)"
        echo "  bash               Open shell in API container"
        echo "  psql               Open PostgreSQL CLI"
        echo "  test [args]        Run tests (pass pytest args)"
        echo "  migrate            Run database migrations"
        echo "  reset-db           Reset database (DELETE ALL DATA)"
        echo "  build              Build Docker images"
        echo "  ps                 Show service status"
        echo "  stats              Show resource usage"
        echo "  clean              Clean up Docker resources"
        echo "  help               Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./docker-helper.sh start"
        echo "  ./docker-helper.sh logs -f"
        echo "  ./docker-helper.sh test tests/test_booking_service.py -v"
        echo "  ./docker-helper.sh bash"
        ;;

    *)
        print_error "Unknown command: $1"
        echo ""
        echo "Run './docker-helper.sh help' for usage information"
        exit 1
        ;;
esac
