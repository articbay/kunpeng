"""
WBSyncService 小时同步单元测试
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, Any, List

from kunpeng.services.wb_sync_service import WBSyncService, _get_val
from kunpeng.models.shop import Shop


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
def sample_advert_stats_response():
    """示例广告统计 API 响应（整天累计）"""
    return [
        {
            "advertId": 100,
            "currency": "RUB",
            "days": [
                {
                    "date": "2024-04-01",
                    "apps": [
                        {
                            "appType": "android",
                            "nms": [
                                {
                                    "nmId": 200,
                                    "name": "Product A",
                                    "views": 1000,
                                    "clicks": 100,
                                    "atbs": 50,
                                    "orders": 20,
                                    "canceled": 2,
                                    "shks": 1,
                                    "sum": 5000.0,
                                    "sum_price": 10000.0,
                                    "cpc": 50.0,
                                    "ctr": 10.0,
                                    "cr": 20.0,
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    ]


class TestFlattenAdvertStats:
    """测试 _flatten_advert_stats 静态方法"""

    def test_flatten_with_nms_data(self):
        """测试展平含 nms 数据"""
        stats_data = [
            {
                "advertId": 100,
                "currency": "RUB",
                "days": [
                    {
                        "date": "2024-04-01",
                        "apps": [
                            {
                                "appType": "android",
                                "nms": [
                                    {
                                        "nmId": 200,
                                        "name": "Product A",
                                        "views": 1000,
                                        "clicks": 100,
                                        "atbs": 50,
                                        "orders": 20,
                                        "canceled": 2,
                                        "shks": 1,
                                        "sum": 5000.0,
                                        "sum_price": 10000.0,
                                        "cpc": 50.0,
                                        "ctr": 10.0,
                                        "cr": 20.0,
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        ]

        result = WBSyncService._flatten_advert_stats(stats_data)

        assert len(result) == 1
        record = result[0]
        assert record["advert_id"] == 100
        assert record["nm_id"] == 200
        assert record["nm_name"] == "Product A"
        assert record["app_type"] == "android"
        assert record["views"] == 1000
        assert record["clicks"] == 100
        assert record["sum_cost"] == 5000.0
        assert record["currency"] == "RUB"
        assert record["cpc"] == 50.0
        assert record["ctr"] == 10.0
        assert record["cr"] == 20.0

    def test_flatten_multiple_nms(self):
        """测试展平多个 nms"""
        stats_data = [
            {
                "advertId": 100,
                "currency": "RUB",
                "days": [
                    {
                        "date": "2024-04-01",
                        "apps": [
                            {
                                "appType": "android",
                                "nms": [
                                    {"nmId": 200, "views": 100},
                                    {"nmId": 201, "views": 200},
                                ]
                            },
                            {
                                "appType": "ios",
                                "nms": [
                                    {"nmId": 200, "views": 50},
                                ]
                            }
                        ]
                    }
                ]
            }
        ]

        result = WBSyncService._flatten_advert_stats(stats_data)

        assert len(result) == 3
        # android + nm200
        assert result[0]["app_type"] == "android"
        assert result[0]["nm_id"] == 200
        # android + nm201
        assert result[1]["app_type"] == "android"
        assert result[1]["nm_id"] == 201
        # ios + nm200
        assert result[2]["app_type"] == "ios"
        assert result[2]["nm_id"] == 200

    def test_flatten_skips_nm_without_id(self):
        """测试跳过没有 nmId 的记录"""
        stats_data = [
            {
                "advertId": 100,
                "days": [
                    {
                        "apps": [
                            {
                                "appType": "android",
                                "nms": [
                                    {"nmId": 200, "views": 100},
                                    {"views": 50},  # 缺少 nmId
                                ]
                            }
                        ]
                    }
                ]
            }
        ]

        result = WBSyncService._flatten_advert_stats(stats_data)

        assert len(result) == 1
        assert result[0]["nm_id"] == 200

    def test_flatten_empty_apps(self):
        """测试 apps 为空时不产生记录"""
        stats_data = [
            {
                "advertId": 100,
                "days": [
                    {
                        "date": "2024-04-01",
                        "apps": []
                    }
                ]
            }
        ]

        result = WBSyncService._flatten_advert_stats(stats_data)

        assert len(result) == 0


class TestGetVal:
    """测试 _get_val 辅助函数"""

    def test_get_val_first_key_exists(self):
        """测试第一个 key 存在"""
        data = {"views": 100, "clicks": 10}
        assert _get_val(data, "views", "view") == 100

    def test_get_val_fallback_key(self):
        """测试 fallback key"""
        data = {"view": 100}
        assert _get_val(data, "views", "view") == 100

    def test_get_val_none_value_skipped(self):
        """测试 None 值被跳过"""
        data = {"views": None, "view": 100}
        assert _get_val(data, "views", "view") == 100

    def test_get_val_all_missing(self):
        """测试所有 key 都不存在"""
        data = {}
        assert _get_val(data, "views", "view") is None


class TestSyncAdvertStatsHourly:
    """测试 sync_advert_stats_hourly 方法"""

    @pytest.fixture(autouse=True)
    def mock_advert_dwd_sync(self):
        with patch(
            "kunpeng.services.wb_sync_service.wb_dwd_service.sync_advert_stats",
            new=AsyncMock(return_value={"hourly_stats": {}, "daily_stats": {}}),
        ):
            yield

    @pytest.mark.asyncio
    @patch('kunpeng.services.wb_sync_service.crud_ods_wb_advert_stat_hourly')
    async def test_sync_advert_stats_hourly_normal_hour(self, mock_hourly_crud, mock_db_session, test_shop):
        """测试正常小时同步"""
        service = WBSyncService(mock_db_session, test_shop)

        # Mock client
        service.client = Mock()
        service.client.advert = AsyncMock()
        service.client.advert.get_adverts_list.return_value = {"adverts": [{"id": 1}]}
        service.client.advert.get_advert_stats.return_value = [
            {
                "advertId": 1,
                "currency": "RUB",
                "days": [
                    {
                        "date": "2024-04-01",
                        "apps": [
                            {
                                "appType": "android",
                                "nms": [
                                    {"nmId": 100, "views": 1000, "clicks": 100, "atbs": 50, "orders": 20, "canceled": 2, "shks": 1, "sum": 5000.0}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)

        # Mock CRUD: no previous hourly data
        mock_hourly_crud.get_hourly_sum_before_hour = AsyncMock(return_value={})
        mock_hourly_crud.upsert_many = AsyncMock()

        with patch(
            'kunpeng.services.wb_sync_service.now_platform',
            return_value=datetime(2024, 4, 1, 14, 5, 0, tzinfo=ZoneInfo("Europe/Moscow")),
        ):

            result = await service.sync_advert_stats_hourly()

        assert result["status"] == "success"
        assert result["count"] == 1

        # Verify upsert was called with the right hour
        call_args = mock_hourly_crud.upsert_many.call_args
        assert call_args.kwargs["stat_hour"] == 14
        assert call_args.kwargs["stat_date"] == date(2024, 4, 1)

        # Verify delta calculation (no previous data = full API value)
        stats_data = call_args.kwargs["stats_data"]
        assert len(stats_data) == 1
        assert stats_data[0]["views"] == 1000
        assert stats_data[0]["clicks"] == 100

    @pytest.mark.asyncio
    @patch('kunpeng.services.wb_sync_service.crud_ods_wb_advert_stat_hourly')
    async def test_sync_advert_stats_hourly_with_previous_data(self, mock_hourly_crud, mock_db_session, test_shop):
        """测试有历史数据时的增量计算"""
        service = WBSyncService(mock_db_session, test_shop)

        service.client = Mock()
        service.client.advert = AsyncMock()
        service.client.advert.get_adverts_list.return_value = {"adverts": [{"id": 1}]}
        service.client.advert.get_advert_stats.return_value = [
            {
                "advertId": 1,
                "currency": "RUB",
                "days": [
                    {
                        "date": "2024-04-01",
                        "apps": [
                            {
                                "appType": "android",
                                "nms": [
                                    {"nmId": 100, "views": 1000, "clicks": 100, "atbs": 50, "orders": 20, "canceled": 2, "shks": 1, "sum": 5000.0}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)

        # Mock CRUD: previous data exists for hours 0-13
        mock_hourly_crud.get_hourly_sum_before_hour = AsyncMock(return_value={
            (1, 100, "android"): {
                "views": 600, "clicks": 60, "atbs": 30, "orders": 12,
                "canceled": 1, "shks": 1, "sum_cost": 3000.0, "sum_price": 6000.0,
            }
        })
        mock_hourly_crud.upsert_many = AsyncMock()

        with patch(
            'kunpeng.services.wb_sync_service.now_platform',
            return_value=datetime(2024, 4, 1, 14, 5, 0, tzinfo=ZoneInfo("Europe/Moscow")),
        ):

            result = await service.sync_advert_stats_hourly()

        assert result["status"] == "success"

        # Verify delta = API(1000) - previous(600) = 400
        stats_data = mock_hourly_crud.upsert_many.call_args.kwargs["stats_data"]
        assert stats_data[0]["views"] == 400
        assert stats_data[0]["clicks"] == 40
        assert stats_data[0]["atbs"] == 20
        assert stats_data[0]["orders"] == 8

    @pytest.mark.asyncio
    @patch('kunpeng.services.wb_sync_service.crud_ods_wb_advert_stat_hourly')
    async def test_sync_advert_stats_hourly_negative_delta_clamped(self, mock_hourly_crud, mock_db_session, test_shop):
        """测试负增量被置为 0"""
        service = WBSyncService(mock_db_session, test_shop)

        service.client = Mock()
        service.client.advert = AsyncMock()
        service.client.advert.get_adverts_list.return_value = {"adverts": [{"id": 1}]}
        service.client.advert.get_advert_stats.return_value = [
            {
                "advertId": 1,
                "currency": "RUB",
                "days": [
                    {
                        "date": "2024-04-01",
                        "apps": [
                            {
                                "appType": "android",
                                "nms": [
                                    {"nmId": 100, "views": 100, "clicks": 10, "atbs": 5, "orders": 2, "canceled": 0, "shks": 1, "sum": 500.0}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)

        # Previous data exceeds API data (should clamp to 0)
        mock_hourly_crud.get_hourly_sum_before_hour = AsyncMock(return_value={
            (1, 100, "android"): {
                "views": 200, "clicks": 20, "atbs": 10, "orders": 5,
                "canceled": 0, "shks": 1, "sum_cost": 1000.0, "sum_price": 2000.0,
            }
        })
        mock_hourly_crud.upsert_many = AsyncMock()

        with patch(
            'kunpeng.services.wb_sync_service.now_platform',
            return_value=datetime(2024, 4, 1, 14, 5, 0, tzinfo=ZoneInfo("Europe/Moscow")),
        ):

            result = await service.sync_advert_stats_hourly()

        # All deltas are negative, so no records should be written
        assert result["status"] == "success"
        stats_data = mock_hourly_crud.upsert_many.call_args.kwargs["stats_data"]
        assert len(stats_data) == 0

    @pytest.mark.asyncio
    @patch('kunpeng.services.wb_sync_service.crud_ods_wb_advert_stat_hourly')
    async def test_sync_advert_stats_hourly_cross_day_boundary(self, mock_hourly_crud, mock_db_session, test_shop):
        """测试跨天边界：00:05 执行时结算昨天 23:00"""
        service = WBSyncService(mock_db_session, test_shop)

        service.client = Mock()
        service.client.advert = AsyncMock()
        service.client.advert.get_adverts_list.return_value = {"adverts": [{"id": 1}]}
        service.client.advert.get_advert_stats.return_value = [
            {
                "advertId": 1,
                "currency": "RUB",
                "days": [
                    {
                        "date": "2024-03-31",
                        "apps": [
                            {
                                "appType": "android",
                                "nms": [
                                    {"nmId": 100, "views": 1000, "clicks": 100, "atbs": 50, "orders": 20, "canceled": 2, "shks": 1, "sum": 5000.0}
                                ]
                            }
                        ]
                    }
                ]
            }
        ]
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)

        mock_hourly_crud.get_hourly_sum_before_hour = AsyncMock(return_value={})
        mock_hourly_crud.upsert_many = AsyncMock()

        with patch(
            'kunpeng.services.wb_sync_service.now_platform',
            return_value=datetime(2024, 4, 1, 0, 5, 0, tzinfo=ZoneInfo("Europe/Moscow")),
        ):

            result = await service.sync_advert_stats_hourly()

        assert result["status"] == "success"

        # Verify it writes to yesterday's hour 23
        call_args = mock_hourly_crud.upsert_many.call_args
        assert call_args.kwargs["stat_hour"] == 23
        assert call_args.kwargs["stat_date"] == date(2024, 3, 31)

    @pytest.mark.asyncio
    @patch('kunpeng.services.wb_sync_service.crud_ods_wb_advert_stat_hourly')
    async def test_sync_advert_stats_hourly_no_adverts(self, mock_hourly_crud, mock_db_session, test_shop):
        """测试没有广告活动时返回空"""
        service = WBSyncService(mock_db_session, test_shop)

        service.client = Mock()
        service.client.advert = AsyncMock()
        service.client.advert.get_adverts_list.return_value = {"adverts": []}
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)

        with patch(
            'kunpeng.services.wb_sync_service.now_platform',
            return_value=datetime(2024, 4, 1, 14, 5, 0, tzinfo=ZoneInfo("Europe/Moscow")),
        ):

            result = await service.sync_advert_stats_hourly()

        assert result["status"] == "success"
        assert result["count"] == 0
        assert "没有广告活动" in result["message"]

    @pytest.mark.asyncio
    async def test_sync_advert_stats_hourly_no_advert_client(self, mock_db_session, test_shop):
        """测试 advert client 未配置"""
        service = WBSyncService(mock_db_session, test_shop)
        service.client = Mock()
        service.client.advert = None

        result = await service.sync_advert_stats_hourly()

        assert result["status"] == "error"
        assert "Advert API client not configured" in result["message"]


class TestSyncSearchClusterStatHourly:
    """测试 sync_search_cluster_stat_hourly 方法"""

    @pytest.mark.asyncio
    @patch('kunpeng.services.wb_sync_service.crud_ods_wb_search_cluster_stat_hourly')
    @patch('kunpeng.services.wb_sync_service.crud_ods_wb_advert_product')
    async def test_sync_search_cluster_hourly_normal(self, mock_advert_product_crud, mock_hourly_crud, mock_db_session, test_shop):
        """测试正常小时同步"""
        service = WBSyncService(mock_db_session, test_shop)

        service.client = Mock()
        service.client.advert = AsyncMock()
        service.client.advert.get_adverts_list.return_value = {"adverts": [{"id": 1}]}
        service.client.advert.get_normquery_stats.return_value = [
            {
                "advertId": 1,
                "nmId": 100,
                "stat": {
                    "date": "2024-04-01",
                    "views": 500,
                    "clicks": 50,
                    "sum": 2500.0,
                    "atbs": 25,
                    "orders": 10,
                }
            }
        ]
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)

        mock_advert_product_crud.get_advert_nm_map = AsyncMock(return_value={1: [100]})
        mock_hourly_crud.get_hourly_sum_before_hour = AsyncMock(return_value={})
        mock_hourly_crud.upsert_many = AsyncMock()

        with patch(
            'kunpeng.services.wb_sync_service.now_platform',
            return_value=datetime(2024, 4, 1, 14, 5, 0, tzinfo=ZoneInfo("Europe/Moscow")),
        ):

            result = await service.sync_search_cluster_stat_hourly()

        assert result["status"] == "success"
        assert result["count"] == 1

        stats_data = mock_hourly_crud.upsert_many.call_args.kwargs["stats_data"]
        assert stats_data[0]["views"] == 500
        assert stats_data[0]["clicks"] == 50

    @pytest.mark.asyncio
    @patch('kunpeng.services.wb_sync_service.crud_ods_wb_search_cluster_stat_hourly')
    @patch('kunpeng.services.wb_sync_service.crud_ods_wb_advert_product')
    async def test_sync_search_cluster_hourly_cross_day(self, mock_advert_product_crud, mock_hourly_crud, mock_db_session, test_shop):
        """测试跨天边界"""
        service = WBSyncService(mock_db_session, test_shop)

        service.client = Mock()
        service.client.advert = AsyncMock()
        service.client.advert.get_adverts_list.return_value = {"adverts": [{"id": 1}]}
        service.client.advert.get_normquery_stats.return_value = [
            {
                "advertId": 1,
                "nmId": 100,
                "stat": {
                    "date": "2024-03-31",
                    "views": 500,
                    "clicks": 50,
                    "sum": 2500.0,
                    "atbs": 25,
                    "orders": 10,
                }
            }
        ]
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)

        mock_advert_product_crud.get_advert_nm_map = AsyncMock(return_value={1: [100]})
        mock_hourly_crud.get_hourly_sum_before_hour = AsyncMock(return_value={})
        mock_hourly_crud.upsert_many = AsyncMock()

        with patch(
            'kunpeng.services.wb_sync_service.now_platform',
            return_value=datetime(2024, 4, 1, 0, 5, 0, tzinfo=ZoneInfo("Europe/Moscow")),
        ):

            result = await service.sync_search_cluster_stat_hourly()

        assert result["status"] == "success"

        call_args = mock_hourly_crud.upsert_many.call_args
        assert call_args.kwargs["stat_hour"] == 23
        assert call_args.kwargs["stat_date"] == date(2024, 3, 31)

    @pytest.mark.asyncio
    @patch('kunpeng.services.wb_sync_service.crud_ods_wb_search_cluster_stat_hourly')
    @patch('kunpeng.services.wb_sync_service.crud_ods_wb_advert_product')
    async def test_sync_search_cluster_hourly_delta_clamped(self, mock_advert_product_crud, mock_hourly_crud, mock_db_session, test_shop):
        """测试负增量被置为 0"""
        service = WBSyncService(mock_db_session, test_shop)

        service.client = Mock()
        service.client.advert = AsyncMock()
        service.client.advert.get_adverts_list.return_value = {"adverts": [{"id": 1}]}
        service.client.advert.get_normquery_stats.return_value = [
            {
                "advertId": 1,
                "nmId": 100,
                "stat": {
                    "date": "2024-04-01",
                    "views": 100,
                    "clicks": 10,
                    "sum": 500.0,
                    "atbs": 5,
                    "orders": 2,
                }
            }
        ]
        service.client.__aenter__ = AsyncMock(return_value=service.client)
        service.client.__aexit__ = AsyncMock(return_value=None)

        mock_advert_product_crud.get_advert_nm_map = AsyncMock(return_value={1: [100]})
        # Previous exceeds API
        mock_hourly_crud.get_hourly_sum_before_hour = AsyncMock(return_value={
            (1, 100, None): {
                "views": 200, "clicks": 20, "sum_cost": 1000.0, "atbs": 10, "orders": 5,
            }
        })
        mock_hourly_crud.upsert_many = AsyncMock()

        with patch(
            'kunpeng.services.wb_sync_service.now_platform',
            return_value=datetime(2024, 4, 1, 14, 5, 0, tzinfo=ZoneInfo("Europe/Moscow")),
        ):

            result = await service.sync_search_cluster_stat_hourly()

        assert result["status"] == "success"
        stats_data = mock_hourly_crud.upsert_many.call_args.kwargs["stats_data"]
        # All negative deltas -> no records
        assert len(stats_data) == 0


class TestHourlyCRUD:
    """测试小时 CRUD 的聚合查询"""

    @pytest.mark.asyncio
    async def test_get_hourly_sum_before_hour(self):
        """测试聚合查询"""
        from kunpeng.crud.ods.wildberries.advert_stats_hourly import CRUDODSWBAdvertStatHourly
        from kunpeng.models.ods.wildberries.advert_stats_hourly import ODSWBAdvertStatHourly

        crud = CRUDODSWBAdvertStatHourly(ODSWBAdvertStatHourly)
        assert crud is not None

    @pytest.mark.asyncio
    async def test_upsert_many_returns_none(self):
        """测试 upsert_many 返回 None"""
        from kunpeng.crud.ods.wildberries.advert_stats_hourly import CRUDODSWBAdvertStatHourly
        from kunpeng.models.ods.wildberries.advert_stats_hourly import ODSWBAdvertStatHourly

        crud = CRUDODSWBAdvertStatHourly(ODSWBAdvertStatHourly)

        import inspect
        sig = inspect.signature(crud.upsert_many)
        return_annotation = sig.return_annotation
        assert return_annotation is None
