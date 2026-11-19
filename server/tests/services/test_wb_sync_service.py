"""
WBSyncService 单元测试
"""

from datetime import date, datetime
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import pytest

from kunpeng.models.shop import Shop
from kunpeng.services.wb_sync_service import WBSyncService


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    return AsyncMock()


@pytest.fixture
def test_shop():
    """测试店铺对象"""
    return Shop(
        id=1,
        name="Test Shop",
        platform="wildberries",
        platform_shop_id="12345",
        api_key="test_api_key_12345",
        user_id=1,
    )


@pytest.fixture
def sample_sales_data():
    """示例销售数据"""
    return [
        {
            "srid": "sale_001",
            "date": "2024-04-01",
            "lastChangeDate": "2024-04-01T12:00:00",
            "totalPrice": 1000,
            "nm_id": 12345,
            "supplierArticle": "TEST001",
        },
        {
            "srid": "sale_002",
            "date": "2024-04-02",
            "lastChangeDate": "2024-04-02T12:00:00",
            "totalPrice": 2000,
            "nm_id": 12346,
            "supplierArticle": "TEST002",
        },
    ]


@pytest.fixture
def sample_orders_data():
    """示例订单数据"""
    return [
        {
            "srid": "order_001",
            "date": "2024-04-01",
            "lastChangeDate": "2024-04-01T12:00:00",
            "totalPrice": 1000,
            "nm_id": 12345,
            "supplierArticle": "TEST001",
            "isCancel": False,
        }
    ]


@pytest.fixture
def sample_funnel_data():
    """示例销售漏斗数据"""
    return [
        {
            "nm_id": 12345,
            "open_count": 100,
            "add_to_cart_count": 50,
            "orders_count": 20,
            "buyouts_count": 18,
        }
    ]


@pytest.fixture
def sample_returns_data():
    """示例退货数据"""
    return [
        {
            "srid": "return_001",
            "date": "2024-04-01",
            "nm_id": 12345,
            "retail_amount": 1000,
        }
    ]


class TestWBSyncService:
    """WBSyncService 测试类"""

    def test_init(self, mock_db_session, test_shop):
        """测试服务初始化"""
        service = WBSyncService(mock_db_session, test_shop)

        assert service.db == mock_db_session
        assert service.shop == test_shop
        assert service.client is not None

    @pytest.mark.asyncio
    async def test_get_date_range_with_dates(self, mock_db_session, test_shop):
        """测试获取日期范围 - 指定日期"""
        service = WBSyncService(mock_db_session, test_shop)

        date_from, date_to = await service._get_date_range("2024-04-01", "2024-04-30")

        assert date_from == "2024-04-01"
        assert date_to == "2024-04-30"

    @pytest.mark.asyncio
    async def test_get_date_range_without_dates(self, mock_db_session, test_shop):
        """测试获取日期范围 - 默认日期"""
        service = WBSyncService(mock_db_session, test_shop)

        date_from, date_to = await service._get_date_range()

        # 验证 date_to 是今天格式
        assert len(date_to) == 10
        assert date_to[4] == "-"
        # 验证 date_from 是 30 天前
        assert len(date_from) == 10

    @pytest.mark.asyncio
    @patch("kunpeng.services.wb_sync_service.crud_ods_wb_supplier_sale.create_many")
    async def test_sync_sales_success(
        self, mock_create_many, mock_db_session, test_shop, sample_sales_data
    ):
        """测试同步销售数据 - 成功"""
        service = WBSyncService(mock_db_session, test_shop)

        # Mock client
        service.client = Mock()
        service.client.statistics = AsyncMock()
        service.client.statistics.get_supplier_sales.return_value = sample_sales_data
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)

        # Mock CRUD
        mock_create_many.return_value = [Mock(), Mock()]

        # 执行测试
        result = await service.sync_sales("2024-04-01", "2024-04-30")

        # 验证结果
        assert result["status"] == "success"
        assert result["count"] == 2
        assert "销售数据" in result["message"]

        # 验证调用
        service.client.statistics.get_supplier_sales.assert_called_once()
        mock_create_many.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_sales_no_statistics_client(self, mock_db_session, test_shop):
        """测试同步销售数据 - 无 statistics client"""
        service = WBSyncService(mock_db_session, test_shop)

        service.client = Mock()
        service.client.statistics = None

        result = await service.sync_sales("2024-04-01", "2024-04-30")

        assert result["status"] == "error"
        assert "Statistics API client not configured" in result["message"]

    @pytest.mark.asyncio
    @patch("kunpeng.services.wb_sync_service.crud_ods_wb_supplier_sale.create_many")
    async def test_sync_sales_api_error(
        self, mock_create_many, mock_db_session, test_shop
    ):
        """测试同步销售数据 - API 错误"""
        service = WBSyncService(mock_db_session, test_shop)

        service.client = Mock()
        service.client.statistics = AsyncMock()
        service.client.statistics.get_supplier_sales.side_effect = Exception(
            "API Error"
        )
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)

        result = await service.sync_sales("2024-04-01", "2024-04-30")

        assert result["status"] == "error"
        assert "API Error" in result["message"]

    @pytest.mark.asyncio
    @patch("kunpeng.services.wb_sync_service.crud_ods_wb_supplier_order.create_many")
    async def test_sync_orders_success(
        self, mock_create_many, mock_db_session, test_shop, sample_orders_data
    ):
        """测试同步订单数据 - 成功"""
        service = WBSyncService(mock_db_session, test_shop)

        service.client = Mock()
        service.client.statistics = AsyncMock()
        service.client.statistics.get_supplier_orders.return_value = sample_orders_data
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)

        mock_create_many.return_value = [Mock()]

        with (
            patch(
                "kunpeng.services.wb_sync_service."
                "crud_dwd_wb_order_detail.upsert_from_ods",
                new=AsyncMock(return_value={"source_count": 1, "affected_rows": 1}),
            ) as dwd_upsert,
            patch(
                "kunpeng.services.wb_sync_service."
                "crud_dwd_wb_order_statistics_detail.upsert_from_ods",
                new=AsyncMock(return_value={"source_count": 1, "affected_rows": 1}),
            ) as statistics_dwd_upsert,
        ):
            result = await service.sync_orders("2024-04-01", "2024-04-30")

        assert result["status"] == "success"
        assert result["count"] == 1
        assert "订单数据" in result["message"]
        assert result["dwd_count"] == 1
        assert result["statistics_dwd_count"] == 1
        dwd_upsert.assert_awaited_once_with(mock_db_session, shop_id=test_shop.id)
        statistics_dwd_upsert.assert_awaited_once_with(
            mock_db_session, shop_id=test_shop.id
        )

    @pytest.mark.asyncio
    @patch(
        "kunpeng.services.wb_sync_service.wb_dwd_service.sync_sales_funnel_detail",
        new_callable=AsyncMock,
    )
    @patch("kunpeng.services.wb_sync_service.crud_ods_wb_sales_funnel.create_many")
    async def test_sync_funnel_with_dict_data(
        self, mock_create_many, mock_dwd_sync, mock_db_session, test_shop
    ):
        """测试同步销售漏斗数据 - data 字段格式"""
        service = WBSyncService(mock_db_session, test_shop)

        service.client = Mock()
        service.client.analytics = AsyncMock()
        service.client.analytics.get_sales_funnel.return_value = {
            "data": [{"nm_id": 12345}]
        }
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)

        mock_create_many.return_value = [Mock()]
        mock_dwd_sync.return_value = {
            "scanned": 1,
            "created": 1,
            "updated": 0,
        }

        with patch(
            "kunpeng.services.wb_sync_service."
            "crud_dwd_wb_order_detail.upsert_from_ods",
            new=AsyncMock(return_value={"source_count": 1, "affected_rows": 1}),
        ):
            result = await service.sync_funnel("2024-04-01", "2024-04-30")

        assert result["status"] == "success"
        assert result["count"] == 1

    @pytest.mark.asyncio
    @patch(
        "kunpeng.services.wb_sync_service.wb_dwd_service.sync_sales_funnel_detail",
        new_callable=AsyncMock,
    )
    @patch("kunpeng.services.wb_sync_service.crud_ods_wb_sales_funnel.create_many")
    async def test_sync_funnel_with_products_data(
        self, mock_create_many, mock_dwd_sync, mock_db_session, test_shop
    ):
        """测试同步销售漏斗数据 - products 字段格式"""
        service = WBSyncService(mock_db_session, test_shop)

        service.client = Mock()
        service.client.analytics = AsyncMock()
        service.client.analytics.get_sales_funnel.return_value = {
            "products": [{"nm_id": 12345}]
        }
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)

        mock_create_many.return_value = [Mock()]
        mock_dwd_sync.return_value = {
            "scanned": 1,
            "created": 1,
            "updated": 0,
        }

        with patch(
            "kunpeng.services.wb_sync_service."
            "crud_dwd_wb_order_detail.upsert_from_ods",
            new=AsyncMock(return_value={"source_count": 1, "affected_rows": 1}),
        ):
            result = await service.sync_funnel("2024-04-01", "2024-04-30")

        assert result["status"] == "success"
        assert result["count"] == 1

    @pytest.mark.asyncio
    @patch(
        "kunpeng.services.wb_sync_service.wb_dwd_service.sync_sales_funnel_detail",
        new_callable=AsyncMock,
    )
    @patch("kunpeng.services.wb_sync_service.crud_ods_wb_sales_funnel.create_many")
    @patch("kunpeng.services.wb_sync_service.now_platform")
    async def test_sync_funnel_without_dates_defaults_to_yesterday(
        self,
        mock_now_platform,
        mock_create_many,
        mock_dwd_sync,
        mock_db_session,
        test_shop,
    ):
        """底层单次漏斗同步未传日期时只同步 T-1。"""
        mock_now_platform.return_value = datetime(2026, 7, 30, 9, 0)
        service = WBSyncService(mock_db_session, test_shop)
        service.client = Mock()
        service.client.analytics = AsyncMock()
        service.client.analytics.get_sales_funnel.return_value = {
            "data": {"products": [{"nm_id": 12345}]}
        }
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)
        mock_create_many.return_value = [Mock()]
        mock_dwd_sync.return_value = {
            "scanned": 1,
            "created": 1,
            "updated": 0,
        }

        result = await service.sync_funnel()

        assert result["status"] == "success"
        assert result["date_from"] == "2026-07-29"
        assert result["date_to"] == "2026-07-29"
        service.client.analytics.get_sales_funnel.assert_awaited_once_with(
            "2026-07-29",
            "2026-07-29",
            limit=1000,
            offset=0,
        )

    @pytest.mark.asyncio
    @patch(
        "kunpeng.services.wb_sync_service.wb_dwd_service.sync_sales_funnel_detail",
        new_callable=AsyncMock,
    )
    @patch("kunpeng.services.wb_sync_service.crud_ods_wb_sales_funnel.create_many")
    async def test_sync_funnel_fetches_all_pages(
        self, mock_create_many, mock_dwd_sync, mock_db_session, test_shop
    ):
        """满 1000 条时继续请求下一页，最后一页不足 1000 条时停止。"""
        service = WBSyncService(mock_db_session, test_shop)
        service.client = Mock()
        service.client.analytics = AsyncMock()
        first_page = [{"nm_id": index} for index in range(1000)]
        service.client.analytics.get_sales_funnel.side_effect = [
            {"data": {"products": first_page}},
            {"data": {"products": [{"nm_id": 1000}]}},
        ]
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)
        mock_create_many.side_effect = [[Mock()] * 1000, [Mock()]]
        mock_dwd_sync.return_value = {
            "scanned": 1001,
            "created": 1001,
            "updated": 0,
        }

        result = await service.sync_funnel("2026-07-22", "2026-07-22")

        assert result["status"] == "success"
        assert result["count"] == 1001
        assert result["ods_count"] == 1001
        assert result["request_count"] == 2
        assert [
            call.kwargs["offset"]
            for call in service.client.analytics.get_sales_funnel.await_args_list
        ] == [0, 1000]

    @pytest.mark.asyncio
    @patch(
        "kunpeng.services.wb_sync_service.wb_dwd_service.sync_sales_funnel_detail",
        new_callable=AsyncMock,
    )
    @patch("kunpeng.services.wb_sync_service.now_platform")
    async def test_sync_funnel_lookback_uses_seven_single_day_windows(
        self, mock_now_platform, mock_dwd_sync, mock_db_session, test_shop
    ):
        """手动和定时回补均按 T-7 至 T-1 的七个单日执行。"""
        mock_now_platform.return_value = datetime(2026, 7, 30, 9, 0)
        service = WBSyncService(mock_db_session, test_shop)
        service.sync_funnel = AsyncMock(
            return_value={
                "status": "success",
                "count": 1,
                "ods_count": 1,
                "request_count": 1,
            }
        )
        mock_dwd_sync.return_value = {
            "scanned": 7,
            "created": 7,
            "updated": 0,
        }

        result = await service.sync_funnel_lookback(7)

        assert result["status"] == "success"
        assert result["count"] == 7
        assert result["request_count"] == 7
        assert [call.args for call in service.sync_funnel.await_args_list] == [
            ("2026-07-23", "2026-07-23"),
            ("2026-07-24", "2026-07-24"),
            ("2026-07-25", "2026-07-25"),
            ("2026-07-26", "2026-07-26"),
            ("2026-07-27", "2026-07-27"),
            ("2026-07-28", "2026-07-28"),
            ("2026-07-29", "2026-07-29"),
        ]
        assert all(
            call.kwargs == {"sync_dwd": False}
            for call in service.sync_funnel.await_args_list
        )
        mock_dwd_sync.assert_awaited_once_with(
            mock_db_session,
            shop_id=test_shop.id,
        )

    @pytest.mark.asyncio
    @patch("kunpeng.services.wb_sync_service.crud_ods_wb_goods_return.create_many")
    async def test_sync_returns_success(
        self, mock_create_many, mock_db_session, test_shop, sample_returns_data
    ):
        """测试同步退货数据 - 成功"""
        service = WBSyncService(mock_db_session, test_shop)

        service.client = Mock()
        service.client.analytics = AsyncMock()
        service.client.analytics.get_goods_return.return_value = {
            "data": sample_returns_data
        }
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)

        mock_create_many.return_value = [Mock()]

        with patch(
            "kunpeng.services.wb_sync_service."
            "crud_dwd_wb_return_detail.upsert_from_ods",
            new=AsyncMock(return_value={"source_count": 1, "affected_rows": 1}),
        ) as dwd_upsert:
            result = await service.sync_returns("2024-04-01", "2024-04-30")

        assert result["status"] == "success"
        assert result["count"] == 1
        assert result["dwd_count"] == 1
        dwd_upsert.assert_awaited_once_with(mock_db_session, shop_id=test_shop.id)

    @pytest.mark.asyncio
    async def test_sync_adverts_success(self, mock_db_session, test_shop):
        """测试同步广告数据 - 成功"""
        service = WBSyncService(mock_db_session, test_shop)

        service.client = Mock()
        service.client.advert = AsyncMock()
        service.client.advert.get_adverts_list.return_value = {"adverts": [{"id": 1}]}
        service.client.advert.get_advert_budget.return_value = {}
        service.client.advert.get_advert_stats.return_value = []
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "kunpeng.services.wb_sync_service.crud_ods_wb_advert.create_many",
                new=AsyncMock(return_value=[Mock()]),
            ),
            patch(
                "kunpeng.services.wb_sync_service.crud_ods_wb_advert_product.create_many",
                new=AsyncMock(return_value=[]),
            ),
        ):
            result = await service.sync_adverts("2024-04-01", "2024-04-30")

        assert result["status"] == "success"
        assert "广告同步完成" in result["message"]

    @pytest.mark.asyncio
    async def test_sync_feedbacks_success(self, mock_db_session, test_shop):
        """测试同步评价数据 - 成功"""
        service = WBSyncService(mock_db_session, test_shop)

        service.client = Mock()
        service.client.feedbacks = AsyncMock()
        service.client.feedbacks.get_feedbacks.return_value = {}
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "kunpeng.services.wb_sync_service."
            "crud_dwd_wb_voc_feedback_detail.upsert_from_ods",
            new=AsyncMock(return_value={"source_count": 4, "affected_rows": 4}),
        ) as dwd_upsert:
            result = await service.sync_feedbacks("2024-04-01", "2024-04-30")

        assert result["status"] == "success"
        assert "评价数据" in result["message"]
        assert result["dwd_count"] == 4
        dwd_upsert.assert_awaited_once_with(mock_db_session, shop_id=test_shop.id)

    @pytest.mark.asyncio
    async def test_sync_questions_success(self, mock_db_session, test_shop):
        """测试同步问答数据 - 成功"""
        service = WBSyncService(mock_db_session, test_shop)

        service.client = Mock()
        service.client.feedbacks = AsyncMock()
        service.client.feedbacks.get_questions.return_value = {}
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "kunpeng.services.wb_sync_service."
            "crud_dwd_wb_voc_question_detail.upsert_from_ods",
            new=AsyncMock(return_value={"source_count": 3, "affected_rows": 3}),
        ) as dwd_upsert:
            result = await service.sync_questions("2024-04-01", "2024-04-30")

        assert result["status"] == "success"
        assert "提问数据" in result["message"]
        assert result["dwd_count"] == 3
        dwd_upsert.assert_awaited_once_with(mock_db_session, shop_id=test_shop.id)

    @pytest.mark.asyncio
    @patch("kunpeng.services.wb_sync_service.wb_dwd_service")
    async def test_sync_finance_success(
        self,
        mock_dwd_service,
        mock_db_session,
        test_shop,
    ):
        """测试同步财务数据 - 成功"""
        service = WBSyncService(mock_db_session, test_shop)
        mock_dwd_service.sync_sales_report_detail = AsyncMock(
            return_value={"scanned": 3, "created": 1, "updated": 2}
        )

        service.client = Mock()
        service.client.finance = AsyncMock()
        service.client.finance.get_sales_reports_detailed.return_value = {"items": []}
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "kunpeng.services.wb_sync_service."
            "crud_dwd_wb_order_detail.upsert_from_ods",
            new=AsyncMock(return_value={"source_count": 1, "affected_rows": 1}),
        ) as dwd_upsert:
            result = await service.sync_finance("2024-04-01", "2024-04-30")

        assert result["status"] == "success"
        assert "销售报告明细" in result["message"]
        assert result["dwd_scanned"] == 3
        assert result["dwd_created"] == 1
        assert result["dwd_updated"] == 2
        mock_dwd_service.sync_sales_report_detail.assert_awaited_once_with(
            mock_db_session,
            shop_id=test_shop.id,
        )

    @pytest.mark.asyncio
    @patch("kunpeng.services.wb_sync_service.wb_dwd_service")
    async def test_sync_finance_reports_dwd_failure_after_ods(
        self,
        mock_dwd_service,
        mock_db_session,
        test_shop,
    ):
        """DWD 失败时明确返回可独立重试的信息。"""
        service = WBSyncService(mock_db_session, test_shop)
        service.client = Mock()
        service.client.finance = AsyncMock()
        service.client.finance.get_sales_reports_detailed.return_value = {"items": []}
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)
        mock_dwd_service.sync_sales_report_detail = AsyncMock(
            side_effect=RuntimeError("DWD unavailable")
        )

        result = await service.sync_finance("2024-04-01", "2024-04-30")

        assert result["status"] == "error"
        assert result["ods_count"] == 0
        assert result["dwd_status"] == "error"
        assert "ODS 已保存" in result["message"]

    @pytest.mark.asyncio
    @patch("kunpeng.services.wb_sync_service.crud_ods_wb_sales_report_daily")
    async def test_sync_finance_daily_uses_daily_period_and_daily_table(
        self,
        mock_daily_crud,
        mock_db_session,
        test_shop,
    ):
        service = WBSyncService(mock_db_session, test_shop)
        service.client = Mock()
        service.client.finance = AsyncMock()
        report = {
            "rrdId": 123,
            "dateFrom": "2026-07-20",
            "dateTo": "2026-07-20",
        }
        service.client.finance.get_sales_reports_detailed.return_value = [report]
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)
        mock_daily_crud.create_many = AsyncMock(return_value=[object()])

        result = await service.sync_finance_daily("2026-07-20", "2026-07-20")

        assert result["status"] == "success"
        assert result["ods_count"] == 1
        service.client.finance.get_sales_reports_detailed.assert_awaited_once_with(
            "2026-07-20",
            "2026-07-20",
            limit=100000,
            next_id=None,
            period="daily",
        )
        mock_daily_crud.create_many.assert_awaited_once_with(
            mock_db_session,
            items=[report],
            shop_id=test_shop.id,
        )
        mock_db_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sync_finance_daily_rejects_reversed_date_range(
        self, mock_db_session, test_shop
    ):
        service = WBSyncService(mock_db_session, test_shop)

        result = await service.sync_finance_daily("2026-07-21", "2026-07-20")

        assert result["status"] == "error"
        assert "不能晚于" in result["message"]

    @pytest.mark.asyncio
    @patch("kunpeng.services.wb_sync_service.crud_ods_wb_seller_balance")
    async def test_sync_seller_balance_success(
        self,
        mock_crud,
        mock_db_session,
        test_shop,
    ):
        """测试财务域卖家余额同步成功。"""
        service = WBSyncService(mock_db_session, test_shop)
        service.client = Mock()
        service.client.finance = AsyncMock()
        service.client.finance.get_balance.return_value = {
            "currency": "RUB",
            "current": 10196.21,
            "for_withdraw": 6395.80,
        }
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)
        mock_crud.upsert_snapshot = AsyncMock()

        result = await service.sync_seller_balance()

        assert result["status"] == "success"
        assert result["count"] == 1
        mock_crud.upsert_snapshot.assert_awaited_once_with(
            mock_db_session,
            shop_id=test_shop.id,
            balance_data={
                "currency": "RUB",
                "current": 10196.21,
                "for_withdraw": 6395.80,
            },
        )

    @pytest.mark.asyncio
    @patch("kunpeng.services.wb_sync_service.wb_dwd_service")
    @patch("kunpeng.services.wb_sync_service.crud_ods_wb_sales_report_list")
    async def test_sync_sales_report_list_success(
        self,
        mock_crud,
        mock_dwd_service,
        mock_db_session,
        test_shop,
    ):
        service = WBSyncService(mock_db_session, test_shop)
        service.client = Mock()
        service.client.finance = AsyncMock()
        report = {
            "reportId": 307401554,
            "dateFrom": "2026-07-20",
            "dateTo": "2026-07-26",
            "createDate": "2026-07-27",
            "currency": "RUB",
            "reportType": 1,
        }
        service.client.finance.get_sales_reports_list.return_value = [report]
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)
        mock_crud.upsert_many = AsyncMock(return_value=[Mock()])
        mock_dwd_service.sync_sales_report_summary = AsyncMock(
            return_value={"scanned": 1, "created": 1, "updated": 0}
        )

        result = await service.sync_sales_report_list(
            "2026-07-20",
            "2026-07-26",
        )

        assert result["status"] == "success"
        assert result["count"] == 1
        service.client.finance.get_sales_reports_list.assert_awaited_once_with(
            "2026-07-20",
            "2026-07-26",
            limit=1000,
            offset=0,
            period="weekly",
        )
        mock_crud.upsert_many.assert_awaited_once_with(
            mock_db_session,
            shop_id=test_shop.id,
            reports=[report],
        )
        mock_dwd_service.sync_sales_report_summary.assert_awaited_once_with(
            mock_db_session,
            shop_id=test_shop.id,
        )
        assert result["dwd_scanned"] == 1
        assert result["dwd_created"] == 1
        assert result["dwd_updated"] == 0

    @pytest.mark.asyncio
    @patch("kunpeng.services.wb_sync_service.wb_dwd_service")
    @patch("kunpeng.services.wb_sync_service.crud_ods_wb_sales_report_list")
    async def test_sync_sales_report_list_reports_dwd_failure_after_ods_saved(
        self,
        mock_crud,
        mock_dwd_service,
        mock_db_session,
        test_shop,
    ):
        service = WBSyncService(mock_db_session, test_shop)
        service.client = Mock()
        service.client.finance = AsyncMock()
        service.client.finance.get_sales_reports_list.return_value = [
            {
                "reportId": 307401554,
                "dateFrom": "2026-07-20",
                "dateTo": "2026-07-26",
            }
        ]
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)
        mock_crud.upsert_many = AsyncMock(return_value=[Mock()])
        mock_dwd_service.sync_sales_report_summary = AsyncMock(
            side_effect=RuntimeError("DWD unavailable")
        )

        result = await service.sync_sales_report_list(
            "2026-07-20",
            "2026-07-26",
        )

        assert result["status"] == "error"
        assert result["ods_count"] == 1
        assert result["dwd_status"] == "error"

    @pytest.mark.asyncio
    @patch("kunpeng.services.wb_sync_service.crud_ods_wb_region_sale")
    async def test_sync_region_sales_success(
        self,
        mock_crud,
        mock_db_session,
        test_shop,
    ):
        """测试区域销售报告同步成功。"""
        service = WBSyncService(mock_db_session, test_shop)
        service.client = Mock()
        service.client.analytics = AsyncMock()
        report = [
            {
                "cityName": "Москва",
                "countryName": "Россия",
                "foName": "Центральный федеральный округ",
                "nmID": 177974431,
                "regionName": "Москва",
                "sa": "article-1",
                "saleInvoiceCostPrice": 592.11,
                "saleInvoiceCostPricePerc": 43.054733,
                "saleItemInvoiceQty": 4,
            }
        ]
        service.client.analytics.get_region_sales.return_value = {"report": report}
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)
        mock_crud.upsert_many = AsyncMock(return_value=[Mock()])

        result = await service.sync_region_sales("2026-07-22", "2026-07-23")

        assert result["status"] == "success"
        assert result["count"] == 1
        mock_crud.upsert_many.assert_awaited_once_with(
            mock_db_session,
            shop_id=test_shop.id,
            date_from=date(2026, 7, 22),
            date_to=date(2026, 7, 23),
            report_data=report,
        )

    @pytest.mark.asyncio
    @patch("kunpeng.services.wb_sync_service.crud_ods_wb_product_search_text")
    async def test_sync_product_search_texts_discovers_products_and_batches(
        self,
        mock_crud,
        mock_db_session,
        test_shop,
    ):
        service = WBSyncService(mock_db_session, test_shop)
        service.client = Mock()
        service.client.analytics = AsyncMock()
        service.client.analytics.get_search_report_products.return_value = {
            "data": {
                "products": [{"nmId": 101}, {"product": {"nmId": 202}}],
                "isNextPage": False,
            }
        }
        item = {"text": "перчатки", "nmId": 101}
        service.client.analytics.get_product_search_texts.return_value = {
            "data": {"items": [item], "currency": "RUB"}
        }
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)
        mock_crud.upsert_many = AsyncMock(return_value=[Mock()])

        result = await service.sync_product_search_texts(
            "2026-07-22",
            "2026-07-23",
        )

        assert result["status"] == "success"
        assert result["product_count"] == 2
        service.client.analytics.get_product_search_texts.assert_awaited_once_with(
            "2026-07-22",
            "2026-07-23",
            [101, 202],
            top_order_by="openCard",
            limit=30,
        )
        mock_crud.upsert_many.assert_awaited_once_with(
            mock_db_session,
            shop_id=test_shop.id,
            date_from=date(2026, 7, 22),
            date_to=date(2026, 7, 23),
            items=[item],
            currency="RUB",
            top_order_by="openCard",
        )

    @pytest.mark.asyncio
    @patch("kunpeng.services.wb_sync_service.crud_ods_wb_search_traffic")
    async def test_sync_search_traffic_paginates_and_saves(
        self,
        mock_crud,
        mock_db_session,
        test_shop,
    ):
        service = WBSyncService(mock_db_session, test_shop)
        service.client = Mock()
        service.client.analytics = AsyncMock()
        product = {"nmId": 101, "name": "Перчатки"}
        service.client.analytics.get_search_report_products.return_value = {
            "data": {"products": [product], "currency": "RUB"}
        }
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)
        mock_crud.upsert_many = AsyncMock(return_value=[Mock()])

        result = await service.sync_search_traffic(
            "2026-07-17",
            "2026-07-23",
        )

        assert result["status"] == "success"
        assert result["count"] == 1
        service.client.analytics.get_search_report_products.assert_awaited_once_with(
            "2026-07-17",
            "2026-07-23",
            limit=1000,
            offset=0,
            position_cluster="all",
            past_date_from="2026-07-10",
            past_date_to="2026-07-16",
        )
        assert result["past_date_from"] == "2026-07-10"
        assert result["past_date_to"] == "2026-07-16"
        mock_crud.upsert_many.assert_awaited_once_with(
            mock_db_session,
            shop_id=test_shop.id,
            date_from=date(2026, 7, 17),
            date_to=date(2026, 7, 23),
            products=[product],
            currency="RUB",
            position_cluster="all",
        )

    @pytest.mark.asyncio
    async def test_sync_all_success(self, mock_db_session, test_shop):
        """测试同步所有数据 - 成功"""
        service = WBSyncService(mock_db_session, test_shop)

        # Mock 各个同步方法
        service.sync_sales = AsyncMock(return_value={"status": "success", "count": 2})
        service.sync_orders = AsyncMock(return_value={"status": "success", "count": 1})
        service.sync_funnel = AsyncMock(return_value={"status": "success", "count": 1})
        service.sync_returns = AsyncMock(return_value={"status": "success", "count": 1})
        service.sync_adverts = AsyncMock(return_value={"status": "success", "count": 0})
        service.sync_feedbacks = AsyncMock(
            return_value={"status": "success", "count": 0}
        )
        service.sync_questions = AsyncMock(
            return_value={"status": "success", "count": 0}
        )
        service.sync_finance = AsyncMock(return_value={"status": "success", "count": 0})

        result = await service.sync_all(
            "2024-04-01", "2024-04-30", sync_types=["sales", "orders"]
        )

        assert result["status"] == "success"
        assert "sales" in result["results"]
        assert "orders" in result["results"]
        assert "funnel" not in result["results"]  # 不在 sync_types 中

    @pytest.mark.asyncio
    async def test_sync_all_funnel_without_dates_uses_lookback(
        self, mock_db_session, test_shop
    ):
        """全量手动入口选择漏斗且未传日期时也执行七日回补。"""
        service = WBSyncService(mock_db_session, test_shop)
        service.sync_funnel = AsyncMock(return_value={"status": "success", "count": 1})
        service.sync_funnel_lookback = AsyncMock(
            return_value={"status": "success", "count": 7}
        )

        result = await service.sync_all(sync_types=["funnel"])

        service.sync_funnel_lookback.assert_awaited_once_with()
        service.sync_funnel.assert_not_called()
        assert result["results"]["funnel"]["count"] == 7

    @pytest.mark.asyncio
    async def test_sync_all_default_types(self, mock_db_session, test_shop):
        """测试同步所有数据 - 默认类型"""
        service = WBSyncService(mock_db_session, test_shop)

        # Mock 所有同步方法
        for method in [
            "sync_sales",
            "sync_orders",
            "sync_funnel",
            "sync_returns",
            "sync_adverts",
            "sync_feedbacks",
            "sync_questions",
            "sync_finance",
            "sync_marketplace_orders",
            "sync_balance",
            "sync_norm_query_bids",
            "sync_norm_query_minus",
            "sync_norm_query_list",
            "sync_norm_query_stats",
            "sync_promotion_count",
            "sync_bid_recommendations",
            "sync_advert_fullstats",
            "sync_adverts_v2",
        ]:
            setattr(
                service,
                method,
                AsyncMock(return_value={"status": "success", "count": 0}),
            )

        result = await service.sync_all("2024-04-01", "2024-04-30")

        assert result["status"] == "success"
        assert len(result["results"]) == 18
