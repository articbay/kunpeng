from datetime import date

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from kunpeng.api.v1 import api_router
from kunpeng.crud.dwm.wildberries.order_lifecycle_query import (
    CRUDDWMWBOrderLifecycleQuery,
)
from kunpeng.models.dwm import DWMWBOrderLifecycleDetail
from kunpeng.schemas.wb_order_lifecycle import (
    WBOrderLifecycleExportRequest,
    WBOrderLifecycleFilters,
)


def test_wb_order_lifecycle_routes_are_registered() -> None:
    paths = {route.path for route in api_router.routes}

    assert {
        "/wildberries/order-lifecycle",
        "/wildberries/order-lifecycle/summary",
        "/wildberries/order-lifecycle/export",
    }.issubset(paths)


def test_wb_lifecycle_filters_reject_reversed_date_range() -> None:
    with pytest.raises(ValidationError, match="开始日期不能晚于结束日期"):
        WBOrderLifecycleFilters(
            date_from=date(2026, 9, 1),
            date_to=date(2026, 8, 31),
        )


def test_wb_selected_export_requires_keys() -> None:
    with pytest.raises(ValidationError, match="至少需要选择一条"):
        WBOrderLifecycleExportRequest(scope="selected")


def test_wb_lifecycle_query_is_permission_scoped_and_index_friendly() -> None:
    query = CRUDDWMWBOrderLifecycleQuery()._apply_filters(
        select(DWMWBOrderLifecycleDetail),
        allowed_shop_ids=[8, 9],
        date_from=date(2026, 8, 1),
        date_to=date(2026, 8, 31),
        stage="sold",
    )
    sql = str(query).upper()

    assert "SHOP_ID IN" in sql
    assert "ORDER_AT >=" in sql
    assert "ORDER_AT <" in sql
    assert "LIFECYCLE_STAGE =" in sql
    assert "DATE(" not in sql


def test_wb_lifecycle_empty_permissions_force_empty_result() -> None:
    query = CRUDDWMWBOrderLifecycleQuery()._apply_filters(
        select(DWMWBOrderLifecycleDetail),
        allowed_shop_ids=[],
    )

    assert "false" in str(query).lower()
