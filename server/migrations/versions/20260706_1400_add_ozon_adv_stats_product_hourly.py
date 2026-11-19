"""add ods_ozon_adv_stats_product_hourly (Ozon 广告SKU小时统计表)

新增 Ozon 广告 SKU 级小时统计表，口径参照 Wildberries 广告小时统计:
Performance API 仅提供按天累计数据，小时数据通过「当天累计 - 已写入小时累计」
计算当前小时增量得到，由定时任务每小时幂等落库。

Revision ID: add_ozon_adv_hourly_20260706
Revises: add_name_zh_20260706
Create Date: 2026-07-06 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision = "add_ozon_adv_hourly_20260706"
down_revision = "add_name_zh_20260706"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ods_ozon_adv_stats_product_hourly",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("shop_id", sa.Integer(), nullable=False, comment="店铺ID"),
        sa.Column("row_data", sa.JSON(), nullable=False, comment="原始JSON数据（当天累计快照）"),
        sa.Column("campaign_id", mysql.VARCHAR(length=64), nullable=False, comment="广告活动ID"),
        sa.Column("sku", sa.BigInteger(), nullable=False, comment="商品SKU"),
        sa.Column("stat_date", sa.Date(), nullable=False, comment="统计日期"),
        sa.Column("stat_hour", sa.Integer(), nullable=False, comment="统计小时（0-23）"),
        sa.Column("title", mysql.TEXT(), nullable=True, comment="商品名称"),
        sa.Column("search_query", mysql.VARCHAR(length=500), nullable=True, comment="搜索词"),
        sa.Column("price", mysql.DECIMAL(precision=18, scale=4), nullable=True, comment="商品价格（当天累计快照）"),
        sa.Column("views", sa.BigInteger(), nullable=True, comment="展现量（当前小时增量）"),
        sa.Column("clicks", sa.BigInteger(), nullable=True, comment="点击次数（当前小时增量）"),
        sa.Column("ctr", mysql.DECIMAL(precision=10, scale=4), nullable=True, comment="点击率(%)（当天累计快照）"),
        sa.Column("to_cart", sa.BigInteger(), nullable=True, comment="加购次数（当前小时增量）"),
        sa.Column("avg_bid", mysql.DECIMAL(precision=18, scale=4), nullable=True, comment="平均出价（当天累计快照）"),
        sa.Column("money_spent", mysql.DECIMAL(precision=18, scale=4), nullable=True, comment="广告费用(₽)（当前小时增量）"),
        sa.Column("orders", sa.BigInteger(), nullable=True, comment="订单数（当前小时增量）"),
        sa.Column("orders_money", mysql.DECIMAL(precision=18, scale=4), nullable=True, comment="订单销售额(₽)（当前小时增量）"),
        sa.Column("models", sa.BigInteger(), nullable=True, comment="含组合卡的订单数（当前小时增量）"),
        sa.Column("models_money", mysql.DECIMAL(precision=18, scale=4), nullable=True, comment="含组合卡的销售额(₽)（当前小时增量）"),
        sa.Column("drr", mysql.DECIMAL(precision=10, scale=4), nullable=True, comment="广告费用份额DRR(%)（当天累计快照）"),
        sa.Column("general_drr", mysql.DECIMAL(precision=10, scale=4), nullable=True, comment="总DRR(%)（当天累计快照）"),
        sa.Column("product_gmv", mysql.DECIMAL(precision=18, scale=4), nullable=True, comment="商品GMV(₽)（当前小时增量）"),
        sa.Column("create_time", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
        sa.Column("update_time", sa.DateTime(timezone=True), nullable=True, comment="更新时间"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "shop_id", "campaign_id", "sku", "stat_date", "stat_hour",
            name="uq_ods_ozon_adv_stats_product_hourly_key",
        ),
        comment="Ozon广告SKU小时统计表",
    )
    op.create_index("idx_ods_ozon_adv_stats_product_hourly_campaign_id", "ods_ozon_adv_stats_product_hourly", ["campaign_id"], unique=False)
    op.create_index("idx_ods_ozon_adv_stats_product_hourly_date", "ods_ozon_adv_stats_product_hourly", ["stat_date"], unique=False)
    op.create_index("idx_ods_ozon_adv_stats_product_hourly_hour", "ods_ozon_adv_stats_product_hourly", ["stat_hour"], unique=False)
    op.create_index("idx_ods_ozon_adv_stats_product_hourly_shop_id", "ods_ozon_adv_stats_product_hourly", ["shop_id"], unique=False)
    op.create_index("idx_ods_ozon_adv_stats_product_hourly_sku", "ods_ozon_adv_stats_product_hourly", ["sku"], unique=False)
    op.create_index(op.f("ix_ods_ozon_adv_stats_product_hourly_shop_id"), "ods_ozon_adv_stats_product_hourly", ["shop_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ods_ozon_adv_stats_product_hourly_shop_id"), table_name="ods_ozon_adv_stats_product_hourly")
    op.drop_index("idx_ods_ozon_adv_stats_product_hourly_sku", table_name="ods_ozon_adv_stats_product_hourly")
    op.drop_index("idx_ods_ozon_adv_stats_product_hourly_shop_id", table_name="ods_ozon_adv_stats_product_hourly")
    op.drop_index("idx_ods_ozon_adv_stats_product_hourly_hour", table_name="ods_ozon_adv_stats_product_hourly")
    op.drop_index("idx_ods_ozon_adv_stats_product_hourly_date", table_name="ods_ozon_adv_stats_product_hourly")
    op.drop_index("idx_ods_ozon_adv_stats_product_hourly_campaign_id", table_name="ods_ozon_adv_stats_product_hourly")
    op.drop_table("ods_ozon_adv_stats_product_hourly")
