"""新增 Ozon 商品订单退货日宽表。

Revision ID: e7bc14b82f34
Revises: 7d1c5e8a9b20
Create Date: 2026-08-31 15:59:48.502224
"""

import sqlalchemy as sa

from alembic import op

revision = "e7bc14b82f34"
down_revision = "7d1c5e8a9b20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dwm_ozon_goods_trade_return_day",
        sa.Column("stat_date", sa.Date(), nullable=False, comment="订单统计日期"),
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column("sku", sa.BigInteger(), nullable=False, comment="Ozon SKU"),
        sa.Column("offer_id", sa.String(length=255), nullable=True, comment="商家货号"),
        sa.Column("product_name", sa.Text(), nullable=True, comment="商品名称"),
        sa.Column(
            "product_name_cn", sa.Text(), nullable=True, comment="商品名称（中文）"
        ),
        sa.Column(
            "order_cnt",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
            comment="去重货件数",
        ),
        sa.Column(
            "order_line_cnt",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
            comment="订单商品明细行数",
        ),
        sa.Column(
            "order_qty",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
            comment="下单件数",
        ),
        sa.Column(
            "delivered_qty",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
            comment="已送达件数",
        ),
        sa.Column(
            "cancelled_qty",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
            comment="已取消件数",
        ),
        sa.Column(
            "sales_amount_sum",
            sa.Numeric(precision=18, scale=4),
            server_default=sa.text("0"),
            nullable=True,
            comment="销售金额合计（seller_price×quantity）",
        ),
        sa.Column(
            "sales_currency",
            sa.String(length=10),
            nullable=True,
            comment="销售金额币种",
        ),
        sa.Column(
            "return_cnt",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
            comment="退货单数",
        ),
        sa.Column(
            "return_qty",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
            comment="退货件数",
        ),
        sa.Column(
            "return_amount_sum",
            sa.Numeric(precision=18, scale=4),
            server_default=sa.text("0"),
            nullable=True,
            comment="退货商品金额合计",
        ),
        sa.Column(
            "return_amount_currency",
            sa.String(length=10),
            nullable=True,
            comment="退货商品金额币种",
        ),
        sa.Column(
            "storage_fee_sum",
            sa.Numeric(precision=18, scale=4),
            server_default=sa.text("0"),
            nullable=True,
            comment="退货仓储费合计",
        ),
        sa.Column(
            "storage_fee_currency",
            sa.String(length=10),
            nullable=True,
            comment="退货仓储费币种",
        ),
        sa.Column(
            "utilization_fee_sum",
            sa.Numeric(precision=18, scale=4),
            server_default=sa.text("0"),
            nullable=True,
            comment="退货销毁费合计",
        ),
        sa.Column(
            "utilization_fee_currency",
            sa.String(length=10),
            nullable=True,
            comment="退货销毁费币种",
        ),
        sa.Column(
            "commission_amount_sum",
            sa.Numeric(precision=18, scale=4),
            server_default=sa.text("0"),
            nullable=True,
            comment="退货佣金合计",
        ),
        sa.Column(
            "commission_currency",
            sa.String(length=10),
            nullable=True,
            comment="退货佣金币种",
        ),
        sa.Column(
            "return_rate_ordered",
            sa.Numeric(precision=12, scale=6),
            server_default=sa.text("0"),
            nullable=False,
            comment="按下单件数计算的退货率（0-1）",
        ),
        sa.Column(
            "return_rate_delivered",
            sa.Numeric(precision=12, scale=6),
            server_default=sa.text("0"),
            nullable=False,
            comment="按送达件数计算的退货率（0-1）",
        ),
        sa.Column(
            "has_currency_conflict",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
            comment="金额存在混币或缺少币种",
        ),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "update_time", sa.DateTime(timezone=True), nullable=True, comment="更新时间"
        ),
        sa.PrimaryKeyConstraint("stat_date", "shop_id", "sku"),
        comment="DWM-Ozon商品订单与退货日宽表（订单日期cohort）",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        "idx_dwm_ozon_trade_return_shop_date",
        "dwm_ozon_goods_trade_return_day",
        ["shop_id", "stat_date"],
        unique=False,
    )
    op.create_index(
        "idx_dwm_ozon_trade_return_sku_date",
        "dwm_ozon_goods_trade_return_day",
        ["sku", "stat_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_dwm_ozon_trade_return_sku_date",
        table_name="dwm_ozon_goods_trade_return_day",
    )
    op.drop_index(
        "idx_dwm_ozon_trade_return_shop_date",
        table_name="dwm_ozon_goods_trade_return_day",
    )
    op.drop_table("dwm_ozon_goods_trade_return_day")
