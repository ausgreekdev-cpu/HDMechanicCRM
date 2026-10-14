"""add square_payment_link_id to pending purchase/subscription tables

Revision ID: b2c9e1f0a7d4
Revises: 1fc3b4a8c5c8
Create Date: 2026-10-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c9e1f0a7d4'
down_revision: Union[str, Sequence[str], None] = '1fc3b4a8c5c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('template_purchases',
                  sa.Column('square_payment_link_id', sa.String(length=200), nullable=True))
    op.add_column('user_subscriptions',
                  sa.Column('square_payment_link_id', sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column('user_subscriptions', 'square_payment_link_id')
    op.drop_column('template_purchases', 'square_payment_link_id')
