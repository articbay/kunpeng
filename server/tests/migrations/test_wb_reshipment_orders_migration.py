import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect


def _load_migration():
    migration_path = (
        Path(__file__).parents[2]
        / "migrations"
        / "versions"
        / "20260724_1404_a0bb9a3312c7_add_wb_reshipment_orders.py"
    )
    spec = importlib.util.spec_from_file_location(
        "wb_reshipment_orders_migration",
        migration_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reshipment_orders_migration_upgrade_downgrade_upgrade():
    migration = _load_migration()
    engine = create_engine("sqlite://")

    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))

        migration.upgrade()
        assert inspect(connection).has_table("ods_wb_reshipment_orders")

        migration.upgrade()
        assert inspect(connection).has_table("ods_wb_reshipment_orders")

        migration.downgrade()
        assert not inspect(connection).has_table("ods_wb_reshipment_orders")

        migration.upgrade()
        assert inspect(connection).has_table("ods_wb_reshipment_orders")
