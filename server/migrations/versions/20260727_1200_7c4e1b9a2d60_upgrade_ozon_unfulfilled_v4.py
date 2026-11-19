"""upgrade Ozon unfulfilled postings to v4 snapshot state

Revision ID: 7c4e1b9a2d60
Revises: 2fbfbfd7f3c3
Create Date: 2026-07-27 12:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7c4e1b9a2d60"
down_revision: Union[str, None] = "2fbfbfd7f3c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "ods_ozon_unfulfilled_postings"
ACTIVE_INDEX = "idx_ods_ozon_unfulfilled_postings_shop_active"
CUTOFF_INDEX = "idx_ods_ozon_unfulfilled_postings_shop_cutoff"
UNIQUE_NAME = "uq_ods_ozon_unfulfilled_postings_shop_posting"


def _create_complete_table() -> None:
    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("shop_id", sa.Integer(), nullable=False, comment="店铺ID"),
        sa.Column("row_data", sa.JSON(), nullable=False, comment="原始JSON数据"),
        sa.Column(
            "posting_number",
            sa.String(length=100),
            nullable=False,
            comment="订单号(API: posting_number)",
        ),
        sa.Column("order_id", sa.BigInteger(), nullable=True, comment="订单ID"),
        sa.Column(
            "order_number",
            sa.String(length=100),
            nullable=True,
            comment="订单编号",
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=True,
            comment="订单状态",
        ),
        sa.Column(
            "substatus",
            sa.String(length=50),
            nullable=True,
            comment="订单子状态",
        ),
        sa.Column(
            "delivery_method_name",
            sa.String(length=255),
            nullable=True,
            comment="配送方式名称",
        ),
        sa.Column(
            "in_process_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="进入处理状态时间",
        ),
        sa.Column(
            "shipment_date",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="计划发货时间",
        ),
        sa.Column(
            "cutoff_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="履约截止时间",
        ),
        sa.Column("products", sa.JSON(), nullable=True, comment="商品明细"),
        sa.Column(
            "analytics_data",
            sa.JSON(),
            nullable=True,
            comment="分析数据",
        ),
        sa.Column(
            "financial_data",
            sa.JSON(),
            nullable=True,
            comment="财务数据",
        ),
        sa.Column(
            "delivery_method",
            sa.JSON(),
            nullable=True,
            comment="配送方式",
        ),
        sa.Column("barcodes", sa.JSON(), nullable=True, comment="条码"),
        sa.Column(
            "cancellation",
            sa.JSON(),
            nullable=True,
            comment="取消信息",
        ),
        sa.Column("customer", sa.JSON(), nullable=True, comment="客户信息"),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="首次入库时间",
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
            comment="最近一次在未履约接口中看到的时间",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
            comment="当前是否仍在未履约列表",
        ),
        sa.Column(
            "resolved_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="从未履约列表消失的时间",
        ),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
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
            "posting_number",
            name=UNIQUE_NAME,
        ),
        comment="Ozon待处理（未发货）FBS订单表",
    )
    op.create_index(
        "idx_ods_ozon_unfulfilled_postings_shop_id",
        TABLE_NAME,
        ["shop_id"],
        unique=False,
    )
    op.create_index(
        "idx_ods_ozon_unfulfilled_postings_in_process",
        TABLE_NAME,
        ["in_process_at"],
        unique=False,
    )
    op.create_index(
        "idx_ods_ozon_unfulfilled_postings_first_seen",
        TABLE_NAME,
        ["first_seen_at"],
        unique=False,
    )
    op.create_index(ACTIVE_INDEX, TABLE_NAME, ["shop_id", "is_active"])
    op.create_index(CUTOFF_INDEX, TABLE_NAME, ["shop_id", "cutoff_at"])


def _ensure_unique_constraint(inspector: object) -> None:
    unique_names = {
        constraint.get("name")
        for constraint in inspector.get_unique_constraints(TABLE_NAME)
    }
    if UNIQUE_NAME in unique_names:
        return

    duplicate_count = (
        op.get_bind()
        .execute(
            sa.text(
                f"""
            SELECT COUNT(*)
            FROM (
                SELECT shop_id, posting_number
                FROM {TABLE_NAME}
                GROUP BY shop_id, posting_number
                HAVING COUNT(*) > 1
            ) duplicate_keys
            """
            )
        )
        .scalar_one()
    )
    if duplicate_count:
        raise RuntimeError(
            "Cannot add Ozon unfulfilled unique constraint: "
            f"found {duplicate_count} duplicate business keys"
        )

    with op.batch_alter_table(TABLE_NAME) as batch_op:
        batch_op.create_unique_constraint(
            UNIQUE_NAME,
            ["shop_id", "posting_number"],
        )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(TABLE_NAME):
        _create_complete_table()
        return

    columns = {column["name"] for column in inspector.get_columns(TABLE_NAME)}
    if "last_seen_at" not in columns:
        op.add_column(
            TABLE_NAME,
            sa.Column(
                "last_seen_at",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="最近一次在未履约接口中看到的时间",
            ),
        )
        op.execute(
            sa.text(
                f"""
                UPDATE {TABLE_NAME}
                SET last_seen_at =
                    COALESCE(first_seen_at, create_time, CURRENT_TIMESTAMP)
                WHERE last_seen_at IS NULL
                """
            )
        )
        with op.batch_alter_table(TABLE_NAME) as batch_op:
            batch_op.alter_column(
                "last_seen_at",
                existing_type=sa.DateTime(timezone=True),
                nullable=False,
            )

    if "is_active" not in columns:
        op.add_column(
            TABLE_NAME,
            sa.Column(
                "is_active",
                sa.Boolean(),
                server_default=sa.true(),
                nullable=False,
                comment="当前是否仍在未履约列表",
            ),
        )

    if "resolved_at" not in columns:
        op.add_column(
            TABLE_NAME,
            sa.Column(
                "resolved_at",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="从未履约列表消失的时间",
            ),
        )

    inspector = sa.inspect(bind)
    _ensure_unique_constraint(inspector)
    index_names = {index.get("name") for index in inspector.get_indexes(TABLE_NAME)}
    if ACTIVE_INDEX not in index_names:
        op.create_index(
            ACTIVE_INDEX,
            TABLE_NAME,
            ["shop_id", "is_active"],
            unique=False,
        )
    if CUTOFF_INDEX not in index_names:
        op.create_index(
            CUTOFF_INDEX,
            TABLE_NAME,
            ["shop_id", "cutoff_at"],
            unique=False,
        )


def downgrade() -> None:
    """Remove only v4 state columns; never drop the historical data table."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table(TABLE_NAME):
        return

    index_names = {index.get("name") for index in inspector.get_indexes(TABLE_NAME)}
    if ACTIVE_INDEX in index_names:
        op.drop_index(ACTIVE_INDEX, table_name=TABLE_NAME)
    if CUTOFF_INDEX in index_names:
        op.drop_index(CUTOFF_INDEX, table_name=TABLE_NAME)

    columns = {column["name"] for column in sa.inspect(bind).get_columns(TABLE_NAME)}
    with op.batch_alter_table(TABLE_NAME) as batch_op:
        for column_name in ("resolved_at", "is_active", "last_seen_at"):
            if column_name in columns:
                batch_op.drop_column(column_name)
