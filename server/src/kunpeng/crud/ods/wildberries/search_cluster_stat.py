"""
ODS 层 - 搜索关键字统计 CRUD 操作
"""
import logging
from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.models.ods.wildberries.balance import ODSWBSearchClusterStat

logger = logging.getLogger(__name__)


class CRUDODSWBSearchClusterStat(CRUDBase[ODSWBSearchClusterStat, Dict[str, Any], Dict[str, Any]]):
    """ODS 搜索关键字统计数据 CRUD"""

    async def _get_existing(
        self,
        db: AsyncSession,
        shop_id: int,
        stat_date: date,
        advert_id: Optional[int],
        nm_id: int,
        norm_query: Optional[str],
    ) -> Optional[ODSWBSearchClusterStat]:
        """根据唯一索引获取现有记录（使用 first 避免 MultipleResultsFound）"""
        query = select(ODSWBSearchClusterStat).where(
            (ODSWBSearchClusterStat.shop_id == shop_id)
            & (ODSWBSearchClusterStat.stat_date == stat_date)
            & (ODSWBSearchClusterStat.nm_id == nm_id)
        )

        # 可选条件
        if advert_id is not None:
            query = query.where(ODSWBSearchClusterStat.advert_id == advert_id)
        else:
            query = query.where(ODSWBSearchClusterStat.advert_id.is_(None))

        if norm_query is not None:
            query = query.where(ODSWBSearchClusterStat.norm_query == norm_query)
        else:
            query = query.where(ODSWBSearchClusterStat.norm_query.is_(None))

        result = await db.execute(query)
        # 使用 first() 避免旧残留数据导致 MultipleResultsFound
        return result.scalars().first()

    async def create_many(
        self,
        db: AsyncSession,
        *,
        stats_data: List[Dict[str, Any]],
        shop_id: int,
    ) -> List[ODSWBSearchClusterStat]:
        """批量创建/更新 ODS 搜索关键字统计数据"""
        logger.debug(f"[ODS CRUD] 开始同步搜索关键字统计 - 店铺: {shop_id}, 数据量: {len(stats_data)}")

        result_list = []

        # 展平嵌套结构：v1 API 返回 {"advertId", "nmId", "stat": {"views", ...}}
        # 如果客户端没展平，在这里把 stat 字典合并到外层
        flat_stats = []
        for raw in stats_data:
            if not isinstance(raw, dict):
                continue
            stat_dict = raw.get("stat")
            advert_id = raw.get("advertId") or raw.get("advert_id")
            nm_id = raw.get("nmId") or raw.get("nm_id")

            if isinstance(stat_dict, dict) and len(stat_dict) > 0:
                # 把 stat 字典合并到外层（去掉 stat 嵌套）
                merged = dict(raw)
                merged.pop("stat", None)
                merged.update(stat_dict)
                # 确保 advertId/nmId 存在（优先使用外层的）
                if advert_id is not None:
                    merged["advertId"] = advert_id
                if nm_id is not None:
                    merged["nmId"] = nm_id
                flat_stats.append(merged)
            elif isinstance(stat_dict, list) and len(stat_dict) > 0:
                for ds in stat_dict:
                    if isinstance(ds, dict):
                        if advert_id is not None and "advertId" not in ds:
                            ds["advertId"] = advert_id
                        if nm_id is not None and "nmId" not in ds:
                            ds["nmId"] = nm_id
                        flat_stats.append(ds)
            else:
                flat_stats.append(raw)

        logger.debug(f"[ODS CRUD] 展平后数据量: {len(flat_stats)}")

        for idx, stat_data in enumerate(flat_stats):
            # 解析统计日期（v1 可能用 'date' 或 'dt'）
            stat_date_str = stat_data.get("date") or stat_data.get("dt") or stat_data.get("stat_date")
            stat_date = None
            if stat_date_str:
                try:
                    if isinstance(stat_date_str, str):
                        # 处理 ISO 格式和纯日期格式
                        clean = stat_date_str.strip()
                        if "T" in clean:
                            clean = clean[:10]
                        stat_date = date.fromisoformat(clean)
                    elif isinstance(stat_date_str, date):
                        stat_date = stat_date_str
                except Exception as e:
                    logger.debug(f"[ODS CRUD] 第{idx}条日期解析失败 '{stat_date_str}': {e}")

            if not stat_date:
                logger.debug(f"[ODS CRUD] 第{idx}条跳过: 无有效日期 (date/dt={stat_date_str}, keys={list(stat_data.keys())})")
                continue

            advert_id = stat_data.get("advertId") or stat_data.get("advert_id")
            nm_id = stat_data.get("nmId") or stat_data.get("nm_id")
            norm_query = stat_data.get("normQuery") or stat_data.get("norm_query")

            if not nm_id:
                logger.debug(f"[ODS CRUD] 第{idx}条跳过: 无 nmId (keys={list(stat_data.keys())})")
                continue

            # 调试：打印前3条的实际字段名
            if idx < 3:
                logger.debug(f"[ODS CRUD] 第{idx}条所有字段: {stat_data}")

            # 宽松的字段名映射：尝试多种可能的字段名
            def _get_val(data: dict, *keys):
                for k in keys:
                    if k in data and data[k] is not None:
                        return data[k]
                return None

            # 构建 ODS 记录数据
            ods_data = {
                "shop_id": shop_id,
                "row_data": stat_data,
                "stat_date": stat_date,
                "advert_id": advert_id,
                "nm_id": nm_id,
                "norm_query": norm_query,
                "views": _get_val(stat_data, "views", "view", "shows"),
                "clicks": _get_val(stat_data, "clicks", "click"),
                "sum_cost": _get_val(stat_data, "sum", "sumCost", "cost", "spend", "sum_cost"),
                "atbs": _get_val(stat_data, "atbs", "atb", "addToBaskets"),
                "orders": _get_val(stat_data, "orders", "order"),
                "cpc": _get_val(stat_data, "cpc", "cpcValue"),
                "ctr": _get_val(stat_data, "ctr", "ctrValue"),
                "cr": _get_val(stat_data, "cr", "crValue", "conversionRate"),
            }

            # 调试：检查提取结果
            if idx < 3:
                logger.debug(f"[ODS CRUD] 第{idx}条提取结果: views={ods_data['views']}, clicks={ods_data['clicks']}, sum_cost={ods_data['sum_cost']}, atbs={ods_data['atbs']}, orders={ods_data['orders']}")

            # 检查是否已存在
            existing = await self._get_existing(db, shop_id, stat_date, advert_id, nm_id, norm_query)

            if existing:
                # 更新现有记录
                for field, value in ods_data.items():
                    if hasattr(existing, field):
                        setattr(existing, field, value)
                result_list.append(existing)
            else:
                # 创建新记录
                ods_record = ODSWBSearchClusterStat(**ods_data)
                db.add(ods_record)
                result_list.append(ods_record)

        logger.debug(f"[ODS CRUD] 准备提交数据库 - 总记录: {len(result_list)}")
        await db.commit()
        logger.debug(f"[ODS CRUD] 数据库提交成功")
        for record in result_list:
            await db.refresh(record)
        logger.debug(f"[ODS CRUD] 搜索关键字统计同步完成 - 总计: {len(result_list)}")
        return result_list


# CRUD 实例
crud_ods_wb_search_cluster_stat = CRUDODSWBSearchClusterStat(ODSWBSearchClusterStat)
