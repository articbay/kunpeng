"""
Ozon ODS 层 - 订单相关表 CRUD
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.crud.ods.ozon.utils import (parse_datetime_field,
                                         parse_iso_datetime, safe_decimal,
                                         safe_int, safe_str)
from kunpeng.models.ods.ozon.postings import (ODSOzonFBSPosting,
                                              ODSOzonFBSPostingCancellation,
                                              ODSOzonFBSPostingDelivery,
                                              ODSOzonFBSPostingExternal,
                                              ODSOzonFBSPostingOptional,
                                              ODSOzonFBSPostingProduct)

logger = logging.getLogger(__name__)


# ============================================================================
# FBS Posting 主表 CRUD
# ============================================================================
class CRUDOzonFBSPosting(CRUDBase[ODSOzonFBSPosting, Dict[str, Any], Dict[str, Any]]):
    """ODS FBS订单主表 CRUD"""

    async def _get_existing_item(
        self,
        db: AsyncSession,
        shop_id: int,
        posting_number: str,
    ) -> Optional[ODSOzonFBSPosting]:
        """根据唯一约束获取现有记录"""
        query = select(ODSOzonFBSPosting).where(
            (ODSOzonFBSPosting.shop_id == shop_id)
            & (ODSOzonFBSPosting.posting_number == posting_number)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    def _extract_item_data(
        self,
        item: Dict[str, Any],
        shop_id: int,
    ) -> Dict[str, Any]:
        """从API响应中提取数据到模型字段"""
        # 提取嵌套对象
        analytics_data = item.get("analytics_data") or {}
        financial_data = item.get("financial_data") or {}
        barcodes = item.get("barcodes") or {}
        requirements = item.get("requirements") or {}
        customer = item.get("customer") or {}
        addressee = item.get("addressee") or {}
        prr_option = item.get("prr_option")
        if isinstance(prr_option, dict):
            prr_option = prr_option.get("code")

        return {
            "shop_id": shop_id,
            "row_data": item,
            # 基础信息
            "posting_number": safe_str(item.get("posting_number")),
            "order_id": safe_int(item.get("order_id")),
            "order_number": safe_str(item.get("order_number")),
            "status": safe_str(item.get("status")),
            "substatus": safe_str(item.get("substatus")),
            "delivery_schema": safe_str(item.get("delivery_schema")),
            "tpl_integration_type": safe_str(
                item.get("tpl_integration_type")
                or analytics_data.get("tpl_integration_type")
            ),
            # 时间信息
            "in_process_at": parse_iso_datetime(item.get("in_process_at")),
            "shipment_date": parse_iso_datetime(item.get("shipment_date")),
            "shipment_date_without_delay": parse_iso_datetime(
                item.get("shipment_date_without_delay")
            ),
            "delivering_date": parse_iso_datetime(item.get("delivering_date")),
            # 其他字段
            "tracking_number": safe_str(item.get("tracking_number")),
            "pickup_code_verified_at": parse_iso_datetime(
                item.get("pickup_code_verified_at")
            ),
            "destination_place_id": safe_int(
                item.get("destination_place_id")
                if item.get("destination_place_id") is not None
                else analytics_data.get("destination_place_id")
            ),
            "destination_place_name": safe_str(
                item.get("destination_place_name")
                or analytics_data.get("destination_place_name")
            ),
            "is_express": item.get("is_express"),
            "is_multibox": item.get("is_multibox"),
            "multi_box_qty": safe_int(item.get("multi_box_qty")),
            "is_presortable": item.get("is_presortable"),
            "is_click_and_collect": item.get("is_click_and_collect"),
            "prr_option": safe_str(prr_option),
            "parent_posting_number": safe_str(item.get("parent_posting_number")),
            "quantum_id": safe_int(item.get("quantum_id")),
            "volume_weight": safe_decimal(item.get("volume_weight")),
            "require_blr_traceable_attrs": item.get("require_blr_traceable_attrs"),
            "container_sort_type": safe_str(item.get("container_sort_type")),
            # 嵌套JSON数据
            "customer": customer,
            "addressee": addressee,
            "barcodes": barcodes,
            "analytics_data": analytics_data,
            "financial_data": financial_data,
            "legal_info": item.get("legal_info"),
            "requirements": requirements,
            "tariffication": item.get("tariffication"),
            "container": item.get("container"),
            "available_actions": item.get("available_actions"),
            "tariffication_steps": item.get("tariffication_steps"),
        }

    async def create_many(
        self,
        db: AsyncSession,
        *,
        items: List[Dict[str, Any]],
        shop_id: int,
    ) -> List[ODSOzonFBSPosting]:
        """批量创建/更新FBS订单主表"""
        logger.debug(
            f"[ODS Ozon Posting] 开始同步 - 店铺: {shop_id}, 数据量: {len(items)}"
        )

        result_list = []
        updated_count = 0
        created_count = 0

        for item in items:
            item_data = self._extract_item_data(item, shop_id)
            posting_number = item_data.get("posting_number")

            existing = None
            if posting_number is not None:
                existing = await self._get_existing_item(db, shop_id, posting_number)

            if existing:
                for field, value in item_data.items():
                    if field != "id" and hasattr(existing, field):
                        setattr(existing, field, value)
                result_list.append(existing)
                updated_count += 1
            else:
                new_item = ODSOzonFBSPosting(**item_data)
                db.add(new_item)
                result_list.append(new_item)
                created_count += 1

        await db.flush()

        logger.debug(
            f"[ODS Ozon Posting] 同步完成 - 新增: {created_count}, 更新: {updated_count}, 总计: {len(result_list)}"
        )
        return result_list


# ============================================================================
# FBS Posting Product 商品表 CRUD
# ============================================================================
class CRUDOzonFBSPostingProduct(
    CRUDBase[ODSOzonFBSPostingProduct, Dict[str, Any], Dict[str, Any]]
):
    """ODS FBS订单商品表 CRUD"""

    async def _get_existing_item(
        self,
        db: AsyncSession,
        shop_id: int,
        posting_number: str,
        sku: int,
    ) -> Optional[ODSOzonFBSPostingProduct]:
        """根据唯一约束获取现有记录"""
        query = select(ODSOzonFBSPostingProduct).where(
            (ODSOzonFBSPostingProduct.shop_id == shop_id)
            & (ODSOzonFBSPostingProduct.posting_number == posting_number)
            & (ODSOzonFBSPostingProduct.sku == sku)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    def _extract_item_data(
        self,
        item: Dict[str, Any],
        shop_id: int,
        posting_number: str,
    ) -> Dict[str, Any]:
        """从API响应中提取数据到模型字段"""
        # Handle price object {"amount": "100", "currency": "RUB"}
        price_obj = item.get("price") or {}
        price_amount = (
            safe_decimal(price_obj.get("amount"))
            if isinstance(price_obj, dict)
            else safe_decimal(price_obj)
        )
        price_currency = (
            safe_str(price_obj.get("currency")) if isinstance(price_obj, dict) else None
        )

        return {
            "shop_id": shop_id,
            "row_data": item,
            "posting_number": posting_number,
            "sku": safe_int(item.get("sku")),
            "name": safe_str(item.get("name")),
            "offer_id": safe_str(item.get("offer_id")),
            "price_amount": price_amount,
            "price_currency": price_currency or safe_str(item.get("currency_code")),
            "quantity": safe_int(item.get("quantity")),
            "mandatory_mark": item.get("mandatory_mark"),
            "weight": safe_decimal(item.get("weight")),
            "product_color": safe_str(item.get("product_color")),
            "is_blr_traceable": item.get("is_blr_traceable"),
            "is_marketplace_buyout": item.get("is_marketplace_buyout"),
            "imei": item.get("imei"),
        }

    async def create_many_for_posting(
        self,
        db: AsyncSession,
        *,
        products: List[Dict[str, Any]],
        shop_id: int,
        posting_number: str,
    ) -> List[ODSOzonFBSPostingProduct]:
        """为单个订单创建/更新商品列表"""
        result_list = []
        for product in products:
            item_data = self._extract_item_data(product, shop_id, posting_number)
            sku = item_data.get("sku")

            existing = None
            if sku is not None:
                existing = await self._get_existing_item(
                    db, shop_id, posting_number, sku
                )

            if existing:
                for field, value in item_data.items():
                    if field != "id" and hasattr(existing, field):
                        setattr(existing, field, value)
                result_list.append(existing)
            else:
                new_item = ODSOzonFBSPostingProduct(**item_data)
                db.add(new_item)
                result_list.append(new_item)

        await db.flush()
        return result_list


# ============================================================================
# FBS Posting Delivery 配送信息表 CRUD
# ============================================================================
class CRUDOzonFBSPostingDelivery(
    CRUDBase[ODSOzonFBSPostingDelivery, Dict[str, Any], Dict[str, Any]]
):
    """ODS FBS订单配送信息表 CRUD"""

    async def _get_existing_item(
        self,
        db: AsyncSession,
        shop_id: int,
        posting_number: str,
    ) -> Optional[ODSOzonFBSPostingDelivery]:
        """根据唯一约束获取现有记录"""
        query = select(ODSOzonFBSPostingDelivery).where(
            (ODSOzonFBSPostingDelivery.shop_id == shop_id)
            & (ODSOzonFBSPostingDelivery.posting_number == posting_number)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    def _extract_item_data(
        self,
        delivery_method: Dict[str, Any],
        shop_id: int,
        posting_number: str,
    ) -> Dict[str, Any]:
        """从API响应中提取数据到模型字段"""
        return {
            "shop_id": shop_id,
            "row_data": delivery_method,
            "posting_number": posting_number,
            "delivery_id": safe_int(delivery_method.get("id")),
            "delivery_name": safe_str(delivery_method.get("name")),
            "warehouse_id": safe_int(delivery_method.get("warehouse_id")),
            "warehouse_name": safe_str(delivery_method.get("warehouse")),
            "tpl_provider_id": safe_int(delivery_method.get("tpl_provider_id")),
            "tpl_provider": safe_str(delivery_method.get("tpl_provider")),
        }

    async def create_or_update_for_posting(
        self,
        db: AsyncSession,
        *,
        delivery_method: Dict[str, Any],
        shop_id: int,
        posting_number: str,
    ) -> Optional[ODSOzonFBSPostingDelivery]:
        """为单个订单创建/更新配送信息"""
        if not delivery_method:
            return None

        item_data = self._extract_item_data(delivery_method, shop_id, posting_number)
        existing = await self._get_existing_item(db, shop_id, posting_number)

        if existing:
            for field, value in item_data.items():
                if field != "id" and hasattr(existing, field):
                    setattr(existing, field, value)
            return existing
        else:
            new_item = ODSOzonFBSPostingDelivery(**item_data)
            db.add(new_item)
            return new_item


# ============================================================================
# FBS Posting Cancellation 取消信息表 CRUD
# ============================================================================
class CRUDOzonFBSPostingCancellation(
    CRUDBase[ODSOzonFBSPostingCancellation, Dict[str, Any], Dict[str, Any]]
):
    """ODS FBS订单取消信息表 CRUD"""

    async def _get_existing_item(
        self,
        db: AsyncSession,
        shop_id: int,
        posting_number: str,
    ) -> Optional[ODSOzonFBSPostingCancellation]:
        """根据唯一约束获取现有记录"""
        query = select(ODSOzonFBSPostingCancellation).where(
            (ODSOzonFBSPostingCancellation.shop_id == shop_id)
            & (ODSOzonFBSPostingCancellation.posting_number == posting_number)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    def _extract_item_data(
        self,
        cancellation: Dict[str, Any],
        shop_id: int,
        posting_number: str,
    ) -> Dict[str, Any]:
        """从API响应中提取数据到模型字段"""
        return {
            "shop_id": shop_id,
            "row_data": cancellation,
            "posting_number": posting_number,
            "cancel_reason_id": safe_int(cancellation.get("cancel_reason_id")),
            "cancel_reason": safe_str(cancellation.get("cancel_reason")),
            "cancellation_initiator": safe_str(
                cancellation.get("cancellation_initiator")
            ),
            "cancelled_after_ship": cancellation.get("cancelled_after_ship"),
            "affect_cancellation_rating": cancellation.get(
                "affect_cancellation_rating"
            ),
            "cancellation_type": safe_str(cancellation.get("cancellation_type")),
        }

    async def create_or_update_for_posting(
        self,
        db: AsyncSession,
        *,
        cancellation: Dict[str, Any],
        shop_id: int,
        posting_number: str,
    ) -> Optional[ODSOzonFBSPostingCancellation]:
        """为单个订单创建/更新取消信息"""
        if not cancellation:
            return None

        item_data = self._extract_item_data(cancellation, shop_id, posting_number)
        existing = await self._get_existing_item(db, shop_id, posting_number)

        if existing:
            for field, value in item_data.items():
                if field != "id" and hasattr(existing, field):
                    setattr(existing, field, value)
            return existing
        else:
            new_item = ODSOzonFBSPostingCancellation(**item_data)
            db.add(new_item)
            return new_item


# ============================================================================
# FBS Posting Optional 附加信息表 CRUD
# ============================================================================
class CRUDOzonFBSPostingOptional(
    CRUDBase[ODSOzonFBSPostingOptional, Dict[str, Any], Dict[str, Any]]
):
    """ODS FBS订单附加信息表 CRUD"""

    async def _get_existing_item(
        self,
        db: AsyncSession,
        shop_id: int,
        posting_number: str,
    ) -> Optional[ODSOzonFBSPostingOptional]:
        """根据唯一约束获取现有记录"""
        query = select(ODSOzonFBSPostingOptional).where(
            (ODSOzonFBSPostingOptional.shop_id == shop_id)
            & (ODSOzonFBSPostingOptional.posting_number == posting_number)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    def _extract_item_data(
        self,
        optional_fields: Dict[str, Any],
        shop_id: int,
        posting_number: str,
    ) -> Dict[str, Any]:
        """从API响应中提取数据到模型字段"""
        return {
            "shop_id": shop_id,
            "row_data": optional_fields,
            "posting_number": posting_number,
            "products_with_possible_mandatory_mark": optional_fields.get(
                "products_with_possible_mandatory_mark"
            ),
        }

    async def create_or_update_for_posting(
        self,
        db: AsyncSession,
        *,
        optional_fields: Dict[str, Any],
        shop_id: int,
        posting_number: str,
    ) -> Optional[ODSOzonFBSPostingOptional]:
        """为单个订单创建/更新附加信息"""
        if not optional_fields:
            return None

        item_data = self._extract_item_data(optional_fields, shop_id, posting_number)
        existing = await self._get_existing_item(db, shop_id, posting_number)

        if existing:
            for field, value in item_data.items():
                if field != "id" and hasattr(existing, field):
                    setattr(existing, field, value)
            return existing
        else:
            new_item = ODSOzonFBSPostingOptional(**item_data)
            db.add(new_item)
            return new_item


# ============================================================================
# FBS Posting External 外部订单信息表 CRUD
# ============================================================================
class CRUDOzonFBSPostingExternal(
    CRUDBase[ODSOzonFBSPostingExternal, Dict[str, Any], Dict[str, Any]]
):
    """ODS FBS外部订单信息表 CRUD"""

    async def _get_existing_item(
        self,
        db: AsyncSession,
        shop_id: int,
        posting_number: str,
    ) -> Optional[ODSOzonFBSPostingExternal]:
        """根据唯一约束获取现有记录"""
        query = select(ODSOzonFBSPostingExternal).where(
            (ODSOzonFBSPostingExternal.shop_id == shop_id)
            & (ODSOzonFBSPostingExternal.posting_number == posting_number)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    def _extract_item_data(
        self,
        item: Dict[str, Any],
        shop_id: int,
        posting_number: str,
    ) -> Dict[str, Any]:
        """从API响应中提取数据到模型字段"""
        return {
            "shop_id": shop_id,
            "row_data": item,
            "posting_number": posting_number,
            "is_external": item.get("is_external"),
            "platform_name": safe_str(item.get("platform_name")),
        }

    async def create_or_update_for_posting(
        self,
        db: AsyncSession,
        *,
        item: Dict[str, Any],
        shop_id: int,
        posting_number: str,
    ) -> Optional[ODSOzonFBSPostingExternal]:
        """为单个订单创建/更新外部订单信息"""
        if not item:
            return None

        item_data = self._extract_item_data(item, shop_id, posting_number)
        existing = await self._get_existing_item(db, shop_id, posting_number)

        if existing:
            for field, value in item_data.items():
                if field != "id" and hasattr(existing, field):
                    setattr(existing, field, value)
            return existing
        else:
            new_item = ODSOzonFBSPostingExternal(**item_data)
            db.add(new_item)
            return new_item


# ============================================================================
# CRUD实例
# ============================================================================
crud_ods_ozon_fbs_posting = CRUDOzonFBSPosting(ODSOzonFBSPosting)
crud_ods_ozon_fbs_posting_product = CRUDOzonFBSPostingProduct(ODSOzonFBSPostingProduct)
crud_ods_ozon_fbs_posting_delivery = CRUDOzonFBSPostingDelivery(
    ODSOzonFBSPostingDelivery
)
crud_ods_ozon_fbs_posting_cancellation = CRUDOzonFBSPostingCancellation(
    ODSOzonFBSPostingCancellation
)
crud_ods_ozon_fbs_posting_optional = CRUDOzonFBSPostingOptional(
    ODSOzonFBSPostingOptional
)
crud_ods_ozon_fbs_posting_external = CRUDOzonFBSPostingExternal(
    ODSOzonFBSPostingExternal
)
