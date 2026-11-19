from pathlib import Path


def test_ozon_posting_report_migration_only_creates_report_ods_tables():
    migrations_dir = Path(__file__).parents[2] / "migrations" / "versions_v3"
    migration = next(migrations_dir.glob("*f02795c663c5*.py"))
    content = migration.read_text(encoding="utf-8")

    assert "f653ad9c79e4" in content
    assert "ods_ozon_posting_report_tasks" in content
    assert "ods_ozon_posting_report_rows" in content
    assert "op.alter_column" not in content
    assert "ods_wb_" not in content
