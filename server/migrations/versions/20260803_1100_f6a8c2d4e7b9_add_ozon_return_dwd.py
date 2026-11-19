"""add Ozon return DWD

Revision ID: f6a8c2d4e7b9
Revises: e3b7c9d5f1a2
Create Date: 2026-08-03 11:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6a8c2d4e7b9"
down_revision: Union[str, None] = "e3b7c9d5f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "dwd_ozon_return_detail"


def upgrade() -> None:
    """Create the Ozon return-product business detail table."""
    if sa.inspect(op.get_bind()).has_table(TABLE_NAME):
        return

    op.create_table(
        TABLE_NAME,
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column("return_id", sa.BigInteger(), nullable=False, comment="退货ID"),
        sa.Column(
            "nm_id",
            sa.BigInteger(),
            nullable=False,
            comment="Ozon SKU（沿用nm_id命名）",
        ),
        sa.Column("brand_name", sa.String(255), nullable=True, comment="品牌名称"),
        sa.Column("category_name", sa.String(255), nullable=True, comment="商品品类"),
        sa.Column("product_name", sa.Text(), nullable=True, comment="商品名称"),
        sa.Column(
            "product_barcode", sa.String(255), nullable=True, comment="商品条形码"
        ),
        sa.Column("offer_id", sa.String(255), nullable=True, comment="商家货号"),
        sa.Column(
            "logistic_barcode", sa.String(255), nullable=True, comment="退货物流条码"
        ),
        sa.Column("exemplar_id", sa.BigInteger(), nullable=True, comment="商品实例ID"),
        sa.Column("status_id", sa.Integer(), nullable=True, comment="状态ID"),
        sa.Column("status_display_name", sa.String(255), nullable=True, comment="状态"),
        sa.Column("status_sys_name", sa.String(255), nullable=True, comment="状态编码"),
        sa.Column(
            "status_change_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="状态变更时间",
        ),
        sa.Column(
            "ready_to_pickup_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="已准备好取货时间",
        ),
        sa.Column(
            "picked_up_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="已被领取时间",
        ),
        sa.Column(
            "storage_expire_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="免费存储到期时间",
        ),
        sa.Column(
            "utilization_forecast_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="预计销毁时间",
        ),
        sa.Column("storage_days", sa.Integer(), nullable=True, comment="仓储天数"),
        sa.Column(
            "pickup_duration_hours",
            sa.Numeric(12, 2),
            nullable=True,
            comment="提货用时（小时）",
        ),
        sa.Column(
            "order_date",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="下单时间",
        ),
        sa.Column("return_reason_name", sa.Text(), nullable=True, comment="退货原因"),
        sa.Column("posting_number", sa.String(100), nullable=True, comment="配货单号"),
        sa.Column("order_id", sa.BigInteger(), nullable=True, comment="订单ID"),
        sa.Column("order_number", sa.String(100), nullable=True, comment="订单编号"),
        sa.Column(
            "srid",
            sa.String(255),
            nullable=True,
            comment="系统订单号（兼容字段，取Ozon order_number）",
        ),
        sa.Column("place_id", sa.BigInteger(), nullable=True, comment="当前地点ID"),
        sa.Column("place_name", sa.String(255), nullable=True, comment="当前地点名称"),
        sa.Column("place_address", sa.Text(), nullable=True, comment="当前地点地址"),
        sa.Column(
            "target_place_id", sa.BigInteger(), nullable=True, comment="目标提货点ID"
        ),
        sa.Column(
            "target_place_name",
            sa.String(255),
            nullable=True,
            comment="目标提货点名称",
        ),
        sa.Column(
            "target_place_address", sa.Text(), nullable=True, comment="目标提货点地址"
        ),
        sa.Column("return_type", sa.String(50), nullable=True, comment="退货类型"),
        sa.Column(
            "schema", sa.String(20), nullable=True, comment="发货模式（FBO/FBS）"
        ),
        sa.Column(
            "return_date",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="退货日期",
        ),
        sa.Column("is_opened", sa.Boolean(), nullable=True, comment="是否拆封"),
        sa.Column(
            "is_super_econom", sa.Boolean(), nullable=True, comment="是否超级经济"
        ),
        sa.Column("quantity", sa.Integer(), nullable=True, comment="退货数量"),
        sa.Column("price_amount", sa.Numeric(18, 4), nullable=True, comment="商品金额"),
        sa.Column(
            "price_currency", sa.String(10), nullable=True, comment="商品金额币种"
        ),
        sa.PrimaryKeyConstraint("shop_id", "return_id", "nm_id"),
        comment="Ozon退货业务明细表",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("idx_dwd_ozon_return_posting", TABLE_NAME, ["posting_number"])
    op.create_index("idx_dwd_ozon_return_order_date", TABLE_NAME, ["order_date"])
    op.create_index("idx_dwd_ozon_return_status", TABLE_NAME, ["status_sys_name"])
    op.create_index("idx_dwd_ozon_return_offer", TABLE_NAME, ["offer_id"])


def downgrade() -> None:
    """Drop the Ozon return DWD table."""
    if sa.inspect(op.get_bind()).has_table(TABLE_NAME):
        op.drop_table(TABLE_NAME)
