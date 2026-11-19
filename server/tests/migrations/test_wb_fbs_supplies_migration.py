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
        / "20260724_1247_26b43661b6f5_add_wb_fbs_supplies.py"
    )
    spec = importlib.util.spec_from_file_location(
        "wb_fbs_supplies_migration",
        migration_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fbs_supply_migration_upgrade_downgrade_upgrade():
    migration = _load_migration()
    engine = create_engine("sqlite://")

    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))

        migration.upgrade()
        assert inspect(connection).has_table("ods_wb_fbs_supplies")

        # Re-running the guarded upgrade must not damage an existing table.
        migration.upgrade()
        assert inspect(connection).has_table("ods_wb_fbs_supplies")

        migration.downgrade()
        assert not inspect(connection).has_table("ods_wb_fbs_supplies")

        migration.upgrade()
        assert inspect(connection).has_table("ods_wb_fbs_supplies")
