"""
ODS 层 - 广告数据 CRUD 操作
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.models.ods.wildberries.adverts import ODSWBAdvert, ODSWBAdvertStat

logger = logging.getLogger(__name__)


class CRUDODSWBAdvert(CRUDBase[ODSWBAdvert, Dict[str, Any], Dict[str, Any]]):
    """ODS 广告活动数据 CRUD"""

    async def _get_existing(
        self, db: AsyncSession, shop_id: int, advert_id: int
    ) -> Optional[ODSWBAdvert]:
        """根据唯一索引获取现有记录"""
        result = await db.execute(
            select(ODSWBAdvert).where(
                (ODSWBAdvert.shop_id == shop_id) & (ODSWBAdvert.advert_id == advert_id)
            )
        )
        return result.scalar_one_or_none()

    async def create_many(
        self,
        db: AsyncSession,
        *,
        adverts_data: List[Dict[str, Any]],
        shop_id: int,
    ) -> List[ODSWBAdvert]:
        """批量创建/更新 ODS 广告活动数据（幂等同步）"""
        logger.debug(
            f"[ODS CRUD] 开始幂等同步广告数据 - 店铺: {shop_id}, 数据量: {len(adverts_data)}"
        )

        result_list = []

        for data in adverts_data:
            advert_id = data.get("id") or data.get("advertId")
            if not advert_id:
                logger.warning(f"[ODS CRUD] 广告数据缺少 advert_id, 跳过: {data}")
                continue

            # 解析时间字段
            def parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
                if not dt_str:
                    return None
                try:
                    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                except Exception:
                    return None

            # 提取嵌套数据
            settings = data.get("settings", {})
            placements = settings.get("placements", {})
            timestamps = data.get("timestamps", {})

            # 构建 ODS 记录数据
            ods_data = {
                "shop_id": shop_id,
                "row_data": data,
                "advert_id": advert_id,
                "name": settings.get("name"),
                "status": data.get("status"),
                "bid_type": data.get("bid_type"),
                "currency": data.get("currency"),
                "payment_type": settings.get("payment_type"),
                "placement_search": placements.get("search"),
                "placement_recommendations": placements.get("recommendations"),
                "started_at": parse_datetime(timestamps.get("started")),
                "deleted_at": parse_datetime(timestamps.get("deleted")),
            }

            # 检查是否已存在
            existing = await self._get_existing(db, shop_id, advert_id)

            if existing:
                # 更新现有记录
                for field, value in ods_data.items():
                    if hasattr(existing, field):
                        setattr(existing, field, value)
                result_list.append(existing)
            else:
                # 创建新记录
                ods_record = ODSWBAdvert(**ods_data)
                db.add(ods_record)
                result_list.append(ods_record)

        logger.debug(f"[ODS CRUD] 准备提交数据库 - 总记录: {len(result_list)}")
        await db.commit()
        logger.debug(f"[ODS CRUD] 数据库提交成功")
        for record in result_list:
            await db.refresh(record)
        logger.debug(f"[ODS CRUD] 幂等同步完成 - 总计: {len(result_list)}")
        return result_list


class CRUDODSWBAdvertStat(CRUDBase[ODSWBAdvertStat, Dict[str, Any], Dict[str, Any]]):
    """ODS 广告统计数据 CRUD"""

    async def _get_existing(
        self,
        db: AsyncSession,
        shop_id: int,
        advert_id: Optional[int],
        stat_date: date,
        nm_id: Optional[int],
        app_type: Optional[str],
    ) -> Optional[ODSWBAdvertStat]:
        """根据唯一索引获取现有记录"""
        if not advert_id or not stat_date:
            return None

        # 构建查询条件
        conditions = [
            ODSWBAdvertStat.shop_id == shop_id,
            ODSWBAdvertStat.advert_id == advert_id,
            ODSWBAdvertStat.stat_date == stat_date,
        ]

        # nm_id 条件：如果为 None，则匹配数据库中的 NULL；否则匹配具体值
        if nm_id is None:
            conditions.append(ODSWBAdvertStat.nm_id.is_(None))
        else:
            conditions.append(ODSWBAdvertStat.nm_id == nm_id)

        # app_type 条件：如果为 None，则匹配数据库中的 NULL；否则匹配具体值
        if app_type is None:
            conditions.append(ODSWBAdvertStat.app_type.is_(None))
        else:
            conditions.append(ODSWBAdvertStat.app_type == app_type)

        result = await db.execute(select(ODSWBAdvertStat).where(*conditions))
        # 使用 one_or_none 而不是 scalar_one_or_none 来避免多行错误
        rows = result.all()
        if len(rows) == 0:
            return None
        elif len(rows) == 1:
            return rows[0][0]
        else:
            logger.warning(
                f"[ODS CRUD] 找到多条记录，返回第一条: shop_id={shop_id}, advert_id={advert_id}, stat_date={stat_date}, nm_id={nm_id}, app_type={app_type}"
            )
            return rows[0][0]

    async def create_many(
        self,
        db: AsyncSession,
        *,
        stats_data: List[Dict[str, Any]],
        shop_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[ODSWBAdvertStat]:
        """批量创建/更新 ODS 广告统计数据（商品维度） - 处理 days->apps->nms 字段"""
        logger.debug(
            f"[ODS CRUD] 开始幂等同步广告统计数据（商品维度） - 店铺: {shop_id}"
        )

        result_list = []
        # 批内去重：同批 days->apps->nms 展开后可能出现重复
        # (advert_id, stat_date, nm_id, app_type)，DB 查不到会重复新增触发唯一键
        # 冲突(1062)。用 seen 缓存本批已处理键，命中则就地更新。
        seen: Dict[Any, ODSWBAdvertStat] = {}

        # Process each advert's stats
        for advert_stat in stats_data:
            advert_id = advert_stat.get("advertId") or advert_stat.get("advert_id")
            currency = advert_stat.get("currency")

            # Extract days array - this has the daily data
            days = advert_stat.get("days", [])

            for day_data in days:
                # Parse date - it can be "YYYY-MM-DD" or "YYYY-MM-DDTHH:MM:SSZ"
                stat_date_str = day_data.get("date")
                stat_date = None
                if stat_date_str:
                    try:
                        # Try to parse just the date part
                        if "T" in stat_date_str:
                            stat_date = date.fromisoformat(stat_date_str[:10])
                        else:
                            stat_date = date.fromisoformat(stat_date_str)
                    except Exception:
                        pass

                if not stat_date:
                    continue

                # First try to extract nms data from apps->nms
                apps = day_data.get("apps", [])
                has_nms_data = False

                if apps:
                    for app in apps:
                        app_type = app.get("appType") or app.get("app_type")
                        nms = app.get("nms", [])
                        for nm_data in nms:
                            nm_id = nm_data.get("nmId")
                            if not nm_id:
                                continue

                            has_nms_data = True

                            # Build ODS record data from nm data
                            ods_data = {
                                "shop_id": shop_id,
                                "row_data": nm_data,
                                "advert_id": advert_id,
                                "stat_date": stat_date,
                                "nm_id": nm_id,
                                "nm_name": nm_data.get("name"),
                                "app_type": app_type,
                                # Core stats
                                "views": nm_data.get("views"),
                                "clicks": nm_data.get("clicks"),
                                "atbs": nm_data.get("atbs"),
                                "orders": nm_data.get("orders"),
                                "canceled": nm_data.get("canceled"),
                                "shks": nm_data.get("shks"),
                                # Money
                                "sum_cost": nm_data.get("sum"),
                                "sum_price": nm_data.get("sum_price"),
                                # Metrics
                                "cpc": nm_data.get("cpc"),
                                "ctr": nm_data.get("ctr"),
                                "cr": nm_data.get("cr"),
                                "currency": currency,
                            }

                            batch_key = (advert_id, stat_date, nm_id, app_type)
                            if batch_key in seen:
                                # 同批已处理该键，就地更新，避免重复新增
                                existing_in_batch = seen[batch_key]
                                for field, value in ods_data.items():
                                    if hasattr(existing_in_batch, field):
                                        setattr(existing_in_batch, field, value)
                                continue

                            # Check if exists
                            existing = await self._get_existing(
                                db, shop_id, advert_id, stat_date, nm_id, app_type
                            )

                            if existing:
                                # Update existing
                                for field, value in ods_data.items():
                                    if hasattr(existing, field):
                                        setattr(existing, field, value)
                                result_list.append(existing)
                                seen[batch_key] = existing
                            else:
                                # Create new
                                ods_record = ODSWBAdvertStat(**ods_data)
                                db.add(ods_record)
                                result_list.append(ods_record)
                                seen[batch_key] = ods_record

                # If no nms data, fall back to day level data (for backward compatibility)
                if not has_nms_data:
                    # Build ODS record data from day data
                    ods_data = {
                        "shop_id": shop_id,
                        "row_data": day_data,
                        "advert_id": advert_id,
                        "stat_date": stat_date,
                        "nm_id": None,
                        "nm_name": None,
                        "app_type": None,
                        # Core stats
                        "views": day_data.get("views"),
                        "clicks": day_data.get("clicks"),
                        "atbs": day_data.get("atbs"),
                        "orders": day_data.get("orders"),
                        "canceled": day_data.get("canceled"),
                        "shks": day_data.get("shks"),
                        # Money
                        "sum_cost": day_data.get("sum"),
                        "sum_price": day_data.get("sum_price"),
                        # Metrics
                        "cpc": day_data.get("cpc"),
                        "ctr": day_data.get("ctr"),
                        "cr": day_data.get("cr"),
                        "currency": currency,
                    }

                    batch_key = (advert_id, stat_date, None, None)
                    if batch_key in seen:
                        existing_in_batch = seen[batch_key]
                        for field, value in ods_data.items():
                            if hasattr(existing_in_batch, field):
                                setattr(existing_in_batch, field, value)
                        continue

                    # Check if exists
                    existing = await self._get_existing(
                        db, shop_id, advert_id, stat_date, None, None
                    )

                    if existing:
                        # Update existing
                        for field, value in ods_data.items():
                            if hasattr(existing, field):
                                setattr(existing, field, value)
                        result_list.append(existing)
                        seen[batch_key] = existing
                    else:
                        # Create new
                        ods_record = ODSWBAdvertStat(**ods_data)
                        db.add(ods_record)
                        result_list.append(ods_record)
                        seen[batch_key] = ods_record

        logger.debug(f"[ODS CRUD] 准备提交数据库 - 总记录: {len(result_list)}")
        await db.commit()
        logger.debug(f"[ODS CRUD] 数据库提交成功")
        for record in result_list:
            await db.refresh(record)
        logger.debug(f"[ODS CRUD] 幂等同步完成 - 总计: {len(result_list)}")
        return result_list


# CRUD 实例
crud_ods_wb_advert = CRUDODSWBAdvert(ODSWBAdvert)
crud_ods_wb_advert_stat = CRUDODSWBAdvertStat(ODSWBAdvertStat)
