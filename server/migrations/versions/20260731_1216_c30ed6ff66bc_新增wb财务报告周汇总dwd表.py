"""新增WB财务报告周汇总DWD表

Revision ID: c30ed6ff66bc
Revises: 3c21b0b022a3
Create Date: 2026-07-31 12:16:46.485752

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c30ed6ff66bc"
down_revision = "3c21b0b022a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dwd_wb_sales_report_summary",
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
            comment="来源 ods_wb_sales_report_list.id",
        ),
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column(
            "report_id",
            sa.BigInteger(),
            nullable=False,
            comment="报告编号",
        ),
        sa.Column(
            "seller_finance_name",
            sa.String(length=255),
            nullable=True,
            comment="法人",
        ),
        sa.Column("date_from", sa.Date(), nullable=False, comment="开始日期"),
        sa.Column("date_to", sa.Date(), nullable=False, comment="结束日期"),
        sa.Column("create_date", sa.Date(), nullable=True, comment="生成日期"),
        sa.Column("report_type", sa.Integer(), nullable=True, comment="报告类型"),
        sa.Column(
            "retail_amount_sum",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="销售",
        ),
        sa.Column(
            "cashback_discount_sum",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="包括忠诚度计划的折扣赔偿",
        ),
        sa.Column(
            "for_pay_sum",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="应支付商品金额",
        ),
        sa.Column(
            "avg_sale_percent",
            sa.Numeric(precision=10, scale=4),
            nullable=True,
            comment="协商折扣(%)",
        ),
        sa.Column(
            "delivery_service_sum",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="物流费用",
        ),
        sa.Column(
            "paid_storage_sum",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="仓储费用",
        ),
        sa.Column(
            "paid_acceptance_sum",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="入库验收费用",
        ),
        sa.Column(
            "deduction_sum",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="其他扣款/付款",
        ),
        sa.Column(
            "penalty_sum",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="罚款总额",
        ),
        sa.Column(
            "additional_payment_sum",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="WB佣金调整",
        ),
        sa.Column(
            "cashback_commission_change_sum",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="忠诚度计划参与费用",
        ),
        sa.Column(
            "cashback_amount_sum",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="已扣除的忠诚度积分金额",
        ),
        sa.Column(
            "payment_schedule",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="一次性结算周期变更",
        ),
        sa.Column(
            "bank_payment_sum",
            sa.Numeric(precision=20, scale=2),
            nullable=True,
            comment="应付总额",
        ),
        sa.Column(
            "currency",
            sa.String(length=10),
            nullable=True,
            comment="货币",
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
            name="uq_dwd_wb_sales_report_summary_shop_report",
        ),
        sa.UniqueConstraint(
            "source_ods_id",
            name="uq_dwd_wb_sales_report_summary_source_ods",
        ),
        comment="Wildberries 财务报告周汇总 DWD 表",
    )
    op.create_index(
        "idx_dwd_wb_sales_report_summary_create_date",
        "dwd_wb_sales_report_summary",
        ["create_date"],
        unique=False,
    )
    op.create_index(
        "idx_dwd_wb_sales_report_summary_date_range",
        "dwd_wb_sales_report_summary",
        ["date_from", "date_to"],
        unique=False,
    )
    op.create_index(
        "idx_dwd_wb_sales_report_summary_shop_id",
        "dwd_wb_sales_report_summary",
        ["shop_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_dwd_wb_sales_report_summary_shop_id",
        table_name="dwd_wb_sales_report_summary",
    )
    op.drop_index(
        "idx_dwd_wb_sales_report_summary_date_range",
        table_name="dwd_wb_sales_report_summary",
    )
    op.drop_index(
        "idx_dwd_wb_sales_report_summary_create_date",
        table_name="dwd_wb_sales_report_summary",
    )
    op.drop_table("dwd_wb_sales_report_summary")
