"""新增WB销售漏斗DWD表

Revision ID: f4a7c2e91b3d
Revises: c9f0a7791118
Create Date: 2026-07-30 12:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "f4a7c2e91b3d"
down_revision = "c9f0a7791118"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dwd_wb_sales_funnel_detail",
        sa.Column(
            "id",
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
            comment="主键ID",
        ),
        sa.Column(
            "source_ods_id",
            sa.BigInteger(),
            nullable=False,
            comment="来源 ods_wb_sales_funnels.id",
        ),
        sa.Column("shop_id", sa.Integer(), nullable=False, comment="店铺ID"),
        sa.Column(
            "vendor_code",
            sa.String(length=255),
            nullable=True,
            comment="卖家商品编号",
        ),
        sa.Column(
            "nm_id",
            sa.BigInteger(),
            nullable=False,
            comment="WB商品编号",
        ),
        sa.Column(
            "title",
            sa.String(length=1000),
            nullable=True,
            comment="名称",
        ),
        sa.Column(
            "subject_name",
            sa.String(length=255),
            nullable=True,
            comment="项目",
        ),
        sa.Column(
            "brand_name",
            sa.String(length=255),
            nullable=True,
            comment="品牌",
        ),
        sa.Column("tags", sa.JSON(), nullable=True, comment="商品标签"),
        sa.Column(
            "product_rating",
            sa.Integer(),
            nullable=True,
            comment="商品详情页评分",
        ),
        sa.Column(
            "feedback_rating",
            sa.Numeric(precision=5, scale=2),
            nullable=True,
            comment="评论评分",
        ),
        sa.Column(
            "date_from",
            sa.Date(),
            nullable=False,
            comment="统计开始日期",
        ),
        sa.Column(
            "date_to",
            sa.Date(),
            nullable=False,
            comment="统计结束日期（技术字段）",
        ),
        sa.Column(
            "open_count",
            sa.Integer(),
            nullable=True,
            comment="商品点击",
        ),
        sa.Column(
            "cart_count",
            sa.Integer(),
            nullable=True,
            comment="商品加购",
        ),
        sa.Column(
            "add_to_wishlist",
            sa.Integer(),
            nullable=True,
            comment="加入收藏夹",
        ),
        sa.Column(
            "order_count",
            sa.Integer(),
            nullable=True,
            comment="下单商品量",
        ),
        sa.Column(
            "buyout_count",
            sa.Integer(),
            nullable=True,
            comment="售出件数",
        ),
        sa.Column(
            "cancel_count",
            sa.Integer(),
            nullable=True,
            comment="取消订单商品量",
        ),
        sa.Column(
            "add_to_cart_percent",
            sa.Numeric(precision=8, scale=2),
            nullable=True,
            comment="加购转化率",
        ),
        sa.Column(
            "cart_to_order_percent",
            sa.Numeric(precision=8, scale=2),
            nullable=True,
            comment="下单转化率",
        ),
        sa.Column(
            "buyout_percent",
            sa.Numeric(precision=8, scale=2),
            nullable=True,
            comment="购买转化率",
        ),
        sa.Column(
            "order_sum",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="订单金额",
        ),
        sa.Column(
            "buyout_sum",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="售出金额",
        ),
        sa.Column(
            "cancel_sum",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="取消订单金额",
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
            name="uq_dwd_wb_funnel_shop_window_nm",
        ),
        sa.UniqueConstraint(
            "source_ods_id",
            name="uq_dwd_wb_funnel_source_ods",
        ),
        comment="Wildberries 销售漏斗商品明细 DWD 表",
    )
    op.create_index(
        "idx_dwd_wb_funnel_date_range",
        "dwd_wb_sales_funnel_detail",
        ["date_from", "date_to"],
        unique=False,
    )
    op.create_index(
        "idx_dwd_wb_funnel_nm_id",
        "dwd_wb_sales_funnel_detail",
        ["nm_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_dwd_wb_funnel_nm_id",
        table_name="dwd_wb_sales_funnel_detail",
    )
    op.drop_index(
        "idx_dwd_wb_funnel_date_range",
        table_name="dwd_wb_sales_funnel_detail",
    )
    op.drop_table("dwd_wb_sales_funnel_detail")
