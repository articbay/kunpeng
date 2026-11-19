from pathlib import Path

MIGRATION = next(
    Path("migrations/versions_v3").glob("*_4b7f2d91a6c3_统一wb订单状态中文词典.py")
)


def test_migration_normalizes_both_wb_order_tables():
    content = MIGRATION.read_text(encoding="utf-8")
    assert 'down_revision = "86a5e58bca0a"' in content
    assert '"dwd_wb_order_detail"' in content
    assert '"dwm_wb_order_lifecycle_detail"' in content
    assert '"sorted": "WB已接收并分拣"' in content
    assert '"confirm": "组装中"' in content
    assert "LOWER(TRIM({source_column}))" in content
