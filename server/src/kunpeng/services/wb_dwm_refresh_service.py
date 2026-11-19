"""Orchestrate Wildberries SKU-day DWM backfills."""

from collections.abc import Iterator
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.dwm.wildberries import (
    crud_dwm_wb_goods_oper_day,
    crud_dwm_wb_order_lifecycle_detail,
)
from kunpeng.utils.timezone import now_platform, platform_tz


class WBDWMRefreshService:
    """Refresh complete source coverage in restart-safe date chunks."""

    backfill_chunk_days = 30
    lifecycle_recent_order_days = 90

    @staticmethod
    def _chunk_range(
        date_from: date,
        date_to: date,
        *,
        chunk_days: int,
    ) -> Iterator[tuple[date, date]]:
        cursor = date_from
        while cursor <= date_to:
            chunk_to = min(cursor + timedelta(days=chunk_days - 1), date_to)
            yield cursor, chunk_to
            cursor = chunk_to + timedelta(days=1)

    @staticmethod
    def _consecutive_ranges(dates: list[date]) -> list[tuple[date, date]]:
        unique_dates = sorted(set(dates))
        if not unique_dates:
            return []
        ranges: list[tuple[date, date]] = []
        range_from = unique_dates[0]
        range_to = unique_dates[0]
        for current in unique_dates[1:]:
            if current == range_to + timedelta(days=1):
                range_to = current
                continue
            ranges.append((range_from, range_to))
            range_from = current
            range_to = current
        ranges.append((range_from, range_to))
        return ranges

    async def refresh_range(
        self,
        db: AsyncSession,
        *,
        date_from: date,
        date_to: date,
        shop_id: int | None = None,
    ) -> dict[str, Any]:
        try:
            result = await crud_dwm_wb_goods_oper_day.refresh_date_range(
                db,
                date_from=date_from,
                date_to=date_to,
                shop_id=shop_id,
            )
            await db.commit()
            return result
        except Exception:
            await db.rollback()
            raise

    async def backfill_all(
        self,
        db: AsyncSession,
        *,
        shop_id: int | None = None,
    ) -> dict[str, Any]:
        source_from, source_to = (
            await crud_dwm_wb_goods_oper_day.get_source_date_bounds(db)
        )
        if source_from is None or source_to is None:
            return {
                "date_from": None,
                "date_to": None,
                "range_count": 0,
                "affected_rows": 0,
                "deleted_stale_rows": 0,
            }

        summary: dict[str, Any] = {
            "date_from": source_from.isoformat(),
            "date_to": source_to.isoformat(),
            "range_count": 0,
            "affected_rows": 0,
            "deleted_stale_rows": 0,
            "unattributed_order_rows": 0,
            "unattributed_return_rows": 0,
        }
        for chunk_from, chunk_to in self._chunk_range(
            source_from,
            source_to,
            chunk_days=self.backfill_chunk_days,
        ):
            result = await self.refresh_range(
                db,
                date_from=chunk_from,
                date_to=chunk_to,
                shop_id=shop_id,
            )
            summary["range_count"] += 1
            summary["affected_rows"] += int(result["affected_rows"])
            summary["deleted_stale_rows"] += int(result["deleted_stale_rows"])
            summary["unattributed_order_rows"] = int(result["unattributed_order_rows"])
            summary["unattributed_return_rows"] = int(
                result["unattributed_return_rows"]
            )
        return summary

    async def refresh_lifecycle_range(
        self,
        db: AsyncSession,
        *,
        date_from: date,
        date_to: date,
        shop_id: int | None = None,
    ) -> dict[str, Any]:
        """Refresh one lifecycle order-date cohort transactionally."""
        try:
            result = await crud_dwm_wb_order_lifecycle_detail.refresh_order_date_range(
                db,
                date_from=date_from,
                date_to=date_to,
                shop_id=shop_id,
            )
            await db.commit()
            return result
        except Exception:
            await db.rollback()
            raise

    async def backfill_lifecycle_all(
        self,
        db: AsyncSession,
        *,
        shop_id: int | None = None,
    ) -> dict[str, Any]:
        """Backfill the complete WB lifecycle source range in safe chunks."""
        source_from, source_to = (
            await crud_dwm_wb_order_lifecycle_detail.get_source_date_bounds(db)
        )
        if source_from is None or source_to is None:
            return {
                "date_from": None,
                "date_to": None,
                "range_count": 0,
                "affected_rows": 0,
                "deleted_stale_rows": 0,
                "unmatched_return_rows": 0,
                "ambiguous_return_rows": 0,
                "marketplace_missing_srid_rows": 0,
            }

        summary: dict[str, Any] = {
            "date_from": source_from.isoformat(),
            "date_to": source_to.isoformat(),
            "range_count": 0,
            "affected_rows": 0,
            "deleted_stale_rows": 0,
            "unmatched_return_rows": 0,
            "ambiguous_return_rows": 0,
            "marketplace_missing_srid_rows": 0,
        }
        for chunk_from, chunk_to in self._chunk_range(
            source_from,
            source_to,
            chunk_days=self.backfill_chunk_days,
        ):
            result = await self.refresh_lifecycle_range(
                db,
                date_from=chunk_from,
                date_to=chunk_to,
                shop_id=shop_id,
            )
            summary["range_count"] += 1
            summary["affected_rows"] += int(result["affected_rows"])
            summary["deleted_stale_rows"] += int(result["deleted_stale_rows"])
            for key in (
                "unmatched_return_rows",
                "ambiguous_return_rows",
                "marketplace_missing_srid_rows",
            ):
                summary[key] += int(result[key])
        return summary

    async def _backfill_missing_lifecycle_coverage(
        self,
        db: AsyncSession,
    ) -> dict[str, int]:
        crud = crud_dwm_wb_order_lifecycle_detail
        source_from, source_to = await crud.get_source_date_bounds(db)
        if source_from is None or source_to is None:
            return {
                "range_count": 0,
                "affected_rows": 0,
                "deleted_stale_rows": 0,
            }
        target_from, target_to = await crud.get_target_date_bounds(db)
        missing_ranges: list[tuple[date, date]] = []
        if target_from is None or target_to is None:
            missing_ranges.append((source_from, source_to))
        else:
            if source_from < target_from:
                missing_ranges.append(
                    (source_from, min(source_to, target_from - timedelta(days=1)))
                )
            if source_to > target_to:
                missing_ranges.append(
                    (max(source_from, target_to + timedelta(days=1)), source_to)
                )

        summary = {
            "range_count": 0,
            "affected_rows": 0,
            "deleted_stale_rows": 0,
        }
        for missing_from, missing_to in missing_ranges:
            for chunk_from, chunk_to in self._chunk_range(
                missing_from,
                missing_to,
                chunk_days=self.backfill_chunk_days,
            ):
                result = await self.refresh_lifecycle_range(
                    db,
                    date_from=chunk_from,
                    date_to=chunk_to,
                )
                summary["range_count"] += 1
                summary["affected_rows"] += int(result["affected_rows"])
                summary["deleted_stale_rows"] += int(result["deleted_stale_rows"])
        return summary

    async def refresh_lifecycle_all(
        self,
        db: AsyncSession,
        *,
        run_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Backfill gaps and refresh recent orders plus historical return dates."""
        crud = crud_dwm_wb_order_lifecycle_detail
        effective_run_at = run_at or now_platform()
        today = effective_run_at.astimezone(platform_tz()).date()
        source_from, source_to = await crud.get_source_date_bounds(db)
        if source_from is None or source_to is None:
            return {
                "status": "success",
                "backfill": {
                    "range_count": 0,
                    "affected_rows": 0,
                    "deleted_stale_rows": 0,
                },
                "recent": None,
                "historical_return_range_count": 0,
                "historical_returns": [],
            }

        try:
            backfill = await self._backfill_missing_lifecycle_coverage(db)
            recent_from = max(
                source_from,
                today - timedelta(days=self.lifecycle_recent_order_days - 1),
            )
            recent_to = min(source_to, today)
            recent = None
            if recent_from <= recent_to:
                recent = {
                    "date_from": recent_from.isoformat(),
                    "date_to": recent_to.isoformat(),
                    "result": await self.refresh_lifecycle_range(
                        db,
                        date_from=recent_from,
                        date_to=recent_to,
                    ),
                }

            return_dates = await crud.get_return_order_dates(db)
            historical_dates = [
                return_date
                for return_date in return_dates
                if return_date < recent_from or return_date > recent_to
            ]
            historical_results = []
            for range_from, range_to in self._consecutive_ranges(historical_dates):
                historical_results.append(
                    {
                        "date_from": range_from.isoformat(),
                        "date_to": range_to.isoformat(),
                        "result": await self.refresh_lifecycle_range(
                            db,
                            date_from=range_from,
                            date_to=range_to,
                        ),
                    }
                )
            return {
                "status": "success",
                "backfill": backfill,
                "recent": recent,
                "historical_return_range_count": len(historical_results),
                "historical_returns": historical_results,
            }
        except Exception:
            await db.rollback()
            raise


wb_dwm_refresh_service = WBDWMRefreshService()
