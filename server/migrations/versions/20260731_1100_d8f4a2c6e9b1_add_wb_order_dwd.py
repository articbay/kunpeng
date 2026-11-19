"""add Wildberries order DWD table

Revision ID: d8f4a2c6e9b1
Revises: b7d3e9f1a6c4
Create Date: 2026-07-31 11:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d8f4a2c6e9b1"
down_revision: Union[str, None] = "b7d3e9f1a6c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "dwd_wb_order_detail"
REPORT_INDEX = "idx_ods_sales_report_shop_order"
FUNNEL_INDEX = "idx_ods_funnel_shop_nm_date"


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    """Create the order DWD table, source indexes and initial ODS backfill."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table(TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
            sa.Column("order_id", sa.BigInteger(), nullable=False, comment="工作编号"),
            sa.Column("supply_id", sa.String(255), nullable=True, comment="供货ID"),
            sa.Column("sticker_id", sa.String(255), nullable=True, comment="贴纸ID"),
            sa.Column(
                "order_dt",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="创建日期",
            ),
            sa.Column("title", sa.Text(), nullable=True, comment="商品名称"),
            sa.Column("tech_size", sa.String(100), nullable=True, comment="尺寸"),
            sa.Column("color", sa.String(100), nullable=True, comment="颜色"),
            sa.Column("barcode", sa.String(255), nullable=True, comment="条码"),
            sa.Column(
                "retail_price",
                sa.Numeric(18, 2),
                nullable=True,
                comment="零售价",
            ),
            sa.Column("currency", sa.String(10), nullable=True, comment="货币"),
            sa.Column("nm_id", sa.BigInteger(), nullable=True, comment="WB货号"),
            sa.Column(
                "supplier_article",
                sa.String(255),
                nullable=True,
                comment="卖家货号",
            ),
            sa.Column(
                "warehouse_id",
                sa.BigInteger(),
                nullable=True,
                comment="卖家仓库ID",
            ),
            sa.Column(
                "warehouse_name",
                sa.String(255),
                nullable=True,
                comment="卖家仓库",
            ),
            sa.Column("wb_status", sa.String(100), nullable=True, comment="工作状态"),
            sa.Column("address", sa.Text(), nullable=True, comment="地址"),
            sa.Column("is_b2b", sa.Boolean(), nullable=True, comment="是否B2B"),
            sa.PrimaryKeyConstraint("shop_id", "order_id"),
            comment="Wildberries订单业务明细表",
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )
        op.create_index("idx_dwd_wb_order_nm_id", TABLE_NAME, ["nm_id"])
        op.create_index("idx_dwd_wb_order_order_dt", TABLE_NAME, ["order_dt"])
        op.create_index("idx_dwd_wb_order_wb_status", TABLE_NAME, ["wb_status"])
        op.create_index("idx_dwd_wb_order_supply_id", TABLE_NAME, ["supply_id"])
        op.create_index("idx_dwd_wb_order_sticker_id", TABLE_NAME, ["sticker_id"])

    inspector = sa.inspect(bind)
    if inspector.has_table("ods_wb_sales_reports"):
        if REPORT_INDEX not in _index_names(inspector, "ods_wb_sales_reports"):
            op.create_index(
                REPORT_INDEX,
                "ods_wb_sales_reports",
                ["shop_id", "order_id"],
            )

    inspector = sa.inspect(bind)
    if inspector.has_table("ods_wb_sales_funnels"):
        if FUNNEL_INDEX not in _index_names(inspector, "ods_wb_sales_funnels"):
            op.create_index(
                FUNNEL_INDEX,
                "ods_wb_sales_funnels",
                ["shop_id", "nm_id", "date_to", "date_from"],
            )

    if sa.inspect(bind).has_table("ods_wb_marketplace_orders"):
        op.execute(
            sa.text(
                """
                INSERT INTO dwd_wb_order_detail (
                    shop_id,
                    order_id,
                    supply_id,
                    order_dt,
                    color,
                    barcode,
                    nm_id,
                    supplier_article,
                    warehouse_id,
                    wb_status,
                    address,
                    is_b2b
                )
                SELECT
                    marketplace.shop_id,
                    marketplace.order_id,
                    marketplace.supply_id,
                    marketplace.created_at,
                    NULLIF(marketplace.color_code, ''),
                    NULLIF(
                        NULLIF(
                            JSON_UNQUOTE(
                                JSON_EXTRACT(marketplace.skus, '$[0]')
                            ),
                            'null'
                        ),
                        ''
                    ),
                    marketplace.nm_id,
                    marketplace.article,
                    marketplace.warehouse_id,
                    marketplace.wb_status,
                    CASE
                        WHEN JSON_TYPE(marketplace.address) = 'OBJECT'
                        THEN COALESCE(
                            NULLIF(
                                JSON_UNQUOTE(
                                    JSON_EXTRACT(
                                        marketplace.address,
                                        '$.fullAddress'
                                    )
                                ),
                                ''
                            ),
                            NULLIF(
                                JSON_UNQUOTE(
                                    JSON_EXTRACT(
                                        marketplace.address,
                                        '$.address'
                                    )
                                ),
                                ''
                            )
                        )
                        WHEN JSON_TYPE(marketplace.address) = 'STRING'
                        THEN NULLIF(JSON_UNQUOTE(marketplace.address), '')
                        ELSE NULL
                    END,
                    CASE LOWER(
                        JSON_UNQUOTE(
                            JSON_EXTRACT(marketplace.options, '$.isB2B')
                        )
                    )
                        WHEN 'true' THEN 1
                        WHEN 'false' THEN 0
                        ELSE NULL
                    END
                FROM ods_wb_marketplace_orders AS marketplace
                WHERE marketplace.order_id IS NOT NULL
                ON DUPLICATE KEY UPDATE
                    supply_id = VALUES(supply_id),
                    order_dt = VALUES(order_dt),
                    color = VALUES(color),
                    barcode = VALUES(barcode),
                    nm_id = VALUES(nm_id),
                    supplier_article = VALUES(supplier_article),
                    warehouse_id = VALUES(warehouse_id),
                    wb_status = VALUES(wb_status),
                    address = VALUES(address),
                    is_b2b = VALUES(is_b2b)
                """
            )
        )


def downgrade() -> None:
    """Drop the DWD table and its dedicated source indexes."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("ods_wb_sales_funnels"):
        if FUNNEL_INDEX in _index_names(inspector, "ods_wb_sales_funnels"):
            op.drop_index(FUNNEL_INDEX, table_name="ods_wb_sales_funnels")

    inspector = sa.inspect(bind)
    if inspector.has_table("ods_wb_sales_reports"):
        if REPORT_INDEX in _index_names(inspector, "ods_wb_sales_reports"):
            op.drop_index(REPORT_INDEX, table_name="ods_wb_sales_reports")

    if sa.inspect(bind).has_table(TABLE_NAME):
        op.drop_table(TABLE_NAME)
