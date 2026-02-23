"""
Hold repository - handles hold queries.
"""

from typing import Optional
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import and_

from app.models import Hold, HoldStatus
from app.repositories.base_repository import BaseRepository


class HoldRepository(BaseRepository):
    """Repository for Hold model."""
    
    def __init__(self, session):
        """Initialize with session."""
        super().__init__(session, Hold)
    
    def get_for_update(self, id: UUID) -> Optional[Hold]:
        """Get hold with row-level lock (FOR UPDATE).
        
        Args:
            id: Hold UUID
            
        Returns:
            Hold with lock acquired or None
        """
        return self._base_query().filter(Hold.id == id).with_for_update().first()
    
    def get_by_event_and_user(self, event_id: UUID, user_id: UUID) -> Optional[Hold]:
        """Get active hold for user on event.
        
        Args:
            event_id: Event UUID
            user_id: User UUID
            
        Returns:
            Active hold or None
        """
        return self._base_query().filter(
            Hold.event_id == event_id,
            Hold.user_id == user_id,
            Hold.status == HoldStatus.ACTIVE,
            Hold.expires_at > datetime.now(timezone.utc),
        ).first()
    
    def get_active_holds_by_event(self, event_id: UUID) -> list[Hold]:
        """Get all active (not expired) holds for an event.
        
        Args:
            event_id: Event UUID
            
        Returns:
            List of active holds
        """
        return self._base_query().filter(
            Hold.event_id == event_id,
            Hold.status == HoldStatus.ACTIVE,
            Hold.expires_at > datetime.now(timezone.utc),
        ).all()
    
    def get_expired_holds(self, limit: int = 1000) -> list[Hold]:
        """Get holds that have expired but not yet marked as EXPIRED.
        
        Used by background cleanup job.
        
        Args:
            limit: Max results to return
            
        Returns:
            List of expired holds
        """
        return self.session.query(Hold).filter(
            Hold.status == HoldStatus.ACTIVE,
            Hold.expires_at <= datetime.now(timezone.utc),
            Hold.deleted_at.is_(None),
        ).limit(limit).all()
    
    def mark_expired(self, hold: Hold) -> Hold:
        """Mark hold as EXPIRED.
        
        Args:
            hold: Hold to mark
            
        Returns:
            Updated hold
        """
        hold.status = HoldStatus.EXPIRED
        return self.update(hold)
    
    def mark_confirmed(self, hold: Hold) -> Hold:
        """Mark hold as CONFIRMED.
        
        Args:
            hold: Hold to mark
            
        Returns:
            Updated hold
        """
        hold.status = HoldStatus.CONFIRMED
        return self.update(hold)
    
    def get_holds_by_user(self, user_id: UUID, event_id: UUID) -> list[Hold]:
        """Get all holds for user on specific event.
        
        Args:
            user_id: User UUID
            event_id: Event UUID
            
        Returns:
            List of holds
        """
        return self._base_query().filter(
            Hold.event_id == event_id,
            Hold.user_id == user_id,
        ).all()
