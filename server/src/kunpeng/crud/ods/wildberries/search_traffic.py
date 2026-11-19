"""Wildberries 商品搜索流量报告 CRUD。"""

from datetime import date
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.models.ods.wildberries.search_traffic import ODSWBSearchTraffic
from kunpeng.utils.timezone import now_platform


def _metric_value(data: Dict[str, Any], metric: str, field: str) -> Any:
    value = data.get(metric) or {}
    return value.get(field) if isinstance(value, dict) else None


class CRUDODSWBSearchTraffic(
    CRUDBase[ODSWBSearchTraffic, Dict[str, Any], Dict[str, Any]]
):
    """按店铺、窗口、商品和位置分组幂等保存搜索流量。"""

    async def upsert_many(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        date_from: date,
        date_to: date,
        products: List[Dict[str, Any]],
        currency: str | None,
        position_cluster: str = "all",
    ) -> List[ODSWBSearchTraffic]:
        products_by_nm_id = {
            int(product["nmId"]): product
            for product in products
            if product.get("nmId") is not None
        }
        nm_ids = set(products_by_nm_id)
        records_by_nm_id: Dict[int, ODSWBSearchTraffic] = {}
        if nm_ids:
            result = await db.execute(
                select(ODSWBSearchTraffic).where(
                    ODSWBSearchTraffic.shop_id == shop_id,
                    ODSWBSearchTraffic.date_from == date_from,
                    ODSWBSearchTraffic.date_to == date_to,
                    ODSWBSearchTraffic.position_cluster == position_cluster,
                    ODSWBSearchTraffic.nm_id.in_(nm_ids),
                )
            )
            records_by_nm_id = {
                record.nm_id: record for record in result.scalars().all()
            }

        records: List[ODSWBSearchTraffic] = []
        synced_at = now_platform()
        for nm_id, product in products_by_nm_id.items():
            price = product.get("price") or {}
            values = {
                "shop_id": shop_id,
                "date_from": date_from,
                "date_to": date_to,
                "nm_id": nm_id,
                "position_cluster": position_cluster,
                "product_name": product.get("name"),
                "vendor_code": product.get("vendorCode"),
                "subject_name": product.get("subjectName"),
                "brand_name": product.get("brandName"),
                "main_photo": product.get("mainPhoto"),
                "is_advertised": product.get("isAdvertised"),
                "is_substituted_sku": product.get("isSubstitutedSKU"),
                "is_card_rated": product.get("isCardRated"),
                "rating": product.get("rating"),
                "feedback_rating": product.get("feedbackRating"),
                "min_price": price.get("minPrice"),
                "max_price": price.get("maxPrice"),
                "avg_position_current": _metric_value(
                    product, "avgPosition", "current"
                ),
                "avg_position_dynamics": _metric_value(
                    product, "avgPosition", "dynamics"
                ),
                "open_card_current": _metric_value(product, "openCard", "current"),
                "open_card_dynamics": _metric_value(product, "openCard", "dynamics"),
                "add_to_cart_current": _metric_value(product, "addToCart", "current"),
                "add_to_cart_dynamics": _metric_value(product, "addToCart", "dynamics"),
                "open_to_cart_current": _metric_value(product, "openToCart", "current"),
                "open_to_cart_dynamics": _metric_value(
                    product, "openToCart", "dynamics"
                ),
                "orders_current": _metric_value(product, "orders", "current"),
                "orders_dynamics": _metric_value(product, "orders", "dynamics"),
                "cart_to_order_current": _metric_value(
                    product, "cartToOrder", "current"
                ),
                "cart_to_order_dynamics": _metric_value(
                    product, "cartToOrder", "dynamics"
                ),
                "visibility_current": _metric_value(product, "visibility", "current"),
                "visibility_dynamics": _metric_value(product, "visibility", "dynamics"),
                "currency": currency,
                "row_data": product,
                "synced_at": synced_at,
            }
            record = records_by_nm_id.get(nm_id)
            if record:
                for field, value in values.items():
                    setattr(record, field, value)
            else:
                record = ODSWBSearchTraffic(**values)
                db.add(record)
            records_by_nm_id[nm_id] = record
            records.append(record)

        try:
            await db.commit()
            for record in records:
                await db.refresh(record)
        except Exception:
            await db.rollback()
            raise
        return records


crud_ods_wb_search_traffic = CRUDODSWBSearchTraffic(ODSWBSearchTraffic)
