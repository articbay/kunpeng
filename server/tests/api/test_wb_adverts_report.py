"""Tests for Wildberries adverts report API handlers."""

from datetime import datetime
from io import BytesIO
from unittest.mock import AsyncMock, Mock

import openpyxl
import pytest
from fastapi import HTTPException

from kunpeng.api.v1 import wildberries


@pytest.mark.asyncio
async def test_normal_user_cannot_call_wildberries_write_endpoints():
    with pytest.raises(HTTPException) as exc_info:
        await wildberries._require_authenticated_reader_or_admin_writer(
            Mock(method="POST"), Mock(is_superuser=False)
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_export_adverts_report_returns_readable_xlsx(monkeypatch):
    monkeypatch.setattr(
        wildberries,
        "_accessible_wb_shop_ids",
        AsyncMock(return_value=[8]),
    )
    monkeypatch.setattr(
        wildberries,
        "now_platform",
        lambda: datetime(2026, 8, 13, 10, 30, 25),
    )
    advert = Mock(
        shop_id=8,
        week="week202632",
        advert_id=12345,
        advert_name="测试广告",
        advert_status_label="进行中",
        paid_views=100,
        paid_clicks=10,
        ctr=10,
        cpc=2.5,
        atbs=4,
        orders=2,
        cr=20,
        sum_cost=25,
        sum_price=100,
    )
    get_paginated = AsyncMock(return_value=([advert], 1))
    monkeypatch.setattr(
        wildberries.crud_dwd_wb_adverts_report_detail,
        "get_paginated",
        get_paginated,
    )
    monkeypatch.setattr(
        wildberries.shop_crud,
        "get_names_by_ids",
        AsyncMock(return_value={8: "测试店铺"}),
    )

    response = await wildberries.export_adverts_report_excel(
        shop_id=8,
        week=None,
        advert_id=None,
        advert_status=None,
        db=Mock(),
        current_user=Mock(id=3),
    )
    content = b"".join([chunk async for chunk in response.body_iterator])

    assert response.media_type.endswith("spreadsheetml.sheet")
    disposition = response.headers["content-disposition"]
    assert disposition == (
        'attachment; filename="wb_adverts_report_20260813_103025.xlsx"; '
        "filename*=UTF-8''WB%E5%B9%BF%E5%91%8A%E5%91%A8%E6%8A%A5_"
        "20260813_103025.xlsx"
    )
    disposition.encode("latin-1")

    workbook = openpyxl.load_workbook(BytesIO(content), read_only=True)
    worksheet = workbook["广告周度报表"]
    assert worksheet["A1"].value == "店铺ID"
    assert worksheet["B1"].value == "店铺名称"
    assert worksheet["A2"].value == 8
    assert worksheet["B2"].value == "测试店铺"
    assert worksheet["C2"].value == "week202632"
    assert worksheet["E2"].value == "测试广告"
    workbook.close()
