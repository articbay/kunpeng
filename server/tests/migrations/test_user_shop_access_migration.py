from pathlib import Path

MIGRATION = (
    Path(__file__).resolve().parents[2]
    / "migrations"
    / "versions_v3"
    / "20260814_1216_ed9544c6a0c7_新增用户店铺授权关系.py"
)


def test_user_shop_access_migration_is_additive_and_scoped():
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'down_revision = "c3f1a9e7b2d4"' in source
    assert '"user_shop_access"' in source
    assert '"uq_user_shop_access_user_shop"' in source
    assert '"fk_user_shop_access_user_id"' in source
    assert '"fk_user_shop_access_shop_id"' in source
    assert "op.drop_table" not in source
