"""客户评价增加商品名称及中文字段

Revision ID: 86a5e58bca0a
Revises: c0b697b2cf0a
Create Date: 2026-09-02 16:17:07.893531

"""

import sqlalchemy as sa

from alembic import op

revision = "86a5e58bca0a"
down_revision = "c0b697b2cf0a"
branch_labels = None
depends_on = None

TABLE = "dwd_wb_voc_feedback_detail"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(
            "product_name",
            sa.String(length=500),
            nullable=True,
            comment="商品名称",
        ),
    )
    op.add_column(
        TABLE,
        sa.Column(
            "product_name_cn",
            sa.String(length=500),
            nullable=True,
            comment="商品名称（中文）",
        ),
    )


def downgrade() -> None:
    op.drop_column(TABLE, "product_name_cn")
    op.drop_column(TABLE, "product_name")
