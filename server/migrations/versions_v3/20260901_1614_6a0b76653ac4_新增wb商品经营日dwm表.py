"""新增WB商品经营日DWM表

Revision ID: 6a0b76653ac4
Revises: 06b7070c30ee
Create Date: 2026-09-01 16:14:23.031675
"""

import sqlalchemy as sa

from alembic import op

revision = "6a0b76653ac4"
down_revision = "06b7070c30ee"
branch_labels = None
depends_on = None

TABLE = "dwm_wb_goods_oper_day"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("stat_date", sa.Date(), nullable=False, comment="平台统计日期"),
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column("nm_id", sa.BigInteger(), nullable=False, comment="WB商品编号"),
        sa.Column("vendor_code", sa.String(255), nullable=True, comment="卖家商品编号"),
        sa.Column("product_title", sa.Text(), nullable=True, comment="商品名称"),
        sa.Column(
            "product_title_cn", sa.Text(), nullable=True, comment="商品名称（中文）"
        ),
        sa.Column("brand_name", sa.String(255), nullable=True, comment="品牌"),
        sa.Column("subject_name", sa.String(255), nullable=True, comment="商品品类"),
        sa.Column(
            "subject_name_cn", sa.String(255), nullable=True, comment="商品品类（中文）"
        ),
        sa.Column(
            "has_funnel_data", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "has_order_data", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "has_return_data", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "has_ad_data", sa.Boolean(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "product_rating", sa.Numeric(5, 2), nullable=True, comment="商品评分"
        ),
        sa.Column(
            "feedback_rating", sa.Numeric(5, 2), nullable=True, comment="评论评分"
        ),
        sa.Column(
            "traffic_clicks", sa.BigInteger(), nullable=True, comment="商品点击数"
        ),
        sa.Column(
            "traffic_cart_qty", sa.BigInteger(), nullable=True, comment="商品加购数"
        ),
        sa.Column(
            "traffic_wishlist_qty", sa.BigInteger(), nullable=True, comment="商品收藏数"
        ),
        sa.Column(
            "funnel_order_qty", sa.BigInteger(), nullable=True, comment="漏斗下单商品量"
        ),
        sa.Column(
            "funnel_buyout_qty", sa.BigInteger(), nullable=True, comment="漏斗售出件数"
        ),
        sa.Column(
            "funnel_cancel_qty",
            sa.BigInteger(),
            nullable=True,
            comment="漏斗取消商品量",
        ),
        sa.Column(
            "funnel_order_amount",
            sa.Numeric(18, 4),
            nullable=True,
            comment="漏斗订单金额",
        ),
        sa.Column(
            "funnel_buyout_amount",
            sa.Numeric(18, 4),
            nullable=True,
            comment="漏斗售出金额",
        ),
        sa.Column(
            "funnel_cancel_amount",
            sa.Numeric(18, 4),
            nullable=True,
            comment="漏斗取消金额",
        ),
        sa.Column(
            "order_cnt",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
            comment="去重订单数",
        ),
        sa.Column(
            "order_qty",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
            comment="订单商品件数",
        ),
        sa.Column(
            "cancelled_order_cnt",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
            comment="取消订单数",
        ),
        sa.Column(
            "cancelled_qty",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
            comment="取消商品件数",
        ),
        sa.Column(
            "order_amount_sum",
            sa.Numeric(18, 4),
            nullable=True,
            comment="折后订单金额合计",
        ),
        sa.Column(
            "finished_amount_sum",
            sa.Numeric(18, 4),
            nullable=True,
            comment="最终价格合计",
        ),
        sa.Column(
            "return_cnt",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
            comment="退货记录数",
        ),
        sa.Column(
            "return_qty",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
            comment="退货件数",
        ),
        sa.Column(
            "return_ready_cnt",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
            comment="已准备退货数",
        ),
        sa.Column(
            "return_completed_cnt",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
            comment="已领取退货数",
        ),
        sa.Column(
            "return_expired_cnt",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
            comment="已过期退货数",
        ),
        sa.Column(
            "ad_campaign_cnt", sa.BigInteger(), nullable=True, comment="广告活动数"
        ),
        sa.Column("ad_views", sa.BigInteger(), nullable=True, comment="广告曝光量"),
        sa.Column("ad_clicks", sa.BigInteger(), nullable=True, comment="广告点击数"),
        sa.Column("ad_to_cart", sa.BigInteger(), nullable=True, comment="广告加购数"),
        sa.Column(
            "ad_order_cnt", sa.BigInteger(), nullable=True, comment="广告归因订单数"
        ),
        sa.Column(
            "ad_cancelled_cnt", sa.BigInteger(), nullable=True, comment="广告取消数"
        ),
        sa.Column(
            "ad_sales_qty", sa.BigInteger(), nullable=True, comment="广告归因销量"
        ),
        sa.Column(
            "ad_spend_amount", sa.Numeric(18, 4), nullable=True, comment="广告花费"
        ),
        sa.Column(
            "ad_attributed_sales_amount",
            sa.Numeric(18, 4),
            nullable=True,
            comment="广告归因销售额",
        ),
        sa.Column("ad_currency", sa.String(10), nullable=True, comment="广告金额币种"),
        sa.Column(
            "has_ad_currency_conflict",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "traffic_cart_rate",
            sa.Numeric(12, 6),
            nullable=True,
            comment="加购率（加购/点击）",
        ),
        sa.Column(
            "traffic_order_rate",
            sa.Numeric(12, 6),
            nullable=True,
            comment="下单率（漏斗下单/点击）",
        ),
        sa.Column(
            "traffic_buyout_rate",
            sa.Numeric(12, 6),
            nullable=True,
            comment="售出率（漏斗售出/点击）",
        ),
        sa.Column(
            "order_cancel_rate", sa.Numeric(12, 6), nullable=True, comment="订单取消率"
        ),
        sa.Column(
            "return_rate_ordered",
            sa.Numeric(12, 6),
            nullable=True,
            comment="按下单件数计算的退货率",
        ),
        sa.Column(
            "return_rate_buyout",
            sa.Numeric(12, 6),
            nullable=True,
            comment="按漏斗售出件数计算的退货率",
        ),
        sa.Column("ad_ctr", sa.Numeric(12, 6), nullable=True, comment="广告点击率"),
        sa.Column(
            "ad_cart_rate", sa.Numeric(12, 6), nullable=True, comment="广告加购率"
        ),
        sa.Column("ad_cvr", sa.Numeric(12, 6), nullable=True, comment="广告订单转化率"),
        sa.Column(
            "ad_cpc", sa.Numeric(18, 6), nullable=True, comment="广告单次点击成本"
        ),
        sa.Column(
            "ad_cpo", sa.Numeric(18, 6), nullable=True, comment="广告单笔订单成本"
        ),
        sa.Column(
            "ad_roas", sa.Numeric(18, 6), nullable=True, comment="广告投入产出比"
        ),
        sa.Column("ad_drr", sa.Numeric(12, 6), nullable=True, comment="广告费用率"),
        sa.Column(
            "ad_click_share",
            sa.Numeric(12, 6),
            nullable=True,
            comment="广告点击占商品点击比例",
        ),
        sa.Column(
            "estimated_organic_clicks",
            sa.BigInteger(),
            nullable=True,
            comment="估算自然点击",
        ),
        sa.Column(
            "has_click_scope_conflict",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("update_time", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("stat_date", "shop_id", "nm_id"),
        comment="DWM-WB商品流量、交易、退货与广告经营日宽表",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        "idx_dwm_wb_goods_oper_nm_date",
        TABLE,
        ["nm_id", "stat_date"],
        unique=False,
    )
    op.create_index(
        "idx_dwm_wb_goods_oper_shop_date",
        TABLE,
        ["shop_id", "stat_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_dwm_wb_goods_oper_shop_date", table_name=TABLE)
    op.drop_index("idx_dwm_wb_goods_oper_nm_date", table_name=TABLE)
    op.drop_table(TABLE)
