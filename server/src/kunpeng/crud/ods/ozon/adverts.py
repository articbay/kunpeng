"""
Ozon ODS 层 - 广告（Performance API）相关表 CRUD
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.crud.ods.ozon.utils import (parse_iso_datetime, parse_ru_date,
                                         parse_ru_decimal, safe_decimal,
                                         safe_int, safe_str)
from kunpeng.models.ods.ozon.adverts import (ODSOzonAdvCampaign,
                                             ODSOzonAdvStatDaily,
                                             ODSOzonAdvStatProductDaily)

logger = logging.getLogger(__name__)


class CRUDOzonAdvCampaign(CRUDBase[ODSOzonAdvCampaign, Dict[str, Any], Dict[str, Any]]):
    """ODS 广告活动表 CRUD"""

    async def _get_existing_item(
        self,
        db: AsyncSession,
        shop_id: int,
        campaign_id: str,
    ) -> Optional[ODSOzonAdvCampaign]:
        query = select(ODSOzonAdvCampaign).where(
            (ODSOzonAdvCampaign.shop_id == shop_id)
            & (ODSOzonAdvCampaign.campaign_id == campaign_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    def _extract_item_data(self, item: Dict[str, Any], shop_id: int) -> Dict[str, Any]:
        """从 /api/client/campaign 响应提取字段"""
        placement = item.get("placement")
        if isinstance(placement, list):
            placement = ",".join(str(p) for p in placement)

        return {
            "shop_id": shop_id,
            "row_data": item,
            "campaign_id": safe_str(item.get("id")),
            "title": safe_str(item.get("title")),
            "state": safe_str(item.get("state")),
            "adv_object_type": safe_str(item.get("advObjectType")),
            "placement": safe_str(placement),
            "payment_type": safe_str(
                item.get("PaymentType") or item.get("paymentType")
            ),
            # 预算字段单位为「微卢布(micro)」整数(=卢布×10^6)，ODS 忠实存原始值，
            # 换算为卢布请在分析层 /1e6
            "daily_budget": parse_ru_decimal(item.get("dailyBudget")),
            "weekly_budget": parse_ru_decimal(item.get("weeklyBudget")),
            "budget": parse_ru_decimal(item.get("budget")),
            "from_date": parse_iso_datetime(item.get("fromDate")),
            "to_date": parse_iso_datetime(item.get("toDate")),
        }

    async def create_many(
        self,
        db: AsyncSession,
        *,
        items: List[Dict[str, Any]],
        shop_id: int,
    ) -> List[ODSOzonAdvCampaign]:
        """批量创建/更新广告活动"""
        logger.debug(
            f"[ODS Ozon AdvCampaign] 开始同步 - 店铺: {shop_id}, 数据量: {len(items)}"
        )

        result_list = []
        created_count = 0
        updated_count = 0

        for item in items:
            item_data = self._extract_item_data(item, shop_id)
            campaign_id = item_data.get("campaign_id")
            if not campaign_id:
                continue

            existing = await self._get_existing_item(db, shop_id, campaign_id)
            if existing:
                for field, value in item_data.items():
                    if field != "id" and hasattr(existing, field):
                        setattr(existing, field, value)
                result_list.append(existing)
                updated_count += 1
            else:
                new_item = ODSOzonAdvCampaign(**item_data)
                db.add(new_item)
                result_list.append(new_item)
                created_count += 1

        await db.flush()
        logger.debug(
            f"[ODS Ozon AdvCampaign] 同步完成 - 新增: {created_count}, 更新: {updated_count}, 总计: {len(result_list)}"
        )
        return result_list


class CRUDOzonAdvStatDaily(
    CRUDBase[ODSOzonAdvStatDaily, Dict[str, Any], Dict[str, Any]]
):
    """ODS 广告日统计表 CRUD"""

    async def _get_existing_item(
        self,
        db: AsyncSession,
        shop_id: int,
        campaign_id: str,
        stat_date,
    ) -> Optional[ODSOzonAdvStatDaily]:
        query = select(ODSOzonAdvStatDaily).where(
            (ODSOzonAdvStatDaily.shop_id == shop_id)
            & (ODSOzonAdvStatDaily.campaign_id == campaign_id)
            & (ODSOzonAdvStatDaily.stat_date == stat_date)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    def _extract_item_data(self, item: Dict[str, Any], shop_id: int) -> Dict[str, Any]:
        """从 daily/json 的 rows 提取字段（俄式小数需转换）"""
        return {
            "shop_id": shop_id,
            "row_data": item,
            "campaign_id": safe_str(item.get("id")),
            "title": safe_str(item.get("title")),
            "stat_date": parse_iso_datetime(item.get("date")),
            "views": safe_int(item.get("views")),
            "clicks": safe_int(item.get("clicks")),
            "money_spent": parse_ru_decimal(item.get("moneySpent")),
            "orders": safe_int(item.get("orders")),
            "orders_money": parse_ru_decimal(item.get("ordersMoney")),
        }

    async def create_many(
        self,
        db: AsyncSession,
        *,
        items: List[Dict[str, Any]],
        shop_id: int,
    ) -> List[ODSOzonAdvStatDaily]:
        """批量创建/更新广告日统计（按 shop+campaign+date 幂等 upsert）"""
        logger.debug(
            f"[ODS Ozon AdvStatDaily] 开始同步 - 店铺: {shop_id}, 数据量: {len(items)}"
        )

        result_list = []
        created_count = 0
        updated_count = 0
        # 批内去重：同批 rows 可能出现重复 (campaign_id, stat_date)，pending 对象
        # DB 查不到会导致重复新增触发唯一键冲突(1062)，用 seen 缓存本批已处理键。
        seen: Dict[Any, ODSOzonAdvStatDaily] = {}

        for item in items:
            item_data = self._extract_item_data(item, shop_id)
            campaign_id = item_data.get("campaign_id")
            stat_date = item_data.get("stat_date")
            if not campaign_id or stat_date is None:
                continue

            batch_key = (campaign_id, stat_date)
            if batch_key in seen:
                existing_in_batch = seen[batch_key]
                for field, value in item_data.items():
                    if field != "id" and hasattr(existing_in_batch, field):
                        setattr(existing_in_batch, field, value)
                continue
            existing = await self._get_existing_item(
                db, shop_id, campaign_id, stat_date
            )
            if existing:
                for field, value in item_data.items():
                    if field != "id" and hasattr(existing, field):
                        setattr(existing, field, value)
                result_list.append(existing)
                seen[batch_key] = existing
                updated_count += 1
            else:
                new_item = ODSOzonAdvStatDaily(**item_data)
                db.add(new_item)
                result_list.append(new_item)
                seen[batch_key] = new_item
                created_count += 1

        await db.flush()
        logger.debug(
            f"[ODS Ozon AdvStatDaily] 同步完成 - 新增: {created_count}, 更新: {updated_count}, 总计: {len(result_list)}"
        )
        return result_list


class CRUDOzonAdvStatProductDaily(
    CRUDBase[ODSOzonAdvStatProductDaily, Dict[str, Any], Dict[str, Any]]
):
    """ODS 广告SKU日统计表 CRUD（来源异步报表）"""

    async def _get_existing_item(
        self, db: AsyncSession, shop_id: int, campaign_id: str, sku: int, stat_date
    ) -> Optional[ODSOzonAdvStatProductDaily]:
        query = select(ODSOzonAdvStatProductDaily).where(
            (ODSOzonAdvStatProductDaily.shop_id == shop_id)
            & (ODSOzonAdvStatProductDaily.campaign_id == campaign_id)
            & (ODSOzonAdvStatProductDaily.sku == sku)
            & (ODSOzonAdvStatProductDaily.stat_date == stat_date)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    def _extract_item_data(
        self, item: Dict[str, Any], shop_id: int, campaign_id: str
    ) -> Dict[str, Any]:
        """从异步报表 rows 提取字段（俄式小数/日期需转换）"""
        return {
            "shop_id": shop_id,
            "row_data": item,
            "campaign_id": campaign_id,
            "sku": safe_int(item.get("sku")),
            "stat_date": parse_ru_date(item.get("date")),
            "title": safe_str(item.get("title")),
            "search_query": safe_str(item.get("search_query")),
            "price": parse_ru_decimal(item.get("price")),
            "views": safe_int(item.get("views")),
            "clicks": safe_int(item.get("clicks")),
            "ctr": parse_ru_decimal(item.get("ctr")),
            "to_cart": safe_int(item.get("toCart")),
            "avg_bid": parse_ru_decimal(item.get("avgBid")),
            "money_spent": parse_ru_decimal(item.get("moneySpent")),
            "orders": safe_int(item.get("orders")),
            "orders_money": parse_ru_decimal(item.get("ordersMoney")),
            "models": safe_int(item.get("models")),
            "models_money": parse_ru_decimal(item.get("modelsMoney")),
            "drr": parse_ru_decimal(item.get("drr")),
            "general_drr": parse_ru_decimal(item.get("general_drr")),
            "product_gmv": parse_ru_decimal(item.get("product_gmv")),
        }

    async def create_many(
        self,
        db: AsyncSession,
        *,
        items: List[Dict[str, Any]],
        shop_id: int,
        campaign_id: str,
    ) -> List[ODSOzonAdvStatProductDaily]:
        """批量 upsert（按 shop+campaign+sku+date 幂等）"""
        logger.debug(
            f"[ODS Ozon AdvStatProductDaily] 开始同步 - 店铺: {shop_id}, 活动: {campaign_id}, 数据量: {len(items)}"
        )
        result_list = []
        created_count = 0
        updated_count = 0
        # 批内去重：同一次报表 rows 里可能出现重复的 (sku, stat_date)，
        # 若仅按 DB 查询判断存在性，pending(未 flush) 的新对象查不到，会导致
        # 同批两条都走新增分支，flush 时触发唯一键冲突(1062)。这里用 seen 缓存
        # 本批已处理过的键，命中则就地更新，保证批内幂等。
        seen: Dict[Any, ODSOzonAdvStatProductDaily] = {}
        for item in items:
            item_data = self._extract_item_data(item, shop_id, campaign_id)
            sku = item_data.get("sku")
            stat_date = item_data.get("stat_date")
            if sku is None or stat_date is None:
                continue
            batch_key = (sku, stat_date)
            if batch_key in seen:
                existing_in_batch = seen[batch_key]
                for field, value in item_data.items():
                    if field != "id" and hasattr(existing_in_batch, field):
                        setattr(existing_in_batch, field, value)
                continue
            existing = await self._get_existing_item(
                db, shop_id, campaign_id, sku, stat_date
            )
            if existing:
                for field, value in item_data.items():
                    if field != "id" and hasattr(existing, field):
                        setattr(existing, field, value)
                result_list.append(existing)
                seen[batch_key] = existing
                updated_count += 1
            else:
                new_item = ODSOzonAdvStatProductDaily(**item_data)
                db.add(new_item)
                result_list.append(new_item)
                seen[batch_key] = new_item
                created_count += 1
        await db.flush()
        logger.debug(
            f"[ODS Ozon AdvStatProductDaily] 同步完成 - 新增: {created_count}, 更新: {updated_count}, 总计: {len(result_list)}"
        )
        return result_list


crud_ods_ozon_adv_campaign = CRUDOzonAdvCampaign(ODSOzonAdvCampaign)
crud_ods_ozon_adv_stat_daily = CRUDOzonAdvStatDaily(ODSOzonAdvStatDaily)
crud_ods_ozon_adv_stat_product_daily = CRUDOzonAdvStatProductDaily(
    ODSOzonAdvStatProductDaily
)
