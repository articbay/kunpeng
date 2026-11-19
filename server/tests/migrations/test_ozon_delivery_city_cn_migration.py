from pathlib import Path


def test_ozon_delivery_city_cn_migration_only_adds_target_column():
    migrations_dir = Path(__file__).parents[2] / "migrations" / "versions_v3"
    migration = next(migrations_dir.glob("*eb27b4879a81*.py"))
    content = migration.read_text(encoding="utf-8")

    assert 'down_revision = "d2f6a91c8e47"' in content
    assert '"dwd_ozon_order_detail"' in content
    assert '"delivery_city_cn"' in content
    assert "op.add_column(" in content
    assert "op.drop_column(" in content
    assert "op.alter_column(" not in content
    assert "op.create_foreign_key(" not in content
    assert "dwd_ozon_return_detail" not in content
    assert "ods_" not in content
