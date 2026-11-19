from pathlib import Path

MIGRATION = next(Path("migrations/versions_v3").glob("*3c0abdefb7e3*.py"))


def test_wb_order_lifecycle_migration_is_isolated() -> None:
    content = MIGRATION.read_text(encoding="utf-8")

    assert 'revision = "3c0abdefb7e3"' in content
    assert 'down_revision = "6a0b76653ac4"' in content
    assert 'TABLE = "dwm_wb_order_lifecycle_detail"' in content
    assert "op.create_table(" in content
    assert "op.drop_table(TABLE)" in content
    assert "op.alter_column(" not in content
    assert "op.create_foreign_key(" not in content
    assert "dwm_ozon_" not in content
