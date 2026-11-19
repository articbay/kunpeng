import importlib.util
from pathlib import Path


def _load_migration():
    migration_path = (
        Path(__file__).parents[2]
        / "migrations"
        / "versions_v2"
        / "20260807_1123_f7cdab07927f_restore_wb_ods_api_native_barcode_fields.py"
    )
    spec = importlib.util.spec_from_file_location(
        "wb_ods_native_barcode_migration",
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
        self.events = []

    def add_column(self, table_name, column):
        self.added.append((table_name, column.name))
        self.events.append(("add", table_name, column.name))

    def drop_column(self, table_name, column_name):
        self.dropped.append((table_name, column_name))
        self.events.append(("drop", table_name, column_name))

    def execute(self, statement):
        self.statements.append(str(statement))
        self.events.append(("execute", str(statement)))


def test_upgrade_restores_native_fields_before_dropping_ods_normalized_fields():
    migration = _load_migration()
    operations = RecordingOperations()
    migration.op = operations

    migration.upgrade()

    assert set(operations.added) == set(
        (*migration.SCALAR_ODS_COLUMNS, *migration.ARRAY_ODS_COLUMNS)
    )
    assert set(operations.dropped) == {
        (table_name, column_name)
        for table_name, _ in (
            *migration.SCALAR_ODS_COLUMNS,
            *migration.ARRAY_ODS_COLUMNS,
        )
        for column_name in ("barcode_ori", "barcode_hand")
    }
    sql = "\n".join(operations.statements)
    assert "JSON_UNQUOTE(JSON_EXTRACT(row_data, '$.barcode'))" in sql
    assert "JSON_UNQUOTE(JSON_EXTRACT(row_data, '$.sku'))" in sql
    assert "JSON_EXTRACT(row_data, '$.skus')" in sql
    assert "COALESCE" in sql
    first_drop = next(
        i for i, event in enumerate(operations.events) if event[0] == "drop"
    )
    last_backfill = max(
        i for i, event in enumerate(operations.events) if event[0] == "execute"
    )
    assert last_backfill < first_drop


def test_downgrade_can_recreate_normalized_ods_fields_from_native_values():
    migration = _load_migration()
    operations = RecordingOperations()
    migration.op = operations

    migration.downgrade()

    for table_name, _ in (
        *migration.SCALAR_ODS_COLUMNS,
        *migration.ARRAY_ODS_COLUMNS,
    ):
        assert (table_name, "barcode_ori") in operations.added
        assert (table_name, "barcode_hand") in operations.added
    assert set(operations.dropped) == set(
        (*migration.SCALAR_ODS_COLUMNS, *migration.ARRAY_ODS_COLUMNS)
    )
    sql = "\n".join(operations.statements)
    assert "REGEXP '^[0-9]{13}$'" in sql
    assert "REGEXP '[A-Za-z]'" in sql
    assert "JSON_TABLE" in sql
