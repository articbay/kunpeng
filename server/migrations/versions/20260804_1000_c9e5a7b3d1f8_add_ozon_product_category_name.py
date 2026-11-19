"""add Ozon product category name

Revision ID: c9e5a7b3d1f8
Revises: a7c3e5f9b2d4
Create Date: 2026-08-04 10:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9e5a7b3d1f8"
down_revision: Union[str, None] = "a7c3e5f9b2d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ods_ozon_products",
        sa.Column(
            "category_name",
            sa.String(255),
            nullable=True,
            comment="商品品类名称",
        ),
    )


def downgrade() -> None:
    op.drop_column("ods_ozon_products", "category_name")
