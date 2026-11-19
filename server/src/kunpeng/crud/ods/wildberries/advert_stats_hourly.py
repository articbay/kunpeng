"""
ODS 层 - 广告统计小时数据 CRUD
"""
import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.models.ods.wildberries.advert_stats_hourly import ODSWBAdvertStatHourly

logger = logging.getLogger(__name__)


class CRUDODSWBAdvertStatHourly(CRUDBase[ODSWBAdvertStatHourly, Dict[str, Any], Dict[str, Any]]):
    """ODS 广告统计小时数据 CRUD"""

    async def get_hourly_sum_before_hour(
        self,
        db: AsyncSession,
        shop_id: int,
        stat_date: date,
        stat_hour: int,
    ) -> Dict[Tuple[Optional[int], Optional[int], Optional[str]], Dict[str, Any]]:
        """
        查询当天已写入的小时数据累计（排除当前小时）

        Returns:
            {(advert_id, nm_id, app_type): {'views': x, 'clicks': y, ...}}
        """
        result = await db.execute(
            select(
                ODSWBAdvertStatHourly.advert_id,
                ODSWBAdvertStatHourly.nm_id,
                ODSWBAdvertStatHourly.app_type,
                func.sum(ODSWBAdvertStatHourly.views).label("views"),
                func.sum(ODSWBAdvertStatHourly.clicks).label("clicks"),
                func.sum(ODSWBAdvertStatHourly.atbs).label("atbs"),
                func.sum(ODSWBAdvertStatHourly.orders).label("orders"),
                func.sum(ODSWBAdvertStatHourly.canceled).label("canceled"),
                func.sum(ODSWBAdvertStatHourly.shks).label("shks"),
                func.sum(ODSWBAdvertStatHourly.sum_cost).label("sum_cost"),
                func.sum(ODSWBAdvertStatHourly.sum_price).label("sum_price"),
            )
            .where(
                (ODSWBAdvertStatHourly.shop_id == shop_id)
                & (ODSWBAdvertStatHourly.stat_date == stat_date)
                & (ODSWBAdvertStatHourly.stat_hour < stat_hour)
            )
            .group_by(
                ODSWBAdvertStatHourly.advert_id,
                ODSWBAdvertStatHourly.nm_id,
                ODSWBAdvertStatHourly.app_type,
            )
        )

        sums = {}
        for row in result.all():
            key = (row.advert_id, row.nm_id, row.app_type)
            sums[key] = {
                "views": row.views or 0,
                "clicks": row.clicks or 0,
                "atbs": row.atbs or 0,
                "orders": row.orders or 0,
                "canceled": row.canceled or 0,
                "shks": row.shks or 0,
                "sum_cost": row.sum_cost or 0,
                "sum_price": row.sum_price or 0,
            }
        return sums

    async def upsert_many(
        self,
        db: AsyncSession,
        *,
        stats_data: List[Dict[str, Any]],
        shop_id: int,
        stat_date: date,
        stat_hour: int,
    ) -> None:
        """
        批量 upsert 小时数据（MySQL ON DUPLICATE KEY UPDATE）

        Args:
            stats_data: 列表，每项为展平后的统计字典，含 advert_id, nm_id, app_type 等
            shop_id: 店铺ID
            stat_date: 统计日期
            stat_hour: 统计小时
        """
        logger.debug(
            f"[ODS CRUD Hourly] 开始 upsert 广告小时统计 - 店铺: {shop_id}, 日期: {stat_date}, 小时: {stat_hour}, 数据量: {len(stats_data)}"
        )

        if not stats_data:
            return []

        records = []
        for data in stats_data:
            record = {
                "shop_id": shop_id,
                "row_data": data.get("row_data", data),
                "advert_id": data.get("advert_id"),
                "stat_date": stat_date,
                "stat_hour": stat_hour,
                "nm_id": data.get("nm_id"),
                "nm_name": data.get("nm_name"),
                "app_type": data.get("app_type"),
                "views": data.get("views"),
                "clicks": data.get("clicks"),
                "atbs": data.get("atbs"),
                "orders": data.get("orders"),
                "canceled": data.get("canceled"),
                "shks": data.get("shks"),
                "sum_cost": data.get("sum_cost"),
                "sum_price": data.get("sum_price"),
                "cpc": data.get("cpc"),
                "ctr": data.get("ctr"),
                "cr": data.get("cr"),
                "currency": data.get("currency"),
            }
            records.append(record)

        # MySQL upsert
        stmt = insert(ODSWBAdvertStatHourly).values(records)
        update_dict = {
            "row_data": stmt.inserted.row_data,
            "nm_name": stmt.inserted.nm_name,
            "views": stmt.inserted.views,
            "clicks": stmt.inserted.clicks,
            "atbs": stmt.inserted.atbs,
            "orders": stmt.inserted.orders,
            "canceled": stmt.inserted.canceled,
            "shks": stmt.inserted.shks,
            "sum_cost": stmt.inserted.sum_cost,
            "sum_price": stmt.inserted.sum_price,
            "cpc": stmt.inserted.cpc,
            "ctr": stmt.inserted.ctr,
            "cr": stmt.inserted.cr,
            "currency": stmt.inserted.currency,
        }
        upsert_stmt = stmt.on_duplicate_key_update(**update_dict)
        await db.execute(upsert_stmt)
        await db.commit()

        logger.debug(f"[ODS CRUD Hourly] upsert 完成 - 记录数: {len(records)}")
        return []


# CRUD 实例
crud_ods_wb_advert_stat_hourly = CRUDODSWBAdvertStatHourly(ODSWBAdvertStatHourly)
