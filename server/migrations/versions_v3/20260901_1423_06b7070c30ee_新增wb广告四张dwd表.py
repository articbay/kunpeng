"""新增WB广告四张DWD表

Revision ID: 06b7070c30ee
Revises: 708d523cbcbf
Create Date: 2026-09-01 14:23:20.653183
"""

import sqlalchemy as sa

from alembic import op

revision = "06b7070c30ee"
down_revision = "708d523cbcbf"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
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
    ]


def _fact_columns(*, hourly: bool) -> list[sa.Column]:
    columns = [
        sa.Column(
            "id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"
        ),
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column("advert_id", sa.BigInteger(), nullable=False, comment="广告活动ID"),
        sa.Column(
            "status", sa.Integer(), nullable=True, comment="构建时广告活动状态编码"
        ),
        sa.Column(
            "status_name",
            sa.String(64),
            nullable=True,
            comment="构建时广告活动状态名称",
        ),
        sa.Column(
            "payment_type", sa.String(20), nullable=True, comment="构建时计费类型"
        ),
        sa.Column("bid_type", sa.String(50), nullable=True, comment="构建时出价类型"),
        sa.Column("nm_id", sa.BigInteger(), nullable=False, comment="WB商品编号"),
        sa.Column("nm_name", sa.String(500), nullable=True, comment="商品名称"),
        sa.Column("stat_date", sa.Date(), nullable=False, comment="统计日期"),
    ]
    if hourly:
        columns.append(
            sa.Column(
                "stat_hour", sa.Integer(), nullable=False, comment="统计小时（0-23）"
            )
        )
    columns.extend(
        [
            sa.Column(
                "currency", sa.String(10), nullable=False, comment="原始金额币种"
            ),
            sa.Column("views", sa.BigInteger(), nullable=False, comment="浏览次数"),
            sa.Column("clicks", sa.BigInteger(), nullable=False, comment="点击次数"),
            sa.Column("atbs", sa.BigInteger(), nullable=False, comment="加购次数"),
            sa.Column("orders", sa.BigInteger(), nullable=False, comment="订单次数"),
            sa.Column("canceled", sa.BigInteger(), nullable=False, comment="取消次数"),
            sa.Column("shks", sa.BigInteger(), nullable=False, comment="SKU数量"),
            sa.Column(
                "sum_cost", sa.Numeric(18, 4), nullable=False, comment="原币花费"
            ),
            sa.Column(
                "sum_price", sa.Numeric(18, 4), nullable=False, comment="原币销售额"
            ),
            sa.Column(
                "cpc", sa.Numeric(18, 6), nullable=False, comment="原币单次点击成本"
            ),
            sa.Column(
                "ctr", sa.Numeric(18, 6), nullable=False, comment="点击率（0-1）"
            ),
            sa.Column("cr", sa.Numeric(18, 6), nullable=False, comment="转化率（0-1）"),
            sa.Column("roi", sa.Numeric(18, 6), nullable=False, comment="投入产出比"),
            sa.Column(
                "source_platform", sa.String(16), nullable=False, comment="来源平台"
            ),
            *_timestamps(),
        ]
    )
    return columns


def upgrade() -> None:
    op.create_table(
        "dwd_wb_advert_activity_detail",
        sa.Column(
            "id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"
        ),
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column(
            "snapshot_date",
            sa.Date(),
            nullable=False,
            comment="快照日期（平台业务日期）",
        ),
        sa.Column("advert_id", sa.BigInteger(), nullable=False, comment="广告活动ID"),
        sa.Column("nm_id", sa.BigInteger(), nullable=False, comment="WB商品编号"),
        sa.Column("advert_name", sa.String(500), nullable=True, comment="广告活动名称"),
        sa.Column("status", sa.Integer(), nullable=True, comment="广告活动状态编码"),
        sa.Column(
            "status_name", sa.String(64), nullable=True, comment="广告活动状态名称"
        ),
        sa.Column("bid_type", sa.String(50), nullable=True, comment="出价类型"),
        sa.Column("payment_type", sa.String(20), nullable=True, comment="计费类型"),
        sa.Column("currency", sa.String(10), nullable=True, comment="原始金额币种"),
        sa.Column(
            "placement_search", sa.Boolean(), nullable=True, comment="是否投放搜索"
        ),
        sa.Column(
            "placement_recommendations",
            sa.Boolean(),
            nullable=True,
            comment="是否投放推荐",
        ),
        sa.Column("subject_id", sa.BigInteger(), nullable=True, comment="商品类目ID"),
        sa.Column(
            "subject_name", sa.String(500), nullable=True, comment="商品类目名称"
        ),
        sa.Column(
            "bid_search",
            sa.BigInteger(),
            nullable=True,
            comment="搜索出价（接口原始最小货币单位）",
        ),
        sa.Column(
            "bid_recommendations",
            sa.BigInteger(),
            nullable=True,
            comment="推荐出价（接口原始最小货币单位）",
        ),
        sa.Column(
            "total_budget",
            sa.Numeric(18, 4),
            nullable=True,
            comment="活动预算（接口原始币种金额）",
        ),
        sa.Column(
            "budget_sync_date", sa.Date(), nullable=True, comment="预算来源同步日期"
        ),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shop_id",
            "advert_id",
            "nm_id",
            name="uq_dwd_wb_advert_activity_shop_advert_nm",
        ),
        comment="Wildberries广告活动商品当前配置快照",
    )
    op.create_index(
        "idx_dwd_wb_advert_activity_nm",
        "dwd_wb_advert_activity_detail",
        ["nm_id"],
    )
    op.create_index(
        "idx_dwd_wb_advert_activity_shop_status",
        "dwd_wb_advert_activity_detail",
        ["shop_id", "status"],
    )

    op.create_table(
        "dwd_wb_advert_bid_config",
        sa.Column(
            "id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"
        ),
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column(
            "snapshot_date",
            sa.Date(),
            nullable=False,
            comment="快照日期（平台业务日期）",
        ),
        sa.Column("advert_id", sa.BigInteger(), nullable=False, comment="广告活动ID"),
        sa.Column("nm_id", sa.BigInteger(), nullable=False, comment="WB商品编号"),
        sa.Column(
            "norm_query", sa.String(500), nullable=False, comment="标准查询词/搜索集群"
        ),
        sa.Column("is_active", sa.Boolean(), nullable=True, comment="关键词是否启用"),
        sa.Column("currency", sa.String(10), nullable=True, comment="出价原始币种"),
        sa.Column(
            "reach_max_bid_kopecks",
            sa.BigInteger(),
            nullable=True,
            comment="最大触达原始戈比值",
        ),
        sa.Column(
            "reach_max_bid",
            sa.Numeric(12, 4),
            nullable=True,
            comment="最大触达接口金额",
        ),
        sa.Column(
            "reach_medium_bid_kopecks",
            sa.BigInteger(),
            nullable=True,
            comment="中等触达原始戈比值",
        ),
        sa.Column(
            "reach_medium_bid",
            sa.Numeric(12, 4),
            nullable=True,
            comment="中等触达接口金额",
        ),
        sa.Column(
            "reach_min_bid_kopecks",
            sa.BigInteger(),
            nullable=True,
            comment="最小触达原始戈比值",
        ),
        sa.Column(
            "reach_min_bid",
            sa.Numeric(12, 4),
            nullable=True,
            comment="最小触达接口金额",
        ),
        sa.Column(
            "base_competitive_bid_kopecks",
            sa.BigInteger(),
            nullable=True,
            comment="竞争档位原始戈比值",
        ),
        sa.Column(
            "base_competitive_bid",
            sa.Numeric(12, 4),
            nullable=True,
            comment="竞争档位接口金额",
        ),
        sa.Column(
            "base_leaders_bid_kopecks",
            sa.BigInteger(),
            nullable=True,
            comment="领先档位原始戈比值",
        ),
        sa.Column(
            "base_leaders_bid",
            sa.Numeric(12, 4),
            nullable=True,
            comment="领先档位接口金额",
        ),
        sa.Column(
            "base_top2_bid_kopecks",
            sa.BigInteger(),
            nullable=True,
            comment="Top2档位原始戈比值",
        ),
        sa.Column(
            "base_top2_bid",
            sa.Numeric(12, 4),
            nullable=True,
            comment="Top2档位接口金额",
        ),
        sa.Column(
            "query_bid",
            sa.Numeric(12, 4),
            nullable=True,
            comment="关键词实际出价（接口原始值，不做汇率换算）",
        ),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shop_id",
            "advert_id",
            "nm_id",
            "norm_query",
            name="uq_dwd_wb_advert_bid_shop_advert_nm_query",
        ),
        comment="Wildberries Norm关键词当前出价配置快照",
    )
    op.create_index(
        "idx_dwd_wb_advert_bid_nm",
        "dwd_wb_advert_bid_config",
        ["nm_id"],
    )
    op.create_index(
        "idx_dwd_wb_advert_bid_shop_advert",
        "dwd_wb_advert_bid_config",
        ["shop_id", "advert_id"],
    )

    op.create_table(
        "dwd_wb_advert_stats_hourly_incr",
        *_fact_columns(hourly=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shop_id",
            "stat_date",
            "stat_hour",
            "advert_id",
            "nm_id",
            "currency",
            name="uq_dwd_wb_advert_hourly_dim",
        ),
        comment="Wildberries广告商品小时增量效果事实表",
    )
    op.create_index(
        "idx_dwd_wb_advert_hourly_advert_nm",
        "dwd_wb_advert_stats_hourly_incr",
        ["advert_id", "nm_id"],
    )
    op.create_index(
        "idx_dwd_wb_advert_hourly_shop_date",
        "dwd_wb_advert_stats_hourly_incr",
        ["shop_id", "stat_date"],
    )

    op.create_table(
        "dwd_wb_advert_stats_daily_incr",
        *_fact_columns(hourly=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shop_id",
            "stat_date",
            "advert_id",
            "nm_id",
            "currency",
            name="uq_dwd_wb_advert_daily_dim",
        ),
        comment="Wildberries广告商品日增量效果事实表",
    )
    op.create_index(
        "idx_dwd_wb_advert_daily_advert_nm",
        "dwd_wb_advert_stats_daily_incr",
        ["advert_id", "nm_id"],
    )
    op.create_index(
        "idx_dwd_wb_advert_daily_shop_date",
        "dwd_wb_advert_stats_daily_incr",
        ["shop_id", "stat_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_dwd_wb_advert_daily_shop_date",
        table_name="dwd_wb_advert_stats_daily_incr",
    )
    op.drop_index(
        "idx_dwd_wb_advert_daily_advert_nm",
        table_name="dwd_wb_advert_stats_daily_incr",
    )
    op.drop_table("dwd_wb_advert_stats_daily_incr")
    op.drop_index(
        "idx_dwd_wb_advert_hourly_shop_date",
        table_name="dwd_wb_advert_stats_hourly_incr",
    )
    op.drop_index(
        "idx_dwd_wb_advert_hourly_advert_nm",
        table_name="dwd_wb_advert_stats_hourly_incr",
    )
    op.drop_table("dwd_wb_advert_stats_hourly_incr")
    op.drop_index(
        "idx_dwd_wb_advert_bid_shop_advert",
        table_name="dwd_wb_advert_bid_config",
    )
    op.drop_index(
        "idx_dwd_wb_advert_bid_nm",
        table_name="dwd_wb_advert_bid_config",
    )
    op.drop_table("dwd_wb_advert_bid_config")
    op.drop_index(
        "idx_dwd_wb_advert_activity_shop_status",
        table_name="dwd_wb_advert_activity_detail",
    )
    op.drop_index(
        "idx_dwd_wb_advert_activity_nm",
        table_name="dwd_wb_advert_activity_detail",
    )
    op.drop_table("dwd_wb_advert_activity_detail")
