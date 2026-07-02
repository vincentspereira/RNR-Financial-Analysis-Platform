"""Add ibkr_orders table for Interactive Brokers integration

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-21 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ibkr_orders',
        sa.Column('id', PGUUID(as_uuid=True), primary_key=True),
        sa.Column(
            'user_id', PGUUID(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False, index=True,
        ),
        sa.Column('client_order_id', sa.String(64), nullable=False, unique=True),
        sa.Column('ib_order_id', sa.Integer(), nullable=True),
        sa.Column('ib_perm_id', sa.BigInteger(), nullable=True),
        sa.Column('account_id', sa.String(32), nullable=True),
        sa.Column('symbol', sa.String(16), nullable=False, index=True),
        sa.Column('sec_type', sa.String(8), nullable=False, server_default='STK'),
        sa.Column('exchange', sa.String(16), nullable=False, server_default='SMART'),
        sa.Column('currency', sa.String(8), nullable=False, server_default='USD'),
        sa.Column('action', sa.String(8), nullable=False),
        sa.Column('order_type', sa.String(16), nullable=False),
        sa.Column('quantity', sa.Numeric(20, 6), nullable=False),
        sa.Column('limit_price', sa.Numeric(20, 6), nullable=True),
        sa.Column('stop_price', sa.Numeric(20, 6), nullable=True),
        sa.Column('time_in_force', sa.String(8), nullable=False, server_default='DAY'),
        sa.Column('status', sa.String(24), nullable=False, server_default='pending_submit'),
        sa.Column('filled_quantity', sa.Numeric(20, 6), nullable=False, server_default='0'),
        sa.Column('avg_fill_price', sa.Numeric(20, 6), nullable=True),
        sa.Column('notional_usd_at_submit', sa.Numeric(20, 2), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column(
            'submitted_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True),
            server_default=sa.func.now(), nullable=False,
        ),
    )
    op.create_index(
        'ix_ibkr_orders_user_status', 'ibkr_orders', ['user_id', 'status']
    )
    op.create_index(
        'ix_ibkr_orders_user_submitted_at',
        'ibkr_orders',
        ['user_id', 'submitted_at'],
    )
    op.create_index(
        'ix_ibkr_orders_ib_order_id', 'ibkr_orders', ['ib_order_id']
    )
    op.create_index(
        'ix_ibkr_orders_client_order_id', 'ibkr_orders', ['client_order_id']
    )


def downgrade() -> None:
    op.drop_index('ix_ibkr_orders_client_order_id', table_name='ibkr_orders')
    op.drop_index('ix_ibkr_orders_ib_order_id', table_name='ibkr_orders')
    op.drop_index('ix_ibkr_orders_user_submitted_at', table_name='ibkr_orders')
    op.drop_index('ix_ibkr_orders_user_status', table_name='ibkr_orders')
    op.drop_table('ibkr_orders')
