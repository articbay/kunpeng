"""新增Wildberries搜索流量表

Revision ID: 279c3844ce06
Revises: 34c0cea842a3
Create Date: 2026-07-24 11:36:47.134995
"""

import sqlalchemy as sa
from alembic import op

revision = "279c3844ce06"
down_revision = "34c0cea842a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ods_wb_search_traffic",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column("date_from", sa.Date(), nullable=False, comment="报告开始日期"),
        sa.Column("date_to", sa.Date(), nullable=False, comment="报告结束日期"),
        sa.Column(
            "nm_id", sa.BigInteger(), nullable=False, comment="Wildberries商品ID"
        ),
        sa.Column(
            "position_cluster",
            sa.String(length=32),
            nullable=False,
            comment="搜索位置分组",
        ),
        sa.Column(
            "product_name", sa.String(length=500), nullable=True, comment="商品名称"
        ),
        sa.Column(
            "vendor_code", sa.String(length=255), nullable=True, comment="卖家货号"
        ),
        sa.Column(
            "subject_name", sa.String(length=255), nullable=True, comment="商品分类"
        ),
        sa.Column("brand_name", sa.String(length=255), nullable=True, comment="品牌"),
        sa.Column(
            "main_photo", sa.String(length=1000), nullable=True, comment="商品主图"
        ),
        sa.Column("is_advertised", sa.Boolean(), nullable=True, comment="是否广告商品"),
        sa.Column(
            "is_substituted_sku",
            sa.Boolean(),
            nullable=True,
            comment="是否替换商品",
        ),
        sa.Column(
            "is_card_rated", sa.Boolean(), nullable=True, comment="商品卡是否有评分"
        ),
        sa.Column(
            "rating",
            sa.Numeric(precision=10, scale=4),
            nullable=True,
            comment="商品卡评分",
        ),
        sa.Column(
            "feedback_rating",
            sa.Numeric(precision=10, scale=4),
            nullable=True,
            comment="用户反馈评分",
        ),
        sa.Column(
            "min_price",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="最低价格",
        ),
        sa.Column(
            "max_price",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="最高价格",
        ),
        sa.Column(
            "avg_position_current",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="当前平均搜索位置",
        ),
        sa.Column(
            "avg_position_dynamics",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="平均搜索位置变化",
        ),
        sa.Column(
            "open_card_current",
            sa.BigInteger(),
            nullable=True,
            comment="打开商品卡次数",
        ),
        sa.Column(
            "open_card_dynamics",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="打开商品卡变化",
        ),
        sa.Column(
            "add_to_cart_current", sa.BigInteger(), nullable=True, comment="加购次数"
        ),
        sa.Column(
            "add_to_cart_dynamics",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="加购变化",
        ),
        sa.Column(
            "open_to_cart_current",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="打开到加购转化率",
        ),
        sa.Column(
            "open_to_cart_dynamics",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="打开到加购转化率变化",
        ),
        sa.Column("orders_current", sa.BigInteger(), nullable=True, comment="订单数"),
        sa.Column(
            "orders_dynamics",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="订单数变化",
        ),
        sa.Column(
            "cart_to_order_current",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="加购到下单转化率",
        ),
        sa.Column(
            "cart_to_order_dynamics",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="加购到下单转化率变化",
        ),
        sa.Column(
            "visibility_current",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="当前搜索可见度",
        ),
        sa.Column(
            "visibility_dynamics",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="搜索可见度变化",
        ),
        sa.Column("currency", sa.String(length=16), nullable=True, comment="币种"),
        sa.Column("row_data", sa.JSON(), nullable=False, comment="API原始JSON数据"),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="同步时间",
        ),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "update_time",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="更新时间",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shop_id",
            "date_from",
            "date_to",
            "nm_id",
            "position_cluster",
            name="uq_wb_search_traffic_window_product",
        ),
        comment="Wildberries商品搜索流量滚动窗口表",
    )
    op.create_index(
        "idx_wb_search_traffic_date_range",
        "ods_wb_search_traffic",
        ["date_from", "date_to"],
        unique=False,
    )
    op.create_index(
        "idx_wb_search_traffic_nm_id",
        "ods_wb_search_traffic",
        ["nm_id"],
        unique=False,
    )
    op.create_index(
        "idx_wb_search_traffic_shop_id",
        "ods_wb_search_traffic",
        ["shop_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ods_wb_search_traffic_id"),
        "ods_wb_search_traffic",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_ods_wb_search_traffic_id"),
        table_name="ods_wb_search_traffic",
    )
    op.drop_index(
        "idx_wb_search_traffic_shop_id",
        table_name="ods_wb_search_traffic",
    )
    op.drop_index(
        "idx_wb_search_traffic_nm_id",
        table_name="ods_wb_search_traffic",
    )
    op.drop_index(
        "idx_wb_search_traffic_date_range",
        table_name="ods_wb_search_traffic",
    )
    op.drop_table("ods_wb_search_traffic")
