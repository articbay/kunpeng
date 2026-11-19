from pathlib import Path


def test_ozon_goods_trade_return_dwm_migration_is_isolated():
    migrations_dir = Path(__file__).parents[2] / "migrations" / "versions_v3"
    migration = next(migrations_dir.glob("*e7bc14b82f34*.py"))
    content = migration.read_text(encoding="utf-8")

    assert 'down_revision = "7d1c5e8a9b20"' in content
    assert '"dwm_ozon_goods_trade_return_day"' in content
    assert "op.create_table(" in content
    assert 'op.drop_table("dwm_ozon_goods_trade_return_day")' in content
    assert "op.alter_column" not in content
    assert "op.drop_constraint" not in content
    assert "dwd_ozon_return_detail" not in content
    assert "ods_wb_" not in content


def test_ozon_goods_trade_return_metrics_migration_is_isolated():
    migrations_dir = Path(__file__).parents[2] / "migrations" / "versions_v3"
    migration = next(migrations_dir.glob("*71aa58ec43a8*.py"))
    content = migration.read_text(encoding="utf-8")

    assert 'down_revision = "e7bc14b82f34"' in content
    assert 'TABLE = "dwm_ozon_goods_trade_return_day"' in content
    assert '"traffic_views"' in content
    assert '"ad_spend_amount"' in content
    assert "dwd_ozon_return_detail" not in content
    assert "ods_wb_" not in content
    assert "drop_constraint" not in content


def test_ozon_funnel_trade_metrics_migration_is_isolated():
    migrations_dir = Path(__file__).parents[2] / "migrations" / "versions_v3"
    migration = next(migrations_dir.glob("*15a40516a399*.py"))
    content = migration.read_text(encoding="utf-8")

    assert 'down_revision = "71aa58ec43a8"' in content
    assert 'TABLE = "dwm_ozon_goods_trade_return_day"' in content
    assert '"funnel_ordered_units"' in content
    assert '"funnel_revenue"' in content
    assert "dwd_ozon_return_detail" not in content
    assert "ods_wb_" not in content
    assert "drop_constraint" not in content
