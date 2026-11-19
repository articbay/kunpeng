"""补充Ozon漏斗成交指标并过滤空占位

Revision ID: 15a40516a399
Revises: 71aa58ec43a8
Create Date: 2026-09-01 10:40:30.335531
"""

import sqlalchemy as sa

from alembic import op

revision = "15a40516a399"
down_revision = "71aa58ec43a8"
branch_labels = None
depends_on = None

TABLE = "dwm_ozon_goods_trade_return_day"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(
            "funnel_ordered_units",
            sa.BigInteger(),
            nullable=True,
            comment="Ozon销售漏斗下单商品件数",
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "funnel_revenue",
            sa.Numeric(18, 4),
            nullable=True,
            comment="Ozon销售漏斗下单金额",
        ),
    )


def downgrade() -> None:
    op.drop_column(TABLE, "funnel_revenue")
    op.drop_column(TABLE, "funnel_ordered_units")
