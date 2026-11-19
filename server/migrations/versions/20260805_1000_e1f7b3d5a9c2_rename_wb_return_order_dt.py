"""rename Wildberries return DWD order date column

Revision ID: e1f7b3d5a9c2
Revises: c9e5a7b3d1f8
Create Date: 2026-08-05 10:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f7b3d5a9c2"
down_revision: Union[str, None] = "c9e5a7b3d1f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "dwd_wb_return_detail"
OLD_COLUMN_NAME = "order_date"
NEW_COLUMN_NAME = "order_dt"
OLD_INDEX_NAME = "idx_dwd_wb_return_order_date"
NEW_INDEX_NAME = "idx_dwd_wb_return_order_dt"


def _column_names(bind: sa.engine.Connection) -> set[str]:
    return {column["name"] for column in sa.inspect(bind).get_columns(TABLE_NAME)}


def _index_names(bind: sa.engine.Connection) -> set[str]:
    return {index["name"] for index in sa.inspect(bind).get_indexes(TABLE_NAME)}


def upgrade() -> None:
    """Rename order_date to order_dt without changing existing values."""
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(TABLE_NAME):
        return

    columns = _column_names(bind)
    if OLD_COLUMN_NAME in columns and NEW_COLUMN_NAME in columns:
        raise RuntimeError(
            f"{TABLE_NAME} contains both {OLD_COLUMN_NAME} and {NEW_COLUMN_NAME}"
        )
    if OLD_COLUMN_NAME in columns:
        if OLD_INDEX_NAME in _index_names(bind):
            op.drop_index(OLD_INDEX_NAME, table_name=TABLE_NAME)
        op.alter_column(
            TABLE_NAME,
            OLD_COLUMN_NAME,
            new_column_name=NEW_COLUMN_NAME,
            existing_type=sa.Date(),
            existing_nullable=True,
            existing_comment="下单日期",
        )
    elif NEW_COLUMN_NAME not in columns:
        raise RuntimeError(
            f"{TABLE_NAME} contains neither {OLD_COLUMN_NAME} nor {NEW_COLUMN_NAME}"
        )

    if NEW_INDEX_NAME not in _index_names(bind):
        op.create_index(
            NEW_INDEX_NAME,
            TABLE_NAME,
            [NEW_COLUMN_NAME],
            unique=False,
        )


def downgrade() -> None:
    """Restore the previous order_date column and index names."""
    bind = op.get_bind()
    if not sa.inspect(bind).has_table(TABLE_NAME):
        return

    columns = _column_names(bind)
    if OLD_COLUMN_NAME in columns and NEW_COLUMN_NAME in columns:
        raise RuntimeError(
            f"{TABLE_NAME} contains both {OLD_COLUMN_NAME} and {NEW_COLUMN_NAME}"
        )
    if NEW_COLUMN_NAME in columns:
        if NEW_INDEX_NAME in _index_names(bind):
            op.drop_index(NEW_INDEX_NAME, table_name=TABLE_NAME)
        op.alter_column(
            TABLE_NAME,
            NEW_COLUMN_NAME,
            new_column_name=OLD_COLUMN_NAME,
            existing_type=sa.Date(),
            existing_nullable=True,
            existing_comment="下单日期",
        )
    elif OLD_COLUMN_NAME not in columns:
        raise RuntimeError(
            f"{TABLE_NAME} contains neither {OLD_COLUMN_NAME} nor {NEW_COLUMN_NAME}"
        )

    if OLD_INDEX_NAME not in _index_names(bind):
        op.create_index(
            OLD_INDEX_NAME,
            TABLE_NAME,
            [OLD_COLUMN_NAME],
            unique=False,
        )
