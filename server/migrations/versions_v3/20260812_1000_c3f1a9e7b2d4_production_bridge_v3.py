"""Bridge the production schema at 935ae1532222 to the current model.

Revision ID: c3f1a9e7b2d4
Revises: 935ae1532222
Create Date: 2026-08-12 10:00:00

This migration is deliberately additive. It never drops an existing table,
column, index, constraint, or row. The legacy Ozon unfulfilled-postings table
is retained so the pre-migration application can still be restarted.
"""

import hashlib
import json

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

import kunpeng.models.ods.ozon  # noqa: F401
import kunpeng.models.ods.wildberries.adv_enhanced  # noqa: F401
from alembic import op
from kunpeng.models import Base

revision = "c3f1a9e7b2d4"
down_revision = "935ae1532222"
branch_labels = None
depends_on = None

EXPECTED_PREVIOUS_REVISION = "935ae1532222"
EXPECTED_MODEL_TABLE_COUNT = 81
EXPECTED_MODEL_SIGNATURE = (
    "c309a8ec700a57164196f2633e7ded340fc8344e9eff82f7543059587e9fd102"
)
LEGACY_UNFULFILLED_TABLE = "ods_ozon_unfulfilled_postings"
CURRENT_UNFULFILLED_TABLE = "ods_ozon_order_unfulfilled_postings"


def _quote(connection, identifier: str) -> str:
    return connection.dialect.identifier_preparer.quote(identifier)


def _model_signature() -> str:
    dialect = mysql.dialect()
    tables = []
    for table_name, table in sorted(Base.metadata.tables.items()):
        columns = []
        for column in table.columns:
            default = (
                None
                if column.server_default is None
                else str(column.server_default.arg)
            )
            columns.append(
                [
                    column.name,
                    str(column.type.compile(dialect=dialect)),
                    column.nullable,
                    column.primary_key,
                    default,
                ]
            )
        indexes = sorted(
            [
                index.name,
                bool(index.unique),
                [column.name for column in index.columns],
            ]
            for index in table.indexes
        )
        unique_constraints = sorted(
            [constraint.name, [column.name for column in constraint.columns]]
            for constraint in table.constraints
            if isinstance(constraint, sa.UniqueConstraint)
        )
        foreign_keys = sorted(
            [
                constraint.name,
                [element.parent.name for element in constraint.elements],
                [element.target_fullname for element in constraint.elements],
                constraint.ondelete,
                constraint.onupdate,
            ]
            for constraint in table.foreign_key_constraints
        )
        tables.append(
            [
                table_name,
                columns,
                indexes,
                unique_constraints,
                foreign_keys,
                table.comment,
            ]
        )
    payload = json.dumps(tables, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _assert_frozen_model() -> None:
    if len(Base.metadata.tables) != EXPECTED_MODEL_TABLE_COUNT:
        raise RuntimeError(
            "production bridge model table count changed; create a new migration "
            "instead of changing this historical bridge"
        )
    if _model_signature() != EXPECTED_MODEL_SIGNATURE:
        raise RuntimeError(
            "production bridge model signature changed; create a new migration "
            "instead of changing this historical bridge"
        )


def _assert_previous_revision(connection) -> None:
    inspector = sa.inspect(connection)
    if not inspector.has_table("alembic_version"):
        raise RuntimeError("alembic_version table is missing")
    versions = (
        connection.execute(sa.text("SELECT version_num FROM alembic_version"))
        .scalars()
        .all()
    )
    if versions != [EXPECTED_PREVIOUS_REVISION]:
        raise RuntimeError(
            "production bridge requires alembic version "
            f"{EXPECTED_PREVIOUS_REVISION}; found {versions!r}"
        )


def _row_count(connection, table_name: str) -> int:
    quoted = _quote(connection, table_name)
    return int(
        connection.execute(sa.text(f"SELECT COUNT(*) FROM {quoted}")).scalar_one()
    )


def _assert_existing_columns_are_compatible(connection, inspector) -> None:
    implementation = op.get_context().impl
    existing_tables = set(inspector.get_table_names())
    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            continue
        existing_columns = {
            column["name"]: column for column in inspector.get_columns(table_name)
        }
        for column in table.columns:
            existing = existing_columns.get(column.name)
            if existing is None:
                if (
                    not column.nullable
                    and column.server_default is None
                    and _row_count(connection, table_name) > 0
                ):
                    raise RuntimeError(
                        f"cannot safely add required column {table_name}.{column.name} "
                        "to a non-empty production table"
                    )
                continue
            reflected = sa.Column(
                column.name,
                existing["type"],
                nullable=existing.get("nullable", True),
            )
            if implementation.compare_type(reflected, column):
                raise RuntimeError(
                    f"column type conflict for {table_name}.{column.name}: "
                    f"database={existing['type']!s}, model={column.type!s}"
                )
            if bool(existing.get("nullable", True)) != bool(column.nullable):
                raise RuntimeError(
                    f"column nullability conflict for {table_name}.{column.name}"
                )


def _assert_legacy_source_is_safe(connection, inspector) -> None:
    if not inspector.has_table(LEGACY_UNFULFILLED_TABLE):
        raise RuntimeError(
            f"required legacy table {LEGACY_UNFULFILLED_TABLE} is missing"
        )
    columns = {
        column["name"] for column in inspector.get_columns(LEGACY_UNFULFILLED_TABLE)
    }
    required = {"id", "shop_id", "posting_number", "first_seen_at", "create_time"}
    missing = required - columns
    if missing:
        raise RuntimeError(
            f"legacy unfulfilled-postings table is missing columns: {sorted(missing)}"
        )
    quoted = _quote(connection, LEGACY_UNFULFILLED_TABLE)
    invalid = connection.execute(
        sa.text(
            f"SELECT COUNT(*) FROM {quoted} "
            "WHERE shop_id IS NULL OR posting_number IS NULL OR posting_number = ''"
        )
    ).scalar_one()
    if invalid:
        raise RuntimeError(
            f"legacy unfulfilled-postings table has {invalid} invalid business keys"
        )
    duplicate_groups = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM ("
            f"SELECT 1 FROM {quoted} GROUP BY shop_id, posting_number "
            "HAVING COUNT(*) > 1"
            ") AS duplicate_keys"
        )
    ).scalar_one()
    if duplicate_groups:
        raise RuntimeError(
            "legacy unfulfilled-postings table contains duplicate "
            f"(shop_id, posting_number) groups: {duplicate_groups}"
        )


def _create_missing_tables(connection, inspector) -> set[str]:
    existing_tables = set(inspector.get_table_names())
    created = set()
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            table.create(connection, checkfirst=True)
            created.add(table.name)
    return created


def _add_missing_columns(connection, created_tables: set[str]) -> None:
    inspector = sa.inspect(connection)
    existing_tables = set(inspector.get_table_names())
    for table_name, table in Base.metadata.tables.items():
        if table_name in created_tables or table_name not in existing_tables:
            continue
        existing_columns = {
            column["name"] for column in inspector.get_columns(table_name)
        }
        for column in table.columns:
            if column.name not in existing_columns:
                op.add_column(table_name, column._copy())


def _index_signatures(inspector, table_name: str) -> set[tuple[bool, tuple[str, ...]]]:
    signatures = {
        (bool(index.get("unique")), tuple(index["column_names"]))
        for index in inspector.get_indexes(table_name)
    }
    signatures.update(
        (True, tuple(item["column_names"]))
        for item in inspector.get_unique_constraints(table_name)
    )
    return signatures


def _duplicate_group_count(
    connection, table_name: str, columns: tuple[str, ...]
) -> int:
    quoted_table = _quote(connection, table_name)
    quoted_columns = ", ".join(_quote(connection, name) for name in columns)
    return int(
        connection.execute(
            sa.text(
                "SELECT COUNT(*) FROM ("
                f"SELECT 1 FROM {quoted_table} GROUP BY {quoted_columns} "
                "HAVING COUNT(*) > 1"
                ") AS duplicate_keys"
            )
        ).scalar_one()
    )


def _add_missing_indexes_and_unique_constraints(connection) -> None:
    inspector = sa.inspect(connection)
    for table_name, table in Base.metadata.tables.items():
        signatures = _index_signatures(inspector, table_name)
        for constraint in table.constraints:
            if not isinstance(constraint, sa.UniqueConstraint):
                continue
            columns = tuple(column.name for column in constraint.columns)
            signature = (True, columns)
            if signature in signatures:
                continue
            duplicates = _duplicate_group_count(connection, table_name, columns)
            if duplicates:
                raise RuntimeError(
                    f"cannot add unique constraint to {table_name}{columns}; "
                    f"found {duplicates} duplicate groups"
                )
            op.create_unique_constraint(constraint.name, table_name, list(columns))
            signatures.add(signature)
        for index in table.indexes:
            columns = tuple(column.name for column in index.columns)
            signature = (bool(index.unique), columns)
            if signature in signatures:
                continue
            if index.unique:
                duplicates = _duplicate_group_count(connection, table_name, columns)
                if duplicates:
                    raise RuntimeError(
                        f"cannot add unique index to {table_name}{columns}; "
                        f"found {duplicates} duplicate groups"
                    )
            op.create_index(index.name, table_name, list(columns), unique=index.unique)
            signatures.add(signature)


def _add_missing_foreign_keys(connection) -> None:
    inspector = sa.inspect(connection)
    for table_name, table in Base.metadata.tables.items():
        existing = {
            (
                tuple(item["constrained_columns"]),
                item["referred_table"],
                tuple(item["referred_columns"]),
            )
            for item in inspector.get_foreign_keys(table_name)
        }
        for constraint in table.foreign_key_constraints:
            elements = list(constraint.elements)
            signature = (
                tuple(element.parent.name for element in elements),
                elements[0].column.table.name,
                tuple(element.column.name for element in elements),
            )
            if signature in existing:
                continue
            local_columns, remote_table, remote_columns = signature
            op.create_foreign_key(
                constraint.name,
                table_name,
                remote_table,
                list(local_columns),
                list(remote_columns),
                ondelete=constraint.ondelete,
                onupdate=constraint.onupdate,
            )
            existing.add(signature)


def _copy_legacy_unfulfilled_rows(connection) -> None:
    source_count = _row_count(connection, LEGACY_UNFULFILLED_TABLE)
    target_count = _row_count(connection, CURRENT_UNFULFILLED_TABLE)
    source = Base.metadata.tables[CURRENT_UNFULFILLED_TABLE]
    inspector = sa.inspect(connection)
    legacy_columns = {
        column["name"] for column in inspector.get_columns(LEGACY_UNFULFILLED_TABLE)
    }
    common_columns = [
        column.name
        for column in source.columns
        if column.name in legacy_columns
        and column.name not in {"last_seen_at", "is_active", "resolved_at"}
    ]
    if target_count == 0 and source_count:
        quoted_target = _quote(connection, CURRENT_UNFULFILLED_TABLE)
        quoted_source = _quote(connection, LEGACY_UNFULFILLED_TABLE)
        insert_columns = common_columns + ["last_seen_at", "is_active"]
        insert_sql = ", ".join(_quote(connection, name) for name in insert_columns)
        select_sql = ", ".join(_quote(connection, name) for name in common_columns)
        connection.execute(
            sa.text(
                f"INSERT INTO {quoted_target} ({insert_sql}) "
                f"SELECT {select_sql}, "
                "COALESCE(update_time, first_seen_at, create_time, CURRENT_TIMESTAMP), 1 "
                f"FROM {quoted_source}"
            )
        )
        target_count = _row_count(connection, CURRENT_UNFULFILLED_TABLE)
    if target_count != source_count:
        raise RuntimeError(
            "legacy unfulfilled-postings copy count mismatch: "
            f"source={source_count}, target={target_count}"
        )
    quoted_source = _quote(connection, LEGACY_UNFULFILLED_TABLE)
    quoted_target = _quote(connection, CURRENT_UNFULFILLED_TABLE)
    missing_keys = connection.execute(
        sa.text(
            f"SELECT COUNT(*) FROM {quoted_source} AS source "
            f"LEFT JOIN {quoted_target} AS target "
            "ON target.shop_id = source.shop_id "
            "AND target.posting_number = source.posting_number "
            "WHERE target.id IS NULL"
        )
    ).scalar_one()
    if missing_keys:
        raise RuntimeError(
            f"legacy unfulfilled-postings copy is missing {missing_keys} business keys"
        )


def upgrade() -> None:
    connection = op.get_bind()
    _assert_frozen_model()
    _assert_previous_revision(connection)
    inspector = sa.inspect(connection)
    _assert_existing_columns_are_compatible(connection, inspector)
    _assert_legacy_source_is_safe(connection, inspector)
    created_tables = _create_missing_tables(connection, inspector)
    _add_missing_columns(connection, created_tables)
    _add_missing_indexes_and_unique_constraints(connection)
    _add_missing_foreign_keys(connection)
    _copy_legacy_unfulfilled_rows(connection)


def downgrade() -> None:
    raise RuntimeError(
        "production bridge downgrade is intentionally disabled because removing "
        "the additive schema could destroy data; restore the verified backup instead"
    )
