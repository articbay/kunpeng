import importlib.util
from datetime import datetime
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    inspect,
    select,
)


def _load_migration():
    migration_path = (
        Path(__file__).parents[2]
        / "migrations"
        / "versions"
        / "20260727_1200_7c4e1b9a2d60_upgrade_ozon_unfulfilled_v4.py"
    )
    spec = importlib.util.spec_from_file_location(
        "ozon_unfulfilled_v4_migration",
        migration_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _install_operations(migration, connection):
    migration.op = Operations(MigrationContext.configure(connection))


def test_migration_creates_full_table_when_missing_and_is_repeatable():
    migration = _load_migration()
    engine = create_engine("sqlite://")

    with engine.begin() as connection:
        _install_operations(migration, connection)
        migration.upgrade()
        migration.upgrade()

        inspector = inspect(connection)
        columns = {
            column["name"]
            for column in inspector.get_columns("ods_ozon_unfulfilled_postings")
        }
        indexes = {
            index["name"]
            for index in inspector.get_indexes("ods_ozon_unfulfilled_postings")
        }
        unique_names = {
            constraint["name"]
            for constraint in inspector.get_unique_constraints(
                "ods_ozon_unfulfilled_postings"
            )
        }

        assert {"last_seen_at", "is_active", "resolved_at"} <= columns
        assert {
            "idx_ods_ozon_unfulfilled_postings_shop_active",
            "idx_ods_ozon_unfulfilled_postings_shop_cutoff",
        } <= indexes
        assert "uq_ods_ozon_unfulfilled_postings_shop_posting" in unique_names

        migration.downgrade()
        assert inspector.has_table("ods_ozon_unfulfilled_postings")
        remaining = {
            column["name"]
            for column in inspect(connection).get_columns(
                "ods_ozon_unfulfilled_postings"
            )
        }
        assert "last_seen_at" not in remaining
        assert "is_active" not in remaining
        assert "resolved_at" not in remaining


def test_migration_preserves_existing_rows_and_backfills_state():
    migration = _load_migration()
    engine = create_engine("sqlite://")
    metadata = MetaData()
    legacy = Table(
        "ods_ozon_unfulfilled_postings",
        metadata,
        Column("id", BigInteger, primary_key=True),
        Column("shop_id", Integer, nullable=False),
        Column("posting_number", String(100), nullable=False),
        Column("cutoff_at", DateTime, nullable=True),
        Column("first_seen_at", DateTime, nullable=False),
        Column("create_time", DateTime, nullable=False),
    )
    first_seen = datetime(2026, 7, 20, 8, 30)

    with engine.begin() as connection:
        metadata.create_all(connection)
        connection.execute(
            legacy.insert().values(
                id=1,
                shop_id=7,
                posting_number="P-1",
                cutoff_at=datetime(2026, 7, 27, 9, 0),
                first_seen_at=first_seen,
                create_time=first_seen,
            )
        )
        _install_operations(migration, connection)
        migration.upgrade()

        upgraded = Table(
            "ods_ozon_unfulfilled_postings",
            MetaData(),
            autoload_with=connection,
        )
        row = connection.execute(select(upgraded)).mappings().one()
        assert row["posting_number"] == "P-1"
        assert row["last_seen_at"] == first_seen
        assert bool(row["is_active"]) is True
        assert row["resolved_at"] is None
