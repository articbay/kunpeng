"""expand WB order DWD and add statistics order DWD

Revision ID: e3b7c9d5f1a2
Revises: d8f4a2c6e9b1
Create Date: 2026-07-31 16:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e3b7c9d5f1a2"
down_revision: Union[str, None] = "d8f4a2c6e9b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ORDER_TABLE = "dwd_wb_order_detail"
STATISTICS_TABLE = "dwd_wb_order_statistics_detail"


ORDER_COLUMNS = (
    sa.Column("delivery_type", sa.String(50), nullable=True, comment="配送类型"),
    sa.Column("supplier_status", sa.String(100), nullable=True, comment="卖家处理状态"),
    sa.Column("is_cancellable", sa.Boolean(), nullable=True, comment="是否可取消"),
    sa.Column("price", sa.Numeric(18, 2), nullable=True, comment="订单价格"),
    sa.Column("converted_price", sa.Numeric(18, 2), nullable=True, comment="折算价格"),
    sa.Column("currency_code", sa.Integer(), nullable=True, comment="货币代码"),
    sa.Column("office_id", sa.BigInteger(), nullable=True, comment="配送办公点ID"),
    sa.Column("cargo_type", sa.Integer(), nullable=True, comment="货物类型"),
    sa.Column("cross_border_type", sa.Integer(), nullable=True, comment="跨境类型"),
    sa.Column("is_zero_order", sa.Boolean(), nullable=True, comment="是否零订单"),
)


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    """Expand the operational order DWD and create the statistics-order DWD."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table(ORDER_TABLE):
        existing_columns = _column_names(inspector, ORDER_TABLE)
        for column in ORDER_COLUMNS:
            if column.name not in existing_columns:
                op.add_column(ORDER_TABLE, column)

        inspector = sa.inspect(bind)
        if "idx_dwd_wb_order_supplier_status" not in _index_names(
            inspector, ORDER_TABLE
        ):
            op.create_index(
                "idx_dwd_wb_order_supplier_status",
                ORDER_TABLE,
                ["supplier_status"],
            )

    inspector = sa.inspect(bind)
    if not inspector.has_table(STATISTICS_TABLE):
        op.create_table(
            STATISTICS_TABLE,
            sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
            sa.Column("srid", sa.String(255), nullable=False, comment="系统订单号"),
            sa.Column(
                "order_date",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="下单时间",
            ),
            sa.Column(
                "last_change_date",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="最后修改时间",
            ),
            sa.Column(
                "warehouse_name",
                sa.String(255),
                nullable=True,
                comment="仓库名称",
            ),
            sa.Column("country_name", sa.String(255), nullable=True, comment="国家"),
            sa.Column(
                "oblast_okrug_name",
                sa.String(255),
                nullable=True,
                comment="联邦管区",
            ),
            sa.Column("region_name", sa.String(255), nullable=True, comment="地区"),
            sa.Column(
                "supplier_article",
                sa.String(255),
                nullable=True,
                comment="卖家货号",
            ),
            sa.Column("nm_id", sa.BigInteger(), nullable=True, comment="WB货号"),
            sa.Column("barcode", sa.String(255), nullable=True, comment="条码"),
            sa.Column("category", sa.String(255), nullable=True, comment="商品分类"),
            sa.Column(
                "subject_name",
                sa.String(255),
                nullable=True,
                comment="商品品类",
            ),
            sa.Column("tech_size", sa.String(100), nullable=True, comment="尺码"),
            sa.Column("total_price", sa.Numeric(18, 2), nullable=True, comment="原价"),
            sa.Column(
                "discount_percent",
                sa.Integer(),
                nullable=True,
                comment="折扣百分比",
            ),
            sa.Column(
                "price_with_disc",
                sa.Numeric(18, 2),
                nullable=True,
                comment="折后价格",
            ),
            sa.Column(
                "finished_price",
                sa.Numeric(18, 2),
                nullable=True,
                comment="最终价格",
            ),
            sa.Column("is_cancel", sa.Boolean(), nullable=True, comment="是否取消"),
            sa.Column(
                "cancel_date",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="取消时间",
            ),
            sa.Column("sticker_id", sa.String(255), nullable=True, comment="贴纸ID"),
            sa.Column("g_number", sa.String(255), nullable=True, comment="订单组号"),
            sa.PrimaryKeyConstraint("shop_id", "srid"),
            comment="Wildberries统计订单业务明细表",
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )
        op.create_index(
            "idx_dwd_wb_order_stats_order_date",
            STATISTICS_TABLE,
            ["order_date"],
        )
        op.create_index("idx_dwd_wb_order_stats_nm_id", STATISTICS_TABLE, ["nm_id"])
        op.create_index(
            "idx_dwd_wb_order_stats_is_cancel",
            STATISTICS_TABLE,
            ["is_cancel"],
        )
        op.create_index(
            "idx_dwd_wb_order_stats_warehouse",
            STATISTICS_TABLE,
            ["warehouse_name"],
        )
        op.create_index(
            "idx_dwd_wb_order_stats_region",
            STATISTICS_TABLE,
            ["region_name"],
        )

    inspector = sa.inspect(bind)
    if inspector.has_table(ORDER_TABLE) and inspector.has_table(
        "ods_wb_marketplace_orders"
    ):
        op.execute(
            sa.text(
                """
                UPDATE dwd_wb_order_detail AS target
                INNER JOIN ods_wb_marketplace_orders AS source
                    ON source.shop_id = target.shop_id
                   AND source.order_id = target.order_id
                SET
                    target.delivery_type = source.delivery_type,
                    target.supplier_status = source.supplier_status,
                    target.is_cancellable = source.is_cancellable,
                    target.price = source.price,
                    target.converted_price = source.converted_price,
                    target.currency_code = source.currency_code,
                    target.office_id = source.office_id,
                    target.cargo_type = source.cargo_type,
                    target.cross_border_type = source.cross_border_type,
                    target.is_zero_order = source.is_zero_order
                """
            )
        )

    if sa.inspect(bind).has_table("ods_wb_supplier_orders"):
        op.execute(
            sa.text(
                """
                INSERT INTO dwd_wb_order_statistics_detail (
                    shop_id,
                    srid,
                    order_date,
                    last_change_date,
                    warehouse_name,
                    country_name,
                    oblast_okrug_name,
                    region_name,
                    supplier_article,
                    nm_id,
                    barcode,
                    category,
                    subject_name,
                    tech_size,
                    total_price,
                    discount_percent,
                    price_with_disc,
                    finished_price,
                    is_cancel,
                    cancel_date,
                    sticker_id,
                    g_number
                )
                SELECT
                    shop_id,
                    srid,
                    date,
                    last_change_date,
                    warehouse_name,
                    country_name,
                    oblast_okrug_name,
                    region_name,
                    supplier_article,
                    nm_id,
                    barcode,
                    category,
                    subject,
                    tech_size,
                    total_price,
                    discount_percent,
                    price_with_disc,
                    finished_price,
                    is_cancel,
                    cancel_date,
                    sticker,
                    g_number
                FROM ods_wb_supplier_orders
                WHERE srid IS NOT NULL
                  AND srid <> ''
                ON DUPLICATE KEY UPDATE
                    order_date = VALUES(order_date),
                    last_change_date = VALUES(last_change_date),
                    warehouse_name = VALUES(warehouse_name),
                    country_name = VALUES(country_name),
                    oblast_okrug_name = VALUES(oblast_okrug_name),
                    region_name = VALUES(region_name),
                    supplier_article = VALUES(supplier_article),
                    nm_id = VALUES(nm_id),
                    barcode = VALUES(barcode),
                    category = VALUES(category),
                    subject_name = VALUES(subject_name),
                    tech_size = VALUES(tech_size),
                    total_price = VALUES(total_price),
                    discount_percent = VALUES(discount_percent),
                    price_with_disc = VALUES(price_with_disc),
                    finished_price = VALUES(finished_price),
                    is_cancel = VALUES(is_cancel),
                    cancel_date = VALUES(cancel_date),
                    sticker_id = VALUES(sticker_id),
                    g_number = VALUES(g_number)
                """
            )
        )


def downgrade() -> None:
    """Drop the statistics DWD and remove operational-order extensions."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table(STATISTICS_TABLE):
        op.drop_table(STATISTICS_TABLE)

    inspector = sa.inspect(bind)
    if inspector.has_table(ORDER_TABLE):
        indexes = _index_names(inspector, ORDER_TABLE)
        if "idx_dwd_wb_order_supplier_status" in indexes:
            op.drop_index("idx_dwd_wb_order_supplier_status", table_name=ORDER_TABLE)
        columns = _column_names(inspector, ORDER_TABLE)
        for column in reversed(ORDER_COLUMNS):
            if column.name in columns:
                op.drop_column(ORDER_TABLE, column.name)
