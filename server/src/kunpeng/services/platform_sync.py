"""
Platform Registry and Sync Service
==================================

Central registry for managing multiple platform sync services.
Each platform (wildberries, zone, wb_crawler) has its own implementation.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.shop import Shop
from kunpeng.services.ozon_sync_service import OzonSyncService
from kunpeng.services.wb_sync_service import WBSyncService

logger = structlog.get_logger(__name__)


class PlatformSyncService(ABC):
    """
    Abstract base class for platform sync services.
    All platform-specific sync services must implement this interface.
    """

    @abstractmethod
    async def sync_all(
        self,
        db: AsyncSession,
        shop_id: int,
        date_from: str,
        date_to: str,
    ) -> Dict[str, int]:
        """
        Sync all data types for the platform.

        Args:
            db: Async database session
            shop_id: Shop ID to sync
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)

        Returns:
            Dict of {data_type: count} synced
        """
        pass

    @abstractmethod
    async def sync_type(
        self,
        data_type: str,
        db: AsyncSession,
        shop_id: int,
        date_from: str,
        date_to: str,
    ) -> int:
        """
        Sync a specific data type for the platform.

        Args:
            data_type: Type of data to sync (e.g., 'sales', 'orders')
            db: Async database session
            shop_id: Shop ID to sync
            date_from: Start date (YYYY-MM-DD)
            date_to: End date (YYYY-MM-DD)

        Returns:
            Count of records synced
        """
        pass

    @abstractmethod
    def get_data_types(self) -> List[str]:
        """
        Get list of supported data types for this platform.

        Returns:
            List of data type identifiers
        """
        pass


class WildberriesPlatformService(PlatformSyncService):
    """
    Wildberries platform sync service adapter.
    Adapts the existing WBSyncService to the PlatformSyncService interface.
    """

    # Data type mapping from new interface to existing service
    DATA_TYPE_MAPPING = {
        "sales": "sync_sales",
        "orders": "sync_orders",
        "funnel": "sync_funnel",
        "returns": "sync_returns",
        "adverts": "sync_adverts",
        "feedbacks": "sync_feedbacks",
        "questions": "sync_questions",
        "finance": "sync_finance",
        "marketplace_orders": "sync_marketplace_orders",
    }

    def get_data_types(self) -> List[str]:
        """Get list of supported data types for Wildberries."""
        return list(self.DATA_TYPE_MAPPING.keys())

    async def _get_shop(self, db: AsyncSession, shop_id: int) -> Shop:
        """Get shop from database by ID."""
        result = await db.execute(select(Shop).where(Shop.id == shop_id))
        shop = result.scalar_one_or_none()
        if not shop:
            raise ValueError(f"Shop with ID {shop_id} not found")
        return shop

    async def sync_all(
        self,
        db: AsyncSession,
        shop_id: int,
        date_from: str,
        date_to: str,
    ) -> Dict[str, int]:
        """
        Sync all data types for Wildberries.
        """
        shop = await self._get_shop(db, shop_id)
        wb_service = WBSyncService(db, shop)

        result = await wb_service.sync_all(date_from, date_to, sync_types=None)

        # Convert the result format
        counts: Dict[str, int] = {}
        results_dict = result.get("results", {})
        for data_type, type_result in results_dict.items():
            if type_result.get("status") == "success":
                # Try to get the count from different possible fields
                count = type_result.get("count") or type_result.get("ods_count") or 0
                counts[data_type] = count
            else:
                counts[data_type] = 0

        return counts

    async def sync_type(
        self,
        data_type: str,
        db: AsyncSession,
        shop_id: int,
        date_from: str,
        date_to: str,
    ) -> int:
        """
        Sync a specific data type for Wildberries.
        """
        if data_type not in self.DATA_TYPE_MAPPING:
            raise ValueError(f"Unknown data type: {data_type}")

        shop = await self._get_shop(db, shop_id)
        wb_service = WBSyncService(db, shop)

        # Get the sync method
        method_name = self.DATA_TYPE_MAPPING[data_type]
        sync_method = getattr(wb_service, method_name, None)

        if not sync_method:
            raise ValueError(f"Sync method not found for data type: {data_type}")

        # Call the sync method
        result = await sync_method(date_from, date_to)

        # Extract count from result
        if result.get("status") == "success":
            count = result.get("count") or result.get("ods_count") or 0
            return count
        else:
            raise Exception(f"Sync failed: {result.get('message')}")


class OzonPlatformService(PlatformSyncService):
    """
    Ozon 平台同步服务适配器
    适配现有的 OzonSyncService 到 PlatformSyncService 接口
    """

    DATA_TYPE_MAPPING = {
        "accrual_types": "sync_accrual_types",
        "postings": "sync_postings",
        "fbo_postings": "sync_fbo_postings",
        "order_dwd": "sync_order_dwd",
        "product_name_translation": "sync_product_name_translations",
        "postings_report": "sync_posting_reports",
        "returns": "sync_returns",
        "return_status_changes": "sync_return_status_changes",
        "reviews": "sync_reviews",
        "customer_voice_dwd": "sync_customer_voice_dwd",
        "advert_efficiency_dwd": "sync_advert_efficiency_dwd",
        "sales_funnel_dwd": "sync_sales_funnel_dwd",
        "products": "sync_products",
        "adverts": "sync_adverts",
        "advert_products": "sync_advert_products",
        "advert_products_hourly": "sync_advert_products_hourly",
        "analytics_data": "sync_analytics_data",
        "finance_accruals": "sync_finance_accruals",
        "realization_report": "sync_realization_report",
    }

    def get_data_types(self) -> List[str]:
        """获取 Ozon 支持的数据类型列表"""
        return list(self.DATA_TYPE_MAPPING.keys())

    async def _get_shop(self, db: AsyncSession, shop_id: int) -> Shop:
        """通过 ID 从数据库获取店铺"""
        result = await db.execute(select(Shop).where(Shop.id == shop_id))
        shop = result.scalar_one_or_none()
        if not shop:
            raise ValueError(f"未找到 ID 为 {shop_id} 的店铺")
        return shop

    async def sync_all(
        self,
        db: AsyncSession,
        shop_id: int,
        date_from: str,
        date_to: str,
    ) -> Dict[str, int]:
        """
        同步 Ozon 的所有数据
        """
        shop = await self._get_shop(db, shop_id)
        ozon_service = OzonSyncService(db, shop)

        result = await ozon_service.sync_all(date_from, date_to, sync_types=None)

        counts: Dict[str, int] = {}
        results_dict = result.get("results", {})
        for data_type, type_result in results_dict.items():
            if type_result.get("status") == "success":
                count = type_result.get("count") or type_result.get("ods_count") or 0
                counts[data_type] = count
            else:
                counts[data_type] = 0

        return counts

    async def sync_type(
        self,
        data_type: str,
        db: AsyncSession,
        shop_id: int,
        date_from: str,
        date_to: str,
    ) -> int:
        """
        同步 Ozon 的特定数据类型
        """
        if data_type not in self.DATA_TYPE_MAPPING:
            raise ValueError(f"未知的数据类型: {data_type}")

        shop = await self._get_shop(db, shop_id)
        ozon_service = OzonSyncService(db, shop)

        method_name = self.DATA_TYPE_MAPPING[data_type]
        sync_method = getattr(ozon_service, method_name, None)

        if not sync_method:
            raise ValueError(f"未找到数据类型的同步方法: {data_type}")

        if data_type in [
            "realization_report",
            "accrual_types",
            "products",
            "advert_products_hourly",
        ]:
            result = await sync_method()
        else:
            result = await sync_method(date_from, date_to)

        if result.get("status") == "success":
            count = result.get("count") or result.get("ods_count") or 0
            return count
        else:
            raise Exception(f"同步失败: {result.get('message')}")


class PlatformRegistry:
    """
    Central registry for all platform sync services.
    """

    _platforms: Dict[str, Type[PlatformSyncService]] = {}
    _instances: Dict[str, PlatformSyncService] = {}

    @classmethod
    def register_platform(cls, platform: str, service_class: Type[PlatformSyncService]):
        """
        Register a platform sync service.

        Args:
            platform: Platform identifier (e.g., 'wildberries', 'zone')
            service_class: PlatformSyncService subclass
        """
        cls._platforms[platform] = service_class
        logger.info("Registered platform", platform=platform)

    @classmethod
    def get_service(cls, platform: str) -> Optional[PlatformSyncService]:
        """
        Get a platform sync service instance.

        Args:
            platform: Platform identifier

        Returns:
            PlatformSyncService instance or None if not registered
        """
        if platform not in cls._platforms:
            logger.warning("Platform not registered", platform=platform)
            return None

        if platform not in cls._instances:
            service_class = cls._platforms[platform]
            cls._instances[platform] = service_class()
            logger.info("Created platform service instance", platform=platform)

        return cls._instances[platform]

    @classmethod
    def get_platforms(cls) -> List[str]:
        """
        Get list of registered platforms.

        Returns:
            List of platform identifiers
        """
        return list(cls._platforms.keys())

    @classmethod
    def is_registered(cls, platform: str) -> bool:
        """
        Check if a platform is registered.

        Args:
            platform: Platform identifier

        Returns:
            True if registered
        """
        return platform in cls._platforms


# Register Wildberries platform
PlatformRegistry.register_platform("wildberries", WildberriesPlatformService)
# Register Ozon platform
PlatformRegistry.register_platform("ozon", OzonPlatformService)
