"""add wb order metadata

Revision ID: 5f3a9c1d7e42
Revises: 34c0cea842a3
Create Date: 2026-07-24 11:35:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "5f3a9c1d7e42"
down_revision = "34c0cea842a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ods_wb_order_metadata",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column("order_id", sa.BigInteger(), nullable=False, comment="组装订单ID"),
        sa.Column(
            "row_data",
            sa.JSON(),
            nullable=False,
            comment="Wildberries 原始JSON数据",
        ),
        sa.Column(
            "meta_details",
            sa.JSON(),
            nullable=True,
            comment="订单元数据明细及校验结果 (API: metaDetails)",
        ),
        sa.Column(
            "legacy_meta",
            sa.JSON(),
            nullable=True,
            comment="兼容旧版订单元数据结构 (API: meta)",
        ),
        sa.Column(
            "last_synced_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="最近同步时间",
        ),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
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
            "order_id",
            name="uq_ods_wb_order_metadata_shop_order",
        ),
        comment="Wildberries FBS组装订单元数据表",
    )
    op.create_index(
        "ix_ods_wb_order_metadata_id",
        "ods_wb_order_metadata",
        ["id"],
        unique=False,
    )
    op.create_index(
        "idx_ods_wb_order_metadata_shop_synced",
        "ods_wb_order_metadata",
        ["shop_id", "last_synced_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "idx_ods_wb_order_metadata_shop_synced",
        table_name="ods_wb_order_metadata",
    )
    op.drop_index(
        "ix_ods_wb_order_metadata_id",
        table_name="ods_wb_order_metadata",
    )
    op.drop_table("ods_wb_order_metadata")
