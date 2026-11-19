"""
ODS 层 - 搜索关键字统计小时数据 CRUD
"""
import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.models.ods.wildberries.search_cluster_stat_hourly import ODSWBSearchClusterStatHourly

logger = logging.getLogger(__name__)


class CRUDODSWBSearchClusterStatHourly(CRUDBase[ODSWBSearchClusterStatHourly, Dict[str, Any], Dict[str, Any]]):
    """ODS 搜索关键字统计小时数据 CRUD"""

    async def get_hourly_sum_before_hour(
        self,
        db: AsyncSession,
        shop_id: int,
        stat_date: date,
        stat_hour: int,
    ) -> Dict[Tuple[Optional[int], int, Optional[str]], Dict[str, Any]]:
        """
        查询当天已写入的小时数据累计（排除当前小时）

        Returns:
            {(advert_id, nm_id, norm_query): {'views': x, 'clicks': y, ...}}
        """
        result = await db.execute(
            select(
                ODSWBSearchClusterStatHourly.advert_id,
                ODSWBSearchClusterStatHourly.nm_id,
                ODSWBSearchClusterStatHourly.norm_query,
                func.sum(ODSWBSearchClusterStatHourly.views).label("views"),
                func.sum(ODSWBSearchClusterStatHourly.clicks).label("clicks"),
                func.sum(ODSWBSearchClusterStatHourly.sum_cost).label("sum_cost"),
                func.sum(ODSWBSearchClusterStatHourly.atbs).label("atbs"),
                func.sum(ODSWBSearchClusterStatHourly.orders).label("orders"),
            )
            .where(
                (ODSWBSearchClusterStatHourly.shop_id == shop_id)
                & (ODSWBSearchClusterStatHourly.stat_date == stat_date)
                & (ODSWBSearchClusterStatHourly.stat_hour < stat_hour)
            )
            .group_by(
                ODSWBSearchClusterStatHourly.advert_id,
                ODSWBSearchClusterStatHourly.nm_id,
                ODSWBSearchClusterStatHourly.norm_query,
            )
        )

        sums = {}
        for row in result.all():
            key = (row.advert_id, row.nm_id, row.norm_query)
            sums[key] = {
                "views": row.views or 0,
                "clicks": row.clicks or 0,
                "sum_cost": row.sum_cost or 0,
                "atbs": row.atbs or 0,
                "orders": row.orders or 0,
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
        批量 upsert 搜索关键字小时数据（MySQL ON DUPLICATE KEY UPDATE）
        """
        logger.debug(
            f"[ODS CRUD Hourly] 开始 upsert 搜索关键字小时统计 - 店铺: {shop_id}, 日期: {stat_date}, 小时: {stat_hour}, 数据量: {len(stats_data)}"
        )

        if not stats_data:
            return []

        records = []
        for data in stats_data:
            record = {
                "shop_id": shop_id,
                "row_data": data.get("row_data", data),
                "stat_date": stat_date,
                "stat_hour": stat_hour,
                "advert_id": data.get("advert_id"),
                "nm_id": data.get("nm_id"),
                "norm_query": data.get("norm_query"),
                "views": data.get("views"),
                "clicks": data.get("clicks"),
                "sum_cost": data.get("sum_cost"),
                "atbs": data.get("atbs"),
                "orders": data.get("orders"),
                "cpc": data.get("cpc"),
                "ctr": data.get("ctr"),
                "cr": data.get("cr"),
            }
            records.append(record)

        stmt = insert(ODSWBSearchClusterStatHourly).values(records)
        update_dict = {
            "row_data": stmt.inserted.row_data,
            "views": stmt.inserted.views,
            "clicks": stmt.inserted.clicks,
            "sum_cost": stmt.inserted.sum_cost,
            "atbs": stmt.inserted.atbs,
            "orders": stmt.inserted.orders,
            "cpc": stmt.inserted.cpc,
            "ctr": stmt.inserted.ctr,
            "cr": stmt.inserted.cr,
        }
        upsert_stmt = stmt.on_duplicate_key_update(**update_dict)
        await db.execute(upsert_stmt)
        await db.commit()

        logger.debug(f"[ODS CRUD Hourly] upsert 完成 - 记录数: {len(records)}")
        return []


# CRUD 实例
crud_ods_wb_search_cluster_stat_hourly = CRUDODSWBSearchClusterStatHourly(ODSWBSearchClusterStatHourly)
