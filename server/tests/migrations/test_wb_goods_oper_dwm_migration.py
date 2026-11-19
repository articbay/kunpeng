from pathlib import Path


def test_wb_goods_oper_migration_is_scoped_to_one_table():
    migration = next(
        Path("migrations/versions_v3").glob("*6a0b76653ac4*.py")
    ).read_text(encoding="utf-8")
    assert 'TABLE = "dwm_wb_goods_oper_day"' in migration
    assert 'down_revision = "06b7070c30ee"' in migration
    assert "op.create_table(" in migration
    assert "op.drop_table(TABLE)" in migration
    assert "op.alter_column" not in migration
    assert "op.create_foreign_key" not in migration
