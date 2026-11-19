"""新增Wildberries区域销售报告表

Revision ID: 1166dfad1d2c
Revises: 6433594fe8b8
Create Date: 2026-07-24 10:06:00.443512

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1166dfad1d2c"
down_revision = "6433594fe8b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ods_wb_region_sales",
        sa.Column(
            "id",
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
            comment="主键ID",
        ),
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column("date_from", sa.Date(), nullable=False, comment="报告开始日期"),
        sa.Column("date_to", sa.Date(), nullable=False, comment="报告结束日期"),
        sa.Column(
            "row_key",
            sa.String(length=64),
            nullable=False,
            comment="地区商品维度哈希",
        ),
        sa.Column(
            "country_name",
            sa.String(length=100),
            nullable=True,
            comment="国家",
        ),
        sa.Column(
            "fo_name",
            sa.String(length=255),
            nullable=True,
            comment="联邦区",
        ),
        sa.Column(
            "region_name",
            sa.String(length=255),
            nullable=True,
            comment="地区",
        ),
        sa.Column(
            "city_name",
            sa.String(length=255),
            nullable=True,
            comment="城市",
        ),
        sa.Column(
            "nm_id",
            sa.BigInteger(),
            nullable=True,
            comment="Wildberries商品ID",
        ),
        sa.Column(
            "supplier_article",
            sa.String(length=255),
            nullable=True,
            comment="卖家货号",
        ),
        sa.Column(
            "sale_invoice_cost_price",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="销售金额",
        ),
        sa.Column(
            "sale_invoice_cost_price_percent",
            sa.Numeric(precision=18, scale=6),
            nullable=True,
            comment="销售金额占比",
        ),
        sa.Column(
            "sale_item_invoice_qty",
            sa.Integer(),
            nullable=True,
            comment="销售数量",
        ),
        sa.Column("row_data", sa.JSON(), nullable=False, comment="API原始JSON数据"),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="同步时间",
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
            "row_key",
            name="uq_ods_wb_region_sale_shop_window_row",
        ),
        comment="Wildberries区域销售报告表",
    )
    op.create_index(
        "idx_ods_wb_region_sale_date_range",
        "ods_wb_region_sales",
        ["date_from", "date_to"],
        unique=False,
    )
    op.create_index(
        "idx_ods_wb_region_sale_nm_id",
        "ods_wb_region_sales",
        ["nm_id"],
        unique=False,
    )
    op.create_index(
        "idx_ods_wb_region_sale_region_name",
        "ods_wb_region_sales",
        ["region_name"],
        unique=False,
    )
    op.create_index(
        "idx_ods_wb_region_sale_shop_id",
        "ods_wb_region_sales",
        ["shop_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ods_wb_region_sales_id"),
        "ods_wb_region_sales",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_ods_wb_region_sales_id"),
        table_name="ods_wb_region_sales",
    )
    op.drop_index(
        "idx_ods_wb_region_sale_shop_id",
        table_name="ods_wb_region_sales",
    )
    op.drop_index(
        "idx_ods_wb_region_sale_region_name",
        table_name="ods_wb_region_sales",
    )
    op.drop_index(
        "idx_ods_wb_region_sale_nm_id",
        table_name="ods_wb_region_sales",
    )
    op.drop_index(
        "idx_ods_wb_region_sale_date_range",
        table_name="ods_wb_region_sales",
    )
    op.drop_table("ods_wb_region_sales")
