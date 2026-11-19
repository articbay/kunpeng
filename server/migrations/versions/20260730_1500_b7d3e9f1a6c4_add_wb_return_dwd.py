"""add Wildberries return DWD table

Revision ID: b7d3e9f1a6c4
Revises: a5e9c7d1b4f2
Create Date: 2026-07-30 15:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7d3e9f1a6c4"
down_revision: Union[str, None] = "a5e9c7d1b4f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "dwd_wb_return_detail"


def upgrade() -> None:
    """Create the DWD table when absent and backfill it from ODS."""
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(TABLE_NAME):
        op.create_table(
            TABLE_NAME,
            sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
            sa.Column("brand", sa.String(255), nullable=True, comment="品牌"),
            sa.Column(
                "subject_name", sa.String(255), nullable=True, comment="商品品类"
            ),
            sa.Column("barcode", sa.String(255), nullable=True, comment="条形码"),
            sa.Column("nm_id", sa.BigInteger(), nullable=True, comment="WB货号"),
            sa.Column("bar_code", sa.String(255), nullable=True, comment="条码"),
            sa.Column("sticker_id", sa.String(255), nullable=True, comment="标签ID"),
            sa.Column("status", sa.String(255), nullable=True, comment="状态"),
            sa.Column(
                "ready_to_return_dt",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="准备好取货时间",
            ),
            sa.Column(
                "completed_dt",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="已被领取时间",
            ),
            sa.Column(
                "expired_dt",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="过期时间",
            ),
            sa.Column("return_type", sa.String(255), nullable=True, comment="退货类型"),
            sa.Column("order_date", sa.Date(), nullable=True, comment="下单日期"),
            sa.Column("reason", sa.String(500), nullable=True, comment="退货原因"),
            sa.Column("order_id", sa.BigInteger(), nullable=True, comment="配货单号"),
            sa.Column("srid", sa.String(255), nullable=False, comment="系统订单号"),
            sa.Column(
                "dst_office_address",
                sa.String(500),
                nullable=True,
                comment="地址",
            ),
            sa.Column(
                "dst_office_id", sa.BigInteger(), nullable=True, comment="地址ID"
            ),
            sa.PrimaryKeyConstraint("shop_id", "srid"),
            comment="Wildberries退货业务明细表",
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_unicode_ci",
        )
        op.create_index("idx_dwd_wb_return_nm_id", TABLE_NAME, ["nm_id"], unique=False)
        op.create_index(
            "idx_dwd_wb_return_status", TABLE_NAME, ["status"], unique=False
        )
        op.create_index(
            "idx_dwd_wb_return_order_date",
            TABLE_NAME,
            ["order_date"],
            unique=False,
        )

    if sa.inspect(bind).has_table("ods_wb_goods_returns"):
        op.execute(
            sa.text(
                """
                INSERT INTO dwd_wb_return_detail (
                    shop_id,
                    brand,
                    subject_name,
                    barcode,
                    nm_id,
                    bar_code,
                    sticker_id,
                    status,
                    ready_to_return_dt,
                    completed_dt,
                    expired_dt,
                    return_type,
                    order_date,
                    reason,
                    order_id,
                    srid,
                    dst_office_address,
                    dst_office_id
                )
                SELECT
                    source_shop_id,
                    source_brand,
                    source_subject_name,
                    source_barcode,
                    source_nm_id,
                    source_bar_code,
                    source_sticker_id,
                    source_status,
                    source_ready_to_return_dt,
                    source_completed_dt,
                    source_expired_dt,
                    source_return_type,
                    source_order_date,
                    source_reason,
                    source_order_id,
                    source_srid,
                    source_dst_office_address,
                    source_dst_office_id
                FROM (
                    SELECT
                        shop_id AS source_shop_id,
                        brand AS source_brand,
                        subject_name AS source_subject_name,
                        barcode AS source_barcode,
                        nm_id AS source_nm_id,
                        NULL AS source_bar_code,
                        sticker_id AS source_sticker_id,
                        status AS source_status,
                        ready_to_return_dt AS source_ready_to_return_dt,
                        completed_dt AS source_completed_dt,
                        expired_dt AS source_expired_dt,
                        return_type AS source_return_type,
                        order_dt AS source_order_date,
                        reason AS source_reason,
                        order_id AS source_order_id,
                        srid AS source_srid,
                        dst_office_address AS source_dst_office_address,
                        dst_office_id AS source_dst_office_id
                    FROM ods_wb_goods_returns
                    WHERE srid IS NOT NULL
                ) AS source_rows
                ON DUPLICATE KEY UPDATE
                    brand = source_brand,
                    subject_name = source_subject_name,
                    barcode = source_barcode,
                    nm_id = source_nm_id,
                    sticker_id = source_sticker_id,
                    status = source_status,
                    ready_to_return_dt = source_ready_to_return_dt,
                    completed_dt = source_completed_dt,
                    expired_dt = source_expired_dt,
                    return_type = source_return_type,
                    order_date = source_order_date,
                    reason = source_reason,
                    order_id = source_order_id,
                    dst_office_address = source_dst_office_address,
                    dst_office_id = source_dst_office_id
                """
            )
        )


def downgrade() -> None:
    """Drop the Wildberries return DWD table."""
    if sa.inspect(op.get_bind()).has_table(TABLE_NAME):
        op.drop_table(TABLE_NAME)
