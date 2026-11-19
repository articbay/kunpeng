"""Orchestrate first-time backfill and incremental refreshes for Ozon DWM tables."""

from collections.abc import Iterator
from datetime import date, datetime, time, timedelta
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.dwm.ozon import (
    crud_dwm_ozon_goods_trade_return_day,
    crud_dwm_ozon_order_lifecycle_detail,
    crud_dwm_ozon_refresh_scope,
)
from kunpeng.utils.timezone import now_platform, platform_tz


class _DateRangeDWMCRUD(Protocol):
    async def get_source_date_bounds(
        self, db: AsyncSession
    ) -> tuple[date | None, date | None]: ...

    async def get_target_date_bounds(
        self, db: AsyncSession
    ) -> tuple[date | None, date | None]: ...

    async def refresh_order_date_range(
        self,
        db: AsyncSession,
        *,
        date_from: date,
        date_to: date,
        shop_id: int | None = None,
    ) -> dict[str, Any]: ...


class OzonDWMRefreshService:
    """Keep the two Ozon DWM tables complete and current."""

    backfill_chunk_days = 30
    recent_order_days = 7
    recent_return_update_days = 3

    @staticmethod
    def _chunk_range(
        date_from: date,
        date_to: date,
        *,
        chunk_days: int,
    ) -> Iterator[tuple[date, date]]:
        cursor = date_from
        while cursor <= date_to:
            chunk_to = min(
                cursor + timedelta(days=chunk_days - 1),
                date_to,
            )
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

    async def _refresh_and_commit(
        self,
        db: AsyncSession,
        *,
        crud: _DateRangeDWMCRUD,
        date_from: date,
        date_to: date,
    ) -> dict[str, Any]:
        result = await crud.refresh_order_date_range(
            db,
            date_from=date_from,
            date_to=date_to,
        )
        await db.commit()
        return result

    async def _backfill_missing_coverage(
        self,
        db: AsyncSession,
        *,
        crud: _DateRangeDWMCRUD,
    ) -> dict[str, int]:
        source_from, source_to = await crud.get_source_date_bounds(db)
        if source_from is None or source_to is None:
            return {"range_count": 0, "affected_rows": 0, "deleted_stale_rows": 0}

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

        summary = {"range_count": 0, "affected_rows": 0, "deleted_stale_rows": 0}
        for missing_from, missing_to in missing_ranges:
            for chunk_from, chunk_to in self._chunk_range(
                missing_from,
                missing_to,
                chunk_days=self.backfill_chunk_days,
            ):
                result = await self._refresh_and_commit(
                    db,
                    crud=crud,
                    date_from=chunk_from,
                    date_to=chunk_to,
                )
                summary["range_count"] += 1
                summary["affected_rows"] += int(result.get("affected_rows", 0))
                summary["deleted_stale_rows"] += int(
                    result.get("deleted_stale_rows", 0)
                )
        return summary

    async def _refresh_both(
        self,
        db: AsyncSession,
        *,
        date_from: date,
        date_to: date,
    ) -> dict[str, dict[str, Any]]:
        goods_result = (
            await crud_dwm_ozon_goods_trade_return_day.refresh_order_date_range(
                db,
                date_from=date_from,
                date_to=date_to,
            )
        )
        lifecycle_result = (
            await crud_dwm_ozon_order_lifecycle_detail.refresh_order_date_range(
                db,
                date_from=date_from,
                date_to=date_to,
            )
        )
        await db.commit()
        return {
            "goods_trade_return_day": goods_result,
            "order_lifecycle_detail": lifecycle_result,
        }

    async def refresh_all(
        self,
        db: AsyncSession,
        *,
        run_at: datetime | None = None,
    ) -> dict[str, Any]:
        """Backfill missing coverage, then refresh current and late-return dates."""
        effective_run_at = run_at or now_platform()
        today = effective_run_at.astimezone(platform_tz()).date()
        recent_from = today - timedelta(days=self.recent_order_days - 1)
        updated_since = datetime.combine(
            today - timedelta(days=self.recent_return_update_days),
            time.min,
            tzinfo=platform_tz(),
        )

        try:
            backfill = {
                "goods_trade_return_day": await self._backfill_missing_coverage(
                    db,
                    crud=crud_dwm_ozon_goods_trade_return_day,
                ),
                "order_lifecycle_detail": await self._backfill_missing_coverage(
                    db,
                    crud=crud_dwm_ozon_order_lifecycle_detail,
                ),
            }

            recent = await self._refresh_both(
                db,
                date_from=recent_from,
                date_to=today,
            )

            return_order_dates = (
                await crud_dwm_ozon_refresh_scope.get_recent_return_order_dates(
                    db,
                    updated_since=updated_since,
                )
            )
            historical_dates = [
                order_date
                for order_date in return_order_dates
                if order_date < recent_from or order_date > today
            ]
            historical_results = []
            for range_from, range_to in self._consecutive_ranges(historical_dates):
                historical_results.append(
                    {
                        "date_from": range_from.isoformat(),
                        "date_to": range_to.isoformat(),
                        "tables": await self._refresh_both(
                            db,
                            date_from=range_from,
                            date_to=range_to,
                        ),
                    }
                )

            return {
                "status": "success",
                "backfill": backfill,
                "recent": {
                    "date_from": recent_from.isoformat(),
                    "date_to": today.isoformat(),
                    "tables": recent,
                },
                "historical_return_range_count": len(historical_results),
                "historical_returns": historical_results,
            }
        except Exception:
            await db.rollback()
            raise


ozon_dwm_refresh_service = OzonDWMRefreshService()
