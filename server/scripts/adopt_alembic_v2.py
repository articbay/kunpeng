"""Align an existing localhost database before stamping the Alembic v2 baseline.

This one-time helper is deliberately conservative:
- only localhost database URLs are accepted;
- existing tables and rows are never deleted;
- model tables that are absent are created;
- the WB return DWD date column and index are renamed in place;
- database-only legacy tables are preserved.
"""

from __future__ import annotations

import argparse

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

import kunpeng.models.dwd  # noqa: F401
import kunpeng.models.ods.ozon  # noqa: F401
import kunpeng.models.ods.wildberries  # noqa: F401
import kunpeng.models.shop  # noqa: F401
import kunpeng.models.user  # noqa: F401
from kunpeng.config import settings
from kunpeng.models.base import Base

LOCAL_DATABASE_HOSTS = {"localhost", "127.0.0.1", "::1"}
RETURN_TABLE = "dwd_wb_return_detail"
OLD_RETURN_COLUMN = "order_date"
NEW_RETURN_COLUMN = "order_dt"
OLD_RETURN_INDEX = "idx_dwd_wb_return_order_date"
NEW_RETURN_INDEX = "idx_dwd_wb_return_order_dt"
COMMENT_RECONCILIATIONS = {
    "ods_wb_sales_reports": {
        "kvw_base": ("DECIMAL(8, 2) NULL", "KVW基础"),
        "kvw": ("DECIMAL(8, 2) NULL", "KVW"),
    },
    "ods_wb_supplier_sales": {
        "discount_percent": ("INTEGER NULL", "折扣百分比"),
        "spp": ("DECIMAL(5, 2) NULL", "SPP"),
        "srid": ("VARCHAR(255) NOT NULL", "SRID"),
    },
}


def _sync_database_url() -> str:
    url = make_url(settings.database_url)
    if url.host not in LOCAL_DATABASE_HOSTS:
        raise RuntimeError(f"只允许处理 localhost 数据库，当前主机：{url.host}")
    if url.drivername == "mysql+asyncmy":
        url = url.set(drivername="mysql+pymysql")
    return url.render_as_string(hide_password=False)


def _rename_return_column(engine) -> str:
    inspector = inspect(engine)
    if RETURN_TABLE not in inspector.get_table_names():
        return "退货 DWD 表将由模型创建，字段已经是 order_dt"

    columns = {column["name"] for column in inspector.get_columns(RETURN_TABLE)}
    if OLD_RETURN_COLUMN in columns and NEW_RETURN_COLUMN in columns:
        raise RuntimeError(
            f"{RETURN_TABLE} 同时存在 {OLD_RETURN_COLUMN} 和 {NEW_RETURN_COLUMN}"
        )
    if NEW_RETURN_COLUMN in columns:
        return "退货 DWD 字段已经是 order_dt"
    if OLD_RETURN_COLUMN not in columns:
        raise RuntimeError(
            f"{RETURN_TABLE} 不存在 {OLD_RETURN_COLUMN} 或 {NEW_RETURN_COLUMN}"
        )

    indexes = {index["name"] for index in inspector.get_indexes(RETURN_TABLE)}
    with engine.begin() as connection:
        if OLD_RETURN_INDEX in indexes:
            connection.execute(
                text(f"ALTER TABLE `{RETURN_TABLE}` DROP INDEX `{OLD_RETURN_INDEX}`")
            )
        connection.execute(
            text(
                f"ALTER TABLE `{RETURN_TABLE}` "
                f"CHANGE COLUMN `{OLD_RETURN_COLUMN}` `{NEW_RETURN_COLUMN}` "
                "DATE NULL COMMENT '下单日期'"
            )
        )

    indexes = {index["name"] for index in inspect(engine).get_indexes(RETURN_TABLE)}
    if NEW_RETURN_INDEX not in indexes:
        with engine.begin() as connection:
            connection.execute(
                text(
                    f"CREATE INDEX `{NEW_RETURN_INDEX}` "
                    f"ON `{RETURN_TABLE}` (`{NEW_RETURN_COLUMN}`)"
                )
            )
    return "退货 DWD 字段和索引已原地改名，数据保持不变"


def _align_model_comments(engine) -> int:
    changed = 0
    for table_name, columns in COMMENT_RECONCILIATIONS.items():
        current_columns = {
            column["name"]: column for column in inspect(engine).get_columns(table_name)
        }
        for column_name, (column_sql, desired_comment) in columns.items():
            current = current_columns.get(column_name)
            if current is None:
                raise RuntimeError(f"{table_name}.{column_name} 不存在")
            if current.get("comment") == desired_comment:
                continue
            with engine.begin() as connection:
                connection.execute(
                    text(
                        f"ALTER TABLE `{table_name}` MODIFY COLUMN `{column_name}` "
                        f"{column_sql} COMMENT :comment"
                    ),
                    {"comment": desired_comment},
                )
            changed += 1
    return changed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="实际执行；不传时只显示计划",
    )
    args = parser.parse_args()

    engine = create_engine(_sync_database_url())
    database_tables = set(inspect(engine).get_table_names())
    model_tables = set(Base.metadata.tables)
    missing_tables = sorted(model_tables - database_tables)
    legacy_tables = sorted(database_tables - model_tables - {"alembic_version"})

    print(f"模型缺失表数量：{len(missing_tables)}")
    print("模型缺失表：" + (", ".join(missing_tables) or "无"))
    print(f"保留的数据库独有表数量：{len(legacy_tables)}")
    print("执行模式：" + ("写入" if args.apply else "只读预览"))
    if not args.apply:
        return

    if missing_tables:
        Base.metadata.create_all(
            engine,
            tables=[Base.metadata.tables[name] for name in missing_tables],
            checkfirst=True,
        )
    print(_rename_return_column(engine))
    changed_comments = _align_model_comments(engine)
    print(f"已同步字段注释数量：{changed_comments}")

    final_tables = set(inspect(engine).get_table_names())
    still_missing = sorted(model_tables - final_tables)
    if still_missing:
        raise RuntimeError("仍缺少模型表：" + ", ".join(still_missing))
    print("现有数据库已满足当前模型的表级结构要求")


if __name__ == "__main__":
    main()
