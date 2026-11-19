"""新增Ozon经营分析ODS表

Revision ID: 805203c7b547
Revises: 839c47d148ed
Create Date: 2026-08-25 02:20:19.030174

"""

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision = "805203c7b547"
down_revision = "839c47d148ed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    metric_columns = _metric_columns()
    op.create_table(
        "ods_ozon_analytics_data_daily",
        sa.Column(
            "id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"
        ),
        sa.Column("shop_id", sa.Integer(), nullable=False, comment="店铺ID"),
        sa.Column("sku", sa.BigInteger(), nullable=False, comment="Ozon SKU"),
        sa.Column("sku_name", mysql.TEXT(), nullable=True, comment="API返回的商品名称"),
        sa.Column("stat_date", sa.Date(), nullable=False, comment="平台统计日期"),
        sa.Column(
            "source_date_from", sa.Date(), nullable=False, comment="API请求开始日期"
        ),
        sa.Column(
            "source_date_to", sa.Date(), nullable=False, comment="API请求结束日期"
        ),
        sa.Column(
            "requested_metrics_core",
            sa.JSON(),
            nullable=False,
            comment="核心指标请求顺序",
        ),
        sa.Column(
            "requested_metrics_outcome",
            sa.JSON(),
            nullable=False,
            comment="履约指标请求顺序",
        ),
        sa.Column(
            "row_data_core", sa.JSON(), nullable=True, comment="核心指标API原始行"
        ),
        sa.Column(
            "row_data_outcome", sa.JSON(), nullable=True, comment="履约指标API原始行"
        ),
        sa.Column(
            "has_core_metrics",
            sa.Boolean(),
            nullable=False,
            comment="核心指标组是否返回该行",
        ),
        sa.Column(
            "has_outcome_metrics",
            sa.Boolean(),
            nullable=False,
            comment="履约指标组是否返回该行",
        ),
        sa.Column(
            "api_timestamp_core",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="核心指标报告生成时间",
        ),
        sa.Column(
            "api_timestamp_outcome",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="履约指标报告生成时间",
        ),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="最近成功同步时间",
        ),
        *metric_columns,
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "update_time", sa.DateTime(timezone=True), nullable=True, comment="更新时间"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shop_id",
            "sku",
            "stat_date",
            name="uq_ods_ozon_analytics_daily_shop_sku_date",
        ),
        comment="Ozon经营分析SKU日明细表",
    )
    op.create_index(
        "idx_ods_ozon_analytics_daily_shop_date",
        "ods_ozon_analytics_data_daily",
        ["shop_id", "stat_date"],
    )
    op.create_index(
        "idx_ods_ozon_analytics_daily_sku_date",
        "ods_ozon_analytics_data_daily",
        ["sku", "stat_date"],
    )

    op.create_table(
        "ods_ozon_analytics_totals_window",
        sa.Column(
            "id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"
        ),
        sa.Column("shop_id", sa.Integer(), nullable=False, comment="店铺ID"),
        sa.Column("date_from", sa.Date(), nullable=False, comment="API请求开始日期"),
        sa.Column("date_to", sa.Date(), nullable=False, comment="API请求结束日期"),
        sa.Column(
            "requested_metrics_core",
            sa.JSON(),
            nullable=False,
            comment="核心指标请求顺序",
        ),
        sa.Column(
            "requested_metrics_outcome",
            sa.JSON(),
            nullable=False,
            comment="履约指标请求顺序",
        ),
        sa.Column(
            "raw_totals_core",
            sa.JSON(),
            nullable=False,
            comment="核心指标原始totals数组",
        ),
        sa.Column(
            "raw_totals_outcome",
            sa.JSON(),
            nullable=False,
            comment="履约指标原始totals数组",
        ),
        sa.Column(
            "api_timestamp_core",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="核心指标报告生成时间",
        ),
        sa.Column(
            "api_timestamp_outcome",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="履约指标报告生成时间",
        ),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="最近成功同步时间",
        ),
        *_metric_columns(),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "update_time", sa.DateTime(timezone=True), nullable=True, comment="更新时间"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shop_id",
            "date_from",
            "date_to",
            name="uq_ods_ozon_analytics_totals_shop_window",
        ),
        comment="Ozon经营分析请求窗口汇总表",
    )
    op.create_index(
        "idx_ods_ozon_analytics_totals_shop_window",
        "ods_ozon_analytics_totals_window",
        ["shop_id", "date_from", "date_to"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_ods_ozon_analytics_totals_shop_window",
        table_name="ods_ozon_analytics_totals_window",
    )
    op.drop_table("ods_ozon_analytics_totals_window")
    op.drop_index(
        "idx_ods_ozon_analytics_daily_sku_date",
        table_name="ods_ozon_analytics_data_daily",
    )
    op.drop_index(
        "idx_ods_ozon_analytics_daily_shop_date",
        table_name="ods_ozon_analytics_data_daily",
    )
    op.drop_table("ods_ozon_analytics_data_daily")


def _metric_columns():
    return [
        sa.Column("revenue", mysql.DECIMAL(18, 4), nullable=True, comment="下单金额"),
        sa.Column(
            "ordered_units", sa.BigInteger(), nullable=True, comment="下单商品件数"
        ),
        sa.Column(
            "hits_view_search",
            sa.BigInteger(),
            nullable=True,
            comment="搜索/类目展示次数",
        ),
        sa.Column(
            "hits_view_pdp",
            sa.BigInteger(),
            nullable=True,
            comment="商品详情页展示次数",
        ),
        sa.Column("hits_view", sa.BigInteger(), nullable=True, comment="总展示次数"),
        sa.Column(
            "hits_tocart_search",
            sa.BigInteger(),
            nullable=True,
            comment="搜索/类目加购次数",
        ),
        sa.Column(
            "hits_tocart_pdp",
            sa.BigInteger(),
            nullable=True,
            comment="商品详情页加购次数",
        ),
        sa.Column("hits_tocart", sa.BigInteger(), nullable=True, comment="总加购次数"),
        sa.Column(
            "session_view_search",
            sa.BigInteger(),
            nullable=True,
            comment="搜索/类目访问用户数",
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
            "conv_tocart_search",
            mysql.DECIMAL(18, 6),
            nullable=True,
            comment="搜索/类目加购转化率(API原值)",
        ),
        sa.Column(
            "conv_tocart_pdp",
            mysql.DECIMAL(18, 6),
            nullable=True,
            comment="商品详情页加购转化率(API原值)",
        ),
        sa.Column(
            "conv_tocart",
            mysql.DECIMAL(18, 6),
            nullable=True,
            comment="总加购转化率(API原值)",
        ),
        sa.Column("returns", sa.BigInteger(), nullable=True, comment="退货商品件数"),
        sa.Column(
            "cancellations", sa.BigInteger(), nullable=True, comment="取消商品件数"
        ),
        sa.Column(
            "delivered_units", sa.BigInteger(), nullable=True, comment="送达商品件数"
        ),
        sa.Column(
            "position_category",
            mysql.DECIMAL(18, 6),
            nullable=True,
            comment="搜索及类目平均位置",
        ),
    ]
