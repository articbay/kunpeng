"""
Ozon ODS 层 - 评价表 CRUD
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
from kunpeng.models.ods.ozon.reviews import ODSOzonReview

logger = logging.getLogger(__name__)


# ============================================================================
# Review 评价表 CRUD
# ============================================================================
class CRUDOzonReview(CRUDBase[ODSOzonReview, Dict[str, Any], Dict[str, Any]]):
    """ODS 评价表 CRUD"""

    async def _get_existing_item(
        self,
        db: AsyncSession,
        shop_id: int,
        review_id: str,
    ) -> Optional[ODSOzonReview]:
        """根据唯一约束获取现有记录"""
        query = select(ODSOzonReview).where(
            (ODSOzonReview.shop_id == shop_id) & (ODSOzonReview.review_id == review_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    def _extract_item_data(
        self,
        item: Dict[str, Any],
        shop_id: int,
    ) -> Dict[str, Any]:
        """从API响应中提取数据到模型字段"""
        # 兼容当前 v2 接口的扁平结构和旧接口的嵌套结构。
        product = item.get("product") or {}
        data = item.get("data") or {}

        sku = item.get("sku")
        if sku is None:
            sku = product.get("sku")

        review_text = item.get("text")
        if review_text is None:
            review_text = data.get("text")

        return {
            "shop_id": shop_id,
            "row_data": item,
            "review_id": safe_str(item.get("id")),
            "sku": safe_int(sku),
            "product_name": safe_str(item.get("product_name") or product.get("name")),
            "rating": safe_int(item.get("rating")),
            "text": safe_str(review_text),
            "published_at": parse_iso_datetime(item.get("published_at")),
            "created_at": parse_iso_datetime(item.get("created_at")),
            "status": safe_str(item.get("status")),
            "photos_amount": safe_int(item.get("photos_amount")),
            "videos_amount": safe_int(item.get("videos_amount")),
            "comments_amount": safe_int(item.get("comments_amount")),
            "order_status": safe_str(item.get("order_status")),
            "is_editable": item.get("is_editable"),
            "is_replyable": item.get("is_replyable"),
            "reply": safe_str(
                item.get("answer") or (data.get("answer") if data else None)
            ),
            "reply_created_at": parse_iso_datetime(item.get("answered_at")),
        }

    async def create_many(
        self,
        db: AsyncSession,
        *,
        items: List[Dict[str, Any]],
        shop_id: int,
    ) -> List[ODSOzonReview]:
        """批量创建/更新评价表"""
        logger.debug(
            f"[ODS Ozon Review] 开始同步 - 店铺: {shop_id}, 数据量: {len(items)}"
        )

        result_list = []
        updated_count = 0
        created_count = 0

        for item in items:
            item_data = self._extract_item_data(item, shop_id)
            review_id = item_data.get("review_id")

            existing = None
            if review_id is not None:
                existing = await self._get_existing_item(db, shop_id, review_id)

            if existing:
                for field, value in item_data.items():
                    if field != "id" and hasattr(existing, field):
                        setattr(existing, field, value)
                result_list.append(existing)
                updated_count += 1
            else:
                new_item = ODSOzonReview(**item_data)
                db.add(new_item)
                result_list.append(new_item)
                created_count += 1

        await db.flush()

        logger.debug(
            f"[ODS Ozon Review] 同步完成 - 新增: {created_count}, 更新: {updated_count}, 总计: {len(result_list)}"
        )
        return result_list


# ============================================================================
# CRUD实例
# ============================================================================
crud_ods_ozon_review = CRUDOzonReview(ODSOzonReview)
