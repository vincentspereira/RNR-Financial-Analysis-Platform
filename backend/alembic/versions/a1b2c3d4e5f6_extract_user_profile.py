"""Extract user preferences into user_profiles table

Revision ID: a1b2c3d4e5f6
Revises: 7bece66ce402
Create Date: 2026-04-26 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '7bece66ce402'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_profiles',
        sa.Column('id', PGUUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', PGUUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'),
                  unique=True, nullable=False, index=True),
        sa.Column('theme', sa.String(20), nullable=False, server_default='dark'),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('date_format', sa.String(20), nullable=False, server_default='YYYY-MM-DD'),
        sa.Column('timezone', sa.String(50), nullable=False, server_default='UTC'),
        sa.Column('email_notifications', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('push_notifications', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('price_alerts', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('report_notifications', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('default_portfolio_id', PGUUID(as_uuid=True), nullable=True),
        sa.Column('default_watchlist_id', PGUUID(as_uuid=True), nullable=True),
        sa.Column('landing_page', sa.String(50), nullable=False, server_default='dashboard'),
        sa.Column('extra', JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    # Drop the old preferences JSONB column from users
    op.drop_column('users', 'preferences')


def downgrade() -> None:
    # Re-add the preferences column
    op.add_column('users', sa.Column('preferences', JSONB,
                  nullable=False, server_default='{}'))

    op.drop_table('user_profiles')
