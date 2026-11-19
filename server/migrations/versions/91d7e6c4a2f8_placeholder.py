"""placeholder migration to match database version

Revision ID: 91d7e6c4a2f8
Revises: add_wb_advert_full_20260723
Create Date: 2026-07-28

This is a placeholder migration to match the version recorded in the database.
It doesn't make any schema changes.

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '91d7e6c4a2f8'
down_revision = 'add_wb_advert_full_20260723'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This is a placeholder - no schema changes
    pass


def downgrade() -> None:
    # This is a placeholder - no schema changes
    pass
