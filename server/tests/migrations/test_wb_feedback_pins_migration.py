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
        / "20260726_1654_2fbfbfd7f3c3_add_wb_feedback_pins.py"
    )
    spec = importlib.util.spec_from_file_location(
        "wb_feedback_pins_migration",
        migration_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_feedback_pins_migration_upgrade_downgrade_upgrade():
    migration = _load_migration()
    engine = create_engine("sqlite://")

    with engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))

        migration.upgrade()
        assert inspect(connection).has_table("ods_wb_feedback_pins")

        migration.upgrade()
        assert inspect(connection).has_table("ods_wb_feedback_pins")

        migration.downgrade()
        assert not inspect(connection).has_table("ods_wb_feedback_pins")

        migration.upgrade()
        assert inspect(connection).has_table("ods_wb_feedback_pins")
