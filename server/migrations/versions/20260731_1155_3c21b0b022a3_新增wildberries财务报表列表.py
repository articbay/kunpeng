"""新增Wildberries财务报表列表

Revision ID: 3c21b0b022a3
Revises: e71b09c84a6f
Create Date: 2026-07-31 11:55:08.183532

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "3c21b0b022a3"
down_revision = "e71b09c84a6f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ods_wb_sales_report_list",
        sa.Column(
            "id",
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
            comment="主键ID",
        ),
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column(
            "report_id",
            sa.BigInteger(),
            nullable=False,
            comment="Wildberries报表ID",
        ),
        sa.Column(
            "seller_finance_name",
            sa.String(length=255),
            nullable=True,
            comment="卖家财务主体名称",
        ),
        sa.Column("date_from", sa.Date(), nullable=False, comment="报表开始日期"),
        sa.Column("date_to", sa.Date(), nullable=False, comment="报表结束日期"),
        sa.Column("create_date", sa.Date(), nullable=True, comment="报表生成日期"),
        sa.Column("currency", sa.String(length=10), nullable=True, comment="币种"),
        sa.Column("report_type", sa.Integer(), nullable=True, comment="报表类型"),
        sa.Column(
            "retail_amount_sum",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="零售金额合计",
        ),
        sa.Column(
            "for_pay_sum",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="应付金额合计",
        ),
        sa.Column(
            "avg_sale_percent",
            sa.Numeric(precision=10, scale=4),
            nullable=True,
            comment="平均销售折扣百分比",
        ),
        sa.Column(
            "delivery_service_sum",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="配送服务费合计",
        ),
        sa.Column(
            "paid_storage_sum",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="付费仓储费合计",
        ),
        sa.Column(
            "paid_acceptance_sum",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="付费验收费合计",
        ),
        sa.Column(
            "deduction_sum",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="扣款合计",
        ),
        sa.Column(
            "penalty_sum",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="罚款合计",
        ),
        sa.Column(
            "additional_payment_sum",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="额外付款合计",
        ),
        sa.Column(
            "cashback_amount_sum",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="返现金额合计",
        ),
        sa.Column(
            "cashback_discount_sum",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="返现折扣合计",
        ),
        sa.Column(
            "cashback_commission_change_sum",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="返现佣金调整合计",
        ),
        sa.Column(
            "payment_schedule",
            sa.String(length=50),
            nullable=True,
            comment="付款计划",
        ),
        sa.Column(
            "bank_payment_sum",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="银行付款合计",
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
            "report_id",
            name="uq_ods_wb_sales_report_list_shop_report",
        ),
        comment="Wildberries财务报表列表汇总表",
    )
    op.create_index(
        "idx_ods_wb_sales_report_list_create_date",
        "ods_wb_sales_report_list",
        ["create_date"],
        unique=False,
    )
    op.create_index(
        "idx_ods_wb_sales_report_list_date_range",
        "ods_wb_sales_report_list",
        ["date_from", "date_to"],
        unique=False,
    )
    op.create_index(
        "idx_ods_wb_sales_report_list_shop_id",
        "ods_wb_sales_report_list",
        ["shop_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ods_wb_sales_report_list_id"),
        "ods_wb_sales_report_list",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_ods_wb_sales_report_list_id"),
        table_name="ods_wb_sales_report_list",
    )
    op.drop_index(
        "idx_ods_wb_sales_report_list_shop_id",
        table_name="ods_wb_sales_report_list",
    )
    op.drop_index(
        "idx_ods_wb_sales_report_list_date_range",
        table_name="ods_wb_sales_report_list",
    )
    op.drop_index(
        "idx_ods_wb_sales_report_list_create_date",
        table_name="ods_wb_sales_report_list",
    )
    op.drop_table("ods_wb_sales_report_list")
