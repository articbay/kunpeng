"""
ODS 层 - Wildberries 广告增强数据 CRUD 操作
包含8个新API端点对应的CRUD
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.models.ods.wildberries.adv_enhanced import (
    ODSWBNormQueryBid,
    ODSWBNormQueryMinus,
    ODSWBNormQueryList,
    ODSWBNormQueryStat,
    ODSWBPromotionCount,
    ODSWBBidRecommendation,
    ODSWBAdvertFullStat,
    ODSWBAdvertV2,
)

logger = logging.getLogger(__name__)


def _first_not_none(*values: Any) -> Any:
    """返回首个非 None 值，保留数值 0 和布尔 False。"""
    for value in values:
        if value is not None:
            return value
    return None


def _safe_parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    """安全解析日期时间"""
    if not dt_str:
        return None
    try:
        if isinstance(dt_str, datetime):
            return dt_str
        if isinstance(dt_str, str):
            if dt_str.endswith('Z'):
                dt_str = dt_str.replace('Z', '+00:00')
            return datetime.fromisoformat(dt_str)
    except Exception:
        pass
    return None


def _safe_parse_date(d_str: Optional[str]) -> Optional[date]:
    """安全解析日期"""
    if not d_str:
        return None
    try:
        if isinstance(d_str, date):
            return d_str
        if isinstance(d_str, str):
            if 'T' in d_str:
                d_str = d_str[:10]
            return date.fromisoformat(d_str)
    except Exception:
        pass
    return None


class CRUDODSWBNormQueryBid(CRUDBase[ODSWBNormQueryBid, Dict[str, Any], Dict[str, Any]]):
    """ODS 标准查询竞价 CRUD"""

    async def _get_existing(
        self,
        db: AsyncSession,
        shop_id: int,
        advert_id: Optional[int],
        nm_id: Optional[int],
        norm_query: Optional[str],
    ) -> Optional[ODSWBNormQueryBid]:
        """根据唯一索引获取现有记录"""
        result = await db.execute(
            select(ODSWBNormQueryBid).where(
                (ODSWBNormQueryBid.shop_id == shop_id)
                & (ODSWBNormQueryBid.advert_id == advert_id)
                & (ODSWBNormQueryBid.nm_id == nm_id)
                & (ODSWBNormQueryBid.norm_query == norm_query)
            )
        )
        return result.scalar_one_or_none()

    async def upsert_many(
        self,
        db: AsyncSession,
        *,
        bids_data: List[Dict[str, Any]],
        shop_id: int,
        advert_id: Optional[int] = None,
        nm_id: Optional[int] = None,
    ) -> List[ODSWBNormQueryBid]:
        """批量创建/更新标准查询竞价数据"""
        logger.debug(f"[ODS CRUD] 开始同步标准查询竞价 - 店铺: {shop_id}, 数据量: {len(bids_data)}")

        result_list = []
        seen = set()

        for data in bids_data:
            # 提取关键字段
            data_advert_id = data.get("advertId") or data.get("advert_id") or advert_id
            data_nm_id = data.get("nmId") or data.get("nm_id") or nm_id
            data_norm_query = data.get("normQuery") or data.get("norm_query") or data.get("query", "")

            if not data_advert_id or not data_norm_query:
                continue

            key = (data_advert_id, data_nm_id, data_norm_query)
            if key in seen:
                continue
            seen.add(key)

            # 构建ODS数据
            ods_data = {
                "shop_id": shop_id,
                "row_data": data,
                "advert_id": data_advert_id,
                "nm_id": data_nm_id,
                "norm_query": data_norm_query,
                "bid": data.get("bid"),
                "cpm": data.get("cpm"),
                "priority": data.get("priority"),
            }

            # 检查是否已存在
            existing = await self._get_existing(db, shop_id, data_advert_id, data_nm_id, data_norm_query)

            if existing:
                for field, value in ods_data.items():
                    if hasattr(existing, field):
                        setattr(existing, field, value)
                result_list.append(existing)
            else:
                ods_record = ODSWBNormQueryBid(**ods_data)
                db.add(ods_record)
                result_list.append(ods_record)

        if result_list:
            await db.commit()
            for record in result_list:
                await db.refresh(record)

        logger.debug(f"[ODS CRUD] 标准查询竞价同步完成 - 总计: {len(result_list)}")
        return result_list


class CRUDODSWBNormQueryMinus(CRUDBase[ODSWBNormQueryMinus, Dict[str, Any], Dict[str, Any]]):
    """ODS 排除关键词 CRUD"""

    async def _get_existing(
        self,
        db: AsyncSession,
        shop_id: int,
        advert_id: Optional[int],
        nm_id: Optional[int],
        minus_word: Optional[str],
    ) -> Optional[ODSWBNormQueryMinus]:
        """根据唯一索引获取现有记录"""
        result = await db.execute(
            select(ODSWBNormQueryMinus).where(
                (ODSWBNormQueryMinus.shop_id == shop_id)
                & (ODSWBNormQueryMinus.advert_id == advert_id)
                & (ODSWBNormQueryMinus.nm_id == nm_id)
                & (ODSWBNormQueryMinus.minus_word == minus_word)
            )
        )
        return result.scalar_one_or_none()

    async def upsert_many(
        self,
        db: AsyncSession,
        *,
        minus_data: List[Dict[str, Any]],
        shop_id: int,
        advert_id: Optional[int] = None,
        nm_id: Optional[int] = None,
    ) -> List[ODSWBNormQueryMinus]:
        """批量创建/更新排除关键词数据"""
        logger.debug(f"[ODS CRUD] 开始同步排除关键词 - 店铺: {shop_id}, 数据量: {len(minus_data)}")

        result_list = []
        seen = set()

        for data in minus_data:
            # 处理新API格式：{advert_id, nm_id, norm_queries: ["word1", "word2", ...]}
            data_advert_id = data.get("advertId") or data.get("advert_id") or advert_id
            data_nm_id = data.get("nmId") or data.get("nm_id") or nm_id
            norm_queries = data.get("normQueries") or data.get("norm_queries") or []

            # 如果是单个词的格式，也支持
            if not norm_queries and (data.get("minusWord") or data.get("minus_word") or data.get("word")):
                word = data.get("minusWord") or data.get("minus_word") or data.get("word", "")
                norm_queries = [word]

            # 遍历每个排除词
            for word in norm_queries:
                if not word or not isinstance(word, str):
                    continue

                key = (data_advert_id, data_nm_id, word)
                if key in seen:
                    continue
                seen.add(key)

                ods_data = {
                    "shop_id": shop_id,
                    "row_data": data,
                    "advert_id": data_advert_id,
                    "nm_id": data_nm_id,
                    "minus_word": word,
                }

                existing = await self._get_existing(db, shop_id, data_advert_id, data_nm_id, word)

                if existing:
                    for field, value in ods_data.items():
                        if hasattr(existing, field):
                            setattr(existing, field, value)
                    result_list.append(existing)
                else:
                    ods_record = ODSWBNormQueryMinus(**ods_data)
                    db.add(ods_record)
                    result_list.append(ods_record)

        if result_list:
            await db.commit()
            for record in result_list:
                await db.refresh(record)

        logger.debug(f"[ODS CRUD] 排除关键词同步完成 - 总计: {len(result_list)}")
        return result_list


class CRUDODSWBNormQueryList(CRUDBase[ODSWBNormQueryList, Dict[str, Any], Dict[str, Any]]):
    """ODS 标准查询列表 CRUD"""

    async def _get_existing(
        self,
        db: AsyncSession,
        shop_id: int,
        advert_id: Optional[int],
        nm_id: Optional[int],
        norm_query: Optional[str],
    ) -> Optional[ODSWBNormQueryList]:
        """根据唯一索引获取现有记录"""
        result = await db.execute(
            select(ODSWBNormQueryList).where(
                (ODSWBNormQueryList.shop_id == shop_id)
                & (ODSWBNormQueryList.advert_id == advert_id)
                & (ODSWBNormQueryList.nm_id == nm_id)
                & (ODSWBNormQueryList.norm_query == norm_query)
            )
        )
        return result.scalar_one_or_none()

    async def upsert_many(
        self,
        db: AsyncSession,
        *,
        list_data: List[Dict[str, Any]],
        shop_id: int,
        advert_id: Optional[int] = None,
        nm_id: Optional[int] = None,
    ) -> List[ODSWBNormQueryList]:
        """批量创建/更新标准查询列表数据"""
        logger.debug(f"[ODS CRUD] 开始同步标准查询列表 - 店铺: {shop_id}, 数据量: {len(list_data)}")

        result_list = []
        seen = set()

        for data in list_data:
            data_advert_id = data.get("advertId") or data.get("advert_id") or advert_id
            data_nm_id = data.get("nmId") or data.get("nm_id") or nm_id

            # 处理新API格式：normQueries: {active: [...], excluded: [...], archived: [...]}
            norm_queries = data.get("normQueries") or data.get("norm_queries") or {}
            if isinstance(norm_queries, dict):
                # 遍历所有状态的查询
                for status_name, queries in norm_queries.items():
                    if not isinstance(queries, list):
                        continue
                    for query_item in queries:
                        # query_item 可能是字符串或对象
                        if isinstance(query_item, str):
                            data_norm_query = query_item
                            is_active = (status_name == "active")
                        else:
                            data_norm_query = query_item.get("normQuery") or query_item.get("norm_query") or query_item.get("query", "")
                            is_active = _first_not_none(
                                query_item.get("isActive"),
                                query_item.get("is_active"),
                                status_name == "active",
                            )

                        if not data_norm_query:
                            continue

                        key = (data_advert_id, data_nm_id, data_norm_query)
                        if key in seen:
                            continue
                        seen.add(key)

                        ods_data = {
                            "shop_id": shop_id,
                            "row_data": data,
                            "advert_id": data_advert_id,
                            "nm_id": data_nm_id,
                            "norm_query": data_norm_query,
                            "is_active": is_active,
                            "created_at": _safe_parse_datetime(query_item.get("createdAt") or query_item.get("created_at")) if isinstance(query_item, dict) else None,
                        }

                        existing = await self._get_existing(db, shop_id, data_advert_id, data_nm_id, data_norm_query)

                        if existing:
                            for field, value in ods_data.items():
                                if hasattr(existing, field):
                                    setattr(existing, field, value)
                            result_list.append(existing)
                        else:
                            ods_record = ODSWBNormQueryList(**ods_data)
                            db.add(ods_record)
                            result_list.append(ods_record)
            else:
                # 旧格式：直接是查询列表
                data_norm_query = data.get("normQuery") or data.get("norm_query") or data.get("query", "")

                if not data_advert_id or not data_norm_query:
                    continue

                key = (data_advert_id, data_nm_id, data_norm_query)
                if key in seen:
                    continue
                seen.add(key)

                ods_data = {
                    "shop_id": shop_id,
                    "row_data": data,
                    "advert_id": data_advert_id,
                    "nm_id": data_nm_id,
                    "norm_query": data_norm_query,
                    "is_active": _first_not_none(
                        data.get("isActive"), data.get("is_active")
                    ),
                    "created_at": _safe_parse_datetime(data.get("createdAt") or data.get("created_at")),
                }

                existing = await self._get_existing(db, shop_id, data_advert_id, data_nm_id, data_norm_query)

                if existing:
                    for field, value in ods_data.items():
                        if hasattr(existing, field):
                            setattr(existing, field, value)
                    result_list.append(existing)
                else:
                    ods_record = ODSWBNormQueryList(**ods_data)
                    db.add(ods_record)
                    result_list.append(ods_record)

        if result_list:
            await db.commit()
            for record in result_list:
                await db.refresh(record)

        logger.debug(f"[ODS CRUD] 标准查询列表同步完成 - 总计: {len(result_list)}")
        return result_list


class CRUDODSWBNormQueryStat(CRUDBase[ODSWBNormQueryStat, Dict[str, Any], Dict[str, Any]]):
    """ODS 标准查询统计 CRUD"""

    async def _get_existing(
        self,
        db: AsyncSession,
        shop_id: int,
        advert_id: Optional[int],
        nm_id: Optional[int],
        norm_query: Optional[str],
        stat_date: Optional[date],
    ) -> Optional[ODSWBNormQueryStat]:
        """根据唯一索引获取现有记录"""
        result = await db.execute(
            select(ODSWBNormQueryStat).where(
                (ODSWBNormQueryStat.shop_id == shop_id)
                & (ODSWBNormQueryStat.advert_id == advert_id)
                & (ODSWBNormQueryStat.nm_id == nm_id)
                & (ODSWBNormQueryStat.norm_query == norm_query)
                & (ODSWBNormQueryStat.stat_date == stat_date)
            )
        )
        return result.scalar_one_or_none()

    async def upsert_many(
        self,
        db: AsyncSession,
        *,
        stats_data: List[Dict[str, Any]],
        shop_id: int,
        date_from: Optional[date] = None,
    ) -> List[ODSWBNormQueryStat]:
        """批量创建/更新标准查询统计数据"""
        logger.debug(f"[ODS CRUD] 开始同步标准查询统计 - 店铺: {shop_id}, 数据量: {len(stats_data)}")

        result_list = []
        seen = set()

        for data in stats_data:
            # 支持多种数据结构
            data_advert_id = data.get("advertId") or data.get("advert_id")
            data_nm_id = data.get("nmId") or data.get("nm_id")
            # 处理统计数据 - 可能在stat字段中
            stat_dict = data.get("stat", {}) if isinstance(data.get("stat"), dict) else data
            data_norm_query = (
                data.get("normQuery")
                or data.get("norm_query")
                or data.get("query")
                or stat_dict.get("normQuery")
                or stat_dict.get("norm_query")
                or stat_dict.get("query", "")
            )

            data_stat_date = _safe_parse_date(
                data.get("date") or data.get("statDate") or stat_dict.get("date")
            )
            if not data_stat_date and date_from:
                data_stat_date = date_from

            if not data_advert_id or not data_stat_date:
                continue

            key = (data_advert_id, data_nm_id, data_norm_query, data_stat_date)
            if key in seen:
                continue
            seen.add(key)

            ods_data = {
                "shop_id": shop_id,
                "row_data": data,
                "advert_id": data_advert_id,
                "nm_id": data_nm_id,
                "norm_query": data_norm_query,
                "stat_date": data_stat_date,
                "views": _first_not_none(
                    stat_dict.get("views"), data.get("views")
                ),
                "clicks": _first_not_none(
                    stat_dict.get("clicks"), data.get("clicks")
                ),
                "atbs": _first_not_none(stat_dict.get("atbs"), data.get("atbs")),
                "orders": _first_not_none(
                    stat_dict.get("orders"), data.get("orders")
                ),
                "sum_cost": _first_not_none(
                    stat_dict.get("sum"),
                    stat_dict.get("sumCost"),
                    stat_dict.get("spend"),
                    data.get("sum"),
                    data.get("sum_cost"),
                    data.get("spend"),
                ),
                "cpc": _first_not_none(stat_dict.get("cpc"), data.get("cpc")),
                "ctr": _first_not_none(stat_dict.get("ctr"), data.get("ctr")),
                "cr": _first_not_none(stat_dict.get("cr"), data.get("cr")),
            }

            existing = await self._get_existing(db, shop_id, data_advert_id, data_nm_id, data_norm_query, data_stat_date)

            if existing:
                for field, value in ods_data.items():
                    if hasattr(existing, field):
                        setattr(existing, field, value)
                result_list.append(existing)
            else:
                ods_record = ODSWBNormQueryStat(**ods_data)
                db.add(ods_record)
                result_list.append(ods_record)

        if result_list:
            await db.commit()
            for record in result_list:
                await db.refresh(record)

        logger.debug(f"[ODS CRUD] 标准查询统计同步完成 - 总计: {len(result_list)}")
        return result_list


class CRUDODSWBPromotionCount(CRUDBase[ODSWBPromotionCount, Dict[str, Any], Dict[str, Any]]):
    """ODS 促销计数 CRUD"""

    async def _get_existing(
        self,
        db: AsyncSession,
        shop_id: int,
        advert_id: Optional[int],
        nm_id: Optional[int],
        promotion_type: Optional[str],
    ) -> Optional[ODSWBPromotionCount]:
        """根据唯一索引获取现有记录"""
        result = await db.execute(
            select(ODSWBPromotionCount).where(
                (ODSWBPromotionCount.shop_id == shop_id)
                & (ODSWBPromotionCount.advert_id == advert_id)
                & (ODSWBPromotionCount.nm_id == nm_id)
                & (ODSWBPromotionCount.promotion_type == promotion_type)
            )
        )
        return result.scalar_one_or_none()

    async def upsert_many(
        self,
        db: AsyncSession,
        *,
        promotion_data: List[Dict[str, Any]],
        shop_id: int,
        advert_id: Optional[int] = None,
    ) -> List[ODSWBPromotionCount]:
        """批量创建/更新促销计数数据"""
        logger.debug(f"[ODS CRUD] 开始同步促销计数 - 店铺: {shop_id}, 数据量: {len(promotion_data)}")

        result_list = []
        seen = set()

        for data in promotion_data:
            data_advert_id = data.get("advertId") or data.get("advert_id") or advert_id
            data_nm_id = data.get("nmId") or data.get("nm_id")
            data_promotion_type = data.get("promotionType") or data.get("promotion_type") or data.get("type", "")

            key = (data_advert_id, data_nm_id, data_promotion_type)
            if key in seen:
                continue
            seen.add(key)

            ods_data = {
                "shop_id": shop_id,
                "row_data": data,
                "advert_id": data_advert_id,
                "nm_id": data_nm_id,
                "promotion_type": data_promotion_type,
                "active_count": data.get("activeCount") or data.get("active_count"),
                "total_count": data.get("totalCount") or data.get("total_count"),
                "pending_count": data.get("pendingCount") or data.get("pending_count"),
            }

            existing = await self._get_existing(db, shop_id, data_advert_id, data_nm_id, data_promotion_type)

            if existing:
                for field, value in ods_data.items():
                    if hasattr(existing, field):
                        setattr(existing, field, value)
                result_list.append(existing)
            else:
                ods_record = ODSWBPromotionCount(**ods_data)
                db.add(ods_record)
                result_list.append(ods_record)

        if result_list:
            await db.commit()
            for record in result_list:
                await db.refresh(record)

        logger.debug(f"[ODS CRUD] 促销计数同步完成 - 总计: {len(result_list)}")
        return result_list


class CRUDODSWBBidRecommendation(CRUDBase[ODSWBBidRecommendation, Dict[str, Any], Dict[str, Any]]):
    """ODS 竞价推荐 CRUD"""

    async def _get_existing(
        self,
        db: AsyncSession,
        shop_id: int,
        advert_id: Optional[int],
        nm_id: Optional[int],
        subject_id: Optional[int],
        norm_query: Optional[str],
        record_type: Optional[str] = None,
    ) -> Optional[ODSWBBidRecommendation]:
        """根据唯一索引获取现有记录"""
        # 构建查询条件 - 考虑 subject_id 可能为 NULL 的情况
        query = select(ODSWBBidRecommendation).where(
            (ODSWBBidRecommendation.shop_id == shop_id)
            & (ODSWBBidRecommendation.advert_id == advert_id)
            & (ODSWBBidRecommendation.nm_id == nm_id)
            & (ODSWBBidRecommendation.norm_query == norm_query)
            & (ODSWBBidRecommendation.record_type == record_type)
        )

        # 单独处理 subject_id 的 NULL 情况
        if subject_id is None:
            query = query.where(ODSWBBidRecommendation.subject_id.is_(None))
        else:
            query = query.where(ODSWBBidRecommendation.subject_id == subject_id)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def upsert_many(
        self,
        db: AsyncSession,
        *,
        recommendations_data: List[Dict[str, Any]],
        shop_id: int,
        advert_id: Optional[int] = None,
        nm_id: Optional[int] = None,
        full_response: Optional[Dict[str, Any]] = None,
    ) -> List[ODSWBBidRecommendation]:
        """批量创建/更新竞价推荐数据 - 一行存一个查询词，三列存reach数据
        处理两种 API 格式：
        新格式:
        - base: {competitiveBid, leadersBid, top2}
        - normQueries: [{normQuery, reachMax:{bidKopecks}, reachMedium:{bidKopecks}, reachMin:{bidKopecks}}]
        旧格式:
        - levels: {range1To2, range3To10, range11To34, ...}
        """
        logger.debug(f"[ODS CRUD] 开始同步竞价推荐 - 店铺: {shop_id}, 数据量: {len(recommendations_data)}")
        logger.debug(f"[ODS CRUD] 输入数据预览: {recommendations_data[:2] if recommendations_data else '空'}")

        # 检测是否是旧格式（levels）
        if full_response and isinstance(full_response, dict):
            levels_data = full_response.get("levels")
            if levels_data and isinstance(levels_data, dict):
                # 旧格式，直接保存到 row_data，不做展开
                logger.debug(f"[ODS CRUD] 检测到旧格式 levels 数据: {list(levels_data.keys())}")
                # 对于旧格式，我们只保存一条记录，数据在 row_data 中
                return await self._save_old_format(db, full_response, shop_id, advert_id, nm_id)

        # 新格式处理继续...
        # 第一步：在内存中展开所有数据
        all_ods_data = []
        seen = set()

        # ========== 1. 先处理 base 数据（一条记录存所有 base 数据） ==========
        if full_response and isinstance(full_response, dict):
            base_data = full_response.get("base", {})
            if base_data and isinstance(base_data, dict):
                logger.debug(f"[ODS CRUD] 处理 base 数据: {list(base_data.keys())}")

                # 提取三个 base 字段
                competitive_bid_kopecks = None
                competitive_bid = None
                leaders_bid_kopecks = None
                leaders_bid = None
                top2_bid_kopecks = None
                top2_bid = None

                competitive_data = base_data.get("competitiveBid", {})
                if competitive_data:
                    competitive_bid_kopecks = competitive_data.get("bidKopecks")
                    if competitive_bid_kopecks is not None:
                        competitive_bid = competitive_bid_kopecks / 100

                leaders_data = base_data.get("leadersBid", {})
                if leaders_data:
                    leaders_bid_kopecks = leaders_data.get("bidKopecks")
                    if leaders_bid_kopecks is not None:
                        leaders_bid = leaders_bid_kopecks / 100

                top2_data = base_data.get("top2", {})
                if top2_data:
                    top2_bid_kopecks = top2_data.get("bidKopecks")
                    if top2_bid_kopecks is not None:
                        top2_bid = top2_bid_kopecks / 100

                # 只有至少有一个数据时才保存
                if competitive_bid_kopecks is not None or leaders_bid_kopecks is not None or top2_bid_kopecks is not None:
                    base_norm_query = "__base__"
                    key = (advert_id, nm_id, base_norm_query, "base")
                    if key not in seen:
                        seen.add(key)
                        all_ods_data.append({
                            "shop_id": shop_id,
                            "row_data": full_response,
                            "advert_id": advert_id,
                            "nm_id": nm_id,
                            "subject_id": None,
                            "norm_query": base_norm_query,
                            "record_type": "base",
                            "base_competitive_bid_kopecks": competitive_bid_kopecks,
                            "base_competitive_bid": competitive_bid,
                            "base_leaders_bid_kopecks": leaders_bid_kopecks,
                            "base_leaders_bid": leaders_bid,
                            "base_top2_bid_kopecks": top2_bid_kopecks,
                            "base_top2_bid": top2_bid,
                        })

                logger.debug(f"[ODS CRUD] 从 base 数据得到 1 条记录")

        # ========== 2. 再处理 normQueries 数据（一行存一个查询词的三个 reach 值） ==========
        for norm_query_item in recommendations_data:
            if not isinstance(norm_query_item, dict):
                continue

            # 提取查询词
            norm_query = norm_query_item.get("normQuery") or norm_query_item.get("norm_query", "")
            if not norm_query:
                continue

            # 处理subject_id
            subject_id = norm_query_item.get("subjectId") or norm_query_item.get("subject_id")

            # 提取三个 reach 值
            reach_max_bid_kopecks = None
            reach_max_bid = None
            reach_medium_bid_kopecks = None
            reach_medium_bid = None
            reach_min_bid_kopecks = None
            reach_min_bid = None

            reach_max_data = norm_query_item.get("reachMax", {})
            if reach_max_data:
                reach_max_bid_kopecks = reach_max_data.get("bidKopecks")
                if reach_max_bid_kopecks is not None:
                    reach_max_bid = reach_max_bid_kopecks / 100

            reach_medium_data = norm_query_item.get("reachMedium", {})
            if reach_medium_data:
                reach_medium_bid_kopecks = reach_medium_data.get("bidKopecks")
                if reach_medium_bid_kopecks is not None:
                    reach_medium_bid = reach_medium_bid_kopecks / 100

            reach_min_data = norm_query_item.get("reachMin", {})
            if reach_min_data:
                reach_min_bid_kopecks = reach_min_data.get("bidKopecks")
                if reach_min_bid_kopecks is not None:
                    reach_min_bid = reach_min_bid_kopecks / 100

            # 去重
            key = (advert_id, nm_id, norm_query, "query")
            if key in seen:
                continue
            seen.add(key)

            # 构建ODS数据
            all_ods_data.append({
                "shop_id": shop_id,
                "row_data": norm_query_item,
                "advert_id": advert_id,
                "nm_id": nm_id,
                "subject_id": subject_id,
                "norm_query": norm_query,
                "record_type": "query",
                "reach_max_bid_kopecks": reach_max_bid_kopecks,
                "reach_max_bid": reach_max_bid,
                "reach_medium_bid_kopecks": reach_medium_bid_kopecks,
                "reach_medium_bid": reach_medium_bid,
                "reach_min_bid_kopecks": reach_min_bid_kopecks,
                "reach_min_bid": reach_min_bid,
            })

        logger.debug(f"[ODS CRUD] 从 normQueries 得到 {len([d for d in all_ods_data if d['record_type'] == 'query'])} 条记录")
        logger.debug(f"[ODS CRUD] 最终待处理记录数: {len(all_ods_data)}")

        # 第二步：分批处理并提交
        return await self._process_batch(db, all_ods_data)

    async def _save_old_format(
        self,
        db: AsyncSession,
        full_response: Dict[str, Any],
        shop_id: int,
        advert_id: Optional[int],
        nm_id: Optional[int],
    ) -> List[ODSWBBidRecommendation]:
        """保存旧格式 (levels) 数据 - 只保存一条记录到 row_data"""
        result_list = []
        norm_query = "__levels__"
        record_type = "levels"

        existing = await self._get_existing(db, shop_id, advert_id, nm_id, None, norm_query, record_type)

        ods_data = {
            "shop_id": shop_id,
            "row_data": full_response,
            "advert_id": advert_id,
            "nm_id": nm_id,
            "subject_id": None,
            "norm_query": norm_query,
            "record_type": record_type,
        }

        if existing:
            for field, value in ods_data.items():
                if hasattr(existing, field):
                    setattr(existing, field, value)
            result_list.append(existing)
        else:
            ods_record = ODSWBBidRecommendation(**ods_data)
            db.add(ods_record)
            result_list.append(ods_record)

        if result_list:
            await db.commit()
            for record in result_list:
                await db.refresh(record)

        logger.debug(f"[ODS CRUD] 旧格式保存完成 - 总计: {len(result_list)}")
        return result_list

    async def _process_batch(
        self,
        db: AsyncSession,
        batch_data: List[Dict[str, Any]]
    ) -> List[ODSWBBidRecommendation]:
        """分批处理数据并提交 - 避免单次大事务"""
        result_list = []
        batch_size = 10  # 每批10条

        for i in range(0, len(batch_data), batch_size):
            batch = batch_data[i:i + batch_size]
            batch_result = []

            for ods_data in batch:
                shop_id = ods_data["shop_id"]
                advert_id = ods_data["advert_id"]
                nm_id = ods_data["nm_id"]
                subject_id = ods_data.get("subject_id")
                norm_query = ods_data["norm_query"]
                record_type = ods_data.get("record_type")

                existing = await self._get_existing(db, shop_id, advert_id, nm_id, subject_id, norm_query, record_type)

                if existing:
                    for field, value in ods_data.items():
                        if hasattr(existing, field):
                            setattr(existing, field, value)
                    batch_result.append(existing)
                else:
                    ods_record = ODSWBBidRecommendation(**ods_data)
                    db.add(ods_record)
                    batch_result.append(ods_record)

            if batch_result:
                try:
                    await db.commit()
                    for record in batch_result:
                        await db.refresh(record)
                    result_list.extend(batch_result)
                except Exception as e:
                    logger.error(f"[ODS CRUD] 批次提交失败: {e}")
                    await db.rollback()
                    raise

        logger.debug(f"[ODS CRUD] 竞价推荐同步完成 - 总计: {len(result_list)}")
        return result_list


class CRUDODSWBAdvertFullStat(CRUDBase[ODSWBAdvertFullStat, Dict[str, Any], Dict[str, Any]]):
    """ODS 广告完整统计 CRUD"""

    async def _get_existing(
        self,
        db: AsyncSession,
        shop_id: int,
        advert_id: Optional[int],
        stat_date: Optional[date],
        nm_id: Optional[int],
        app_type: Optional[str],
    ) -> Optional[ODSWBAdvertFullStat]:
        """根据唯一索引获取现有记录"""
        result = await db.execute(
            select(ODSWBAdvertFullStat).where(
                (ODSWBAdvertFullStat.shop_id == shop_id)
                & (ODSWBAdvertFullStat.advert_id == advert_id)
                & (ODSWBAdvertFullStat.stat_date == stat_date)
                & (ODSWBAdvertFullStat.nm_id == nm_id)
                & (ODSWBAdvertFullStat.app_type == app_type)
            )
        )
        return result.scalar_one_or_none()

    async def upsert_many(
        self,
        db: AsyncSession,
        *,
        fullstats_data: List[Dict[str, Any]],
        shop_id: int,
    ) -> List[ODSWBAdvertFullStat]:
        """批量创建/更新广告完整统计数据 - 分批处理避免超时"""
        logger.debug(f"[ODS CRUD] 开始同步广告完整统计 - 店铺: {shop_id}, 数据量: {len(fullstats_data)}")

        result_list = []
        seen = set()
        batch_size = 20  # 减小到每批20条记录，防止超时
        current_batch = []

        for advert_stat in fullstats_data:
            advert_id = advert_stat.get("advertId") or advert_stat.get("advert_id")
            currency = advert_stat.get("currency")

            # 展开days数组
            days = advert_stat.get("days", [])

            for day_data in days:
                stat_date = _safe_parse_date(day_data.get("date"))
                if not stat_date:
                    continue

                apps = day_data.get("apps", [])

                if apps:
                    for app in apps:
                        app_type = app.get("appType") or app.get("app_type")
                        nms = app.get("nms", [])

                        for nm_data in nms:
                            nm_id = nm_data.get("nmId")
                            if not nm_id:
                                continue

                            key = (advert_id, stat_date, nm_id, app_type)
                            if key in seen:
                                continue
                            seen.add(key)

                            ods_data = {
                                "shop_id": shop_id,
                                "row_data": nm_data,
                                "advert_id": advert_id,
                                "stat_date": stat_date,
                                "nm_id": nm_id,
                                "nm_name": nm_data.get("name"),
                                "app_type": app_type,
                                "views": nm_data.get("views"),
                                "clicks": nm_data.get("clicks"),
                                "atbs": nm_data.get("atbs"),
                                "orders": nm_data.get("orders"),
                                "canceled": nm_data.get("canceled"),
                                "shks": nm_data.get("shks"),
                                "sum_cost": nm_data.get("sum"),
                                "sum_price": nm_data.get("sum_price"),
                                "cpc": nm_data.get("cpc"),
                                "ctr": nm_data.get("ctr"),
                                "cr": nm_data.get("cr"),
                                "currency": currency,
                            }
                            current_batch.append(ods_data)
                else:
                    # 如果没有app数据,处理day级别数据
                    key = (advert_id, stat_date, None, None)
                    if key in seen:
                        continue
                    seen.add(key)

                    ods_data = {
                        "shop_id": shop_id,
                        "row_data": day_data,
                        "advert_id": advert_id,
                        "stat_date": stat_date,
                        "nm_id": None,
                        "nm_name": None,
                        "app_type": None,
                        "views": day_data.get("views"),
                        "clicks": day_data.get("clicks"),
                        "atbs": day_data.get("atbs"),
                        "orders": day_data.get("orders"),
                        "canceled": day_data.get("canceled"),
                        "shks": day_data.get("shks"),
                        "sum_cost": day_data.get("sum"),
                        "sum_price": day_data.get("sum_price"),
                        "cpc": day_data.get("cpc"),
                        "ctr": day_data.get("ctr"),
                        "cr": day_data.get("cr"),
                        "currency": currency,
                    }
                    current_batch.append(ods_data)

                # 分批提交 - 避免单次事务过大
                if len(current_batch) >= batch_size:
                    batch_result = await self._process_batch(db, current_batch)
                    result_list.extend(batch_result)
                    current_batch = []

        # 处理剩余数据
        if current_batch:
            batch_result = await self._process_batch(db, current_batch)
            result_list.extend(batch_result)

        logger.debug(f"[ODS CRUD] 广告完整统计同步完成 - 总计: {len(result_list)}")
        return result_list

    async def _process_batch(
        self,
        db: AsyncSession,
        batch_data: List[Dict[str, Any]]
    ) -> List[ODSWBAdvertFullStat]:
        """处理一批数据并提交"""
        batch_result = []
        for ods_data in batch_data:
            existing = await self._get_existing(
                db,
                ods_data["shop_id"],
                ods_data["advert_id"],
                ods_data["stat_date"],
                ods_data["nm_id"],
                ods_data["app_type"]
            )
            if existing:
                for field, value in ods_data.items():
                    if hasattr(existing, field):
                        setattr(existing, field, value)
                batch_result.append(existing)
            else:
                ods_record = ODSWBAdvertFullStat(**ods_data)
                db.add(ods_record)
                batch_result.append(ods_record)

        if batch_result:
            try:
                await db.commit()
                for record in batch_result:
                    await db.refresh(record)
            except Exception:
                await db.rollback()
                raise

        return batch_result


class CRUDODSWBAdvertV2(CRUDBase[ODSWBAdvertV2, Dict[str, Any], Dict[str, Any]]):
    """ODS 广告列表V2 CRUD"""

    async def _get_existing(
        self,
        db: AsyncSession,
        shop_id: int,
        advert_id: int,
    ) -> Optional[ODSWBAdvertV2]:
        """根据唯一索引获取现有记录"""
        result = await db.execute(
            select(ODSWBAdvertV2).where(
                (ODSWBAdvertV2.shop_id == shop_id)
                & (ODSWBAdvertV2.advert_id == advert_id)
            )
        )
        return result.scalar_one_or_none()

    async def upsert_many(
        self,
        db: AsyncSession,
        *,
        adverts_data: List[Dict[str, Any]],
        shop_id: int,
    ) -> List[ODSWBAdvertV2]:
        """批量创建/更新广告列表V2数据"""
        logger.debug(f"[ODS CRUD] 开始同步广告列表V2 - 店铺: {shop_id}, 数据量: {len(adverts_data)}")

        # 支持adverts字段在响应中
        if isinstance(adverts_data, dict) and "adverts" in adverts_data:
            adverts_data = adverts_data["adverts"]

        result_list = []

        for data in adverts_data:
            advert_id = data.get("id") or data.get("advertId")
            if not advert_id:
                continue

            # 提取嵌套数据 - 适配实际API返回格式
            settings = data.get("settings", {})
            placements = settings.get("placements", {})
            timestamps = data.get("timestamps", {})
            budget = data.get("budget", {})

            ods_data = {
                "shop_id": shop_id,
                "row_data": data,  # 保存完整原始JSON
                "advert_id": advert_id,
                "name": settings.get("name") or data.get("name"),
                "status": data.get("status"),
                "type": data.get("type"),
                "bid_type": data.get("bidType") or data.get("bid_type"),
                "currency": data.get("currency"),
                "daily_budget": budget.get("daily") or data.get("dailyBudget"),
                "total_budget": budget.get("total") or data.get("totalBudget"),
                "spent": data.get("spent"),
                "placement_search": placements.get("search"),
                "placement_recommendations": placements.get("recommendations"),
                "placement_catalog": placements.get("catalog"),
                "created_at": _safe_parse_datetime(timestamps.get("created") or data.get("createdAt") or data.get("created_at")),
                "updated_at": _safe_parse_datetime(timestamps.get("updated") or data.get("updatedAt") or data.get("updated_at")),
                "started_at": _safe_parse_datetime(timestamps.get("started") or data.get("startedAt") or data.get("started_at")),
                "ended_at": _safe_parse_datetime(timestamps.get("ended") or timestamps.get("deleted") or data.get("endedAt") or data.get("ended_at")),
            }

            existing = await self._get_existing(db, shop_id, advert_id)

            if existing:
                for field, value in ods_data.items():
                    if hasattr(existing, field):
                        setattr(existing, field, value)
                result_list.append(existing)
            else:
                ods_record = ODSWBAdvertV2(**ods_data)
                db.add(ods_record)
                result_list.append(ods_record)

        if result_list:
            try:
                await db.commit()
                for record in result_list:
                    await db.refresh(record)
            except Exception as e:
                logger.error(f"[ODS CRUD] 广告列表V2提交失败: {e}")
                try:
                    await db.rollback()
                except Exception as rollback_err:
                    logger.warning(f"[ODS CRUD] 回滚失败: {rollback_err}")
                raise

        logger.debug(f"[ODS CRUD] 广告列表V2同步完成 - 总计: {len(result_list)}")
        return result_list


# CRUD 实例
crud_ods_wb_norm_query_bid = CRUDODSWBNormQueryBid(ODSWBNormQueryBid)
crud_ods_wb_norm_query_minus = CRUDODSWBNormQueryMinus(ODSWBNormQueryMinus)
crud_ods_wb_norm_query_list = CRUDODSWBNormQueryList(ODSWBNormQueryList)
crud_ods_wb_norm_query_stat = CRUDODSWBNormQueryStat(ODSWBNormQueryStat)
crud_ods_wb_promotion_count = CRUDODSWBPromotionCount(ODSWBPromotionCount)
crud_ods_wb_bid_recommendation = CRUDODSWBBidRecommendation(ODSWBBidRecommendation)
crud_ods_wb_advert_full_stat = CRUDODSWBAdvertFullStat(ODSWBAdvertFullStat)
crud_ods_wb_advert_v2 = CRUDODSWBAdvertV2(ODSWBAdvertV2)
