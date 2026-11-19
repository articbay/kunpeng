"""Wildberries DWD 数据构建服务。"""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.dwd.wildberries.advert import (
    crud_dwd_wb_advert_activity_detail,
    crud_dwd_wb_advert_bid_config,
    crud_dwd_wb_advert_stats_daily_incr,
    crud_dwd_wb_advert_stats_hourly_incr,
)
from kunpeng.crud.dwd.wildberries.finance import crud_dwd_wb_sales_report_detail
from kunpeng.crud.dwd.wildberries.funnel import crud_dwd_wb_sales_funnel_detail
from kunpeng.crud.dwd.wildberries.sales_report_summary import (
    crud_dwd_wb_sales_report_summary,
)
from kunpeng.utils.timezone import today_platform


class WBDWDService:
    """编排 Wildberries ODS 到 DWD 的转换。"""

    @staticmethod
    def _validate_date_range(
        date_from: date | None,
        date_to: date | None,
    ) -> tuple[date, date]:
        """广告效果默认只重算平台当天，避免无边界扫描历史全表。"""
        resolved_from = date_from or today_platform()
        resolved_to = date_to or resolved_from
        if resolved_from > resolved_to:
            raise ValueError("date_from 不能晚于 date_to")
        return resolved_from, resolved_to

    async def sync_advert_config(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        snapshot_date: date | None = None,
    ) -> dict[str, dict[str, int]]:
        """构建广告活动商品与关键词出价两张当前快照表。"""
        business_date = snapshot_date or today_platform()
        try:
            activity = await crud_dwd_wb_advert_activity_detail.refresh(
                db,
                shop_id=shop_id,
                snapshot_date=business_date,
            )
            bid = await crud_dwd_wb_advert_bid_config.refresh(
                db,
                shop_id=shop_id,
                snapshot_date=business_date,
            )
            await db.commit()
            return {"activity_detail": activity, "bid_config": bid}
        except Exception:
            await db.rollback()
            raise

    async def sync_advert_stats(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, dict[str, int]]:
        """由小时 ODS 构建小时事实，再由小时事实构建日事实。"""
        resolved_from, resolved_to = self._validate_date_range(date_from, date_to)
        try:
            hourly = await crud_dwd_wb_advert_stats_hourly_incr.sync(
                db,
                shop_id=shop_id,
                date_from=resolved_from,
                date_to=resolved_to,
            )
            daily = await crud_dwd_wb_advert_stats_daily_incr.sync(
                db,
                shop_id=shop_id,
                date_from=resolved_from,
                date_to=resolved_to,
            )
            await db.commit()
            return {"hourly_stats": hourly, "daily_stats": daily}
        except Exception:
            await db.rollback()
            raise

    async def sync_advert_all(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        snapshot_date: date | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, dict[str, int]]:
        """一次手动请求内构建全部四张广告 DWD 表。"""
        business_date = snapshot_date or today_platform()
        resolved_from, resolved_to = self._validate_date_range(date_from, date_to)
        try:
            activity = await crud_dwd_wb_advert_activity_detail.refresh(
                db,
                shop_id=shop_id,
                snapshot_date=business_date,
            )
            bid = await crud_dwd_wb_advert_bid_config.refresh(
                db,
                shop_id=shop_id,
                snapshot_date=business_date,
            )
            hourly = await crud_dwd_wb_advert_stats_hourly_incr.sync(
                db,
                shop_id=shop_id,
                date_from=resolved_from,
                date_to=resolved_to,
            )
            daily = await crud_dwd_wb_advert_stats_daily_incr.sync(
                db,
                shop_id=shop_id,
                date_from=resolved_from,
                date_to=resolved_to,
            )
            await db.commit()
            return {
                "activity_detail": activity,
                "bid_config": bid,
                "hourly_stats": hourly,
                "daily_stats": daily,
            }
        except Exception:
            await db.rollback()
            raise

    async def sync_sales_report_detail(
        self,
        db: AsyncSession,
        *,
        batch_size: int = 500,
        shop_id: int | None = None,
    ) -> dict[str, int]:
        """扫描全部或指定店铺 ODS，并幂等写入财务结算明细 DWD 表。"""
        if batch_size <= 0:
            raise ValueError("batch_size 必须大于 0")

        stats = {"scanned": 0, "created": 0, "updated": 0}
        after_id = 0

        try:
            while True:
                sources = await crud_dwd_wb_sales_report_detail.get_source_batch(
                    db,
                    after_id=after_id,
                    batch_size=batch_size,
                    shop_id=shop_id,
                )
                if not sources:
                    break

                batch_stats = await crud_dwd_wb_sales_report_detail.upsert_source_batch(
                    db,
                    sources=sources,
                )
                stats["scanned"] += len(sources)
                stats["created"] += batch_stats["created"]
                stats["updated"] += batch_stats["updated"]
                after_id = sources[-1].id

            await db.commit()
            return stats
        except Exception:
            await db.rollback()
            raise

    async def sync_sales_report_summary(
        self,
        db: AsyncSession,
        *,
        batch_size: int = 500,
        shop_id: int | None = None,
    ) -> dict[str, int]:
        """扫描报告列表 ODS，并幂等写入财务报告周汇总 DWD。"""
        if batch_size <= 0:
            raise ValueError("batch_size 必须大于 0")

        stats = {"scanned": 0, "created": 0, "updated": 0}
        after_id = 0

        try:
            while True:
                sources = await crud_dwd_wb_sales_report_summary.get_source_batch(
                    db,
                    after_id=after_id,
                    batch_size=batch_size,
                    shop_id=shop_id,
                )
                if not sources:
                    break

                batch_stats = (
                    await crud_dwd_wb_sales_report_summary.upsert_source_batch(
                        db,
                        sources=sources,
                    )
                )
                stats["scanned"] += len(sources)
                stats["created"] += batch_stats["created"]
                stats["updated"] += batch_stats["updated"]
                after_id = sources[-1].id

            await db.commit()
            return stats
        except Exception:
            await db.rollback()
            raise

    async def sync_sales_funnel_detail(
        self,
        db: AsyncSession,
        *,
        batch_size: int = 500,
        shop_id: int | None = None,
    ) -> dict[str, int]:
        """扫描全部或指定店铺 ODS，并幂等写入销售漏斗 DWD 表。"""
        if batch_size <= 0:
            raise ValueError("batch_size 必须大于 0")

        stats = {"scanned": 0, "created": 0, "updated": 0}
        after_id = 0

        try:
            while True:
                sources = await crud_dwd_wb_sales_funnel_detail.get_source_batch(
                    db,
                    after_id=after_id,
                    batch_size=batch_size,
                    shop_id=shop_id,
                )
                if not sources:
                    break

                batch_stats = await crud_dwd_wb_sales_funnel_detail.upsert_source_batch(
                    db,
                    sources=sources,
                )
                stats["scanned"] += len(sources)
                stats["created"] += batch_stats["created"]
                stats["updated"] += batch_stats["updated"]
                after_id = sources[-1].id

            await db.commit()
            return stats
        except Exception:
            await db.rollback()
            raise


wb_dwd_service = WBDWDService()
