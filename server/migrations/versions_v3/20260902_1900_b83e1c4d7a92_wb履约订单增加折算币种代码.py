"""WB履约订单增加折算币种代码

Revision ID: b83e1c4d7a92
Revises: 4b7f2d91a6c3
Create Date: 2026-09-02 19:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "b83e1c4d7a92"
down_revision = "4b7f2d91a6c3"
branch_labels = None
depends_on = None

TABLE = "dwd_wb_order_detail"
COLUMN = "converted_currency_code"


def _column_exists() -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == COLUMN for column in inspector.get_columns(TABLE))


def upgrade() -> None:
    if not _column_exists():
        op.add_column(
            TABLE,
            sa.Column(
                COLUMN,
                sa.Integer(),
                nullable=True,
                comment="折算币种代码",
            ),
        )
    op.execute(
        sa.text("""
            UPDATE dwd_wb_order_detail AS target
            INNER JOIN ods_wb_marketplace_orders AS source
                ON source.shop_id = target.shop_id
               AND source.order_id = target.order_id
            SET target.converted_currency_code = source.converted_currency_code
            WHERE source.converted_currency_code IS NOT NULL
        """)
    )


def downgrade() -> None:
    if _column_exists():
        op.drop_column(TABLE, COLUMN)
