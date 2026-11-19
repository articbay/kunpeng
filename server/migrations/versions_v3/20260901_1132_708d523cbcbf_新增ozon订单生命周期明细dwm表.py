"""新增Ozon订单生命周期明细DWM表

Revision ID: 708d523cbcbf
Revises: 15a40516a399
Create Date: 2026-09-01 11:32:12.389223
"""

import sqlalchemy as sa

from alembic import op

revision = "708d523cbcbf"
down_revision = "15a40516a399"
branch_labels = None
depends_on = None

TABLE = "dwm_ozon_order_lifecycle_detail"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column(
            "fulfillment_type",
            sa.String(length=3),
            nullable=False,
            comment="履约方式（FBS/FBO）",
        ),
        sa.Column(
            "posting_number",
            sa.String(length=100),
            nullable=False,
            comment="发货号码",
        ),
        sa.Column("sku", sa.BigInteger(), nullable=False, comment="Ozon SKU"),
        sa.Column("order_id", sa.BigInteger(), nullable=True, comment="Ozon订单ID"),
        sa.Column(
            "order_number", sa.String(length=100), nullable=True, comment="订单号"
        ),
        sa.Column("offer_id", sa.String(length=255), nullable=True, comment="货号"),
        sa.Column("product_name", sa.Text(), nullable=True, comment="商品名称"),
        sa.Column(
            "product_name_cn", sa.Text(), nullable=True, comment="商品名称（中文）"
        ),
        sa.Column("quantity", sa.Integer(), nullable=True, comment="下单数量"),
        sa.Column(
            "status_code",
            sa.String(length=50),
            nullable=True,
            comment="订单当前状态编码",
        ),
        sa.Column(
            "substatus_code",
            sa.String(length=50),
            nullable=True,
            comment="订单当前子状态编码",
        ),
        sa.Column(
            "status_name_cn",
            sa.String(length=100),
            nullable=True,
            comment="订单当前状态中文",
        ),
        sa.Column(
            "in_process_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="进入处理时间，业务上近似作为下单时间",
        ),
        sa.Column(
            "shipment_date",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="实际发货日期",
        ),
        sa.Column(
            "transferred_to_delivery_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="实际移交配送日期",
        ),
        sa.Column(
            "delivery_date",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="送往自提点/进入实际配送日期",
        ),
        sa.Column(
            "promised_delivery_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="承诺送达时间",
        ),
        sa.Column(
            "cancellation_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="取消日期",
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
            comment="累计退货数量",
        ),
        sa.Column(
            "first_return_date",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="首次退货日期",
        ),
        sa.Column(
            "latest_return_id",
            sa.BigInteger(),
            nullable=True,
            comment="最新退货记录ID",
        ),
        sa.Column(
            "latest_return_status_sys_name",
            sa.String(length=255),
            nullable=True,
            comment="最新退货状态编码",
        ),
        sa.Column(
            "latest_return_status_display_name_cn",
            sa.String(length=255),
            nullable=True,
            comment="最新退货状态中文",
        ),
        sa.Column(
            "latest_return_status_change_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="最新退货状态变更时间",
        ),
        sa.Column(
            "latest_return_reason_name_cn",
            sa.Text(),
            nullable=True,
            comment="最新退货原因中文",
        ),
        sa.Column(
            "last_ready_to_pickup_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="最近一次到达取货点时间",
        ),
        sa.Column(
            "last_picked_up_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="最近一次向卖家退货时间",
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
        sa.PrimaryKeyConstraint("shop_id", "fulfillment_type", "posting_number", "sku"),
        comment="DWM-Ozon订单商品生命周期明细表",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        "idx_dwm_ozon_lifecycle_in_process",
        TABLE,
        ["shop_id", "in_process_at"],
        unique=False,
    )
    op.create_index(
        "idx_dwm_ozon_lifecycle_order",
        TABLE,
        ["shop_id", "order_number"],
        unique=False,
    )
    op.create_index(
        "idx_dwm_ozon_lifecycle_sku",
        TABLE,
        ["shop_id", "sku"],
        unique=False,
    )
    op.create_index(
        "idx_dwm_ozon_lifecycle_status",
        TABLE,
        ["shop_id", "status_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_dwm_ozon_lifecycle_status", table_name=TABLE)
    op.drop_index("idx_dwm_ozon_lifecycle_sku", table_name=TABLE)
    op.drop_index("idx_dwm_ozon_lifecycle_order", table_name=TABLE)
    op.drop_index("idx_dwm_ozon_lifecycle_in_process", table_name=TABLE)
    op.drop_table(TABLE)
