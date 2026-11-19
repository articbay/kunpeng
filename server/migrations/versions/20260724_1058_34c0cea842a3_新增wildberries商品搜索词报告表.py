"""新增Wildberries商品搜索词报告表

Revision ID: 34c0cea842a3
Revises: 1166dfad1d2c
Create Date: 2026-07-24 10:58:13.252531
"""

import sqlalchemy as sa
from alembic import op

revision = "34c0cea842a3"
down_revision = "1166dfad1d2c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ods_wb_product_search_texts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column("date_from", sa.Date(), nullable=False, comment="报告开始日期"),
        sa.Column("date_to", sa.Date(), nullable=False, comment="报告结束日期"),
        sa.Column(
            "nm_id", sa.BigInteger(), nullable=False, comment="Wildberries商品ID"
        ),
        sa.Column(
            "search_text", sa.String(length=1000), nullable=False, comment="搜索词"
        ),
        sa.Column(
            "search_text_hash",
            sa.String(length=64),
            nullable=False,
            comment="标准化搜索词哈希",
        ),
        sa.Column(
            "top_order_by",
            sa.String(length=32),
            nullable=False,
            comment="取榜排序指标",
        ),
        sa.Column(
            "subject_name", sa.String(length=255), nullable=True, comment="商品分类"
        ),
        sa.Column("brand_name", sa.String(length=255), nullable=True, comment="品牌"),
        sa.Column(
            "vendor_code", sa.String(length=255), nullable=True, comment="卖家货号"
        ),
        sa.Column(
            "product_name", sa.String(length=500), nullable=True, comment="商品名称"
        ),
        sa.Column(
            "is_card_rated", sa.Boolean(), nullable=True, comment="商品卡是否有评分"
        ),
        sa.Column(
            "rating",
            sa.Numeric(precision=10, scale=4),
            nullable=True,
            comment="商品评分",
        ),
        sa.Column(
            "feedback_rating",
            sa.Numeric(precision=10, scale=4),
            nullable=True,
            comment="反馈评分",
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
            "frequency_current",
            sa.BigInteger(),
            nullable=True,
            comment="当前搜索频次",
        ),
        sa.Column(
            "frequency_dynamics",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="搜索频次变化",
        ),
        sa.Column(
            "week_frequency", sa.BigInteger(), nullable=True, comment="周搜索频次"
        ),
        sa.Column(
            "median_position_current",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="当前中位排名",
        ),
        sa.Column(
            "median_position_dynamics",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="中位排名变化",
        ),
        sa.Column(
            "avg_position_current",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="当前平均排名",
        ),
        sa.Column(
            "avg_position_dynamics",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="平均排名变化",
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
            "open_card_percentile",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="打开商品卡百分位",
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
            "add_to_cart_percentile",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="加购百分位",
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
        sa.Column(
            "open_to_cart_percentile",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="打开到加购转化率百分位",
        ),
        sa.Column("orders_current", sa.BigInteger(), nullable=True, comment="订单数"),
        sa.Column(
            "orders_dynamics",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="订单数变化",
        ),
        sa.Column(
            "orders_percentile",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="订单数百分位",
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
            "cart_to_order_percentile",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="加购到下单转化率百分位",
        ),
        sa.Column(
            "visibility_current",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="当前可见度",
        ),
        sa.Column(
            "visibility_dynamics",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="可见度变化",
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
            "search_text_hash",
            "top_order_by",
            name="uq_wb_product_search_text_window_term",
        ),
        comment="Wildberries商品自然搜索词报告表",
    )
    op.create_index(
        "idx_wb_product_search_text_date_range",
        "ods_wb_product_search_texts",
        ["date_from", "date_to"],
        unique=False,
    )
    op.create_index(
        "idx_wb_product_search_text_hash",
        "ods_wb_product_search_texts",
        ["search_text_hash"],
        unique=False,
    )
    op.create_index(
        "idx_wb_product_search_text_nm_id",
        "ods_wb_product_search_texts",
        ["nm_id"],
        unique=False,
    )
    op.create_index(
        "idx_wb_product_search_text_shop_id",
        "ods_wb_product_search_texts",
        ["shop_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ods_wb_product_search_texts_id"),
        "ods_wb_product_search_texts",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_ods_wb_product_search_texts_id"),
        table_name="ods_wb_product_search_texts",
    )
    op.drop_index(
        "idx_wb_product_search_text_shop_id",
        table_name="ods_wb_product_search_texts",
    )
    op.drop_index(
        "idx_wb_product_search_text_nm_id",
        table_name="ods_wb_product_search_texts",
    )
    op.drop_index(
        "idx_wb_product_search_text_hash",
        table_name="ods_wb_product_search_texts",
    )
    op.drop_index(
        "idx_wb_product_search_text_date_range",
        table_name="ods_wb_product_search_texts",
    )
    op.drop_table("ods_wb_product_search_texts")
