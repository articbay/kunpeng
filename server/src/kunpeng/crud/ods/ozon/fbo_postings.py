"""
Ozon ODS 层 - FBO 订单相关表 CRUD
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.crud.ods.ozon.utils import (parse_datetime_field, safe_decimal,
                                         safe_int, safe_str)
from kunpeng.models.ods.ozon.fbo_postings import (ODSOzonFBOPosting,
                                                  ODSOzonFBOPostingProduct)

logger = logging.getLogger(__name__)


class CRUDOzonFBOPosting(CRUDBase[ODSOzonFBOPosting, Dict[str, Any], Dict[str, Any]]):
    """ODS FBO订单主表 CRUD"""

    async def _get_existing_item(
        self, db: AsyncSession, shop_id: int, posting_number: str
    ) -> Optional[ODSOzonFBOPosting]:
        query = select(ODSOzonFBOPosting).where(
            (ODSOzonFBOPosting.shop_id == shop_id)
            & (ODSOzonFBOPosting.posting_number == posting_number)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    def _extract_item_data(self, item: Dict[str, Any], shop_id: int) -> Dict[str, Any]:
        return {
            "shop_id": shop_id,
            "row_data": item,
            "posting_number": safe_str(item.get("posting_number")),
            "order_id": safe_int(item.get("order_id")),
            "order_number": safe_str(item.get("order_number")),
            "status": safe_str(item.get("status")),
            "substatus": safe_str(item.get("substatus")),
            "cancel_reason_id": safe_int(item.get("cancel_reason_id")),
            "created_at": parse_datetime_field(item.get("created_at")),
            "in_process_at": parse_datetime_field(item.get("in_process_at")),
            "analytics_data": item.get("analytics_data"),
            "financial_data": item.get("financial_data"),
            "additional_data": item.get("additional_data"),
            "legal_info": item.get("legal_info"),
        }

    async def create_many(
        self, db: AsyncSession, *, items: List[Dict[str, Any]], shop_id: int
    ) -> List[ODSOzonFBOPosting]:
        logger.debug(
            f"[ODS Ozon FBOPosting] 开始同步 - 店铺: {shop_id}, 数据量: {len(items)}"
        )
        result_list = []
        created_count = 0
        updated_count = 0
        for item in items:
            item_data = self._extract_item_data(item, shop_id)
            posting_number = item_data.get("posting_number")
            if not posting_number:
                continue
            existing = await self._get_existing_item(db, shop_id, posting_number)
            if existing:
                for field, value in item_data.items():
                    if field != "id" and hasattr(existing, field):
                        setattr(existing, field, value)
                result_list.append(existing)
                updated_count += 1
            else:
                new_item = ODSOzonFBOPosting(**item_data)
                db.add(new_item)
                result_list.append(new_item)
                created_count += 1
        await db.flush()
        logger.debug(
            f"[ODS Ozon FBOPosting] 同步完成 - 新增: {created_count}, 更新: {updated_count}, 总计: {len(result_list)}"
        )
        return result_list


class CRUDOzonFBOPostingProduct(
    CRUDBase[ODSOzonFBOPostingProduct, Dict[str, Any], Dict[str, Any]]
):
    """ODS FBO订单商品表 CRUD"""

    async def _get_existing_item(
        self, db: AsyncSession, shop_id: int, posting_number: str, sku: int
    ) -> Optional[ODSOzonFBOPostingProduct]:
        query = select(ODSOzonFBOPostingProduct).where(
            (ODSOzonFBOPostingProduct.shop_id == shop_id)
            & (ODSOzonFBOPostingProduct.posting_number == posting_number)
            & (ODSOzonFBOPostingProduct.sku == sku)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    def _extract_item_data(
        self, item: Dict[str, Any], shop_id: int, posting_number: str
    ) -> Dict[str, Any]:
        price = item.get("price")
        if isinstance(price, dict):
            price_amount = price.get("amount")
            currency_code = price.get("currency")
        else:
            price_amount = price
            currency_code = item.get("currency_code")

        return {
            "shop_id": shop_id,
            "row_data": item,
            "posting_number": posting_number,
            "sku": safe_int(item.get("sku")),
            "name": safe_str(item.get("name")),
            "offer_id": safe_str(item.get("offer_id")),
            "quantity": safe_int(item.get("quantity")),
            "price": safe_decimal(price_amount),
            "currency_code": safe_str(currency_code),
        }

    async def create_many(
        self,
        db: AsyncSession,
        *,
        items: List[Dict[str, Any]],
        shop_id: int,
        posting_number: str,
    ) -> List[ODSOzonFBOPostingProduct]:
        result_list = []
        for item in items:
            item_data = self._extract_item_data(item, shop_id, posting_number)
            sku = item_data.get("sku")
            if sku is None:
                continue
            existing = await self._get_existing_item(db, shop_id, posting_number, sku)
            if existing:
                for field, value in item_data.items():
                    if field != "id" and hasattr(existing, field):
                        setattr(existing, field, value)
                result_list.append(existing)
            else:
                new_item = ODSOzonFBOPostingProduct(**item_data)
                db.add(new_item)
                result_list.append(new_item)
        await db.flush()
        return result_list


crud_ods_ozon_fbo_posting = CRUDOzonFBOPosting(ODSOzonFBOPosting)
crud_ods_ozon_fbo_posting_product = CRUDOzonFBOPostingProduct(ODSOzonFBOPostingProduct)
