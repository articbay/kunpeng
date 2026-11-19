from pathlib import Path


def test_ozon_order_dwd_migration_only_creates_new_table():
    migrations_dir = Path(__file__).parents[2] / "migrations" / "versions_v3"
    migration = next(migrations_dir.glob("*f653ad9c79e4*.py"))
    content = migration.read_text(encoding="utf-8")

    assert 'down_revision = "ed9544c6a0c7"' in content
    assert "op.create_table(" in content
    assert '"dwd_ozon_order_detail"' in content
    assert 'op.drop_table("dwd_ozon_order_detail")' in content
    assert "op.alter_table" not in content
    assert "op.alter_column" not in content
    assert "ods_wb_" not in content
