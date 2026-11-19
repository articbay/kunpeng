from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations" / "versions_v3"


def _migration_content() -> str:
    pattern = "*_d2f6a91c8e47_调整wb订单折算币种列顺序.py"
    migration = next(MIGRATIONS_DIR.glob(pattern))
    return migration.read_text(encoding="utf-8")


def test_migration_moves_converted_currency_code_after_currency_code():
    content = _migration_content()

    assert 'down_revision = "b83e1c4d7a92"' in content
    assert "MODIFY COLUMN converted_currency_code INTEGER NULL" in content
    assert "AFTER currency_code" in content


def test_migration_downgrade_restores_previous_column_position():
    content = _migration_content()

    downgrade = content.split("def downgrade() -> None:", maxsplit=1)[1]
    assert "AFTER is_zero_order" in downgrade
