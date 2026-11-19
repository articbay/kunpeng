"""
DWD 层 - Wildberries 广告报表明细 CRUD
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import and_, delete, func, select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.models.dwd.wildberries.adverts_report import \
    DWDWBAdvertsReportDetail
from kunpeng.models.ods.wildberries.adverts import ODSWBAdvert, ODSWBAdvertStat

logger = logging.getLogger(__name__)


class CRUDDWDWBAdvertsReportDetail(
    CRUDBase[DWDWBAdvertsReportDetail, Dict[str, Any], Dict[str, Any]]
):
    """DWD 广告报表明细 CRUD"""

    async def refresh_weekly_report(
        self,
        db: AsyncSession,
        shop_id: int,
        *,
        week_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        刷新指定店铺的周度广告报表

        从 ODS 层的 ods_wb_advert_stats 和 ods_wb_adverts 聚合数据，
        生成周度报表并写入 dwd_wb_adverts_report_detail。

        Args:
            shop_id: 店铺ID
            week_str: 周度标识 (如 week202530)，如为空则刷新当前周和上一周

        Returns:
            刷新结果信息
        """
        logger.info(
            f"[DWD CRUD] 开始刷新店铺 {shop_id} 的广告周度报表: week={week_str or '当前+上一周'}"
        )

        # 构建聚合查询 - 完全按照用户提供的SQL逻辑
        # CONCAT('week', YEARWEEK(stat_date, 2)) 是 MySQL 的方式
        # 这里使用 SQLAlchemy func 构建等效逻辑
        week_expr = func.concat("week", func.yearweek(ODSWBAdvertStat.stat_date, 2))

        # 基础聚合查询
        agg_query = (
            select(
                week_expr.label("week"),
                ODSWBAdvertStat.advert_id,
                ODSWBAdvert.name.label("advert_name"),
                ODSWBAdvert.status.label("advert_status"),
                func.sum(ODSWBAdvertStat.views).label("paid_views"),
                func.sum(ODSWBAdvertStat.clicks).label("paid_clicks"),
                func.sum(ODSWBAdvertStat.atbs).label("atbs"),
                func.sum(ODSWBAdvertStat.orders).label("orders"),
                func.sum(ODSWBAdvertStat.sum_cost).label("sum_cost"),
                func.sum(ODSWBAdvertStat.sum_price).label("sum_price"),
            )
            .select_from(ODSWBAdvertStat)
            .outerjoin(
                ODSWBAdvert,
                (ODSWBAdvertStat.advert_id == ODSWBAdvert.advert_id)
                & (ODSWBAdvertStat.shop_id == ODSWBAdvert.shop_id),
            )
            .where(ODSWBAdvertStat.shop_id == shop_id)
            .group_by(
                week_expr,
                ODSWBAdvertStat.advert_id,
                ODSWBAdvert.name,
                ODSWBAdvert.status,
            )
        )

        # 如果指定了周，只聚合那一周的数据
        if week_str:
            agg_query = agg_query.having(week_expr == week_str)

        # 执行聚合查询
        result = await db.execute(agg_query)
        rows = result.all()

        if not rows:
            logger.info(f"[DWD CRUD] 店铺 {shop_id} 没有聚合数据，跳过刷新")
            return {"status": "success", "message": "No data to refresh", "count": 0}

        # 计算指标并准备 upsert 数据
        records = []
        weeks_to_clear = set()

        for row in rows:
            week = row.week
            weeks_to_clear.add(week)

            # 计算指标
            paid_views = row.paid_views or 0
            paid_clicks = row.paid_clicks or 0
            sum_cost = row.sum_cost or 0

            # 计算 CTR
            ctr = None
            if paid_views > 0:
                ctr = round((paid_clicks / paid_views) * 100, 4)

            # 计算 CPC
            cpc = None
            if paid_clicks > 0:
                cpc = round(sum_cost / paid_clicks, 4)

            # 计算 CR
            cr = None
            orders = row.orders or 0
            if paid_clicks > 0:
                cr = round((orders / paid_clicks) * 100, 4)

            # 活动状态标签
            status_label = None
            if row.advert_status is not None:
                if row.advert_status == 0:
                    status_label = "已暂停"
                elif row.advert_status == 1:
                    status_label = "进行中"
                else:
                    status_label = "其他"

            record = {
                "shop_id": shop_id,
                "week": week,
                "advert_id": row.advert_id,
                "advert_name": row.advert_name,
                "advert_status": row.advert_status,
                "advert_status_label": status_label,
                "paid_views": paid_views,
                "paid_clicks": paid_clicks,
                "atbs": row.atbs or 0,
                "orders": orders,
                "ctr": ctr,
                "cpc": cpc,
                "cr": cr,
                "sum_cost": sum_cost,
                "sum_price": row.sum_price,
            }
            records.append(record)

        if not records:
            return {
                "status": "success",
                "message": "No valid records to upsert",
                "count": 0,
            }

        # 删除旧数据
        if weeks_to_clear:
            delete_stmt = delete(DWDWBAdvertsReportDetail).where(
                (DWDWBAdvertsReportDetail.shop_id == shop_id)
                & (DWDWBAdvertsReportDetail.week.in_(weeks_to_clear))
            )
            await db.execute(delete_stmt)
            logger.debug(
                f"[DWD CRUD] 删除了店铺 {shop_id} 的旧数据: weeks={weeks_to_clear}"
            )

        # MySQL upsert
        stmt = insert(DWDWBAdvertsReportDetail).values(records)
        update_dict = {
            "advert_name": stmt.inserted.advert_name,
            "advert_status": stmt.inserted.advert_status,
            "advert_status_label": stmt.inserted.advert_status_label,
            "paid_views": stmt.inserted.paid_views,
            "paid_clicks": stmt.inserted.paid_clicks,
            "atbs": stmt.inserted.atbs,
            "orders": stmt.inserted.orders,
            "ctr": stmt.inserted.ctr,
            "cpc": stmt.inserted.cpc,
            "cr": stmt.inserted.cr,
            "sum_cost": stmt.inserted.sum_cost,
            "sum_price": stmt.inserted.sum_price,
        }
        upsert_stmt = stmt.on_duplicate_key_update(**update_dict)
        await db.execute(upsert_stmt)
        await db.commit()

        logger.info(
            f"[DWD CRUD] 刷新完成 - 店铺: {shop_id}, 记录数: {len(records)}, 周数: {len(weeks_to_clear)}"
        )
        return {
            "status": "success",
            "shop_id": shop_id,
            "weeks": list(weeks_to_clear),
            "count": len(records),
        }

    async def get_by_shop_and_week(
        self,
        db: AsyncSession,
        shop_id: int,
        week: str,
    ) -> List[DWDWBAdvertsReportDetail]:
        """查询指定店铺和周度的报表数据"""
        result = await db.execute(
            select(DWDWBAdvertsReportDetail)
            .where(
                (DWDWBAdvertsReportDetail.shop_id == shop_id)
                & (DWDWBAdvertsReportDetail.week == week)
            )
            .order_by(DWDWBAdvertsReportDetail.advert_id)
        )
        return list(result.scalars().all())

    async def get_paginated(
        self,
        db: AsyncSession,
        *,
        shop_id: Optional[int] = None,
        allowed_shop_ids: Optional[Sequence[int]] = None,
        week: Optional[str] = None,
        advert_id: Optional[int] = None,
        advert_status: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[DWDWBAdvertsReportDetail], int]:
        """
        分页查询广告周度报表

        Args:
            shop_id: 店铺ID过滤
            week: 周度过滤
            advert_id: 广告ID过滤
            advert_status: 广告状态过滤
            page: 页码
            page_size: 每页数量

        Returns:
            (数据列表, 总数)
        """
        # 构建where条件
        conditions = []
        if allowed_shop_ids is not None:
            if not allowed_shop_ids:
                return [], 0
            conditions.append(DWDWBAdvertsReportDetail.shop_id.in_(allowed_shop_ids))
        if shop_id is not None:
            conditions.append(DWDWBAdvertsReportDetail.shop_id == shop_id)
        if week is not None:
            conditions.append(DWDWBAdvertsReportDetail.week == week)
        if advert_id is not None:
            conditions.append(DWDWBAdvertsReportDetail.advert_id == advert_id)
        if advert_status is not None:
            conditions.append(DWDWBAdvertsReportDetail.advert_status == advert_status)

        # 查询总数
        count_query = select(func.count(DWDWBAdvertsReportDetail.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        # 查询分页数据
        query = select(DWDWBAdvertsReportDetail)
        if conditions:
            query = query.where(and_(*conditions))
        query = query.order_by(
            DWDWBAdvertsReportDetail.week.desc(), DWDWBAdvertsReportDetail.advert_id
        )
        # 分页
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_available_weeks(
        self,
        db: AsyncSession,
        shop_id: Optional[int] = None,
        allowed_shop_ids: Optional[Sequence[int]] = None,
    ) -> List[str]:
        """获取可用的周度列表"""
        query = select(DWDWBAdvertsReportDetail.week).distinct()
        if allowed_shop_ids is not None:
            if not allowed_shop_ids:
                return []
            query = query.where(DWDWBAdvertsReportDetail.shop_id.in_(allowed_shop_ids))
        if shop_id is not None:
            query = query.where(DWDWBAdvertsReportDetail.shop_id == shop_id)
        query = query.order_by(DWDWBAdvertsReportDetail.week.desc())

        result = await db.execute(query)
        return [row[0] for row in result.all()]


# CRUD 实例
crud_dwd_wb_adverts_report_detail = CRUDDWDWBAdvertsReportDetail(
    DWDWBAdvertsReportDetail
)
