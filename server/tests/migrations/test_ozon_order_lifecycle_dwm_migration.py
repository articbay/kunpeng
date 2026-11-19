from pathlib import Path


def test_ozon_order_lifecycle_dwm_migration_is_isolated():
    migrations_dir = Path(__file__).parents[2] / "migrations" / "versions_v3"
    migration = next(migrations_dir.glob("*708d523cbcbf*.py"))
    content = migration.read_text(encoding="utf-8")

    assert 'down_revision = "15a40516a399"' in content
    assert 'TABLE = "dwm_ozon_order_lifecycle_detail"' in content
    assert "op.create_table(" in content
    assert "op.drop_table(TABLE)" in content
    assert "op.alter_column" not in content
    assert "op.drop_constraint" not in content
    assert '"delivered_at"' not in content
    assert "dwd_ozon_return_detail" not in content
    assert "ods_wb_" not in content
