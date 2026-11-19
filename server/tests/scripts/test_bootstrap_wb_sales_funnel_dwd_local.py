"""Tests for the localhost-only sales funnel DWD bootstrap script."""

import importlib.util
from pathlib import Path

from sqlalchemy.engine import make_url


def _load_script_module():
    script_path = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "bootstrap_wb_sales_funnel_dwd_local.py"
    )
    spec = importlib.util.spec_from_file_location(
        "bootstrap_wb_sales_funnel_dwd_local",
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
