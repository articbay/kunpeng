"""Verify the v3 Alembic bridge against a production structure-only dump.

This script only works against localhost. It creates a uniquely named disposable
database, imports the supplied schema, runs the migration, validates the result,
and removes that disposable database in a ``finally`` block.
"""

from __future__ import annotations

import argparse
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path

import pymysql
from pymysql.constants import CLIENT
from sqlalchemy.engine import make_url

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from kunpeng.config import settings  # noqa: E402

EXPECTED_OLD_REVISION = "935ae1532222"
EXPECTED_NEW_REVISION = "c3f1a9e7b2d4"
DATABASE_PREFIX = "kunpeng_v3_verify_"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
DISPOSABLE_DATABASE_PATTERN = re.compile(r"^kunpeng_v3_verify_[0-9a-f]{12}$")
EXPECTED_ENGLISH_WB_DOMAIN_TABLES = {
    "ods_wb_finance_region_sales",
    "ods_wb_finance_seller_balance",
    "ods_wb_traffic_product_search_texts",
    "ods_wb_traffic_search_traffic",
}
FORBIDDEN_CHINESE_WB_DOMAIN_TABLES = {
    "ods_wb_财务_region_sales",
    "ods_wb_财务_seller_balance",
    "ods_wb_流量_product_search_texts",
    "ods_wb_流量_search_traffic",
}


def _connection_parameters(database: str | None = None) -> dict[str, object]:
    url = make_url(settings.database_url)
    if url.host not in LOCAL_HOSTS:
        raise RuntimeError("v3 verification refuses to connect to a non-local database")
    return {
        "host": url.host,
        "port": url.port or 3306,
        "user": url.username,
        "password": url.password,
        "database": database,
        "charset": "utf8mb4",
        "autocommit": True,
        "client_flag": CLIENT.MULTI_STATEMENTS,
    }


def _execute_all(cursor, sql: str) -> None:
    cursor.execute(sql)
    while cursor.nextset():
        pass


def _quote(identifier: str) -> str:
    if not DISPOSABLE_DATABASE_PATTERN.fullmatch(identifier):
        raise RuntimeError("unsafe disposable database name")
    return f"`{identifier}`"


def _create_database(database: str) -> None:
    with pymysql.connect(**_connection_parameters()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.schemata "
                "WHERE schema_name = %s",
                (database,),
            )
            if cursor.fetchone()[0]:
                raise RuntimeError(
                    "random disposable database unexpectedly already exists"
                )
            cursor.execute(
                f"CREATE DATABASE {_quote(database)} "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )


def _drop_database(database: str) -> None:
    with pymysql.connect(**_connection_parameters()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS {_quote(database)}")


def _prepare_production_shape(database: str, dump_path: Path) -> None:
    dump_sql = dump_path.read_text(encoding="utf-8")
    with pymysql.connect(**_connection_parameters(database)) as connection:
        with connection.cursor() as cursor:
            _execute_all(cursor, dump_sql)
            cursor.execute(
                "INSERT INTO alembic_version (version_num) VALUES (%s)",
                (EXPECTED_OLD_REVISION,),
            )
            cursor.executemany(
                "INSERT INTO ods_ozon_unfulfilled_postings "
                "(shop_id, row_data, posting_number, first_seen_at, create_time) "
                "VALUES (%s, %s, %s, NOW(), NOW())",
                [
                    (1, "{}", "verify-posting-1"),
                    (2, "{}", "verify-posting-2"),
                ],
            )


def _run_upgrade(database: str) -> None:
    environment = os.environ.copy()
    environment["ALEMBIC_DATABASE_NAME"] = database
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        env=environment,
        check=True,
    )


def _validate(database: str) -> None:
    with pymysql.connect(**_connection_parameters(database)) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version_num FROM alembic_version")
            revision = cursor.fetchone()[0]
            if revision != EXPECTED_NEW_REVISION:
                raise RuntimeError(f"unexpected migrated revision: {revision}")
            cursor.execute("SELECT COUNT(*) FROM ods_ozon_unfulfilled_postings")
            source_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM ods_ozon_order_unfulfilled_postings")
            target_count = cursor.fetchone()[0]
            if (source_count, target_count) != (2, 2):
                raise RuntimeError(
                    "unfulfilled-postings validation failed: "
                    f"source={source_count}, target={target_count}"
                )
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = %s",
                (database,),
            )
            table_count = cursor.fetchone()[0]
            if table_count < 81:
                raise RuntimeError(f"too few tables after migration: {table_count}")
            cursor.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = %s",
                (database,),
            )
            table_names = {row[0] for row in cursor.fetchall()}
            missing_english = EXPECTED_ENGLISH_WB_DOMAIN_TABLES - table_names
            unexpected_chinese = FORBIDDEN_CHINESE_WB_DOMAIN_TABLES & table_names
            if missing_english:
                raise RuntimeError(
                    f"missing canonical English WB domain tables: {missing_english}"
                )
            if unexpected_chinese:
                raise RuntimeError(
                    f"unexpected Chinese WB domain tables: {unexpected_chinese}"
                )


def _reset_revision_for_retry_test(database: str) -> None:
    with pymysql.connect(**_connection_parameters(database)) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE alembic_version SET version_num = %s ",
                (EXPECTED_OLD_REVISION,),
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dump", type=Path, help="production structure-only SQL dump")
    arguments = parser.parse_args()
    dump_path = arguments.dump.resolve()
    if not dump_path.is_file():
        raise FileNotFoundError(dump_path)

    database = f"{DATABASE_PREFIX}{secrets.token_hex(6)}"
    created = False
    try:
        _create_database(database)
        created = True
        _prepare_production_shape(database, dump_path)
        _run_upgrade(database)
        _validate(database)
        _reset_revision_for_retry_test(database)
        _run_upgrade(database)
        _validate(database)
        print("v3 production-shape migration verification passed")
    finally:
        if created:
            _drop_database(database)


if __name__ == "__main__":
    main()
