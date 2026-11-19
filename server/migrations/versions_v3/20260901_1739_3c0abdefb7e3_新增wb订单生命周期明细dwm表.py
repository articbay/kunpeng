"""新增WB订单生命周期明细DWM表

Revision ID: 3c0abdefb7e3
Revises: 6a0b76653ac4
Create Date: 2026-09-01 17:39:52
"""

import sqlalchemy as sa

from alembic import op

revision = "3c0abdefb7e3"
down_revision = "6a0b76653ac4"
branch_labels = None
depends_on = None

TABLE = "dwm_wb_order_lifecycle_detail"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column(
            "shop_id",
            sa.BigInteger(),
            primary_key=True,
            nullable=False,
            comment="店铺ID",
        ),
        sa.Column(
            "srid",
            sa.String(255),
            primary_key=True,
            nullable=False,
            comment="订单唯一ID",
        ),
        sa.Column(
            "order_id", sa.BigInteger(), nullable=True, comment="Marketplace组装订单ID"
        ),
        sa.Column(
            "order_uid",
            sa.String(255),
            nullable=True,
            comment="Marketplace订单购物车ID",
        ),
        sa.Column("supply_id", sa.String(255), nullable=True, comment="FBS供货单ID"),
        sa.Column("sticker_id", sa.String(255), nullable=True, comment="订单贴纸ID"),
        sa.Column("g_number", sa.String(255), nullable=True, comment="订单组号"),
        sa.Column("nm_id", sa.BigInteger(), nullable=True, comment="WB商品ID"),
        sa.Column(
            "supplier_article", sa.String(255), nullable=True, comment="卖家货号"
        ),
        sa.Column("barcode", sa.String(255), nullable=True, comment="条码"),
        sa.Column("product_title", sa.Text(), nullable=True, comment="商品名称"),
        sa.Column(
            "product_title_cn", sa.Text(), nullable=True, comment="商品名称（中文）"
        ),
        sa.Column("subject_name", sa.String(255), nullable=True, comment="商品品类"),
        sa.Column(
            "subject_name_cn", sa.String(255), nullable=True, comment="商品品类（中文）"
        ),
        sa.Column("tech_size", sa.String(100), nullable=True, comment="尺码"),
        sa.Column(
            "tech_size_cn", sa.String(100), nullable=True, comment="尺码（中文）"
        ),
        sa.Column(
            "delivery_type", sa.String(50), nullable=True, comment="Marketplace配送类型"
        ),
        sa.Column("warehouse_name", sa.String(255), nullable=True, comment="仓库名称"),
        sa.Column(
            "warehouse_name_cn",
            sa.String(255),
            nullable=True,
            comment="仓库名称（中文）",
        ),
        sa.Column("country_name", sa.String(255), nullable=True, comment="国家"),
        sa.Column(
            "country_name_cn", sa.String(255), nullable=True, comment="国家（中文）"
        ),
        sa.Column("region_name", sa.String(255), nullable=True, comment="地区"),
        sa.Column(
            "region_name_cn", sa.String(255), nullable=True, comment="地区（中文）"
        ),
        sa.Column("total_price", sa.Numeric(18, 2), nullable=True, comment="订单原价"),
        sa.Column(
            "price_with_disc", sa.Numeric(18, 2), nullable=True, comment="折后价格"
        ),
        sa.Column(
            "finished_price", sa.Numeric(18, 2), nullable=True, comment="最终价格"
        ),
        sa.Column(
            "converted_price",
            sa.Numeric(18, 2),
            nullable=True,
            comment="Marketplace折算价格",
        ),
        sa.Column(
            "currency_code", sa.Integer(), nullable=True, comment="Marketplace货币代码"
        ),
        sa.Column(
            "order_at", sa.DateTime(timezone=True), nullable=False, comment="下单时间"
        ),
        sa.Column(
            "last_change_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="订单最后修改时间",
        ),
        sa.Column(
            "cancelled_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="取消时间",
        ),
        sa.Column(
            "supplier_status", sa.String(100), nullable=True, comment="卖家处理状态"
        ),
        sa.Column(
            "supplier_status_cn",
            sa.String(100),
            nullable=True,
            comment="卖家处理状态（中文）",
        ),
        sa.Column("wb_status", sa.String(100), nullable=True, comment="WB当前状态"),
        sa.Column(
            "wb_status_cn", sa.String(100), nullable=True, comment="WB当前状态（中文）"
        ),
        sa.Column(
            "lifecycle_stage",
            sa.String(50),
            nullable=False,
            comment="归一化生命周期阶段",
        ),
        sa.Column(
            "lifecycle_stage_cn",
            sa.String(100),
            nullable=False,
            comment="归一化生命周期阶段中文",
        ),
        sa.Column(
            "is_cancelled",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
            comment="是否取消",
        ),
        sa.Column(
            "is_sold",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
            comment="是否有可靠售出证据",
        ),
        sa.Column(
            "is_terminal",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
            comment="是否终态",
        ),
        sa.Column("supply_name", sa.String(500), nullable=True, comment="供货单名称"),
        sa.Column(
            "supply_is_done", sa.Boolean(), nullable=True, comment="供货单是否完成"
        ),
        sa.Column(
            "supply_created_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="供货单创建时间",
        ),
        sa.Column(
            "supply_scan_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="供货单扫描时间",
        ),
        sa.Column(
            "supply_closed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="供货单关闭时间",
        ),
        sa.Column(
            "supply_rejected_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="供货单拒绝时间",
        ),
        sa.Column(
            "sale_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="销售接口确认的成交时间",
        ),
        sa.Column(
            "sale_last_change_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="销售记录最后修改时间",
        ),
        sa.Column("sale_id", sa.String(255), nullable=True, comment="销售事件ID"),
        sa.Column(
            "sale_event_type", sa.String(20), nullable=True, comment="销售事件类型"
        ),
        sa.Column(
            "finance_row_cnt",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
            comment="关联财务明细数",
        ),
        sa.Column(
            "finance_sale_row_cnt",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
            comment="正向销售财务明细数",
        ),
        sa.Column(
            "finance_first_sale_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="首次正向财务销售时间",
        ),
        sa.Column(
            "return_cnt",
            sa.BigInteger(),
            server_default=sa.text("0"),
            nullable=False,
            comment="已关联退货记录数",
        ),
        sa.Column(
            "latest_return_srid",
            sa.String(255),
            nullable=True,
            comment="最新退货记录SRID",
        ),
        sa.Column(
            "latest_return_order_id",
            sa.BigInteger(),
            nullable=True,
            comment="最新退货组装订单ID",
        ),
        sa.Column(
            "latest_return_status",
            sa.String(255),
            nullable=True,
            comment="最新退货状态",
        ),
        sa.Column(
            "latest_return_status_cn",
            sa.String(255),
            nullable=True,
            comment="最新退货状态（中文）",
        ),
        sa.Column(
            "latest_return_type", sa.String(255), nullable=True, comment="最新退货类型"
        ),
        sa.Column(
            "latest_return_type_cn",
            sa.String(255),
            nullable=True,
            comment="最新退货类型（中文）",
        ),
        sa.Column(
            "latest_return_reason",
            sa.String(500),
            nullable=True,
            comment="最新退货原因",
        ),
        sa.Column(
            "latest_return_reason_cn",
            sa.String(500),
            nullable=True,
            comment="最新退货原因（中文）",
        ),
        sa.Column(
            "return_ready_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="最近退货待领取时间",
        ),
        sa.Column(
            "return_completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="最近退货领取完成时间",
        ),
        sa.Column(
            "return_expired_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="最近退货过期时间",
        ),
        sa.Column(
            "return_link_method",
            sa.String(50),
            nullable=True,
            comment="退货与订单关联方法",
        ),
        sa.Column(
            "has_return_identity_conflict",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
            comment="退货身份关联是否冲突",
        ),
        sa.Column(
            "has_statistics_order_data",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
            comment="是否有统计订单来源",
        ),
        sa.Column(
            "has_marketplace_order_data",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
            comment="是否有Marketplace订单来源",
        ),
        sa.Column(
            "has_supply_data",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
            comment="是否有关联供货单来源",
        ),
        sa.Column(
            "has_sale_data",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
            comment="是否有销售接口来源",
        ),
        sa.Column(
            "has_finance_data",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
            comment="是否有财务明细来源",
        ),
        sa.Column(
            "has_return_data",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
            comment="是否有关联退货来源",
        ),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            comment="创建时间",
        ),
        sa.Column(
            "update_time", sa.DateTime(timezone=True), nullable=True, comment="更新时间"
        ),
        comment="DWM-WB订单商品生命周期明细表",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("idx_dwm_wb_lifecycle_order_at", TABLE, ["shop_id", "order_at"])
    op.create_index("idx_dwm_wb_lifecycle_order_id", TABLE, ["shop_id", "order_id"])
    op.create_index("idx_dwm_wb_lifecycle_nm_id", TABLE, ["shop_id", "nm_id"])
    op.create_index("idx_dwm_wb_lifecycle_stage", TABLE, ["shop_id", "lifecycle_stage"])
    op.create_index("idx_dwm_wb_lifecycle_wb_status", TABLE, ["shop_id", "wb_status"])
    op.create_index("idx_dwm_wb_lifecycle_supply", TABLE, ["shop_id", "supply_id"])


def downgrade() -> None:
    op.drop_index("idx_dwm_wb_lifecycle_supply", table_name=TABLE)
    op.drop_index("idx_dwm_wb_lifecycle_wb_status", table_name=TABLE)
    op.drop_index("idx_dwm_wb_lifecycle_stage", table_name=TABLE)
    op.drop_index("idx_dwm_wb_lifecycle_nm_id", table_name=TABLE)
    op.drop_index("idx_dwm_wb_lifecycle_order_id", table_name=TABLE)
    op.drop_index("idx_dwm_wb_lifecycle_order_at", table_name=TABLE)
    op.drop_table(TABLE)
