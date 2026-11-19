"""Wildberries 广告配置与效果 DWD 构建。"""

from collections import defaultdict
from collections.abc import Iterable
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.dwd.wildberries.advert import (
    DWDWBAdvertActivityDetail,
    DWDWBAdvertBidConfig,
    DWDWBAdvertStatsDailyIncr,
    DWDWBAdvertStatsHourlyIncr,
)
from kunpeng.models.ods.wildberries.adv_enhanced import (
    ODSWBAdvertFullStat,
    ODSWBAdvertV2,
    ODSWBBidRecommendation,
    ODSWBNormQueryBid,
    ODSWBNormQueryList,
)
from kunpeng.models.ods.wildberries.advert_stats_hourly import ODSWBAdvertStatHourly
from kunpeng.models.ods.wildberries.adverts import ODSWBAdvert
from kunpeng.models.ods.wildberries.balance import ODSWBAdvertBudget, ODSWBAdvertProduct

ZERO = Decimal("0")
SIX_DECIMAL_PLACES = Decimal("0.000001")
ADVERT_STATUS_NAMES = {
    -1: "已删除",
    4: "待上线",
    7: "已完成",
    8: "已驳回",
    9: "投放中",
    11: "已暂停",
}
COUNT_FIELDS = ("views", "clicks", "atbs", "orders", "canceled", "shks")
MONEY_FIELDS = ("sum_cost", "sum_price")


def _decimal(value: Any) -> Decimal:
    return ZERO if value is None else Decimal(str(value))


def _ratio(numerator: Any, denominator: Any) -> Decimal:
    denominator_value = _decimal(denominator)
    if denominator_value == 0:
        return ZERO
    return (_decimal(numerator) / denominator_value).quantize(SIX_DECIMAL_PLACES)


def _status_name(status: Any) -> str:
    return ADVERT_STATUS_NAMES.get(status, "未知状态")


def _payment_type(advert: ODSWBAdvertV2 | ODSWBAdvert | None) -> str | None:
    if advert is None:
        return None
    payment_type = getattr(advert, "payment_type", None)
    if payment_type:
        return payment_type
    row_data = advert.row_data if isinstance(advert.row_data, dict) else {}
    settings = row_data.get("settings")
    if isinstance(settings, dict):
        return settings.get("payment_type") or settings.get("paymentType")
    return None


def _first_attribute(items: Iterable[Any], field: str) -> Any:
    for item in items:
        value = getattr(item, field, None)
        if value is not None:
            return value
    return None


def _sum_metrics(rows: Iterable[Any]) -> dict[str, Any]:
    rows = list(rows)
    counts = {
        field: sum(int(getattr(row, field, None) or 0) for row in rows)
        for field in COUNT_FIELDS
    }
    amounts = {
        field: sum((_decimal(getattr(row, field, None)) for row in rows), ZERO)
        for field in MONEY_FIELDS
    }
    return {
        **counts,
        **amounts,
        "cpc": _ratio(amounts["sum_cost"], counts["clicks"]),
        "ctr": _ratio(counts["clicks"], counts["views"]),
        "cr": _ratio(counts["orders"], counts["clicks"]),
        "roi": _ratio(amounts["sum_price"], amounts["sum_cost"]),
    }


def _group_daily_fact_rows(rows: Iterable[Any]) -> dict[tuple[Any, ...], list[Any]]:
    """Group valid advertising facts at the daily DWD business grain."""
    grouped: dict[tuple[Any, ...], list[Any]] = defaultdict(list)
    for row in rows:
        if row.advert_id is None or row.nm_id is None or row.stat_date is None:
            continue
        currency = row.currency or "UNKNOWN"
        grouped[(row.stat_date, row.advert_id, row.nm_id, currency)].append(row)
    return grouped


def _merge_daily_fact_groups(
    hourly_rows: Iterable[Any],
    fullstat_rows: Iterable[Any],
) -> dict[tuple[Any, ...], list[Any]]:
    """Use authoritative full-day facts and fall back to hourly facts by key."""
    grouped = _group_daily_fact_rows(hourly_rows)
    grouped.update(_group_daily_fact_rows(fullstat_rows))
    return grouped


async def _upsert_records(
    db: AsyncSession,
    *,
    model: type,
    records: list[dict[str, Any]],
    key_fields: tuple[str, ...],
    existing_statement: Any,
    reconcile: bool = False,
) -> dict[str, int]:
    """按业务键更新 ORM 记录；快照模式同时移除当前范围的失效行。"""
    existing_result = await db.execute(existing_statement)
    existing_items = list(existing_result.scalars().all())
    existing_by_key = {
        tuple(getattr(item, field) for field in key_fields): item
        for item in existing_items
    }
    incoming_by_key = {
        tuple(record[field] for field in key_fields): record for record in records
    }

    created = 0
    updated = 0
    for key, record in incoming_by_key.items():
        existing = existing_by_key.get(key)
        if existing is None:
            db.add(model(**record))
            created += 1
            continue
        for field, value in record.items():
            setattr(existing, field, value)
        updated += 1

    deleted = 0
    # 空来源可能是上游尚未同步，安全起见不据此清空既有 DWD。
    if reconcile and records:
        for key, existing in existing_by_key.items():
            if key not in incoming_by_key:
                await db.delete(existing)
                deleted += 1

    await db.flush()
    return {
        "source_rows": len(records),
        "created": created,
        "updated": updated,
        "deleted": deleted,
    }


async def _advert_maps(
    db: AsyncSession,
    shop_id: int,
) -> tuple[dict[int, ODSWBAdvertV2], dict[int, ODSWBAdvert]]:
    v2_result = await db.execute(
        select(ODSWBAdvertV2).where(ODSWBAdvertV2.shop_id == shop_id)
    )
    legacy_result = await db.execute(
        select(ODSWBAdvert).where(ODSWBAdvert.shop_id == shop_id)
    )
    return (
        {item.advert_id: item for item in v2_result.scalars().all()},
        {item.advert_id: item for item in legacy_result.scalars().all()},
    )


def _advert_attributes(
    advert_id: int,
    v2_adverts: dict[int, ODSWBAdvertV2],
    legacy_adverts: dict[int, ODSWBAdvert],
) -> dict[str, Any]:
    advert = v2_adverts.get(advert_id) or legacy_adverts.get(advert_id)
    if advert is None:
        return {
            "status": None,
            "status_name": "未知状态",
            "payment_type": None,
            "bid_type": None,
        }
    return {
        "status": advert.status,
        "status_name": _status_name(advert.status),
        "payment_type": _payment_type(advert),
        "bid_type": advert.bid_type,
    }


class CRUDDWDWBAdvertActivityDetail:
    """从当前广告、商品和最新预算 ODS 构建活动商品快照。"""

    async def refresh(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        snapshot_date: date,
    ) -> dict[str, int]:
        v2_adverts, legacy_adverts = await _advert_maps(db, shop_id)
        product_result = await db.execute(
            select(ODSWBAdvertProduct).where(ODSWBAdvertProduct.shop_id == shop_id)
        )
        products = list(product_result.scalars().all())

        budget_result = await db.execute(
            select(ODSWBAdvertBudget)
            .where(ODSWBAdvertBudget.shop_id == shop_id)
            .order_by(
                ODSWBAdvertBudget.advert_id,
                ODSWBAdvertBudget.sync_date.desc(),
                ODSWBAdvertBudget.id.desc(),
            )
        )
        latest_budget: dict[int, ODSWBAdvertBudget] = {}
        for budget in budget_result.scalars().all():
            latest_budget.setdefault(budget.advert_id, budget)

        records = []
        for product in products:
            advert = v2_adverts.get(product.advert_id) or legacy_adverts.get(
                product.advert_id
            )
            if advert is None:
                continue
            budget = latest_budget.get(product.advert_id)
            total_budget = getattr(advert, "total_budget", None)
            records.append(
                {
                    "shop_id": shop_id,
                    "snapshot_date": snapshot_date,
                    "advert_id": product.advert_id,
                    "nm_id": product.nm_id,
                    "advert_name": advert.name,
                    "status": advert.status,
                    "status_name": _status_name(advert.status),
                    "bid_type": advert.bid_type,
                    "payment_type": _payment_type(advert),
                    "currency": advert.currency,
                    "placement_search": advert.placement_search,
                    "placement_recommendations": advert.placement_recommendations,
                    "subject_id": product.subject_id,
                    "subject_name": product.subject_name,
                    "bid_search": product.bid_search,
                    "bid_recommendations": product.bid_recommendations,
                    "total_budget": (
                        budget.total if budget is not None else total_budget
                    ),
                    "budget_sync_date": (
                        budget.sync_date if budget is not None else None
                    ),
                }
            )

        return await _upsert_records(
            db,
            model=DWDWBAdvertActivityDetail,
            records=records,
            key_fields=("shop_id", "advert_id", "nm_id"),
            existing_statement=select(DWDWBAdvertActivityDetail).where(
                DWDWBAdvertActivityDetail.shop_id == shop_id
            ),
            reconcile=True,
        )


class CRUDDWDWBAdvertBidConfig:
    """以 Norm 关键词列表为主表构建当前出价配置。"""

    async def refresh(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        snapshot_date: date,
    ) -> dict[str, int]:
        list_result = await db.execute(
            select(ODSWBNormQueryList).where(ODSWBNormQueryList.shop_id == shop_id)
        )
        query_items = list(list_result.scalars().all())

        bid_result = await db.execute(
            select(ODSWBNormQueryBid).where(ODSWBNormQueryBid.shop_id == shop_id)
        )
        bids = {
            (item.advert_id, item.nm_id, item.norm_query): item
            for item in bid_result.scalars().all()
        }

        recommendation_result = await db.execute(
            select(ODSWBBidRecommendation).where(
                ODSWBBidRecommendation.shop_id == shop_id
            )
        )
        query_recommendations: dict[tuple[Any, Any, Any], list[Any]] = defaultdict(list)
        base_recommendations: dict[tuple[Any, Any], list[Any]] = defaultdict(list)
        for item in recommendation_result.scalars().all():
            if item.record_type == "base" or item.norm_query == "__base__":
                base_recommendations[(item.advert_id, item.nm_id)].append(item)
            else:
                query_recommendations[
                    (item.advert_id, item.nm_id, item.norm_query)
                ].append(item)

        v2_adverts, legacy_adverts = await _advert_maps(db, shop_id)
        records = []
        for query_item in query_items:
            if (
                not query_item.advert_id
                or not query_item.nm_id
                or not query_item.norm_query
            ):
                continue
            key = (query_item.advert_id, query_item.nm_id, query_item.norm_query)
            recommendations = query_recommendations.get(key, [])
            base_items = base_recommendations.get(
                (query_item.advert_id, query_item.nm_id), []
            )
            bid = bids.get(key)
            advert = v2_adverts.get(query_item.advert_id) or legacy_adverts.get(
                query_item.advert_id
            )
            bid_row_data = (
                bid.row_data if bid and isinstance(bid.row_data, dict) else {}
            )
            records.append(
                {
                    "shop_id": shop_id,
                    "snapshot_date": snapshot_date,
                    "advert_id": query_item.advert_id,
                    "nm_id": query_item.nm_id,
                    "norm_query": query_item.norm_query,
                    "is_active": query_item.is_active,
                    "currency": bid_row_data.get("currency")
                    or getattr(advert, "currency", None),
                    "reach_max_bid_kopecks": _first_attribute(
                        recommendations, "reach_max_bid_kopecks"
                    ),
                    "reach_max_bid": _first_attribute(recommendations, "reach_max_bid"),
                    "reach_medium_bid_kopecks": _first_attribute(
                        recommendations, "reach_medium_bid_kopecks"
                    ),
                    "reach_medium_bid": _first_attribute(
                        recommendations, "reach_medium_bid"
                    ),
                    "reach_min_bid_kopecks": _first_attribute(
                        recommendations, "reach_min_bid_kopecks"
                    ),
                    "reach_min_bid": _first_attribute(recommendations, "reach_min_bid"),
                    "base_competitive_bid_kopecks": _first_attribute(
                        base_items, "base_competitive_bid_kopecks"
                    ),
                    "base_competitive_bid": _first_attribute(
                        base_items, "base_competitive_bid"
                    ),
                    "base_leaders_bid_kopecks": _first_attribute(
                        base_items, "base_leaders_bid_kopecks"
                    ),
                    "base_leaders_bid": _first_attribute(
                        base_items, "base_leaders_bid"
                    ),
                    "base_top2_bid_kopecks": _first_attribute(
                        base_items, "base_top2_bid_kopecks"
                    ),
                    "base_top2_bid": _first_attribute(base_items, "base_top2_bid"),
                    "query_bid": getattr(bid, "bid", None),
                }
            )

        return await _upsert_records(
            db,
            model=DWDWBAdvertBidConfig,
            records=records,
            key_fields=("shop_id", "advert_id", "nm_id", "norm_query"),
            existing_statement=select(DWDWBAdvertBidConfig).where(
                DWDWBAdvertBidConfig.shop_id == shop_id
            ),
            reconcile=True,
        )


class CRUDDWDWBAdvertStatsHourlyIncr:
    """跨 app_type 汇总 ODS 小时增量。"""

    async def sync(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, int]:
        statement = select(ODSWBAdvertStatHourly).where(
            ODSWBAdvertStatHourly.shop_id == shop_id
        )
        if date_from is not None:
            statement = statement.where(ODSWBAdvertStatHourly.stat_date >= date_from)
        if date_to is not None:
            statement = statement.where(ODSWBAdvertStatHourly.stat_date <= date_to)
        result = await db.execute(statement)

        grouped: dict[tuple[Any, ...], list[Any]] = defaultdict(list)
        for row in result.scalars().all():
            if (
                row.advert_id is None
                or row.nm_id is None
                or row.stat_date is None
                or row.stat_hour is None
            ):
                continue
            currency = row.currency or "UNKNOWN"
            grouped[
                (row.stat_date, row.stat_hour, row.advert_id, row.nm_id, currency)
            ].append(row)

        v2_adverts, legacy_adverts = await _advert_maps(db, shop_id)
        records = []
        for key, rows in grouped.items():
            stat_date, stat_hour, advert_id, nm_id, currency = key
            records.append(
                {
                    "shop_id": shop_id,
                    "advert_id": advert_id,
                    **_advert_attributes(advert_id, v2_adverts, legacy_adverts),
                    "nm_id": nm_id,
                    "nm_name": next((row.nm_name for row in rows if row.nm_name), None),
                    "stat_date": stat_date,
                    "stat_hour": stat_hour,
                    "currency": currency,
                    **_sum_metrics(rows),
                    "source_platform": "WB",
                }
            )

        existing_statement = select(DWDWBAdvertStatsHourlyIncr).where(
            DWDWBAdvertStatsHourlyIncr.shop_id == shop_id
        )
        if date_from is not None:
            existing_statement = existing_statement.where(
                DWDWBAdvertStatsHourlyIncr.stat_date >= date_from
            )
        if date_to is not None:
            existing_statement = existing_statement.where(
                DWDWBAdvertStatsHourlyIncr.stat_date <= date_to
            )
        return await _upsert_records(
            db,
            model=DWDWBAdvertStatsHourlyIncr,
            records=records,
            key_fields=(
                "shop_id",
                "stat_date",
                "stat_hour",
                "advert_id",
                "nm_id",
                "currency",
            ),
            existing_statement=existing_statement,
            reconcile=True,
        )


class CRUDDWDWBAdvertStatsDailyIncr:
    """优先使用全量日统计，并以小时 DWD 补齐缺失日事实。"""

    async def sync(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, int]:
        statement = select(DWDWBAdvertStatsHourlyIncr).where(
            DWDWBAdvertStatsHourlyIncr.shop_id == shop_id
        )
        if date_from is not None:
            statement = statement.where(
                DWDWBAdvertStatsHourlyIncr.stat_date >= date_from
            )
        if date_to is not None:
            statement = statement.where(DWDWBAdvertStatsHourlyIncr.stat_date <= date_to)
        hourly_result = await db.execute(statement)

        fullstat_statement = select(ODSWBAdvertFullStat).where(
            ODSWBAdvertFullStat.shop_id == shop_id
        )
        if date_from is not None:
            fullstat_statement = fullstat_statement.where(
                ODSWBAdvertFullStat.stat_date >= date_from
            )
        if date_to is not None:
            fullstat_statement = fullstat_statement.where(
                ODSWBAdvertFullStat.stat_date <= date_to
            )
        fullstat_result = await db.execute(fullstat_statement)

        grouped = _merge_daily_fact_groups(
            hourly_result.scalars().all(),
            fullstat_result.scalars().all(),
        )
        v2_adverts, legacy_adverts = await _advert_maps(db, shop_id)

        records = []
        for key, rows in grouped.items():
            stat_date, advert_id, nm_id, currency = key
            records.append(
                {
                    "shop_id": shop_id,
                    "advert_id": advert_id,
                    **_advert_attributes(advert_id, v2_adverts, legacy_adverts),
                    "nm_id": nm_id,
                    "nm_name": next((row.nm_name for row in rows if row.nm_name), None),
                    "stat_date": stat_date,
                    "currency": currency,
                    **_sum_metrics(rows),
                    "source_platform": "WB",
                }
            )

        existing_statement = select(DWDWBAdvertStatsDailyIncr).where(
            DWDWBAdvertStatsDailyIncr.shop_id == shop_id
        )
        if date_from is not None:
            existing_statement = existing_statement.where(
                DWDWBAdvertStatsDailyIncr.stat_date >= date_from
            )
        if date_to is not None:
            existing_statement = existing_statement.where(
                DWDWBAdvertStatsDailyIncr.stat_date <= date_to
            )
        return await _upsert_records(
            db,
            model=DWDWBAdvertStatsDailyIncr,
            records=records,
            key_fields=(
                "shop_id",
                "stat_date",
                "advert_id",
                "nm_id",
                "currency",
            ),
            existing_statement=existing_statement,
            reconcile=True,
        )


crud_dwd_wb_advert_activity_detail = CRUDDWDWBAdvertActivityDetail()
crud_dwd_wb_advert_bid_config = CRUDDWDWBAdvertBidConfig()
crud_dwd_wb_advert_stats_hourly_incr = CRUDDWDWBAdvertStatsHourlyIncr()
crud_dwd_wb_advert_stats_daily_incr = CRUDDWDWBAdvertStatsDailyIncr()
