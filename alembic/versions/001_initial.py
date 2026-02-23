"""Initial migration: Create Event, Hold, Booking tables with constraints.

Revision ID: 001_initial
Revises: 
Create Date: 2026-02-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    """Create initial schema."""
    
    # Create events table
    op.create_table(
        'events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('location', sa.String(255), nullable=False),
        sa.Column('total_seats', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('total_seats > 0', name='check_event_total_seats_positive'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_events_deleted_at', 'events', ['deleted_at'])
    
    # Create holds table
    op.create_table(
        'holds',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('seat_count', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='ACTIVE'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('seat_count > 0', name='check_hold_seat_count_positive'),
        sa.CheckConstraint("status IN ('ACTIVE', 'EXPIRED', 'CONFIRMED')", name='check_hold_status_valid'),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Create indexes on holds
    op.create_index(
        'idx_holds_event_active',
        'holds',
        ['event_id', 'status', 'expires_at'],
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_index(
        'idx_holds_expires_at',
        'holds',
        ['expires_at'],
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_index('idx_holds_deleted_at', 'holds', ['deleted_at'])
    
    # Create bookings table
    op.create_table(
        'bookings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('seat_count', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='CONFIRMED'),
        sa.Column('hold_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('canceled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint('seat_count > 0', name='check_booking_seat_count_positive'),
        sa.CheckConstraint("status IN ('CONFIRMED', 'CANCELED')", name='check_booking_status_valid'),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['hold_id'], ['holds.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Create unique index to prevent double booking (only for confirmed)
    op.create_index(
        'uq_booking_event_user',
        'bookings',
        ['event_id', 'user_id'],
        unique=True,
        postgresql_where=sa.text("status = 'CONFIRMED'"),
    )
    
    # Create indexes on bookings
    op.create_index('idx_bookings_event_status', 'bookings', ['event_id', 'status'])
    op.create_index('idx_bookings_user_id', 'bookings', ['user_id'])
    op.create_index('idx_bookings_deleted_at', 'bookings', ['deleted_at'])


def downgrade() -> None:
    """Drop all tables."""
    
    op.drop_index('idx_bookings_deleted_at', table_name='bookings')
    op.drop_index('idx_bookings_user_id', table_name='bookings')
    op.drop_index('idx_bookings_event_status', table_name='bookings')
    op.drop_index('uq_booking_event_user', table_name='bookings')
    op.drop_table('bookings')
    
    op.drop_index('idx_holds_deleted_at', table_name='holds')
    op.drop_index('idx_holds_expires_at', table_name='holds')
    op.drop_index('idx_holds_event_active', table_name='holds')
    op.drop_table('holds')
    
    op.drop_index('idx_events_deleted_at', table_name='events')
    op.drop_table('events')
