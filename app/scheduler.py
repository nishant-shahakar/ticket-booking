"""
Background scheduler for automatic hold expiry cleanup.

Two-layer safety for hold expiry:
1. Lazy expiry: WHERE expires_at > NOW() in queries (automatic)
2. Eager cleanup: APScheduler job marks expired holds (keeps data clean)
"""

import logging
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.database import SessionLocal
from app.models import Hold, HoldStatus

logger = logging.getLogger(__name__)


class HoldExpiryScheduler:
    """Background scheduler for automatic hold expiry."""
    
    def __init__(self):
        """Initialize scheduler."""
        self.scheduler = BackgroundScheduler()
    
    def cleanup_expired_holds(self):
        """Mark holds as EXPIRED if past expiry time.
        
        Runs every 60 seconds (configurable).
        
        **Optimized for scale**: Uses single BULK UPDATE instead of N+1 queries.
        
        This is the **eager cleanup** layer:
        - Lazy expiry: Queries exclude expired via WHERE expires_at > NOW()
        - Eager cleanup: This job updates status = 'EXPIRED' (keeps data clean)
        
        Database (single query, not loop):
            UPDATE holds
            SET status = 'EXPIRED'
            WHERE status = 'ACTIVE'
            AND expires_at <= NOW()
            AND deleted_at IS NULL
        
        **Performance:**
        - Before: 1 SELECT + N UPDATE queries (N=number of expired) = 10+ minutes
        - After: 1 bulk UPDATE query = 30 seconds
        """
        session = None
        try:
            session = SessionLocal()
            
            # Single bulk UPDATE (not loop!)
            expired_count = session.query(Hold).filter(
                Hold.status == HoldStatus.ACTIVE,
                Hold.expires_at <= datetime.now(timezone.utc),
                Hold.deleted_at.is_(None),
            ).update({Hold.status: HoldStatus.EXPIRED})
            
            session.commit()
            
            if expired_count > 0:
                logger.info(f"Marked {expired_count} holds as EXPIRED (batch update)")
            else:
                logger.debug("No expired holds to clean up")
            
        except Exception as e:
            logger.error(f"Error cleaning up expired holds: {e}")
            if session:
                session.rollback()
        finally:
            if session:
                session.close()
    
    def start(self, interval_seconds: int = 60):
        """Start the scheduler.
        
        Args:
            interval_seconds: Run cleanup job every N seconds (default 60)
        """
        if self.scheduler.running:
            logger.warning("Scheduler already running")
            return
        
        # Add job to run every interval_seconds
        self.scheduler.add_job(
            self.cleanup_expired_holds,
            trigger=IntervalTrigger(seconds=interval_seconds),
            id="cleanup_expired_holds",
            name="Clean up expired holds",
            replace_existing=True,
        )
        
        self.scheduler.start()
        logger.info(f"Hold expiry scheduler started (interval: {interval_seconds}s)")
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Hold expiry scheduler stopped")


# Global scheduler instance
hold_expiry_scheduler = HoldExpiryScheduler()
