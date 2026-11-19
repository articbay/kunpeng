"""add Ozon return Chinese translation fields

Revision ID: a7c3e5f9b2d4
Revises: 9b2f4d6e8a10
Create Date: 2026-08-03 18:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7c3e5f9b2d4"
down_revision: Union[str, None] = "9b2f4d6e8a10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "dwd_ozon_return_detail"
COLUMNS = (
    sa.Column(
        "category_name_cn", sa.String(255), nullable=True, comment="商品品类（中文）"
    ),
    sa.Column("product_name_cn", sa.Text(), nullable=True, comment="商品名称（中文）"),
    sa.Column(
        "status_display_name_cn",
        sa.String(255),
        nullable=True,
        comment="状态（中文）",
    ),
    sa.Column(
        "return_reason_name_cn", sa.Text(), nullable=True, comment="退货原因（中文）"
    ),
    sa.Column(
        "place_name_cn", sa.String(255), nullable=True, comment="当前地点名称（中文）"
    ),
    sa.Column(
        "place_address_cn", sa.Text(), nullable=True, comment="当前地点地址（中文）"
    ),
    sa.Column(
        "target_place_name_cn",
        sa.String(255),
        nullable=True,
        comment="目标提货点名称（中文）",
    ),
    sa.Column(
        "target_place_address_cn",
        sa.Text(),
        nullable=True,
        comment="目标提货点地址（中文）",
    ),
)


def upgrade() -> None:
    for column in COLUMNS:
        op.add_column(TABLE_NAME, column)


def downgrade() -> None:
    for column in reversed(COLUMNS):
        op.drop_column(TABLE_NAME, column.name)
