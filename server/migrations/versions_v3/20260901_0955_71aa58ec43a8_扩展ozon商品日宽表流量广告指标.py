"""扩展Ozon商品日宽表流量广告指标

Revision ID: 71aa58ec43a8
Revises: e7bc14b82f34
Create Date: 2026-09-01 09:55:17.901395
"""

import sqlalchemy as sa

from alembic import op

revision = "71aa58ec43a8"
down_revision = "e7bc14b82f34"
branch_labels = None
depends_on = None

TABLE = "dwm_ozon_goods_trade_return_day"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column("category_name", sa.String(255), nullable=True, comment="商品品类"),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "category_name_cn",
            sa.String(255),
            nullable=True,
            comment="商品品类（中文）",
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "has_funnel_data",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
            comment="销售漏斗DWD是否存在该商品日",
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "has_traffic_metrics",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
            comment="销售漏斗是否实际返回流量指标",
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "traffic_views_search",
            sa.BigInteger(),
            nullable=True,
            comment="搜索和类目展示次数",
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "traffic_views_pdp",
            sa.BigInteger(),
            nullable=True,
            comment="商品详情页浏览次数",
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "traffic_views", sa.BigInteger(), nullable=True, comment="总展示/浏览次数"
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "traffic_visitors_search",
            sa.BigInteger(),
            nullable=True,
            comment="搜索和类目访问用户数",
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "traffic_visitors_pdp",
            sa.BigInteger(),
            nullable=True,
            comment="商品详情页访问用户数",
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "traffic_visitors", sa.BigInteger(), nullable=True, comment="总访问用户数"
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "traffic_to_cart_search",
            sa.BigInteger(),
            nullable=True,
            comment="搜索和类目加购次数",
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "traffic_to_cart_pdp",
            sa.BigInteger(),
            nullable=True,
            comment="商品详情页加购次数",
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "traffic_to_cart", sa.BigInteger(), nullable=True, comment="总加购次数"
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "traffic_cart_rate",
            sa.Numeric(12, 6),
            nullable=True,
            comment="全站加购率（总加购/总访问用户，0-1）",
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "has_ad_data",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
            comment="广告效率DWD是否存在该商品日",
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "ad_campaign_cnt", sa.BigInteger(), nullable=True, comment="广告活动数"
        ),
    )
    op.add_column(
        TABLE,
        sa.Column("ad_views", sa.BigInteger(), nullable=True, comment="广告展现量"),
    )
    op.add_column(
        TABLE,
        sa.Column("ad_clicks", sa.BigInteger(), nullable=True, comment="广告点击次数"),
    )
    op.add_column(
        TABLE,
        sa.Column("ad_to_cart", sa.BigInteger(), nullable=True, comment="广告加购次数"),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "ad_spend_amount", sa.Numeric(18, 4), nullable=True, comment="广告花费"
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "ad_spend_currency", sa.String(10), nullable=True, comment="广告花费币种"
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "ad_attributed_order_cnt",
            sa.BigInteger(),
            nullable=True,
            comment="广告归因订单数",
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "ad_attributed_sales_amount",
            sa.Numeric(18, 4),
            nullable=True,
            comment="广告归因销售额",
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "ad_ctr",
            sa.Numeric(12, 6),
            nullable=True,
            comment="广告点击率（点击/展现，0-1）",
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "ad_cart_rate",
            sa.Numeric(12, 6),
            nullable=True,
            comment="广告加购率（加购/点击，0-1）",
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "ad_cpc", sa.Numeric(18, 4), nullable=True, comment="广告单次点击成本"
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "ad_cpo", sa.Numeric(18, 4), nullable=True, comment="广告单笔订单成本"
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "ad_roas",
            sa.Numeric(18, 6),
            nullable=True,
            comment="广告投入产出比（归因销售额/花费）",
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "ad_drr",
            sa.Numeric(12, 6),
            nullable=True,
            comment="广告费用率（花费/归因销售额，0-1）",
        ),
    )
    op.alter_column(
        TABLE,
        "stat_date",
        existing_type=sa.Date(),
        existing_nullable=False,
        comment="平台统计日期",
        existing_comment="订单统计日期",
    )
    op.create_table_comment(
        TABLE,
        "DWM-Ozon商品交易、退货、流量与广告日宽表",
        existing_comment="DWM-Ozon商品订单与退货日宽表（订单日期cohort）",
    )


def downgrade() -> None:
    op.create_table_comment(
        TABLE,
        "DWM-Ozon商品订单与退货日宽表（订单日期cohort）",
        existing_comment="DWM-Ozon商品交易、退货、流量与广告日宽表",
    )
    op.alter_column(
        TABLE,
        "stat_date",
        existing_type=sa.Date(),
        existing_nullable=False,
        comment="订单统计日期",
        existing_comment="平台统计日期",
    )
    for column_name in reversed(
        [
            "category_name",
            "category_name_cn",
            "has_funnel_data",
            "has_traffic_metrics",
            "traffic_views_search",
            "traffic_views_pdp",
            "traffic_views",
            "traffic_visitors_search",
            "traffic_visitors_pdp",
            "traffic_visitors",
            "traffic_to_cart_search",
            "traffic_to_cart_pdp",
            "traffic_to_cart",
            "traffic_cart_rate",
            "has_ad_data",
            "ad_campaign_cnt",
            "ad_views",
            "ad_clicks",
            "ad_to_cart",
            "ad_spend_amount",
            "ad_spend_currency",
            "ad_attributed_order_cnt",
            "ad_attributed_sales_amount",
            "ad_ctr",
            "ad_cart_rate",
            "ad_cpc",
            "ad_cpo",
            "ad_roas",
            "ad_drr",
        ]
    ):
        op.drop_column(TABLE, column_name)
