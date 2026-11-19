from pathlib import Path


MIGRATION = next(
    Path("migrations/versions_v3").glob(
        "*_b83e1c4d7a92_wb履约订单增加折算币种代码.py"
    )
)


def test_migration_adds_and_backfills_converted_currency_code():
    content = MIGRATION.read_text(encoding="utf-8")
    assert 'down_revision = "4b7f2d91a6c3"' in content
    assert 'COLUMN = "converted_currency_code"' in content
    assert "sa.inspect(op.get_bind())" in content
    assert "if not _column_exists():" in content
    assert "if_not_exists" not in content
    assert "if_exists" not in content
    assert "INNER JOIN ods_wb_marketplace_orders AS source" in content
    assert "source.converted_currency_code" in content
