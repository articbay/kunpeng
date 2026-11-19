"""Store Ozon review identifiers as UUID strings.

Revision ID: b8d4e2f6a9c1
Revises: f7cdab07927f
Create Date: 2026-08-10 14:00:00
"""

from sqlalchemy.dialects import mysql

from alembic import op

revision = "b8d4e2f6a9c1"
down_revision = "f7cdab07927f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "ods_ozon_reviews",
        "review_id",
        existing_type=mysql.BIGINT(),
        type_=mysql.VARCHAR(length=64),
        existing_nullable=True,
        existing_comment="评价ID (API返回的id)",
        comment="评价ID (v2接口返回的 UUID 字符串)",
    )


def downgrade() -> None:
    op.alter_column(
        "ods_ozon_reviews",
        "review_id",
        existing_type=mysql.VARCHAR(length=64),
        type_=mysql.BIGINT(),
        existing_nullable=True,
        existing_comment="评价ID (v2接口返回的 UUID 字符串)",
        comment="评价ID (API返回的id)",
    )
