"""Wildberries 商品搜索词报告 CRUD。"""

import hashlib
import unicodedata
from datetime import date
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.models.ods.wildberries.product_search_text import ODSWBProductSearchText
from kunpeng.utils.timezone import now_platform


def build_search_text_hash(search_text: str) -> str:
    normalized = unicodedata.normalize("NFKC", search_text).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _metric_value(data: Dict[str, Any], metric: str, field: str) -> Any:
    value = data.get(metric) or {}
    return value.get(field) if isinstance(value, dict) else None


class CRUDODSWBProductSearchText(
    CRUDBase[ODSWBProductSearchText, Dict[str, Any], Dict[str, Any]]
):
    """按店铺、窗口、商品和搜索词幂等保存报告。"""

    async def upsert_many(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        date_from: date,
        date_to: date,
        items: List[Dict[str, Any]],
        currency: str | None,
        top_order_by: str,
    ) -> List[ODSWBProductSearchText]:
        prepared = []
        for item in items:
            search_text = str(item.get("text") or "").strip()
            nm_id = item.get("nmId")
            if not search_text or nm_id is None:
                continue
            prepared.append(
                (item, int(nm_id), search_text, build_search_text_hash(search_text))
            )

        hashes = {row[3] for row in prepared}
        nm_ids = {row[1] for row in prepared}
        records_by_key: Dict[tuple[int, str], ODSWBProductSearchText] = {}
        if hashes and nm_ids:
            result = await db.execute(
                select(ODSWBProductSearchText).where(
                    ODSWBProductSearchText.shop_id == shop_id,
                    ODSWBProductSearchText.date_from == date_from,
                    ODSWBProductSearchText.date_to == date_to,
                    ODSWBProductSearchText.top_order_by == top_order_by,
                    ODSWBProductSearchText.nm_id.in_(nm_ids),
                    ODSWBProductSearchText.search_text_hash.in_(hashes),
                )
            )
            records_by_key = {
                (record.nm_id, record.search_text_hash): record
                for record in result.scalars().all()
            }

        records: List[ODSWBProductSearchText] = []
        synced_at = now_platform()
        for item, nm_id, search_text, search_text_hash in prepared:
            price = item.get("price") or {}
            values = {
                "shop_id": shop_id,
                "date_from": date_from,
                "date_to": date_to,
                "nm_id": nm_id,
                "search_text": search_text,
                "search_text_hash": search_text_hash,
                "top_order_by": top_order_by,
                "subject_name": item.get("subjectName"),
                "brand_name": item.get("brandName"),
                "vendor_code": item.get("vendorCode"),
                "product_name": item.get("name"),
                "is_card_rated": item.get("isCardRated"),
                "rating": item.get("rating"),
                "feedback_rating": item.get("feedbackRating"),
                "min_price": price.get("minPrice"),
                "max_price": price.get("maxPrice"),
                "frequency_current": _metric_value(item, "frequency", "current"),
                "frequency_dynamics": _metric_value(item, "frequency", "dynamics"),
                "week_frequency": item.get("weekFrequency"),
                "median_position_current": _metric_value(
                    item, "medianPosition", "current"
                ),
                "median_position_dynamics": _metric_value(
                    item, "medianPosition", "dynamics"
                ),
                "avg_position_current": _metric_value(item, "avgPosition", "current"),
                "avg_position_dynamics": _metric_value(item, "avgPosition", "dynamics"),
                "open_card_current": _metric_value(item, "openCard", "current"),
                "open_card_dynamics": _metric_value(item, "openCard", "dynamics"),
                "open_card_percentile": _metric_value(item, "openCard", "percentile"),
                "add_to_cart_current": _metric_value(item, "addToCart", "current"),
                "add_to_cart_dynamics": _metric_value(item, "addToCart", "dynamics"),
                "add_to_cart_percentile": _metric_value(
                    item, "addToCart", "percentile"
                ),
                "open_to_cart_current": _metric_value(item, "openToCart", "current"),
                "open_to_cart_dynamics": _metric_value(item, "openToCart", "dynamics"),
                "open_to_cart_percentile": _metric_value(
                    item, "openToCart", "percentile"
                ),
                "orders_current": _metric_value(item, "orders", "current"),
                "orders_dynamics": _metric_value(item, "orders", "dynamics"),
                "orders_percentile": _metric_value(item, "orders", "percentile"),
                "cart_to_order_current": _metric_value(item, "cartToOrder", "current"),
                "cart_to_order_dynamics": _metric_value(
                    item, "cartToOrder", "dynamics"
                ),
                "cart_to_order_percentile": _metric_value(
                    item, "cartToOrder", "percentile"
                ),
                "visibility_current": _metric_value(item, "visibility", "current"),
                "visibility_dynamics": _metric_value(item, "visibility", "dynamics"),
                "currency": currency,
                "row_data": item,
                "synced_at": synced_at,
            }
            key = (nm_id, search_text_hash)
            record = records_by_key.get(key)
            if record:
                for field, value in values.items():
                    setattr(record, field, value)
            else:
                record = ODSWBProductSearchText(**values)
                db.add(record)
            records_by_key[key] = record
            records.append(record)

        try:
            await db.commit()
            for record in records:
                await db.refresh(record)
        except Exception:
            await db.rollback()
            raise
        return records


crud_ods_wb_product_search_text = CRUDODSWBProductSearchText(ODSWBProductSearchText)
