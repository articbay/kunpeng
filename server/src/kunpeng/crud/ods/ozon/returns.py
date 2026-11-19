"""
Ozon ODS 层 - 退货相关表 CRUD
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
from kunpeng.models.ods.ozon.returns import (ODSOzonReturn,
                                             ODSOzonReturnProduct,
                                             ODSOzonReturnStorage)

logger = logging.getLogger(__name__)


# ============================================================================
# Return 主表 CRUD
# ============================================================================
class CRUDOzonReturn(CRUDBase[ODSOzonReturn, Dict[str, Any], Dict[str, Any]]):
    """ODS 退货主表 CRUD"""

    async def _get_existing_item(
        self,
        db: AsyncSession,
        shop_id: int,
        return_id: int,
    ) -> Optional[ODSOzonReturn]:
        """根据唯一约束获取现有记录"""
        query = select(ODSOzonReturn).where(
            (ODSOzonReturn.shop_id == shop_id) &
            (ODSOzonReturn.return_id == return_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    def _extract_item_data(
        self,
        item: Dict[str, Any],
        shop_id: int,
    ) -> Dict[str, Any]:
        """从API响应中提取数据到模型字段"""
        # Handle nested objects
        visual = item.get('visual') or {}
        visual_status = visual.get('status') or {}
        logistic = item.get('logistic') or {}
        place = item.get('place') or {}
        target_place = item.get('target_place') or {}
        additional_info = item.get('additional_info') or {}
        compensation_status = item.get('compensation_status')
        compensation_status_obj = (
            compensation_status if isinstance(compensation_status, dict) else {}
        )
        compensation_status_value = (
            compensation_status_obj.get('status') or compensation_status_obj
        )

        # Extract compensation status
        compensation_status_str = None
        if compensation_status:
            if isinstance(compensation_status, dict):
                compensation_status_str = safe_str(
                    compensation_status_value.get('sys_name')
                )
            else:
                compensation_status_str = safe_str(compensation_status)

        customer_info = item.get('customer_info') or {}
        buyer_comment = (
            item.get('buyer_comment')
            or item.get('return_comment')
            or customer_info.get('return_comment')
        )

        return {
            'shop_id': shop_id,
            'row_data': item,

            'return_id': safe_int(item.get('id') or item.get('return_id')),
            'company_id': safe_int(item.get('company_id')),
            'posting_number': safe_str(item.get('posting_number')),
            'order_id': safe_int(item.get('order_id')),
            'order_number': safe_str(item.get('order_number')),
            'schema': safe_str(item.get('schema')),
            'type': safe_str(item.get('type')),
            'return_reason_name': safe_str(item.get('return_reason_name')),
            'clearing_id': safe_int(item.get('clearing_id')),
            'return_clearing_id': safe_int(item.get('return_clearing_id')),
            'source_id': safe_int(item.get('source_id')),
            'compensation_status': compensation_status_str,
            'compensation_status_id': safe_int(compensation_status_value.get('id')),
            'compensation_status_display_name': safe_str(
                compensation_status_value.get('display_name')
            ),
            'compensation_status_sys_name': safe_str(
                compensation_status_value.get('sys_name')
            ),
            'compensation_status_change_moment': parse_iso_datetime(
                compensation_status_obj.get('change_moment')
            ),
            'buyer_comment': safe_str(buyer_comment),
            'status_id': safe_int(visual_status.get('id')),
            'status_display_name': safe_str(visual_status.get('display_name')),
            'status_sys_name': safe_str(visual_status.get('sys_name')),
            'status_change_moment': parse_iso_datetime(visual.get('change_moment')),
            'return_date': parse_iso_datetime(logistic.get('return_date')),
            'logistic_barcode': safe_str(logistic.get('barcode')),
            'logistic_technical_return_moment': parse_iso_datetime(logistic.get('technical_return_moment')),
            'logistic_final_moment': parse_iso_datetime(logistic.get('final_moment')),
            'logistic_cancelled_with_compensation_moment': parse_iso_datetime(logistic.get('cancelled_with_compensation_moment')),
            'place_id': safe_int(place.get('id')),
            'place_name': safe_str(place.get('name')),
            'place_address': safe_str(place.get('address')),
            'target_place_id': safe_int(target_place.get('id')),
            'target_place_name': safe_str(target_place.get('name')),
            'target_place_address': safe_str(target_place.get('address')),
            'is_opened': additional_info.get('is_opened'),
            'is_super_econom': additional_info.get('is_super_econom'),
            'exemplars': item.get('exemplars'),
        }

    async def create_many(
        self,
        db: AsyncSession,
        *,
        items: List[Dict[str, Any]],
        shop_id: int,
    ) -> List[ODSOzonReturn]:
        """批量创建/更新退货主表"""
        logger.debug(
            f"[ODS Ozon Return] 开始同步 - 店铺: {shop_id}, 数据量: {len(items)}"
        )

        result_list = []
        updated_count = 0
        created_count = 0

        for item in items:
            item_data = self._extract_item_data(item, shop_id)
            return_id = item_data.get('return_id')

            existing = None
            if return_id is not None:
                existing = await self._get_existing_item(db, shop_id, return_id)

            if existing:
                for field, value in item_data.items():
                    if field != 'id' and hasattr(existing, field):
                        setattr(existing, field, value)
                result_list.append(existing)
                updated_count += 1
            else:
                new_item = ODSOzonReturn(**item_data)
                db.add(new_item)
                result_list.append(new_item)
                created_count += 1

        await db.flush()

        logger.debug(
            f"[ODS Ozon Return] 同步完成 - 新增: {created_count}, 更新: {updated_count}, 总计: {len(result_list)}"
        )
        return result_list


# ============================================================================
# Return Product 退货商品表 CRUD
# ============================================================================
class CRUDOzonReturnProduct(CRUDBase[ODSOzonReturnProduct, Dict[str, Any], Dict[str, Any]]):
    """ODS 退货商品表 CRUD"""

    async def _get_existing_item(
        self,
        db: AsyncSession,
        shop_id: int,
        return_id: int,
        sku: int,
    ) -> Optional[ODSOzonReturnProduct]:
        """根据唯一约束获取现有记录"""
        query = select(ODSOzonReturnProduct).where(
            (ODSOzonReturnProduct.shop_id == shop_id) &
            (ODSOzonReturnProduct.return_id == return_id) &
            (ODSOzonReturnProduct.sku == sku)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    def _extract_item_data(
        self,
        item: Dict[str, Any],
        shop_id: int,
        return_id: int,
    ) -> Dict[str, Any]:
        """从API响应中提取数据到模型字段"""
        # The product might be nested in 'product' field
        product = item.get('product') or item
        exemplars = item.get('exemplars') or []
        exemplar_id = None
        if exemplars and len(exemplars) > 0:
            exemplar_id = safe_int(exemplars[0].get('exemplar_id'))

        # Extract price objects
        price_obj = product.get('price') or {}
        price_amount = safe_decimal(price_obj.get('price')) if isinstance(price_obj, dict) else safe_decimal(price_obj)
        price_currency = safe_str(price_obj.get('currency_code')) if isinstance(price_obj, dict) else None

        price_without_commission_obj = product.get('price_without_commission') or {}
        price_without_commission_amount = safe_decimal(price_without_commission_obj.get('price')) if isinstance(price_without_commission_obj, dict) else safe_decimal(price_without_commission_obj)
        price_without_commission_currency = safe_str(price_without_commission_obj.get('currency_code')) if isinstance(price_without_commission_obj, dict) else None

        commission_obj = product.get('commission') or {}
        commission_amount = safe_decimal(commission_obj.get('price')) if isinstance(commission_obj, dict) else safe_decimal(commission_obj)
        commission_currency = safe_str(commission_obj.get('currency_code')) if isinstance(commission_obj, dict) else None

        return {
            'shop_id': shop_id,
            'row_data': item,
            'return_id': return_id,

            'sku': safe_int(product.get('sku')),
            'offer_id': safe_str(product.get('offer_id')),
            'product_name': safe_str(product.get('name')),
            'quantity': safe_int(product.get('quantity')),
            'price_amount': price_amount,
            'price_currency': price_currency,
            'price_without_commission_amount': price_without_commission_amount,
            'price_without_commission_currency': price_without_commission_currency,
            'commission_percent': safe_decimal(product.get('commission_percent')),
            'commission_amount': commission_amount,
            'commission_currency': commission_currency,
            'exemplar_id': exemplar_id,
        }

    async def create_many_for_return(
        self,
        db: AsyncSession,
        *,
        item: Dict[str, Any],
        shop_id: int,
        return_id: int,
    ) -> List[ODSOzonReturnProduct]:
        """为单个退货创建/更新商品信息"""
        result_list = []

        item_data = self._extract_item_data(item, shop_id, return_id)
        sku = item_data.get('sku')

        existing = None
        if sku is not None:
            existing = await self._get_existing_item(db, shop_id, return_id, sku)

        if existing:
            for field, value in item_data.items():
                if field != 'id' and hasattr(existing, field):
                    setattr(existing, field, value)
            result_list.append(existing)
        else:
            new_item = ODSOzonReturnProduct(**item_data)
            db.add(new_item)
            result_list.append(new_item)

        await db.flush()
        return result_list


# ============================================================================
# Return Storage 退货仓库表 CRUD
# ============================================================================
class CRUDOzonReturnStorage(CRUDBase[ODSOzonReturnStorage, Dict[str, Any], Dict[str, Any]]):
    """ODS 退货仓库表 CRUD"""

    async def _get_existing_item(
        self,
        db: AsyncSession,
        shop_id: int,
        return_id: int,
    ) -> Optional[ODSOzonReturnStorage]:
        """根据唯一约束获取现有记录"""
        query = select(ODSOzonReturnStorage).where(
            (ODSOzonReturnStorage.shop_id == shop_id) &
            (ODSOzonReturnStorage.return_id == return_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    def _extract_item_data(
        self,
        item: Dict[str, Any],
        shop_id: int,
        return_id: int,
    ) -> Dict[str, Any]:
        """从API响应中提取数据到模型字段"""
        storage = item.get('storage') or {}
        sum_obj = storage.get('sum') or {}
        utilization_sum_obj = storage.get('utilization_sum') or {}

        return {
            'shop_id': shop_id,
            'row_data': storage,
            'return_id': return_id,

            'storage_days': safe_int(storage.get('days')),
            'tariffication_first_date': parse_iso_datetime(storage.get('tariffication_first_date')),
            'tariffication_start_date': parse_iso_datetime(storage.get('tariffication_start_date')),
            'arrived_moment': parse_iso_datetime(storage.get('arrived_moment')),
            'storage_fee_amount': safe_decimal(sum_obj.get('price')),
            'storage_fee_currency': safe_str(sum_obj.get('currency_code')),
            'utilization_fee_amount': safe_decimal(utilization_sum_obj.get('price')),
            'utilization_fee_currency': safe_str(utilization_sum_obj.get('currency_code')),
            'utilization_forecast_date': parse_iso_datetime(storage.get('utilization_forecast_date')),
        }

    async def create_or_update_for_return(
        self,
        db: AsyncSession,
        *,
        item: Dict[str, Any],
        shop_id: int,
        return_id: int,
    ) -> Optional[ODSOzonReturnStorage]:
        """为单个退货创建/更新仓库信息"""
        # /v1/returns/list returns storage data in the ``storage`` object.
        # The old ``return_address`` guard does not exist in this response and
        # caused every valid storage row to be skipped.
        if not item.get('storage'):
            return None

        item_data = self._extract_item_data(item, shop_id, return_id)
        existing = await self._get_existing_item(db, shop_id, return_id)

        if existing:
            for field, value in item_data.items():
                if field != 'id' and hasattr(existing, field):
                    setattr(existing, field, value)
            return existing
        else:
            new_item = ODSOzonReturnStorage(**item_data)
            db.add(new_item)
            return new_item

    async def backfill_missing_from_returns(
        self,
        db: AsyncSession,
        *,
        shop_id: Optional[int] = None,
    ) -> int:
        """Recover missing storage rows from the raw return JSON already in ODS."""
        query = (
            select(ODSOzonReturn)
            .outerjoin(
                ODSOzonReturnStorage,
                (ODSOzonReturnStorage.shop_id == ODSOzonReturn.shop_id)
                & (ODSOzonReturnStorage.return_id == ODSOzonReturn.return_id),
            )
            .where(
                ODSOzonReturn.return_id.is_not(None),
                ODSOzonReturnStorage.id.is_(None),
            )
        )
        if shop_id is not None:
            query = query.where(ODSOzonReturn.shop_id == shop_id)

        returns = (await db.execute(query)).scalars().all()
        recovered = 0
        for source in returns:
            if not isinstance(source.row_data, dict) or not source.row_data.get(
                "storage"
            ):
                continue
            storage = await self.create_or_update_for_return(
                db,
                item=source.row_data,
                shop_id=source.shop_id,
                return_id=source.return_id,
            )
            if storage is not None:
                recovered += 1

        if recovered:
            await db.flush()
        return recovered


# ============================================================================
# CRUD实例
# ============================================================================
crud_ods_ozon_return = CRUDOzonReturn(ODSOzonReturn)
crud_ods_ozon_return_product = CRUDOzonReturnProduct(ODSOzonReturnProduct)
crud_ods_ozon_return_storage = CRUDOzonReturnStorage(ODSOzonReturnStorage)
