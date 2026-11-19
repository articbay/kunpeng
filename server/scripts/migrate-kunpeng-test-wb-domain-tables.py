"""Copy legacy Chinese WB domain tables into their canonical English tables.

The command is intentionally limited to the ``kunpeng_test`` database. Its
default mode is read-only. Applying the copy requires both ``--apply`` and an
explicit confirmation phrase. It never drops, truncates, renames, or deletes a
table or row.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.engine import Connection, Engine, make_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kunpeng.config import settings  # noqa: E402

ALLOWED_DATABASE = "kunpeng_test"
APPLY_CONFIRMATION = "复制中文表数据到英文表"


@dataclass(frozen=True)
class TableCopy:
    source: str
    target: str
    business_key: tuple[str, ...]


TABLE_COPIES = (
    TableCopy(
        "ods_wb_财务_region_sales",
        "ods_wb_finance_region_sales",
        ("shop_id", "date_from", "date_to", "row_key"),
    ),
    TableCopy(
        "ods_wb_财务_seller_balance",
        "ods_wb_finance_seller_balance",
        ("shop_id", "snapshot_date"),
    ),
    TableCopy(
        "ods_wb_流量_product_search_texts",
        "ods_wb_traffic_product_search_texts",
        (
            "shop_id",
            "date_from",
            "date_to",
            "nm_id",
            "search_text_hash",
            "top_order_by",
        ),
    ),
    TableCopy(
        "ods_wb_流量_search_traffic",
        "ods_wb_traffic_search_traffic",
        ("shop_id", "date_from", "date_to", "nm_id", "position_cluster"),
    ),
)


def _sync_url() -> sa.engine.URL:
    url = make_url(settings.database_url)
    if url.database != ALLOWED_DATABASE:
        raise RuntimeError(
            f"this script only permits database {ALLOWED_DATABASE!r}; "
            f"configured database is {url.database!r}"
        )
    if url.drivername == "mysql+asyncmy":
        url = url.set(drivername="mysql+pymysql")
    if not url.drivername.startswith("mysql"):
        raise RuntimeError("this script requires MySQL")
    return url


def _quote(connection: Connection, identifier: str) -> str:
    return connection.dialect.identifier_preparer.quote(identifier)


def _column_signature(inspector: sa.Inspector, table_name: str) -> list[tuple]:
    return [
        (
            column["name"],
            str(column["type"]),
            bool(column["nullable"]),
            str(column.get("default")),
        )
        for column in inspector.get_columns(table_name)
    ]


def _validate_pair(connection: Connection, item: TableCopy) -> list[str]:
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names())
    missing = [name for name in (item.source, item.target) if name not in tables]
    if missing:
        raise RuntimeError(f"required tables are missing: {missing}")
    if _column_signature(inspector, item.source) != _column_signature(
        inspector, item.target
    ):
        raise RuntimeError(
            f"column definitions differ between {item.source} and {item.target}"
        )
    columns = [column["name"] for column in inspector.get_columns(item.source)]
    if "id" not in columns or not set(item.business_key).issubset(columns):
        raise RuntimeError(f"unexpected columns in {item.source}")
    return columns


def _join_condition(
    connection: Connection, item: TableCopy, left: str, right: str
) -> str:
    return " AND ".join(
        f"{left}.{_quote(connection, column)} = "
        f"{right}.{_quote(connection, column)}"
        for column in item.business_key
    )


def _scalar(connection: Connection, sql: str) -> int:
    return int(connection.execute(sa.text(sql)).scalar_one())


def _pair_counts(
    connection: Connection, item: TableCopy, columns: list[str]
) -> dict[str, int]:
    source = _quote(connection, item.source)
    target = _quote(connection, item.target)
    join = _join_condition(connection, item, "source", "target")
    first_key = _quote(connection, item.business_key[0])
    comparable_columns = [column for column in columns if column != "id"]
    different = " OR ".join(
        "NOT (target.{column} <=> source.{column})".format(
            column=_quote(connection, column)
        )
        for column in comparable_columns
    )
    return {
        "source": _scalar(connection, f"SELECT COUNT(*) FROM {source}"),
        "target": _scalar(connection, f"SELECT COUNT(*) FROM {target}"),
        "missing": _scalar(
            connection,
            f"SELECT COUNT(*) FROM {source} AS source "
            f"LEFT JOIN {target} AS target ON {join} "
            f"WHERE target.{first_key} IS NULL",
        ),
        "conflicting_business_rows": _scalar(
            connection,
            f"SELECT COUNT(*) FROM {source} AS source "
            f"JOIN {target} AS target ON {join} WHERE {different}",
        ),
    }


def _copy_missing_rows(
    connection: Connection, item: TableCopy, columns: list[str]
) -> None:
    source = _quote(connection, item.source)
    target = _quote(connection, item.target)
    join = _join_condition(connection, item, "source", "target")
    first_key = _quote(connection, item.business_key[0])
    insert_columns = [column for column in columns if column != "id"]
    quoted_columns = ", ".join(_quote(connection, column) for column in insert_columns)
    selected_columns = ", ".join(
        f"source.{_quote(connection, column)}" for column in insert_columns
    )
    connection.execute(
        sa.text(
            f"INSERT INTO {target} ({quoted_columns}) "
            f"SELECT {selected_columns} FROM {source} AS source "
            f"LEFT JOIN {target} AS target ON {join} "
            f"WHERE target.{first_key} IS NULL"
        )
    )


def inspect_or_copy(engine: Engine, apply: bool) -> None:
    with engine.begin() as connection:
        for item in TABLE_COPIES:
            columns = _validate_pair(connection, item)
            before = _pair_counts(connection, item, columns)
            print(
                f"{item.source} -> {item.target}: "
                f"source={before['source']}, target={before['target']}, "
                f"missing={before['missing']}, "
                f"conflicts={before['conflicting_business_rows']}"
            )
            if before["conflicting_business_rows"]:
                raise RuntimeError(f"conflicting rows detected for {item.target}")
            if not apply:
                continue
            _copy_missing_rows(connection, item, columns)
            after = _pair_counts(connection, item, columns)
            if after["missing"] or after["conflicting_business_rows"]:
                raise RuntimeError(f"copy validation failed for {item.target}")
            print(f"validated {item.target}: target={after['target']}, missing=0")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="copy missing rows; without this option the command is read-only",
    )
    parser.add_argument(
        "--confirm",
        help=f"required with --apply; exact value: {APPLY_CONFIRMATION}",
    )
    arguments = parser.parse_args()
    if arguments.apply and arguments.confirm != APPLY_CONFIRMATION:
        raise RuntimeError("--apply requires the exact confirmation phrase")
    engine = sa.create_engine(_sync_url())
    try:
        inspect_or_copy(engine, arguments.apply)
    finally:
        engine.dispose()
    if not arguments.apply:
        print("read-only inspection complete; no rows were written")


if __name__ == "__main__":
    main()
