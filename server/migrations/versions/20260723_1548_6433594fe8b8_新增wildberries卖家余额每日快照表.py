"""新增Wildberries卖家余额每日快照表

Revision ID: 6433594fe8b8
Revises: b0c2eb2aaa42
Create Date: 2026-07-23 15:48:08.722522

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "6433594fe8b8"
down_revision = "b0c2eb2aaa42"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ods_wb_seller_balance",
        sa.Column(
            "id",
            sa.BigInteger(),
            autoincrement=True,
            nullable=False,
            comment="主键ID",
        ),
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column("row_data", sa.JSON(), nullable=False, comment="API原始JSON数据"),
        sa.Column("currency", sa.String(length=10), nullable=True, comment="币种"),
        sa.Column(
            "current",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="当前余额",
        ),
        sa.Column(
            "for_withdraw",
            sa.Numeric(precision=18, scale=2),
            nullable=True,
            comment="可提现金额",
        ),
        sa.Column(
            "snapshot_date",
            sa.Date(),
            nullable=False,
            comment="平台时区快照日期",
        ),
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
            "snapshot_date",
            name="uq_ods_wb_seller_balance_shop_date",
        ),
        comment="Wildberries卖家余额每日快照表",
    )
    op.create_index(
        "idx_ods_wb_seller_balance_shop_id",
        "ods_wb_seller_balance",
        ["shop_id"],
        unique=False,
    )
    op.create_index(
        "idx_ods_wb_seller_balance_snapshot_date",
        "ods_wb_seller_balance",
        ["snapshot_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_ods_wb_seller_balance_id"),
        "ods_wb_seller_balance",
        ["id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_ods_wb_seller_balance_id"),
        table_name="ods_wb_seller_balance",
    )
    op.drop_index(
        "idx_ods_wb_seller_balance_snapshot_date",
        table_name="ods_wb_seller_balance",
    )
    op.drop_index(
        "idx_ods_wb_seller_balance_shop_id",
        table_name="ods_wb_seller_balance",
    )
    op.drop_table("ods_wb_seller_balance")
