from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from kunpeng.services.ozon_sync_service import (
    OzonSyncService, build_product_category_name_map)


class AsyncContextClient:
    def __init__(self):
        self.finance = SimpleNamespace()
        self.product = SimpleNamespace()
        self.posting = SimpleNamespace()
        self.report = SimpleNamespace()
        self.performance = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


class AsyncContextPerformance:
    """模拟 OzonPerformanceClient（异步上下文管理器）"""

    def __init__(self):
        self.get_campaigns = None
        self.get_statistics_daily = None
        self.fetch_statistics_report = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


class FakeDb:
    def __init__(self):
        self.flush_count = 0
        self.commit_count = 0

    async def flush(self):
        self.flush_count += 1

    async def commit(self):
        self.commit_count += 1


def build_service():
    shop = SimpleNamespace(id=7, platform_shop_id="client-id", api_key="api-key")
    service = OzonSyncService(FakeDb(), shop)
    service.client = AsyncContextClient()
    service._translate_order_dwd_fields = AsyncMock(return_value={})
    service._translate_return_dwd_fields = AsyncMock(return_value={})
    return service


@pytest.mark.asyncio
async def test_sync_product_name_translations_uses_current_shop(monkeypatch):
    service = build_service()
    translate_all_missing = AsyncMock(
        return_value={
            "batches": 1,
            "unique_products": 1,
            "api_translations": 1,
            "cache_hits": 0,
            "passthrough": 0,
            "failed": 0,
            "pending": 0,
            "updated_dwd_rows": 4,
            "stalled": False,
        }
    )
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service."
        "ozon_product_translation_service.translate_all_missing",
        translate_all_missing,
    )

    result = await service.sync_product_name_translations()

    translate_all_missing.assert_awaited_once_with(
        service.db, shop_id=7, batch_size=500, max_batches=10
    )
    assert result["status"] == "success"
    assert result["count"] == 4
    assert service.db.commit_count == 1


@pytest.mark.asyncio
async def test_sync_posting_reports_builds_both_schemas_and_refreshes_dwd(
    monkeypatch,
):
    service = build_service()
    service.sync_postings = AsyncMock(return_value={"status": "success", "count": 4})
    service.sync_fbo_postings = AsyncMock(
        return_value={"status": "success", "count": 2}
    )
    sync_one = AsyncMock(side_effect=[(3, "fbs-code"), (2, "fbo-code")])
    monkeypatch.setattr(service, "_sync_posting_report_type", sync_one)
    hydrate = AsyncMock(
        return_value={
            "attempted_postings": 1,
            "hydrated_postings": 1,
            "failed_postings": 0,
            "remaining_rows": 0,
        }
    )
    monkeypatch.setattr(service, "_hydrate_unmatched_report_rows", hydrate)
    refresh_dwd = AsyncMock(
        return_value={
            "source_count": 5,
            "fbs_count": 3,
            "fbo_count": 2,
            "affected_rows": 5,
        }
    )
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_dwd_ozon_order_detail.upsert_from_ods",
        refresh_dwd,
    )

    result = await service.sync_posting_reports("2026-08-01", "2026-08-02")

    assert result["status"] == "success"
    assert result["count"] == 5
    assert result["counts"] == {"FBS": 3, "FBO": 2}
    assert result["hydration"]["remaining_rows"] == 0
    service.sync_postings.assert_awaited_once_with("2026-08-01", "2026-08-02")
    service.sync_fbo_postings.assert_awaited_once_with("2026-08-01", "2026-08-02")
    assert [call.kwargs["fulfillment_type"] for call in sync_one.await_args_list] == [
        "FBS",
        "FBO",
    ]
    hydrate.assert_awaited_once_with(report_codes={"fbs-code", "fbo-code"})
    refresh_dwd.assert_awaited_once_with(service.db, shop_id=7)
    service._translate_order_dwd_fields.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_hydrate_unmatched_report_rows_fetches_posting_detail(monkeypatch):
    service = build_service()
    report_row = SimpleNamespace(
        fulfillment_type="FBS",
        posting_number="posting-1",
    )
    list_unmatched = AsyncMock(side_effect=[[report_row], []])
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service."
        "crud_ods_ozon_posting_report_row.list_unmatched",
        list_unmatched,
    )
    service.client.posting.get_fbs_posting = AsyncMock(
        return_value={"result": {"posting_number": "posting-1", "products": [{}]}}
    )
    persist = AsyncMock(return_value=True)
    monkeypatch.setattr(service, "_persist_posting_detail", persist)

    result = await service._hydrate_unmatched_report_rows(report_codes={"report-1"})

    assert result == {
        "attempted_postings": 1,
        "hydrated_postings": 1,
        "failed_postings": 0,
        "remaining_rows": 0,
    }
    service.client.posting.get_fbs_posting.assert_awaited_once_with("posting-1")
    persist.assert_awaited_once()


@pytest.mark.asyncio
async def test_sync_finance_accruals_writes_fee_lines(monkeypatch):
    service = build_service()
    accrual_payload = {
        "accrual_id": 52796360085,
        "date": "2026-05-01",
        "total_amount": {"amount": "100.00", "currency": "RUB"},
        "unit_number": "12345-0001-1",
        "accrued_category": "POSTING",
        "posting": {
            "delivery_schema": "Fbs",
            "products": [
                {
                    "sku": 2089207791,
                    "commission": {
                        "sale_amount": {"amount": "106.00", "currency": "RUB"},
                        "sale_commission": {"amount": "-1.00", "currency": "RUB"},
                    },
                    "delivery": {
                        "services": [
                            {
                                "type_id": 32,
                                "accrued": {"amount": "-5.00", "currency": "RUB"},
                            }
                        ]
                    },
                }
            ],
        },
        "item_fees": None,
        "non_item_fee": None,
    }
    service.client.finance.get_accrual_by_day = AsyncMock(
        return_value={"accruals": [accrual_payload], "last_id": ""}
    )

    created_accrual = SimpleNamespace(id=42)
    create_accruals = AsyncMock(return_value=[created_accrual])
    replace_fees = AsyncMock(return_value=[])

    # 预加载类型字典替换为返回空字典，避免真实查库
    async def fake_load_dict():
        return {}

    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_finance_accrual.create_many",
        create_accruals,
    )
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_accrual_fee.replace_for_accrual",
        replace_fees,
    )
    monkeypatch.setattr(service, "_load_accrual_type_dict", fake_load_dict)

    result = await service.sync_finance_accruals("2026-05-01", "2026-05-01")

    assert result["status"] == "success"
    service.client.finance.get_accrual_by_day.assert_awaited_once_with(
        date="2026-05-01", last_id=None
    )
    # 费用行按 accrual_id 写入统一明细表
    assert replace_fees.await_args.kwargs["accrual_id"] == 52796360085
    assert replace_fees.await_args.kwargs["accrual"] is accrual_payload


@pytest.mark.asyncio
async def test_sync_products_uses_list_then_info_flow(monkeypatch):
    """商品同步应先调用 /v3/product/list 拿ID，再用 /v3/product/info/list 拿详情。"""
    service = build_service()
    service.client.product.get_description_category_tree = AsyncMock(
        return_value={
            "result": [
                {
                    "description_category_id": 17028668,
                    "category_name": "Уход за животными",
                    "children": [
                        {
                            "type_id": 93883,
                            "type_name": "Поводки",
                            "children": [],
                        }
                    ],
                }
            ]
        }
    )
    # 第一步：product/list 分两页，第二页无数据
    service.client.product.get_product_list = AsyncMock(
        side_effect=[
            {
                "result": {
                    "items": [
                        {"product_id": 1001, "offer_id": "OFFER-1", "sku": 2089207791},
                    ],
                    "last_id": "cursor-1",
                    "total": 1,
                }
            },
            {"result": {"items": [], "last_id": "", "total": 1}},
        ]
    )
    # 第二步：product/info/list 返回详情
    service.client.product.get_product_info_list = AsyncMock(
        return_value={
            "items": [
                {
                    "id": 1001,
                    "offer_id": "OFFER-1",
                    "name": "Collar",
                    "description_category_id": 17028668,
                    "type_id": 93883,
                    "sources": [{"sku": 2089207791}],
                }
            ]
        }
    )
    create_products = AsyncMock(return_value=[SimpleNamespace(id=1)])
    refresh_return_dwd = AsyncMock(return_value={"source_count": 0, "affected_rows": 0})
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_product.create_many",
        create_products,
    )
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_dwd_ozon_return_detail.upsert_from_ods",
        refresh_return_dwd,
    )

    result = await service.sync_products()

    assert result["status"] == "success"
    assert result["count"] == 1
    assert service.client.product.get_product_list.await_count == 2
    service.client.product.get_product_info_list.assert_awaited_once_with(
        product_ids=[1001]
    )
    create_products.assert_awaited_once()
    assert create_products.await_args.kwargs["items"][0]["_category_name"] == (
        "Поводки"
    )
    refresh_return_dwd.assert_awaited_once_with(service.db, shop_id=7)


def test_product_category_map_prefers_product_type_name():
    category_map = build_product_category_name_map(
        [
            {
                "description_category_id": 10,
                "category_name": "Родительская категория",
                "children": [
                    {"type_id": 20, "type_name": "Точный тип", "children": []}
                ],
            }
        ]
    )

    assert category_map[(10, None)] == "Родительская категория"
    assert category_map[(10, 20)] == "Точный тип"


def test_extract_product_sku_from_sources():
    """v3 详情 SKU 位于 sources[].sku，需正确提取。"""
    from kunpeng.crud.ods.ozon.products import crud_ods_ozon_product

    data = crud_ods_ozon_product._extract_item_data(
        {
            "id": 1001,
            "offer_id": "OFFER-1",
            "name": "Collar",
            "barcodes": ["BC-1", "BC-2"],
            "description_category_id": 17028668,
            "type_id": 93883,
            "_category_name": "Поводки",
            "sources": [{"sku": 2089207791}],
        },
        shop_id=7,
    )
    assert data["sku"] == 2089207791
    assert data["barcode"] == "BC-1"
    assert data["category_id"] == 17028668
    assert data["type_id"] == 93883
    assert data["category_name"] == "Поводки"
    assert data["product_id"] == 1001


@pytest.mark.asyncio
async def test_sync_returns_refreshes_storage_and_return_dwd(monkeypatch):
    service = build_service()
    service.client.return_ = SimpleNamespace(
        get_returns_list=AsyncMock(
            return_value={
                "returns": [
                    {
                        "id": 99,
                        "product": {"sku": 1234567890},
                        "storage": {"days": 2},
                    }
                ],
                "has_next": False,
                "last_id": 99,
            }
        )
    )
    create_returns = AsyncMock(return_value=[])
    create_product = AsyncMock(return_value=[])
    create_storage = AsyncMock(return_value=SimpleNamespace(id=1))
    backfill_storage = AsyncMock(return_value=1)
    refresh_return_dwd = AsyncMock(return_value={"source_count": 1, "affected_rows": 1})
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_return.create_many",
        create_returns,
    )
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_return_product.create_many_for_return",
        create_product,
    )
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_return_storage.create_or_update_for_return",
        create_storage,
    )
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_return_storage.backfill_missing_from_returns",
        backfill_storage,
    )
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_dwd_ozon_return_detail.upsert_from_ods",
        refresh_return_dwd,
    )

    result = await service.sync_returns("2026-08-01", "2026-08-02")

    assert result["status"] == "success"
    assert result["count"] == 1
    assert result["storage_backfilled"] == 1
    create_storage.assert_awaited_once()
    backfill_storage.assert_awaited_once_with(service.db, shop_id=7)
    refresh_return_dwd.assert_awaited_once_with(service.db, shop_id=7)
    service._translate_return_dwd_fields.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_sync_adverts_skips_without_performance_client():
    """未配置 Performance 凭证时，广告同步应跳过而非报错。"""
    service = build_service()
    service.client.performance = None

    result = await service.sync_adverts("2026-06-20", "2026-06-27")

    assert result["status"] == "skipped"


@pytest.mark.asyncio
async def test_sync_adverts_syncs_campaigns_and_daily_stats(monkeypatch):
    """广告同步应拉取活动列表 + 按天统计并分别 upsert。"""
    service = build_service()
    perf = AsyncContextPerformance()
    perf.get_campaigns = AsyncMock(
        return_value={"list": [{"id": "29020622", "title": "狗项圈"}]}
    )
    perf.get_statistics_daily = AsyncMock(
        return_value={
            "rows": [
                {
                    "id": "29020622",
                    "title": "狗项圈",
                    "date": "2026-06-20",
                    "views": "5883",
                    "clicks": "413",
                    "moneySpent": "881,05",
                    "orders": "17",
                    "ordersMoney": "12317,00",
                }
            ]
        }
    )
    service.client.performance = perf

    create_campaigns = AsyncMock(return_value=[SimpleNamespace(id=1)])
    create_stats = AsyncMock(return_value=[SimpleNamespace(id=1)])
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_adv_campaign.create_many",
        create_campaigns,
    )
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_adv_stat_daily.create_many",
        create_stats,
    )

    result = await service.sync_adverts("2026-06-20", "2026-06-27")

    assert result["status"] == "success"
    assert result["campaigns"] == 1
    assert result["stats"] == 1
    perf.get_campaigns.assert_awaited_once()
    perf.get_statistics_daily.assert_awaited_once_with(
        date_from="2026-06-20", date_to="2026-06-27"
    )


def test_advert_stat_extract_parses_ru_decimal_and_date():
    """广告日统计应正确解析俄式小数与日期。"""
    from decimal import Decimal

    from kunpeng.crud.ods.ozon.adverts import crud_ods_ozon_adv_stat_daily

    data = crud_ods_ozon_adv_stat_daily._extract_item_data(
        {
            "id": "29020622",
            "title": "狗项圈",
            "date": "2026-06-20",
            "views": "5883",
            "clicks": "413",
            "moneySpent": "881,05",
            "orders": "17",
            "ordersMoney": "12317,00",
        },
        shop_id=7,
    )
    assert data["campaign_id"] == "29020622"
    assert data["views"] == 5883
    assert data["money_spent"] == Decimal("881.05")
    assert data["orders_money"] == Decimal("12317.00")
    assert str(data["stat_date"]) == "2026-06-20"


def test_advert_campaign_extract_joins_placement():
    """广告活动应将 placement 数组拼接并解析预算。"""
    from decimal import Decimal

    from kunpeng.crud.ods.ozon.adverts import crud_ods_ozon_adv_campaign

    data = crud_ods_ozon_adv_campaign._extract_item_data(
        {
            "id": "29020622",
            "title": "狗项圈",
            "state": "CAMPAIGN_STATE_RUNNING",
            "advObjectType": "SKU",
            "placement": ["PLACEMENT_SEARCH_AND_CATEGORY"],
            "weeklyBudget": "6000,00",
            "fromDate": "2026-06-09",
        },
        shop_id=7,
    )
    assert data["campaign_id"] == "29020622"
    assert data["placement"] == "PLACEMENT_SEARCH_AND_CATEGORY"
    assert data["weekly_budget"] == Decimal("6000.00")
    assert str(data["from_date"]) == "2026-06-09"


def test_product_statistics_supports_only_sku_campaigns():
    service = build_service()

    assert service._supports_product_statistics({"advObjectType": "SKU"}) is True
    assert (
        service._supports_product_statistics({"advObjectType": "SEARCH_PROMO"}) is False
    )


@pytest.mark.asyncio
async def test_sync_fbs_postings_parses_v4_cursor_pages(monkeypatch):
    """FBS 同步应按 v4 cursor 翻页并读取当前响应字段。"""
    service = build_service()
    service.client.posting.get_fbs_postings = AsyncMock(
        side_effect=[
            {
                "postings": [
                    {
                        "posting_number": "12345-0001-1",
                        "products": [{"sku": 2098562954}],
                        "optional": {
                            "products_with_possible_mandatory_mark": [2098562954]
                        },
                        "external_order": {
                            "is_external": True,
                            "platform_name": "External marketplace",
                        },
                    }
                ],
                "cursor": "next-page",
                "has_next": True,
            },
            {
                "postings": [{"posting_number": "12345-0001-2", "products": []}],
                "cursor": "",
                "has_next": False,
            },
        ]
    )
    create_postings = AsyncMock(return_value=[SimpleNamespace(id=1)])
    create_products = AsyncMock(return_value=[SimpleNamespace(id=1)])
    create_optional = AsyncMock(return_value=SimpleNamespace(id=1))
    create_external = AsyncMock(return_value=SimpleNamespace(id=1))
    refresh_order_dwd = AsyncMock(
        return_value={
            "source_count": 1,
            "fbs_count": 1,
            "fbo_count": 0,
            "affected_rows": 1,
        }
    )
    refresh_return_dwd = AsyncMock(return_value={"source_count": 1, "affected_rows": 1})
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_fbs_posting.create_many",
        create_postings,
    )
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_fbs_posting_product.create_many_for_posting",
        create_products,
    )
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_fbs_posting_optional.create_or_update_for_posting",
        create_optional,
    )
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_fbs_posting_external.create_or_update_for_posting",
        create_external,
    )
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_dwd_ozon_order_detail.upsert_from_ods",
        refresh_order_dwd,
    )
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_dwd_ozon_return_detail.upsert_from_ods",
        refresh_return_dwd,
    )

    result = await service.sync_postings("2026-03-01", "2026-03-02")

    assert result["status"] == "success"
    assert result["count"] == 2
    assert create_postings.await_count == 2
    create_products.assert_awaited_once()
    refresh_order_dwd.assert_awaited_once_with(service.db, shop_id=7)
    service._translate_order_dwd_fields.assert_awaited_once_with()
    service._translate_return_dwd_fields.assert_awaited_once_with()
    assert create_optional.await_args.kwargs["optional_fields"] == {
        "products_with_possible_mandatory_mark": [2098562954]
    }
    assert create_external.await_args.kwargs["item"] == {
        "posting_number": "12345-0001-1",
        "is_external": True,
        "platform_name": "External marketplace",
    }
    calls = service.client.posting.get_fbs_postings.await_args_list
    assert calls[0].kwargs["cursor"] == ""
    assert calls[1].kwargs["cursor"] == "next-page"


@pytest.mark.asyncio
async def test_sync_fbo_postings_parses_cursor_pages_and_products(monkeypatch):
    """FBO 同步应解析 v3 顶层 postings 并按 cursor 翻页。"""
    service = build_service()
    service.client.posting.get_fbo_postings = AsyncMock(
        side_effect=[
            {
                "postings": [
                    {
                        "posting_number": "69912901-0431-2",
                        "order_id": 33921322373,
                        "status": "delivered",
                        "products": [
                            {
                                "sku": 2098562954,
                                "name": "Collar",
                                "quantity": 1,
                                "price": "528.00",
                            }
                        ],
                    }
                ],
                "cursor": "next-page",
                "has_next": True,
            },
            {
                "postings": [
                    {
                        "posting_number": "69912901-0431-3",
                        "order_id": 33921322374,
                        "status": "delivered",
                        "products": [],
                    }
                ],
                "cursor": "",
                "has_next": False,
            },
        ]
    )
    create_postings = AsyncMock(return_value=[SimpleNamespace(id=1)])
    create_products = AsyncMock(return_value=[SimpleNamespace(id=1)])
    refresh_order_dwd = AsyncMock(
        return_value={
            "source_count": 1,
            "fbs_count": 0,
            "fbo_count": 1,
            "affected_rows": 1,
        }
    )
    refresh_return_dwd = AsyncMock(return_value={"source_count": 1, "affected_rows": 1})
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_fbo_posting.create_many",
        create_postings,
    )
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_fbo_posting_product.create_many",
        create_products,
    )
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_dwd_ozon_order_detail.upsert_from_ods",
        refresh_order_dwd,
    )
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_dwd_ozon_return_detail.upsert_from_ods",
        refresh_return_dwd,
    )

    result = await service.sync_fbo_postings("2026-03-01", "2026-03-02")

    assert result["status"] == "success"
    assert result["count"] == 2
    assert create_postings.await_count == 2
    create_products.assert_awaited_once()
    refresh_order_dwd.assert_awaited_once_with(service.db, shop_id=7)
    refresh_return_dwd.assert_awaited_once_with(service.db, shop_id=7)
    service._translate_order_dwd_fields.assert_awaited_once_with()
    service._translate_return_dwd_fields.assert_awaited_once_with()
    assert create_products.await_args.kwargs["posting_number"] == "69912901-0431-2"
    calls = service.client.posting.get_fbo_postings.await_args_list
    assert calls[0].kwargs["cursor"] == ""
    assert calls[1].kwargs["cursor"] == "next-page"


@pytest.mark.asyncio
async def test_sync_fbo_postings_rejects_non_advancing_cursor(monkeypatch):
    service = build_service()
    service.client.posting.get_fbo_postings = AsyncMock(
        return_value={"postings": [], "cursor": "", "has_next": True}
    )
    refresh_return_dwd = AsyncMock()
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_dwd_ozon_return_detail.upsert_from_ods",
        refresh_return_dwd,
    )

    result = await service.sync_fbo_postings("2026-03-01", "2026-03-02")

    assert result["status"] == "error"
    assert "游标未推进" in result["message"]
    refresh_return_dwd.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_fbo_postings_rejects_missing_postings_field(monkeypatch):
    service = build_service()
    service.client.posting.get_fbo_postings = AsyncMock(
        return_value={"cursor": "", "has_next": False}
    )
    refresh_return_dwd = AsyncMock()
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_dwd_ozon_return_detail.upsert_from_ods",
        refresh_return_dwd,
    )

    result = await service.sync_fbo_postings("2026-03-01", "2026-03-02")

    assert result["status"] == "error"
    assert "缺少 postings 字段" in result["message"]
    refresh_return_dwd.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_advert_products_skips_without_performance():
    service = build_service()
    service.client.performance = None
    service.sync_advert_efficiency_dwd = AsyncMock()
    result = await service.sync_advert_products("2026-06-20", "2026-06-22")
    assert result["status"] == "skipped"
    service.sync_advert_efficiency_dwd.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_advert_products_fetches_report_per_campaign(monkeypatch):
    """SKU 明细同步应对活跃活动逐个拉取异步报表并入库。"""
    service = build_service()
    perf = AsyncContextPerformance()
    perf.get_campaigns = AsyncMock(
        return_value={
            "list": [
                {"id": "29020622", "state": "CAMPAIGN_STATE_RUNNING"},
                {"id": "11111111", "state": "CAMPAIGN_STATE_ARCHIVED"},
            ]
        }
    )
    perf.fetch_statistics_report = AsyncMock(
        return_value={
            "29020622": {
                "title": "狗项圈",
                "report": {
                    "rows": [
                        {
                            "sku": "2089207791",
                            "date": "20.06.2026",
                            "title": "Collar",
                            "views": "898",
                            "clicks": "39",
                            "ctr": "4,34",
                            "toCart": "4",
                            "moneySpent": "86,91",
                            "drr": "0,0",
                        }
                    ]
                },
            }
        }
    )
    service.client.performance = perf
    service.sync_advert_efficiency_dwd = AsyncMock(
        return_value={"status": "success", "count": 1}
    )

    create_rows = AsyncMock(return_value=[SimpleNamespace(id=1)])
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_adv_stat_product_daily.create_many",
        create_rows,
    )

    result = await service.sync_advert_products("2026-06-20", "2026-06-22")

    assert result["status"] == "success"
    # 仅活跃活动 29020622 被处理
    assert result["campaigns"] == 1
    assert result["rows"] == 1
    perf.fetch_statistics_report.assert_awaited_once()
    assert perf.fetch_statistics_report.await_args.kwargs["campaign_ids"] == [
        "29020622"
    ]
    create_rows.assert_awaited_once_with(
        service.db,
        items=perf.fetch_statistics_report.return_value["29020622"]["report"]["rows"],
        shop_id=7,
        campaign_id="29020622",
    )
    service.sync_advert_efficiency_dwd.assert_awaited_once_with(
        "2026-06-20", "2026-06-22"
    )
    assert result["advert_efficiency_dwd"]["status"] == "success"


@pytest.mark.asyncio
async def test_sync_reviews_refreshes_customer_voice_dwd():
    service = build_service()
    service.client.review = SimpleNamespace(
        get_review_list=AsyncMock(return_value={"reviews": [], "has_next": False})
    )
    service.sync_customer_voice_dwd = AsyncMock(
        return_value={"status": "success", "count": 5}
    )

    result = await service.sync_reviews("2026-06-20", "2026-06-22")

    assert result["status"] == "success"
    service.sync_customer_voice_dwd.assert_awaited_once_with("2026-06-20", "2026-06-22")
    assert result["customer_voice_dwd"] == {"status": "success", "count": 5}


@pytest.mark.asyncio
async def test_sync_reviews_reports_dwd_failure_without_losing_ods_count():
    service = build_service()
    service.client.review = SimpleNamespace(
        get_review_list=AsyncMock(return_value={"reviews": [], "has_next": False})
    )
    service.sync_customer_voice_dwd = AsyncMock(
        return_value={"status": "error", "message": "DWD failed"}
    )

    result = await service.sync_reviews("2026-06-20", "2026-06-22")

    assert result["status"] == "error"
    assert result["count"] == 0
    assert "DWD failed" in result["message"]


def test_advert_product_stat_extract_parses_ru_fields():
    """SKU 明细应正确解析俄式日期(DD.MM.YYYY)和小数。"""
    from decimal import Decimal

    from kunpeng.crud.ods.ozon.adverts import \
        crud_ods_ozon_adv_stat_product_daily

    data = crud_ods_ozon_adv_stat_product_daily._extract_item_data(
        {
            "sku": "2089207791",
            "date": "20.06.2026",
            "title": "Collar",
            "views": "898",
            "clicks": "39",
            "ctr": "4,34",
            "toCart": "4",
            "avgBid": "2,23",
            "moneySpent": "86,91",
            "ordersMoney": "0,00",
            "drr": "6,3",
            "general_drr": "2,9",
            "product_gmv": "2960,00",
        },
        shop_id=7,
        campaign_id="29020622",
    )
    assert data["sku"] == 2089207791
    assert str(data["stat_date"]) == "2026-06-20"
    assert data["ctr"] == Decimal("4.34")
    assert data["to_cart"] == 4
    assert data["money_spent"] == Decimal("86.91")
    assert data["product_gmv"] == Decimal("2960.00")


def test_parse_ru_date_and_decimal_helpers():
    import datetime as dt
    from decimal import Decimal

    from kunpeng.crud.ods.ozon.utils import parse_ru_date, parse_ru_decimal

    assert parse_ru_date("20.06.2026") == dt.date(2026, 6, 20)
    assert parse_ru_date("2026-06-20") == dt.date(2026, 6, 20)
    assert parse_ru_date("") is None
    assert parse_ru_decimal("1 234,56") == Decimal("1234.56")
    assert parse_ru_decimal("119,36") == Decimal("119.36")
    assert parse_ru_decimal(None) is None


# ==================== 广告SKU小时统计（口径对齐 WB 广告小时统计） ====================


def _make_hourly_report(views="1000", clicks="100", to_cart="50", money="500,00"):
    """构造单活动单 SKU 的当天累计报表返回"""
    return {
        "29020622": {
            "title": "狗项圈",
            "report": {
                "rows": [
                    {
                        "sku": "2089207791",
                        "date": "20.06.2026",
                        "title": "Collar",
                        "views": views,
                        "clicks": clicks,
                        "ctr": "4,34",
                        "toCart": to_cart,
                        "avgBid": "2,23",
                        "moneySpent": money,
                        "orders": "20",
                        "ordersMoney": "1200,00",
                        "drr": "6,3",
                        "product_gmv": "2960,00",
                    }
                ]
            },
        }
    }


@pytest.mark.asyncio
async def test_sync_advert_products_hourly_skips_without_performance():
    """未配置 Performance 凭证时，小时同步应跳过而非报错。"""
    service = build_service()
    service.client.performance = None
    result = await service.sync_advert_products_hourly()
    assert result["status"] == "skipped"


@pytest.mark.asyncio
async def test_sync_advert_products_hourly_normal_hour(monkeypatch):
    """正常小时：无历史累计，增量 = 当天累计全量。"""
    import datetime as dt

    service = build_service()
    perf = AsyncContextPerformance()
    perf.get_campaigns = AsyncMock(
        return_value={
            "list": [
                {"id": "29020622", "state": "CAMPAIGN_STATE_RUNNING"},
                {"id": "11111111", "state": "CAMPAIGN_STATE_ARCHIVED"},
            ]
        }
    )
    perf.fetch_statistics_report = AsyncMock(return_value=_make_hourly_report())
    service.client.performance = perf

    get_sums = AsyncMock(return_value={})
    upsert = AsyncMock(return_value=1)
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_adv_stat_product_hourly.get_hourly_sum_before_hour",
        get_sums,
    )
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_adv_stat_product_hourly.upsert_many",
        upsert,
    )

    from zoneinfo import ZoneInfo

    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.now_platform",
        lambda: dt.datetime(2026, 6, 20, 14, 5, 0, tzinfo=ZoneInfo("Europe/Moscow")),
    )

    result = await service.sync_advert_products_hourly()

    assert result["status"] == "success"
    # 仅活跃活动被处理
    assert result["campaigns"] == 1
    assert result["count"] == 1
    perf.fetch_statistics_report.assert_awaited_once()
    assert perf.fetch_statistics_report.await_args.kwargs["campaign_ids"] == [
        "29020622"
    ]

    kwargs = upsert.await_args.kwargs
    assert kwargs["stat_hour"] == 14
    assert kwargs["stat_date"] == dt.date(2026, 6, 20)
    records = kwargs["records"]
    assert len(records) == 1
    # 无历史 -> 增量 = 全量
    assert records[0]["views"] == 1000
    assert records[0]["clicks"] == 100
    assert records[0]["to_cart"] == 50
    # 快照型指标保留当天累计值
    from decimal import Decimal

    assert records[0]["ctr"] == Decimal("4.34")


@pytest.mark.asyncio
async def test_sync_advert_products_hourly_with_previous_data(monkeypatch):
    """有历史累计时，增量 = 当天累计 - 已写入累计。"""
    import datetime as dt

    service = build_service()
    perf = AsyncContextPerformance()
    perf.get_campaigns = AsyncMock(
        return_value={"list": [{"id": "29020622", "state": "CAMPAIGN_STATE_RUNNING"}]}
    )
    perf.fetch_statistics_report = AsyncMock(return_value=_make_hourly_report())
    service.client.performance = perf

    get_sums = AsyncMock(
        return_value={
            ("29020622", 2089207791): {
                "views": 600,
                "clicks": 60,
                "to_cart": 30,
                "money_spent": 300,
                "orders": 12,
                "orders_money": 700,
                "models": 0,
                "models_money": 0,
                "product_gmv": 1000,
            }
        }
    )
    upsert = AsyncMock(return_value=1)
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_adv_stat_product_hourly.get_hourly_sum_before_hour",
        get_sums,
    )
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_adv_stat_product_hourly.upsert_many",
        upsert,
    )

    from zoneinfo import ZoneInfo

    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.now_platform",
        lambda: dt.datetime(2026, 6, 20, 14, 5, 0, tzinfo=ZoneInfo("Europe/Moscow")),
    )

    result = await service.sync_advert_products_hourly()

    assert result["status"] == "success"
    records = upsert.await_args.kwargs["records"]
    assert records[0]["views"] == 400  # 1000 - 600
    assert records[0]["clicks"] == 40  # 100 - 60
    assert records[0]["to_cart"] == 20  # 50 - 30


@pytest.mark.asyncio
async def test_sync_advert_products_hourly_negative_delta_clamped(monkeypatch):
    """历史累计超过当天累计时，负增量置 0，全 0 记录被跳过。"""
    import datetime as dt

    service = build_service()
    perf = AsyncContextPerformance()
    perf.get_campaigns = AsyncMock(
        return_value={"list": [{"id": "29020622", "state": "CAMPAIGN_STATE_RUNNING"}]}
    )
    perf.fetch_statistics_report = AsyncMock(
        return_value=_make_hourly_report(
            views="100", clicks="10", to_cart="5", money="50,00"
        )
    )
    service.client.performance = perf

    get_sums = AsyncMock(
        return_value={
            ("29020622", 2089207791): {
                "views": 200,
                "clicks": 20,
                "to_cart": 10,
                "money_spent": 100,
                "orders": 20,
                "orders_money": 1200,
                "models": 0,
                "models_money": 0,
                "product_gmv": 2960,
            }
        }
    )
    upsert = AsyncMock(return_value=0)
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_adv_stat_product_hourly.get_hourly_sum_before_hour",
        get_sums,
    )
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_adv_stat_product_hourly.upsert_many",
        upsert,
    )

    from zoneinfo import ZoneInfo

    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.now_platform",
        lambda: dt.datetime(2026, 6, 20, 14, 5, 0, tzinfo=ZoneInfo("Europe/Moscow")),
    )

    result = await service.sync_advert_products_hourly()

    assert result["status"] == "success"
    # 全部为负增量 -> 无记录写入，upsert 不被调用
    assert result["count"] == 0
    upsert.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_advert_products_hourly_cross_day_boundary(monkeypatch):
    """跨天边界：00:05 执行时结算昨天 23:00。"""
    import datetime as dt

    service = build_service()
    perf = AsyncContextPerformance()
    perf.get_campaigns = AsyncMock(
        return_value={"list": [{"id": "29020622", "state": "CAMPAIGN_STATE_RUNNING"}]}
    )
    perf.fetch_statistics_report = AsyncMock(return_value=_make_hourly_report())
    service.client.performance = perf

    get_sums = AsyncMock(return_value={})
    upsert = AsyncMock(return_value=1)
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_adv_stat_product_hourly.get_hourly_sum_before_hour",
        get_sums,
    )
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_adv_stat_product_hourly.upsert_many",
        upsert,
    )

    from zoneinfo import ZoneInfo

    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.now_platform",
        lambda: dt.datetime(2026, 6, 21, 0, 5, 0, tzinfo=ZoneInfo("Europe/Moscow")),
    )

    result = await service.sync_advert_products_hourly()

    assert result["status"] == "success"
    # fetch_statistics_report 应按结算日（前一天）拉取
    assert perf.fetch_statistics_report.await_args.kwargs["date_from"] == "2026-06-20"
    kwargs = upsert.await_args.kwargs
    assert kwargs["stat_hour"] == 23
    assert kwargs["stat_date"] == dt.date(2026, 6, 20)
    # 结算日与报表日期一致，get_hourly_sum_before_hour 应按结算日查询
    assert get_sums.await_args.args[2] == dt.date(2026, 6, 20)
    assert get_sums.await_args.args[3] == 23


@pytest.mark.asyncio
async def test_sync_advert_products_hourly_uses_moscow_timezone(monkeypatch):
    """时区回归：now_platform 返回莫斯科时间时，stat_date/stat_hour 按莫斯科判定。

    场景：中国时间 2026-06-21 03:30（UTC+8），此刻莫斯科为 2026-06-20 22:30（UTC+3）。
    正确行为应结算莫斯科的 6/20 22 点，而非中国的 6/21 03 点。
    """
    import datetime as dt
    from zoneinfo import ZoneInfo

    service = build_service()
    perf = AsyncContextPerformance()
    perf.get_campaigns = AsyncMock(
        return_value={"list": [{"id": "29020622", "state": "CAMPAIGN_STATE_RUNNING"}]}
    )
    perf.fetch_statistics_report = AsyncMock(return_value=_make_hourly_report())
    service.client.performance = perf

    get_sums = AsyncMock(return_value={})
    upsert = AsyncMock(return_value=1)
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_adv_stat_product_hourly.get_hourly_sum_before_hour",
        get_sums,
    )
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.crud_ods_ozon_adv_stat_product_hourly.upsert_many",
        upsert,
    )

    # 模拟"中国 6/21 03:30 = 莫斯科 6/20 22:30"：now_platform 返回莫斯科挂钟时间
    monkeypatch.setattr(
        "kunpeng.services.ozon_sync_service.now_platform",
        lambda: dt.datetime(2026, 6, 20, 22, 30, 0, tzinfo=ZoneInfo("Europe/Moscow")),
    )

    result = await service.sync_advert_products_hourly()

    assert result["status"] == "success"
    kwargs = upsert.await_args.kwargs
    # 应按莫斯科日期/小时结算，而非中国时间的 6/21 03 点
    assert kwargs["stat_date"] == dt.date(2026, 6, 20)
    assert kwargs["stat_hour"] == 22
    assert perf.fetch_statistics_report.await_args.kwargs["date_from"] == "2026-06-20"
