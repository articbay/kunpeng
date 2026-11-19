import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    func,
    inspect,
    select,
)


def _load_migration():
    migration_path = (
        Path(__file__).parents[2]
        / "migrations"
        / "versions"
        / "20260728_1400_91d7e6c4a2f8_standardize_recent_ods_tables.py"
    )
    spec = importlib.util.spec_from_file_location(
        "standardize_recent_ods_tables_migration",
        migration_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _install_operations(migration, connection):
    migration.op = Operations(MigrationContext.configure(connection))


def _legacy_table(metadata, name, key_columns):
    columns = [
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("shop_id", Integer, nullable=False),
    ]
    columns.extend(
        Column(column, String(100), nullable=False) for column in key_columns
    )
    columns.append(
        UniqueConstraint(
            "shop_id",
            *key_columns,
            name=f"uq_{name}_business",
        )
    )
    return Table(name, metadata, *columns)


def test_upgrade_standardizes_names_merges_rows_and_adds_fields():
    migration = _load_migration()
    engine = create_engine("sqlite://")
    metadata = MetaData()

    chat = _legacy_table(metadata, "ods_wb_chat_events", ("event_id",))
    pins = _legacy_table(metadata, "ods_wb_feedback_pins", ("pin_id",))
    supply_old = _legacy_table(metadata, "ods_wb_fbs_supplies", ("supply_id",))
    supply_target = _legacy_table(
        metadata,
        "ods_wb_order_fbs_supplies",
        ("supply_id",),
    )
    reshipment = _legacy_table(
        metadata,
        "ods_wb_reshipment_orders",
        ("order_id", "supply_id"),
    )
    ozon = _legacy_table(
        metadata,
        "ods_ozon_unfulfilled_postings",
        ("posting_number",),
    )

    with engine.begin() as connection:
        metadata.create_all(connection)
        connection.execute(chat.insert().values(shop_id=1, event_id="E-1"))
        connection.execute(pins.insert().values(shop_id=1, pin_id="11"))
        connection.execute(supply_old.insert().values(shop_id=1, supply_id="S-OLD"))
        connection.execute(
            supply_target.insert().values(shop_id=1, supply_id="S-TARGET")
        )
        connection.execute(
            reshipment.insert().values(
                shop_id=1,
                order_id="101",
                supply_id="S-1",
            )
        )
        connection.execute(ozon.insert().values(shop_id=1, posting_number="P-1"))

        _install_operations(migration, connection)
        migration.upgrade()
        migration.upgrade()

        inspector = inspect(connection)
        expected_tables = {
            "ods_wb_voc_chat_events",
            "ods_wb_voc_feedback_pins",
            "ods_wb_order_fbs_supplies",
            "ods_wb_order_reshipment_orders",
            "ods_ozon_order_unfulfilled_postings",
        }
        assert expected_tables <= set(inspector.get_table_names())
        assert "legacy_20260728_ods_wb_fbs_supplies" in inspector.get_table_names()

        supply_columns = {
            column["name"]
            for column in inspector.get_columns("ods_wb_order_fbs_supplies")
        }
        assert {
            "rejected_at",
            "recommended_warehouse_id",
            "is_pickup_point_shipment_allowed",
        } <= supply_columns

        target_supply = Table(
            "ods_wb_order_fbs_supplies",
            MetaData(),
            autoload_with=connection,
        )
        assert connection.scalar(select(func.count()).select_from(target_supply)) == 2

        ozon_columns = {
            column["name"]
            for column in inspector.get_columns("ods_ozon_order_unfulfilled_postings")
        }
        assert {
            "delivering_at",
            "shipment_without_delay_at",
            "available_actions",
            "requirements",
            "sorting_center",
            "tracking_number",
            "integration_type_flow",
            "parent_posting_number",
            "destination_place_id",
            "destination_place_name",
            "is_express",
            "is_multibox",
            "multi_box_qty",
        } <= ozon_columns
