import importlib.util
from pathlib import Path


def _load_migration():
    migration_path = (
        Path(__file__).parents[2]
        / "migrations"
        / "versions_v2"
        / "20260805_2121_11f65441bb50_standardize_wb_barcode_fields.py"
    )
    spec = importlib.util.spec_from_file_location(
        "wb_barcode_fields_migration",
        migration_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RecordingOperations:
    def __init__(self):
        self.added = []
        self.dropped = []
        self.statements = []

    def add_column(self, table_name, column):
        self.added.append((table_name, column.name))

    def drop_column(self, table_name, column_name):
        self.dropped.append((table_name, column_name))

    def execute(self, statement):
        self.statements.append(str(statement))


def test_upgrade_adds_both_fields_backfills_then_drops_legacy_columns():
    migration = _load_migration()
    operations = RecordingOperations()
    migration.op = operations

    migration.upgrade()

    assert len(operations.added) == 18
    for table_name in migration.ALL_TABLES:
        assert (table_name, "barcode_ori") in operations.added
        assert (table_name, "barcode_hand") in operations.added
    assert set(operations.dropped) == {
        *migration.ODS_SCALAR_COLUMNS,
        *migration.ODS_ARRAY_COLUMNS,
        *migration.DWD_OLD_COLUMNS,
    }
    sql = "\n".join(operations.statements)
    assert "REGEXP '^[0-9]{13}$'" in sql
    assert "REGEXP '[A-Za-z]'" in sql
    assert "JSON_TABLE" in sql
    assert "source.barcode_hand" in sql


def test_downgrade_restores_legacy_columns_and_removes_normalized_fields():
    migration = _load_migration()
    operations = RecordingOperations()
    migration.op = operations

    migration.downgrade()

    assert ("ods_wb_sales_reports", "sku") in operations.added
    assert ("ods_wb_marketplace_orders", "skus") in operations.added
    assert ("dwd_wb_return_detail", "bar_code") in operations.added
    for table_name in migration.ALL_TABLES:
        assert (table_name, "barcode_ori") in operations.dropped
        assert (table_name, "barcode_hand") in operations.dropped
