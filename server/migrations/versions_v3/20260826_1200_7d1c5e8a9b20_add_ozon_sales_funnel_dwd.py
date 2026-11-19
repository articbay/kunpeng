"""add ozon sales funnel dwd

Revision ID: 7d1c5e8a9b20
Revises: fce52063dc73
Create Date: 2026-08-26 12:00:00
"""

import sqlalchemy as sa

from alembic import op

revision = "7d1c5e8a9b20"
down_revision = "fce52063dc73"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dwd_ozon_sales_funnel_detail",
        sa.Column(
            "id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"
        ),
        sa.Column(
            "source_ods_id",
            sa.BigInteger(),
            nullable=False,
            comment="来源 ods_ozon_analytics_data_daily.id",
        ),
        sa.Column("shop_id", sa.Integer(), nullable=False, comment="店铺ID"),
        sa.Column(
            "offer_id", sa.String(length=255), nullable=True, comment="卖家商品编号"
        ),
        sa.Column("sku", sa.BigInteger(), nullable=False, comment="Ozon SKU"),
        sa.Column("product_name", sa.Text(), nullable=True, comment="商品名称"),
        sa.Column(
            "product_name_cn", sa.Text(), nullable=True, comment="商品名称（中文）"
        ),
        sa.Column(
            "category_name", sa.String(length=255), nullable=True, comment="商品品类"
        ),
        sa.Column(
            "category_name_cn",
            sa.String(length=255),
            nullable=True,
            comment="商品品类（中文）",
        ),
        sa.Column("stat_date", sa.Date(), nullable=False, comment="统计日期"),
        sa.Column(
            "hits_view_search",
            sa.BigInteger(),
            nullable=True,
            comment="搜索和类目展示次数",
        ),
        sa.Column(
            "hits_view_pdp",
            sa.BigInteger(),
            nullable=True,
            comment="商品详情页浏览次数",
        ),
        sa.Column(
            "hits_view", sa.BigInteger(), nullable=True, comment="总展示/浏览次数"
        ),
        sa.Column(
            "session_view_search",
            sa.BigInteger(),
            nullable=True,
            comment="搜索和类目访问用户数",
        ),
        sa.Column(
            "session_view_pdp",
            sa.BigInteger(),
            nullable=True,
            comment="商品详情页访问用户数",
        ),
        sa.Column(
            "session_view", sa.BigInteger(), nullable=True, comment="总访问用户数"
        ),
        sa.Column(
            "hits_tocart_search",
            sa.BigInteger(),
            nullable=True,
            comment="搜索和类目加购次数",
        ),
        sa.Column(
            "hits_tocart_pdp",
            sa.BigInteger(),
            nullable=True,
            comment="商品详情页加购次数",
        ),
        sa.Column("hits_tocart", sa.BigInteger(), nullable=True, comment="总加购次数"),
        sa.Column(
            "conv_tocart_search",
            sa.Numeric(18, 6),
            nullable=True,
            comment="搜索和类目加购转化率（API原值）",
        ),
        sa.Column(
            "conv_tocart_pdp",
            sa.Numeric(18, 6),
            nullable=True,
            comment="商品详情页加购转化率（API原值）",
        ),
        sa.Column(
            "conv_tocart",
            sa.Numeric(18, 6),
            nullable=True,
            comment="总加购转化率（API原值）",
        ),
        sa.Column(
            "ordered_units", sa.BigInteger(), nullable=True, comment="下单商品件数"
        ),
        sa.Column("revenue", sa.Numeric(18, 4), nullable=True, comment="下单金额"),
        sa.Column(
            "delivered_units", sa.BigInteger(), nullable=True, comment="送达商品件数"
        ),
        sa.Column(
            "cancellations", sa.BigInteger(), nullable=True, comment="取消商品件数"
        ),
        sa.Column("returns", sa.BigInteger(), nullable=True, comment="退货商品件数"),
        sa.Column(
            "position_category",
            sa.Numeric(18, 6),
            nullable=True,
            comment="搜索和类目平均位置",
        ),
        sa.Column(
            "cart_to_order_rate",
            sa.Numeric(18, 6),
            nullable=True,
            comment="加购至下单转化率（项目计算，%）",
        ),
        sa.Column(
            "has_core_metrics",
            sa.Boolean(),
            nullable=False,
            comment="基础指标组是否返回该行",
        ),
        sa.Column(
            "has_outcome_metrics",
            sa.Boolean(),
            nullable=False,
            comment="结果指标组是否返回该行",
        ),
        sa.Column(
            "source_synced_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="来源ODS最近同步时间",
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_ods_id", name="uq_dwd_ozon_sales_funnel_source_ods"
        ),
        sa.UniqueConstraint(
            "shop_id", "stat_date", "sku", name="uq_dwd_ozon_sales_funnel_shop_date_sku"
        ),
        comment="Ozon销售漏斗SKU日明细表",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        "idx_dwd_ozon_sales_funnel_offer",
        "dwd_ozon_sales_funnel_detail",
        ["offer_id"],
        unique=False,
    )
    op.create_index(
        "idx_dwd_ozon_sales_funnel_shop_date",
        "dwd_ozon_sales_funnel_detail",
        ["shop_id", "stat_date"],
        unique=False,
    )
    op.create_index(
        "idx_dwd_ozon_sales_funnel_sku",
        "dwd_ozon_sales_funnel_detail",
        ["sku"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_dwd_ozon_sales_funnel_sku", table_name="dwd_ozon_sales_funnel_detail"
    )
    op.drop_index(
        "idx_dwd_ozon_sales_funnel_shop_date", table_name="dwd_ozon_sales_funnel_detail"
    )
    op.drop_index(
        "idx_dwd_ozon_sales_funnel_offer", table_name="dwd_ozon_sales_funnel_detail"
    )
    op.drop_table("dwd_ozon_sales_funnel_detail")
