"""扩展Ozon退货诊断字段

Revision ID: a4c8e2f6b9d1
Revises: 805203c7b547
Create Date: 2026-08-25 12:00:00

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "a4c8e2f6b9d1"
down_revision = "805203c7b547"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ods_ozon_returns",
        sa.Column(
            "compensation_status_id", sa.Integer(), nullable=True, comment="赔偿状态ID"
        ),
    )
    op.add_column(
        "ods_ozon_returns",
        sa.Column(
            "compensation_status_display_name",
            sa.String(length=255),
            nullable=True,
            comment="赔偿状态显示名称",
        ),
    )
    op.add_column(
        "ods_ozon_returns",
        sa.Column(
            "compensation_status_sys_name",
            sa.String(length=255),
            nullable=True,
            comment="赔偿状态系统名称",
        ),
    )
    op.add_column(
        "ods_ozon_returns",
        sa.Column(
            "compensation_status_change_moment",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="赔偿状态变更时间",
        ),
    )
    op.add_column(
        "ods_ozon_returns",
        sa.Column(
            "buyer_comment",
            sa.Text(),
            nullable=True,
            comment="买家评论（接口返回时记录）",
        ),
    )

    op.add_column(
        "dwd_ozon_return_detail",
        sa.Column(
            "compensation_status_id", sa.Integer(), nullable=True, comment="赔偿状态ID"
        ),
    )
    op.add_column(
        "dwd_ozon_return_detail",
        sa.Column(
            "compensation_status_display_name",
            sa.String(length=255),
            nullable=True,
            comment="赔偿状态",
        ),
    )
    op.add_column(
        "dwd_ozon_return_detail",
        sa.Column(
            "compensation_status_display_name_cn",
            sa.String(length=255),
            nullable=True,
            comment="赔偿状态（中文）",
        ),
    )
    op.add_column(
        "dwd_ozon_return_detail",
        sa.Column(
            "compensation_status_sys_name",
            sa.String(length=255),
            nullable=True,
            comment="赔偿状态编码",
        ),
    )
    op.add_column(
        "dwd_ozon_return_detail",
        sa.Column(
            "compensation_status_change_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="赔偿状态变更时间",
        ),
    )
    op.add_column(
        "dwd_ozon_return_detail",
        sa.Column("buyer_comment", sa.Text(), nullable=True, comment="买家评论"),
    )
    op.add_column(
        "dwd_ozon_return_detail",
        sa.Column(
            "buyer_comment_cn", sa.Text(), nullable=True, comment="买家评论（中文）"
        ),
    )
    op.add_column(
        "dwd_ozon_return_detail",
        sa.Column(
            "storage_fee_amount",
            sa.Numeric(precision=18, scale=4),
            nullable=True,
            comment="仓储费用",
        ),
    )
    op.add_column(
        "dwd_ozon_return_detail",
        sa.Column(
            "storage_fee_currency",
            sa.String(length=10),
            nullable=True,
            comment="仓储费用币种",
        ),
    )
    op.add_column(
        "dwd_ozon_return_detail",
        sa.Column(
            "utilization_fee_amount",
            sa.Numeric(precision=18, scale=4),
            nullable=True,
            comment="销毁费用",
        ),
    )
    op.add_column(
        "dwd_ozon_return_detail",
        sa.Column(
            "utilization_fee_currency",
            sa.String(length=10),
            nullable=True,
            comment="销毁费用币种",
        ),
    )
    op.add_column(
        "dwd_ozon_return_detail",
        sa.Column(
            "commission_percent",
            sa.Numeric(precision=8, scale=2),
            nullable=True,
            comment="佣金百分比",
        ),
    )
    op.add_column(
        "dwd_ozon_return_detail",
        sa.Column(
            "commission_amount",
            sa.Numeric(precision=18, scale=4),
            nullable=True,
            comment="佣金",
        ),
    )
    op.add_column(
        "dwd_ozon_return_detail",
        sa.Column(
            "commission_currency",
            sa.String(length=10),
            nullable=True,
            comment="佣金币种",
        ),
    )
    op.add_column(
        "dwd_ozon_return_detail",
        sa.Column(
            "price_without_commission_amount",
            sa.Numeric(precision=18, scale=4),
            nullable=True,
            comment="不含佣金的价格",
        ),
    )
    op.add_column(
        "dwd_ozon_return_detail",
        sa.Column(
            "price_without_commission_currency",
            sa.String(length=10),
            nullable=True,
            comment="不含佣金价格币种",
        ),
    )


def downgrade() -> None:
    dwd_columns = (
        "price_without_commission_currency",
        "price_without_commission_amount",
        "commission_currency",
        "commission_amount",
        "commission_percent",
        "utilization_fee_currency",
        "utilization_fee_amount",
        "storage_fee_currency",
        "storage_fee_amount",
        "buyer_comment_cn",
        "buyer_comment",
        "compensation_status_change_at",
        "compensation_status_sys_name",
        "compensation_status_display_name_cn",
        "compensation_status_display_name",
        "compensation_status_id",
    )
    for column_name in dwd_columns:
        op.drop_column("dwd_ozon_return_detail", column_name)

    ods_columns = (
        "buyer_comment",
        "compensation_status_change_moment",
        "compensation_status_sys_name",
        "compensation_status_display_name",
        "compensation_status_id",
    )
    for column_name in ods_columns:
        op.drop_column("ods_ozon_returns", column_name)
