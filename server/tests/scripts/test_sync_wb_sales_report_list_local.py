"""Tests for the localhost WB sales report list sync script."""

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url


def _load_script_module():
    script_path = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "sync_wb_sales_report_list_local.py"
    )
    spec = importlib.util.spec_from_file_location(
        "sync_wb_sales_report_list_local",
        script_path,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_build_local_database_url_forces_localhost():
    module = _load_script_module()

    local_url = module.build_local_database_url(
        "mysql+asyncmy://user:placeholder@remote.example:3307/kunpeng_test"
    )

    assert local_url.host == "localhost"
    assert local_url.port == 3307
    assert local_url.database == "kunpeng_test"
    assert local_url.username == "user"


def test_build_local_database_url_keeps_sqlite_url():
    module = _load_script_module()
    sqlite_url = "sqlite+aiosqlite:///local-test.db"

    assert module.build_local_database_url(sqlite_url) == make_url(sqlite_url)


@pytest.mark.asyncio
async def test_run_rejects_reversed_date_range_before_database_connection():
    module = _load_script_module()

    with pytest.raises(ValueError, match="date_from 不能晚于 date_to"):
        await module.run(8, "2026-07-26", "2026-03-01")
