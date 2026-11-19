"""Ozon订单增加配送城市中文字段

Revision ID: eb27b4879a81
Revises: d2f6a91c8e47
Create Date: 2026-09-03 11:16:10.323420

"""

import sqlalchemy as sa

from alembic import op

revision = "eb27b4879a81"
down_revision = "d2f6a91c8e47"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "dwd_ozon_order_detail",
        sa.Column(
            "delivery_city_cn",
            sa.String(length=255),
            nullable=True,
            comment="配送城市（中文）",
        ),
    )


def downgrade() -> None:
    op.drop_column("dwd_ozon_order_detail", "delivery_city_cn")
