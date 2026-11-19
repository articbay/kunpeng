"""add seller_price / commission_ratio to ods_ozon_finance_accrual_fees

给应计费用明细表补两列(仅 revenue 行填充)：
- seller_price     卖家价格/单价，来自 commission.seller_price
- commission_ratio 销售佣金比例，来自 commission.commission_ratio

Revision ID: add_seller_price_20260706
Revises: baseline_20260706
Create Date: 2026-07-06 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision = "add_seller_price_20260706"
down_revision = "baseline_20260706"
branch_labels = None
depends_on = None

TABLE = "ods_ozon_finance_accrual_fees"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column("seller_price", mysql.DECIMAL(precision=18, scale=4), nullable=True,
                  comment="卖家价格/单价 (仅 revenue 行，来自 commission.seller_price)"),
    )
    op.add_column(
        TABLE,
        sa.Column("commission_ratio", mysql.DECIMAL(precision=9, scale=6), nullable=True,
                  comment="销售佣金比例 (仅 revenue 行，来自 commission.commission_ratio)"),
    )


def downgrade() -> None:
    op.drop_column(TABLE, "commission_ratio")
    op.drop_column(TABLE, "seller_price")
