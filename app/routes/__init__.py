"""
Routes - API endpoints for the ticket booking system.
"""

from app.routes.events import router as events_router
from app.routes.holds import router as holds_router
from app.routes.bookings import router as bookings_router

__all__ = [
    "events_router",
    "holds_router",
    "bookings_router",
]
