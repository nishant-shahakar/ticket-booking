"""
Application initialization and FastAPI app setup.
"""

import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.settings import settings
from app.exception_handlers import register_exception_handlers
from app.routes import events_router, holds_router, bookings_router
from app.scheduler import hold_expiry_scheduler
from app.database import engine
from app.models import Base

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle - startup and shutdown.
    
    Args:
        app: FastAPI application
        
    Yields:
        Control back to app
    """
    # Startup
    logger.info("Starting Ticket Booking System...")
    
    # Initialize database tables
    logger.info("Initializing database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
    
    if settings.scheduler_enabled:
        hold_expiry_scheduler.start(
            interval_seconds=settings.scheduler_hold_cleanup_interval_seconds
        )
        logger.info("Hold expiry scheduler initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Ticket Booking System...")
    
    if settings.scheduler_enabled:
        hold_expiry_scheduler.stop()
        logger.info("Hold expiry scheduler stopped")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )
    
    # Register exception handlers
    register_exception_handlers(app)
    
    # Register routes
    app.include_router(events_router)
    app.include_router(holds_router)
    app.include_router(bookings_router)

    return app


# Create app instance
app = create_app()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
