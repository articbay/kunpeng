"""standardize recent ODS table names and parsed fields

Revision ID: 91d7e6c4a2f8
Revises: 7c4e1b9a2d60
Create Date: 2026-07-28 14:00:00

"""

from typing import Dict, Iterable, Sequence, Tuple, Union

import sqlalchemy as sa
from alembic import op

revision: str = "91d7e6c4a2f8"
down_revision: Union[str, None] = "7c4e1b9a2d60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_RENAMES: Tuple[Tuple[str, Tuple[Tuple[str, str], ...]], ...] = (
    (
        "ods_wb_voc_chat_events",
        (
            ("ods_wb_VOC_chat_events", "legacy_20260728_wb_voc_chat_events_manual"),
            ("ods_wb_chat_events", "legacy_20260728_ods_wb_chat_events"),
        ),
    ),
    (
        "ods_wb_voc_feedback_pins",
        (
            (
                "ods_wb_VOC_feedback_pins",
                "legacy_20260728_wb_voc_feedback_pins_manual",
            ),
            ("ods_wb_feedback_pins", "legacy_20260728_ods_wb_feedback_pins"),
        ),
    ),
    (
        "ods_wb_order_fbs_supplies",
        (("ods_wb_fbs_supplies", "legacy_20260728_ods_wb_fbs_supplies"),),
    ),
    (
        "ods_wb_order_reshipment_orders",
        (
            (
                "ods_wb_reshipment_orders",
                "legacy_20260728_ods_wb_reshipment_orders",
            ),
        ),
    ),
    (
        "ods_ozon_order_unfulfilled_postings",
        (
            (
                "ods_ozon_unfulfilled_postings",
                "legacy_20260728_ods_ozon_unfulfilled_postings",
            ),
        ),
    ),
)

BUSINESS_KEYS: Dict[str, Tuple[str, ...]] = {
    "ods_wb_voc_chat_events": ("shop_id", "event_id"),
    "ods_wb_voc_feedback_pins": ("shop_id", "pin_id"),
    "ods_wb_order_fbs_supplies": ("shop_id", "supply_id"),
    "ods_wb_order_reshipment_orders": ("shop_id", "order_id", "supply_id"),
    "ods_ozon_order_unfulfilled_postings": ("shop_id", "posting_number"),
}

SUPPLY_COLUMNS: Tuple[sa.Column, ...] = (
    sa.Column(
        "rejected_at",
        sa.DateTime(timezone=True),
        nullable=True,
        comment="供货单拒绝时间(API: rejectDt)",
    ),
    sa.Column(
        "recommended_warehouse_id",
        sa.BigInteger(),
        nullable=True,
        comment="推荐仓库ID(API: recommendedWhId)",
    ),
    sa.Column(
        "is_pickup_point_shipment_allowed",
        sa.Boolean(),
        nullable=True,
        comment="是否允许发往取货点(API: isPickupPointShipmentAllowed)",
    ),
)

OZON_COLUMNS: Tuple[sa.Column, ...] = (
    sa.Column(
        "delivering_at",
        sa.DateTime(timezone=True),
        nullable=True,
        comment="计划送达时间(API: delivering_date)",
    ),
    sa.Column(
        "shipment_without_delay_at",
        sa.DateTime(timezone=True),
        nullable=True,
        comment="无延迟情况下的计划发货时间(API: shipment_date_without_delay)",
    ),
    sa.Column(
        "available_actions",
        sa.JSON(),
        nullable=True,
        comment="当前允许的订单操作(API: available_actions)",
    ),
    sa.Column(
        "requirements",
        sa.JSON(),
        nullable=True,
        comment="履约要求(API: requirements)",
    ),
    sa.Column(
        "sorting_center",
        sa.JSON(),
        nullable=True,
        comment="分拣中心信息(API: sorting_center)",
    ),
    sa.Column(
        "tracking_number",
        sa.String(length=255),
        nullable=True,
        comment="物流跟踪号(API: tracking_number)",
    ),
    sa.Column(
        "integration_type_flow",
        sa.String(length=100),
        nullable=True,
        comment="履约集成流程类型(API: integration_type_flow)",
    ),
    sa.Column(
        "parent_posting_number",
        sa.String(length=100),
        nullable=True,
        comment="父发送号(API: parent_posting_number)",
    ),
    sa.Column(
        "destination_place_id",
        sa.BigInteger(),
        nullable=True,
        comment="目的地点ID(API: destination_place_id)",
    ),
    sa.Column(
        "destination_place_name",
        sa.String(length=255),
        nullable=True,
        comment="目的地点名称(API: destination_place_name)",
    ),
    sa.Column(
        "is_express",
        sa.Boolean(),
        nullable=True,
        comment="是否为加急配送(API: is_express)",
    ),
    sa.Column(
        "is_multibox",
        sa.Boolean(),
        nullable=True,
        comment="是否为多箱订单(API: is_multibox)",
    ),
    sa.Column(
        "multi_box_qty",
        sa.Integer(),
        nullable=True,
        comment="多箱数量(API: multi_box_qty)",
    ),
)


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _rename_case_safe(source: str, target: str) -> None:
    """Rename through a temporary name when only identifier case changes."""
    if source == target:
        return
    if source.lower() == target.lower():
        temporary = f"tmp_91d7_{target}"[:64]
        op.rename_table(source, temporary)
        op.rename_table(temporary, target)
        return
    op.rename_table(source, target)


def _merge_rows(source: str, target: str, business_keys: Iterable[str]) -> None:
    """Merge a pre-existing manual table without overwriting first-seen data."""
    inspector = sa.inspect(op.get_bind())
    source_columns = {column["name"] for column in inspector.get_columns(source)}
    target_columns = {column["name"] for column in inspector.get_columns(target)}
    columns = sorted((source_columns & target_columns) - {"id"})
    if not columns:
        return

    bind = op.get_bind()
    quote = bind.dialect.identifier_preparer.quote
    column_sql = ", ".join(quote(column) for column in columns)
    source_sql = quote(source)
    target_sql = quote(target)
    dialect_name = bind.dialect.name

    if dialect_name == "mysql":
        immutable = {
            "shop_id",
            "first_seen_at",
            "create_time",
            *business_keys,
        }
        update_columns = [column for column in columns if column not in immutable]
        if update_columns:
            update_sql = ", ".join(
                f"{quote(column)} = incoming.{quote(column)}"
                for column in update_columns
            )
        else:
            key = next(iter(business_keys))
            update_sql = f"{quote(key)} = incoming.{quote(key)}"
        statement = (
            f"INSERT INTO {target_sql} ({column_sql}) "
            f"SELECT {column_sql} FROM "
            f"(SELECT {column_sql} FROM {source_sql}) AS incoming "
            f"ON DUPLICATE KEY UPDATE {update_sql}"
        )
    elif dialect_name == "sqlite":
        statement = (
            f"INSERT OR IGNORE INTO {target_sql} ({column_sql}) "
            f"SELECT {column_sql} FROM {source_sql}"
        )
    else:
        statement = (
            f"INSERT INTO {target_sql} ({column_sql}) "
            f"SELECT {column_sql} FROM {source_sql} ON CONFLICT DO NOTHING"
        )
    op.execute(sa.text(statement))


def _standardize_table(
    target: str,
    candidates: Tuple[Tuple[str, str], ...],
) -> None:
    names = _table_names()
    if target not in names:
        source = next((name for name, _ in candidates if name in names), None)
        if source is None:
            # A clean migration chain creates the legacy table first. If neither
            # legacy nor manually renamed table exists, another missing migration
            # must be restored instead of silently creating an incomplete table.
            raise RuntimeError(
                f"Cannot standardize {target}: no legacy or manually renamed table exists"
            )
        _rename_case_safe(source, target)

    for source, archive in candidates:
        names = _table_names()
        if source == target or source not in names:
            continue
        _merge_rows(source, target, BUSINESS_KEYS[target])
        if archive not in names:
            op.rename_table(source, archive)


def _add_missing_columns(table_name: str, columns: Iterable[sa.Column]) -> None:
    existing = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }
    for column in columns:
        if column.name not in existing:
            op.add_column(table_name, column)


def upgrade() -> None:
    for target, candidates in TABLE_RENAMES:
        _standardize_table(target, candidates)

    _add_missing_columns("ods_wb_order_fbs_supplies", SUPPLY_COLUMNS)
    _add_missing_columns("ods_ozon_order_unfulfilled_postings", OZON_COLUMNS)


def _drop_columns_if_present(
    table_name: str,
    columns: Iterable[sa.Column],
) -> None:
    if table_name not in _table_names():
        return
    existing = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }
    with op.batch_alter_table(table_name) as batch_op:
        for column in reversed(tuple(columns)):
            if column.name in existing:
                batch_op.drop_column(column.name)


def downgrade() -> None:
    """Restore legacy names when possible without deleting or overwriting rows."""
    _drop_columns_if_present("ods_ozon_order_unfulfilled_postings", OZON_COLUMNS)
    _drop_columns_if_present("ods_wb_order_fbs_supplies", SUPPLY_COLUMNS)

    for target, candidates in reversed(TABLE_RENAMES):
        names = _table_names()
        if target not in names:
            continue
        primary_source, primary_archive = candidates[-1]
        if primary_archive in names and primary_source not in names:
            op.rename_table(primary_archive, primary_source)
            names = _table_names()
        if primary_source in names:
            _merge_rows(target, primary_source, BUSINESS_KEYS[target])
            # Keep the standardized copy as a safety copy. Downgrade switches the
            # old model back to the populated legacy table without deleting data.
            continue
        _rename_case_safe(target, primary_source)
