"""调整WB订单折算币种列顺序

Revision ID: d2f6a91c8e47
Revises: b83e1c4d7a92
Create Date: 2026-09-02 20:30:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "d2f6a91c8e47"
down_revision = "b83e1c4d7a92"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE dwd_wb_order_detail
            MODIFY COLUMN converted_currency_code INTEGER NULL
            COMMENT '折算币种代码'
            AFTER currency_code
        """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            ALTER TABLE dwd_wb_order_detail
            MODIFY COLUMN converted_currency_code INTEGER NULL
            COMMENT '折算币种代码'
            AFTER is_zero_order
        """
        )
    )
