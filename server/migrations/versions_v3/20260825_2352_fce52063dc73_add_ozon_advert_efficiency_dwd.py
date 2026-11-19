"""add ozon advert efficiency dwd

Revision ID: fce52063dc73
Revises: 425a70c7b20a
Create Date: 2026-08-25 23:52:19.464275
"""

import sqlalchemy as sa

from alembic import op

revision = "fce52063dc73"
down_revision = "425a70c7b20a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dwd_ozon_advert_efficiency_detail",
        sa.Column("shop_id", sa.Integer(), nullable=False, comment="店铺ID"),
        sa.Column("stat_date", sa.Date(), nullable=False, comment="统计日期"),
        sa.Column("sku", sa.BigInteger(), nullable=False, comment="Ozon SKU"),
        sa.Column("product_name", sa.Text(), nullable=True, comment="商品名称"),
        sa.Column(
            "product_name_cn", sa.Text(), nullable=True, comment="商品名称（中文）"
        ),
        sa.Column(
            "category_name", sa.String(length=255), nullable=True, comment="品类名称"
        ),
        sa.Column(
            "category_name_cn",
            sa.String(length=255),
            nullable=True,
            comment="品类名称（中文）",
        ),
        sa.Column(
            "payment_type",
            sa.String(length=64),
            nullable=True,
            comment="广告工具/付费类型",
        ),
        sa.Column(
            "placement", sa.String(length=255), nullable=True, comment="投放位置"
        ),
        sa.Column(
            "campaign_id", sa.String(length=64), nullable=False, comment="广告活动ID"
        ),
        sa.Column(
            "campaign_name",
            sa.String(length=500),
            nullable=True,
            comment="广告活动名称",
        ),
        sa.Column(
            "money_spent",
            sa.Numeric(precision=18, scale=4),
            nullable=True,
            comment="费用（卢布）",
        ),
        sa.Column(
            "drr",
            sa.Numeric(precision=12, scale=4),
            nullable=True,
            comment="广告费用份额（%）",
        ),
        sa.Column(
            "orders_money",
            sa.Numeric(precision=18, scale=4),
            nullable=True,
            comment="销售额（卢布）",
        ),
        sa.Column("orders", sa.BigInteger(), nullable=True, comment="订单数"),
        sa.Column(
            "ctr",
            sa.Numeric(precision=12, scale=4),
            nullable=True,
            comment="点击率（%）",
        ),
        sa.Column("views", sa.BigInteger(), nullable=True, comment="展现量"),
        sa.Column("clicks", sa.BigInteger(), nullable=True, comment="点击次数"),
        sa.Column("to_cart", sa.BigInteger(), nullable=True, comment="加购次数"),
        sa.Column(
            "to_cart_conversion_rate",
            sa.Numeric(precision=12, scale=4),
            nullable=True,
            comment="加购转化率（%）",
        ),
        sa.Column(
            "cost_per_order",
            sa.Numeric(precision=18, scale=4),
            nullable=True,
            comment="单笔费用（卢布）",
        ),
        sa.Column(
            "cost_per_click",
            sa.Numeric(precision=18, scale=4),
            nullable=True,
            comment="每次点击成本（卢布）",
        ),
        sa.PrimaryKeyConstraint("shop_id", "stat_date", "sku", "campaign_id"),
        comment="Ozon广告效率SKU日明细表",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        "idx_dwd_ozon_advert_efficiency_campaign",
        "dwd_ozon_advert_efficiency_detail",
        ["campaign_id"],
        unique=False,
    )
    op.create_index(
        "idx_dwd_ozon_advert_efficiency_date",
        "dwd_ozon_advert_efficiency_detail",
        ["stat_date"],
        unique=False,
    )
    op.create_index(
        "idx_dwd_ozon_advert_efficiency_sku",
        "dwd_ozon_advert_efficiency_detail",
        ["sku"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_dwd_ozon_advert_efficiency_sku",
        table_name="dwd_ozon_advert_efficiency_detail",
    )
    op.drop_index(
        "idx_dwd_ozon_advert_efficiency_date",
        table_name="dwd_ozon_advert_efficiency_detail",
    )
    op.drop_index(
        "idx_dwd_ozon_advert_efficiency_campaign",
        table_name="dwd_ozon_advert_efficiency_detail",
    )
    op.drop_table("dwd_ozon_advert_efficiency_detail")
