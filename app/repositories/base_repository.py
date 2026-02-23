"""
Base repository class with common patterns.
"""

from typing import TypeVar, Generic, Optional
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Base repository class with common query patterns."""
    
    def __init__(self, session: Session, model_class: type[T]):
        """Initialize repository with session and model class.
        
        Args:
            session: SQLAlchemy session
            model_class: The model class this repository manages
        """
        self.session = session
        self.model_class = model_class
    
    def _base_query(self):
        """Get base query with soft delete filter."""
        return self.session.query(self.model_class).filter(
            self.model_class.deleted_at.is_(None)
        )
    
    def get_by_id(self, id: UUID) -> Optional[T]:
        """Get entity by ID (excluding soft-deleted).
        
        Args:
            id: Entity UUID
            
        Returns:
            Entity or None
        """
        return self._base_query().filter(self.model_class.id == id).first()
    
    def save(self, entity: T) -> T:
        """Save entity to database.
        
        Args:
            entity: Entity to save
            
        Returns:
            Saved entity
        """
        self.session.add(entity)
        return entity
    
    def update(self, entity: T) -> T:
        """Update entity (merge into session).
        
        Args:
            entity: Entity to update
            
        Returns:
            Updated entity
        """
        return self.session.merge(entity)
    
    def soft_delete(self, entity: T) -> T:
        """Soft delete entity by setting deleted_at timestamp.
        
        Args:
            entity: Entity to soft delete
            
        Returns:
            Soft-deleted entity
        """
        entity.deleted_at = datetime.now(timezone.utc)
        return self.update(entity)
    
    def count(self) -> int:
        """Count active (non-deleted) entities.
        
        Returns:
            Count of entities
        """
        return self._base_query().count()
