"""删除WB订单配送类型中文字段

Revision ID: c0b697b2cf0a
Revises: 3c0abdefb7e3
Create Date: 2026-09-02 15:03:26.909150

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c0b697b2cf0a"
down_revision = "3c0abdefb7e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("dwd_wb_order_detail", "delivery_type_cn")


def downgrade() -> None:
    op.add_column(
        "dwd_wb_order_detail",
        sa.Column(
            "delivery_type_cn",
            sa.String(length=50),
            nullable=True,
            comment="配送类型（中文）",
        ),
    )
