"""
Ozon ODS 层 - 商品信息 CRUD
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.crud.ods.ozon.utils import safe_decimal, safe_int, safe_str
from kunpeng.models.ods.ozon.products import ODSOzonProduct

logger = logging.getLogger(__name__)


class CRUDOzonProduct(CRUDBase[ODSOzonProduct, Dict[str, Any], Dict[str, Any]]):
    """ODS 商品信息表 CRUD"""

    async def _get_existing_item(
        self,
        db: AsyncSession,
        shop_id: int,
        product_id: int,
    ) -> Optional[ODSOzonProduct]:
        """根据唯一约束获取现有记录"""
        query = select(ODSOzonProduct).where(
            (ODSOzonProduct.shop_id == shop_id)
            & (ODSOzonProduct.product_id == product_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    def _extract_sku(item: Dict[str, Any]) -> Optional[int]:
        """
        从 v3 商品详情中提取 SKU。
        v3 结构下 SKU 位于 sources[].sku，同时兼容旧字段。
        """
        sku = item.get("sku") or item.get("fbo_sku") or item.get("fbs_sku")
        if sku:
            return safe_int(sku)
        sources = item.get("sources") or []
        for source in sources:
            if source.get("sku"):
                return safe_int(source.get("sku"))
        return None

    @staticmethod
    def _extract_barcode(item: Dict[str, Any]) -> Optional[str]:
        """提取条形码，v3 下 barcodes 为数组。"""
        barcodes = item.get("barcodes")
        if isinstance(barcodes, list):
            barcodes = barcodes[0] if barcodes else None
        return safe_str(barcodes or item.get("barcode"))

    def _extract_item_data(self, item: Dict[str, Any], shop_id: int) -> Dict[str, Any]:
        """从 API 响应中提取商品字段（适配 /v3/product/info/list）"""
        price_indexes = item.get("price_indexes") or {}
        stocks = item.get("stocks") or item.get("stock")
        statuses = item.get("statuses") or {}

        return {
            "shop_id": shop_id,
            "row_data": item,
            "product_id": safe_int(item.get("id") or item.get("product_id")),
            "sku": self._extract_sku(item),
            "offer_id": safe_str(item.get("offer_id")),
            "name": safe_str(item.get("name")),
            "barcode": self._extract_barcode(item),
            "category_id": safe_int(
                item.get("description_category_id") or item.get("category_id")
            ),
            "type_id": safe_int(item.get("type_id")),
            "category_name": safe_str(item.get("_category_name")),
            "visibility": safe_str(
                statuses.get("status") or item.get("visibility") or item.get("status")
            ),
            "price": safe_decimal(item.get("price")),
            "old_price": safe_decimal(item.get("old_price")),
            "premium_price": safe_decimal(item.get("premium_price")),
            "currency_code": safe_str(
                item.get("currency_code") or item.get("currency")
            ),
            "stocks": stocks,
            "images": item.get("images"),
            "commissions": item.get("commissions"),
            "marketing_price": safe_decimal(
                item.get("marketing_price")
                or price_indexes.get("ozon_index_data", {}).get("minimal_price")
            ),
            "min_price": safe_decimal(
                item.get("min_price") or item.get("min_ozon_price")
            ),
        }

    async def create_many(
        self,
        db: AsyncSession,
        *,
        items: List[Dict[str, Any]],
        shop_id: int,
    ) -> List[ODSOzonProduct]:
        """批量创建/更新商品信息"""
        logger.debug(
            f"[ODS Ozon Product] 开始同步 - 店铺: {shop_id}, 数据量: {len(items)}"
        )

        result_list = []
        updated_count = 0
        created_count = 0

        for item in items:
            item_data = self._extract_item_data(item, shop_id)
            product_id = item_data.get("product_id")

            existing = None
            if product_id is not None:
                existing = await self._get_existing_item(db, shop_id, product_id)

            if existing:
                for field, value in item_data.items():
                    if field != "id" and hasattr(existing, field):
                        if field == "category_name" and value is None:
                            continue
                        setattr(existing, field, value)
                result_list.append(existing)
                updated_count += 1
            else:
                new_item = ODSOzonProduct(**item_data)
                db.add(new_item)
                result_list.append(new_item)
                created_count += 1

        await db.flush()

        logger.debug(
            f"[ODS Ozon Product] 同步完成 - 新增: {created_count}, 更新: {updated_count}, 总计: {len(result_list)}"
        )
        return result_list


crud_ods_ozon_product = CRUDOzonProduct(ODSOzonProduct)
