"""
Ozon ODS 层 - 广告SKU小时统计 CRUD
"""
import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, func
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.crud.ods.ozon.utils import (
    parse_ru_date,
    parse_ru_decimal,
    safe_int,
    safe_str,
)
from kunpeng.models.ods.ozon.advert_stats_hourly import ODSOzonAdvStatProductHourly

logger = logging.getLogger(__name__)


class CRUDOzonAdvStatProductHourly(
    CRUDBase[ODSOzonAdvStatProductHourly, Dict[str, Any], Dict[str, Any]]
):
    """ODS Ozon 广告SKU小时统计 CRUD"""

    async def get_hourly_sum_before_hour(
        self,
        db: AsyncSession,
        shop_id: int,
        stat_date: date,
        stat_hour: int,
    ) -> Dict[Tuple[str, Optional[int]], Dict[str, Any]]:
        """
        查询当天已写入的小时数据累计（排除当前小时）

        Returns:
            {(campaign_id, sku): {'views': x, 'clicks': y, ...}}
        """
        result = await db.execute(
            select(
                ODSOzonAdvStatProductHourly.campaign_id,
                ODSOzonAdvStatProductHourly.sku,
                func.sum(ODSOzonAdvStatProductHourly.views).label("views"),
                func.sum(ODSOzonAdvStatProductHourly.clicks).label("clicks"),
                func.sum(ODSOzonAdvStatProductHourly.to_cart).label("to_cart"),
                func.sum(ODSOzonAdvStatProductHourly.money_spent).label("money_spent"),
                func.sum(ODSOzonAdvStatProductHourly.orders).label("orders"),
                func.sum(ODSOzonAdvStatProductHourly.orders_money).label("orders_money"),
                func.sum(ODSOzonAdvStatProductHourly.models).label("models"),
                func.sum(ODSOzonAdvStatProductHourly.models_money).label("models_money"),
                func.sum(ODSOzonAdvStatProductHourly.product_gmv).label("product_gmv"),
            )
            .where(
                (ODSOzonAdvStatProductHourly.shop_id == shop_id)
                & (ODSOzonAdvStatProductHourly.stat_date == stat_date)
                & (ODSOzonAdvStatProductHourly.stat_hour < stat_hour)
            )
            .group_by(
                ODSOzonAdvStatProductHourly.campaign_id,
                ODSOzonAdvStatProductHourly.sku,
            )
        )

        sums: Dict[Tuple[str, Optional[int]], Dict[str, Any]] = {}
        for row in result.all():
            key = (row.campaign_id, row.sku)
            sums[key] = {
                "views": row.views or 0,
                "clicks": row.clicks or 0,
                "to_cart": row.to_cart or 0,
                "money_spent": row.money_spent or 0,
                "orders": row.orders or 0,
                "orders_money": row.orders_money or 0,
                "models": row.models or 0,
                "models_money": row.models_money or 0,
                "product_gmv": row.product_gmv or 0,
            }
        return sums

    def extract_row(
        self, item: Dict[str, Any], shop_id: int, campaign_id: str
    ) -> Dict[str, Any]:
        """从异步报表 rows 提取字段（俄式小数/日期需转换），与日表口径一致"""
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

    async def upsert_many(
        self,
        db: AsyncSession,
        *,
        records: List[Dict[str, Any]],
        shop_id: int,
        stat_date: date,
        stat_hour: int,
    ) -> int:
        """
        批量 upsert 小时数据（MySQL ON DUPLICATE KEY UPDATE，按 shop+campaign+sku+date+hour 幂等）

        Args:
            records: 已计算好增量的记录列表（含 campaign_id/sku 及各指标）
            shop_id: 店铺ID
            stat_date: 统计日期
            stat_hour: 统计小时
        """
        logger.debug(
            f"[ODS Ozon AdvStatProductHourly] 开始 upsert - 店铺: {shop_id}, "
            f"日期: {stat_date}, 小时: {stat_hour}, 数据量: {len(records)}"
        )

        if not records:
            return 0

        values = []
        for data in records:
            values.append({
                "shop_id": shop_id,
                "row_data": data.get("row_data", data),
                "campaign_id": data.get("campaign_id"),
                "sku": data.get("sku"),
                "stat_date": stat_date,
                "stat_hour": stat_hour,
                "title": data.get("title"),
                "search_query": data.get("search_query"),
                "price": data.get("price"),
                "views": data.get("views"),
                "clicks": data.get("clicks"),
                "ctr": data.get("ctr"),
                "to_cart": data.get("to_cart"),
                "avg_bid": data.get("avg_bid"),
                "money_spent": data.get("money_spent"),
                "orders": data.get("orders"),
                "orders_money": data.get("orders_money"),
                "models": data.get("models"),
                "models_money": data.get("models_money"),
                "drr": data.get("drr"),
                "general_drr": data.get("general_drr"),
                "product_gmv": data.get("product_gmv"),
            })

        stmt = insert(ODSOzonAdvStatProductHourly).values(values)
        update_dict = {
            "row_data": stmt.inserted.row_data,
            "title": stmt.inserted.title,
            "search_query": stmt.inserted.search_query,
            "price": stmt.inserted.price,
            "views": stmt.inserted.views,
            "clicks": stmt.inserted.clicks,
            "ctr": stmt.inserted.ctr,
            "to_cart": stmt.inserted.to_cart,
            "avg_bid": stmt.inserted.avg_bid,
            "money_spent": stmt.inserted.money_spent,
            "orders": stmt.inserted.orders,
            "orders_money": stmt.inserted.orders_money,
            "models": stmt.inserted.models,
            "models_money": stmt.inserted.models_money,
            "drr": stmt.inserted.drr,
            "general_drr": stmt.inserted.general_drr,
            "product_gmv": stmt.inserted.product_gmv,
        }
        await db.execute(stmt.on_duplicate_key_update(**update_dict))
        await db.commit()

        logger.debug(
            f"[ODS Ozon AdvStatProductHourly] upsert 完成 - 记录数: {len(values)}"
        )
        return len(values)


crud_ods_ozon_adv_stat_product_hourly = CRUDOzonAdvStatProductHourly(
    ODSOzonAdvStatProductHourly
)
