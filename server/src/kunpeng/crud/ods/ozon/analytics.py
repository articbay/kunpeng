"""CRUD helpers for Ozon Seller Analytics ODS tables."""

from datetime import date
from typing import Any, Dict, Iterable, List, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.ods.ozon.utils import safe_decimal, safe_int
from kunpeng.models.ods.ozon.analytics import (
    ODSOzonAnalyticsDataDaily,
    ODSOzonAnalyticsTotalsWindow,
)

ANALYTICS_COUNT_METRICS = {
    "ordered_units",
    "hits_view_search",
    "hits_view_pdp",
    "hits_view",
    "hits_tocart_search",
    "hits_tocart_pdp",
    "hits_tocart",
    "session_view_search",
    "session_view_pdp",
    "session_view",
    "returns",
    "cancellations",
    "delivered_units",
}
ANALYTICS_DECIMAL_METRICS = {
    "revenue",
    "conv_tocart_search",
    "conv_tocart_pdp",
    "conv_tocart",
    "position_category",
}
ANALYTICS_METRICS = ANALYTICS_COUNT_METRICS | ANALYTICS_DECIMAL_METRICS


def normalize_metric_values(values: Dict[str, Any]) -> Dict[str, Any]:
    """Convert source numeric values without changing their business meaning."""
    normalized: Dict[str, Any] = {}
    for name in ANALYTICS_COUNT_METRICS:
        normalized[name] = safe_int(values.get(name))
    for name in ANALYTICS_DECIMAL_METRICS:
        normalized[name] = safe_decimal(values.get(name))
    return normalized


class CRUDOzonAnalyticsDataDaily:
    """Idempotent shop x SKU x day upserts."""

    async def upsert_many(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        date_from: date,
        date_to: date,
        items: Iterable[Dict[str, Any]],
    ) -> List[ODSOzonAnalyticsDataDaily]:
        query = select(ODSOzonAnalyticsDataDaily).where(
            ODSOzonAnalyticsDataDaily.shop_id == shop_id,
            ODSOzonAnalyticsDataDaily.stat_date >= date_from,
            ODSOzonAnalyticsDataDaily.stat_date <= date_to,
        )
        result = await db.execute(query)
        existing_by_key: Dict[Tuple[int, date], ODSOzonAnalyticsDataDaily] = {
            (row.sku, row.stat_date): row for row in result.scalars().all()
        }

        saved: List[ODSOzonAnalyticsDataDaily] = []
        for item in items:
            sku = safe_int(item.get("sku"))
            stat_date = item.get("stat_date")
            if sku is None or not isinstance(stat_date, date):
                raise ValueError("analytics row requires valid sku and stat_date")

            values = {
                "shop_id": shop_id,
                "sku": sku,
                "sku_name": item.get("sku_name"),
                "stat_date": stat_date,
                "source_date_from": date_from,
                "source_date_to": date_to,
                "requested_metrics_core": item["requested_metrics_core"],
                "requested_metrics_outcome": item["requested_metrics_outcome"],
                "row_data_core": item.get("row_data_core"),
                "row_data_outcome": item.get("row_data_outcome"),
                "has_core_metrics": bool(item.get("has_core_metrics")),
                "has_outcome_metrics": bool(item.get("has_outcome_metrics")),
                "api_timestamp_core": item.get("api_timestamp_core"),
                "api_timestamp_outcome": item.get("api_timestamp_outcome"),
                **normalize_metric_values(item.get("metrics") or {}),
            }
            key = (sku, stat_date)
            existing = existing_by_key.get(key)
            if existing is None:
                existing = ODSOzonAnalyticsDataDaily(**values)
                db.add(existing)
                existing_by_key[key] = existing
            else:
                for field, value in values.items():
                    setattr(existing, field, value)
            saved.append(existing)

        await db.flush()
        return saved


class CRUDOzonAnalyticsTotalsWindow:
    """Idempotent API-window totals upsert."""

    async def upsert(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        date_from: date,
        date_to: date,
        item: Dict[str, Any],
    ) -> ODSOzonAnalyticsTotalsWindow:
        query = select(ODSOzonAnalyticsTotalsWindow).where(
            ODSOzonAnalyticsTotalsWindow.shop_id == shop_id,
            ODSOzonAnalyticsTotalsWindow.date_from == date_from,
            ODSOzonAnalyticsTotalsWindow.date_to == date_to,
        )
        result = await db.execute(query)
        existing = result.scalar_one_or_none()
        values = {
            "shop_id": shop_id,
            "date_from": date_from,
            "date_to": date_to,
            "requested_metrics_core": item["requested_metrics_core"],
            "requested_metrics_outcome": item["requested_metrics_outcome"],
            "raw_totals_core": item["raw_totals_core"],
            "raw_totals_outcome": item["raw_totals_outcome"],
            "api_timestamp_core": item.get("api_timestamp_core"),
            "api_timestamp_outcome": item.get("api_timestamp_outcome"),
            **normalize_metric_values(item.get("metrics") or {}),
        }
        if existing is None:
            existing = ODSOzonAnalyticsTotalsWindow(**values)
            db.add(existing)
        else:
            for field, value in values.items():
                setattr(existing, field, value)
        await db.flush()
        return existing


crud_ods_ozon_analytics_data_daily = CRUDOzonAnalyticsDataDaily()
crud_ods_ozon_analytics_totals_window = CRUDOzonAnalyticsTotalsWindow()
