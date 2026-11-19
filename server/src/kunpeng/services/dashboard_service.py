"""
仪表盘业务层

职责：确定统计范围与店铺集合，编排 DashboardCRUD 的多路聚合查询，
按业务口径计算退货率、DRR、客单价等派生指标，并组装成前端友好的结构。

口径约定（金额单位统一 ₽，不做汇率换算）：
- 销售额 GMV：WB = 供应商销售 price_with_disc 之和；Ozon = FBO/FBS 订单商品 price×quantity 之和
- 订单量：WB = 供应商订单行数；Ozon = FBO + FBS 订单数
- 退货率：退货量 / 订单量 × 100%
- 广告花费：WB = advert_stats.sum_cost；Ozon = adv_stats_daily.money_spent
- DRR（广告费用占比）：广告花费 / 销售额 × 100%
- 客单价：销售额 / 订单量
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud import shop_crud
from kunpeng.crud.dashboard import dashboard_crud
from kunpeng.schemas.dashboard import (DashboardSummary, DateRange, KpiBlock,
                                       PlatformStat, ShopStat, TopProduct,
                                       TrendPoint)

PLATFORM_LABELS = {
    "wildberries": "Wildberries",
    "ozon": "Ozon",
}


def _rate(part: float, whole: float) -> float:
    """安全百分比，保留两位小数"""
    if not whole:
        return 0.0
    return round(part / whole * 100, 2)


def _r2(value: float) -> float:
    return round(value or 0.0, 2)


class DashboardService:
    """仪表盘数据编排"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_summary(
        self,
        *,
        user_id: int,
        days: int = 30,
        platform: Optional[str] = None,
        shop_id: Optional[int] = None,
        top_limit: int = 10,
    ) -> DashboardSummary:
        # 1. 时间范围：[date_from, date_to)，date_to 为“明天零点”以包含今天
        today = date.today()
        date_to = today + timedelta(days=1)
        date_from = date_to - timedelta(days=days)

        # 2. 店铺集合：限定在当前用户名下，可再按平台/店铺过滤
        shops = await shop_crud.get_accessible_by_user(
            self.db, user_id=user_id, limit=1000
        )
        if platform:
            shops = [s for s in shops if s.platform == platform]
        if shop_id is not None:
            shops = [s for s in shops if s.id == shop_id]

        shop_meta = {s.id: {"name": s.name, "platform": s.platform} for s in shops}
        wb_ids = [s.id for s in shops if s.platform == "wildberries"]
        ozon_ids = [s.id for s in shops if s.platform == "ozon"]

        # 3. 各店铺指标累加器
        acc: Dict[int, Dict[str, float]] = {
            sid: {
                "gmv": 0.0,
                "orders": 0,
                "units": 0,
                "returns": 0,
                "ad_spend": 0.0,
            }
            for sid in shop_meta
        }

        async def _apply(rows, key):
            for row in rows:
                sid = row["shop_id"]
                if sid in acc:
                    acc[sid][key] += row[key]

        # WB
        for row in await dashboard_crud.wb_sales_by_shop(
            self.db, shop_ids=wb_ids, date_from=date_from, date_to=date_to
        ):
            if row["shop_id"] in acc:
                acc[row["shop_id"]]["gmv"] += row["gmv"]
                acc[row["shop_id"]]["units"] += row["units"]
        await _apply(
            await dashboard_crud.wb_orders_by_shop(
                self.db, shop_ids=wb_ids, date_from=date_from, date_to=date_to
            ),
            "orders",
        )
        await _apply(
            await dashboard_crud.wb_returns_by_shop(
                self.db, shop_ids=wb_ids, date_from=date_from, date_to=date_to
            ),
            "returns",
        )
        await _apply(
            await dashboard_crud.wb_ad_spend_by_shop(
                self.db, shop_ids=wb_ids, date_from=date_from, date_to=date_to
            ),
            "ad_spend",
        )

        # Ozon
        for row in await dashboard_crud.ozon_sales_by_shop(
            self.db, shop_ids=ozon_ids, date_from=date_from, date_to=date_to
        ):
            if row["shop_id"] in acc:
                acc[row["shop_id"]]["gmv"] += row["gmv"]
                acc[row["shop_id"]]["units"] += row["units"]
        await _apply(
            await dashboard_crud.ozon_orders_by_shop(
                self.db, shop_ids=ozon_ids, date_from=date_from, date_to=date_to
            ),
            "orders",
        )
        await _apply(
            await dashboard_crud.ozon_returns_by_shop(
                self.db, shop_ids=ozon_ids, date_from=date_from, date_to=date_to
            ),
            "returns",
        )
        await _apply(
            await dashboard_crud.ozon_ad_spend_by_shop(
                self.db, shop_ids=ozon_ids, date_from=date_from, date_to=date_to
            ),
            "ad_spend",
        )

        # 4. 店铺维度
        shop_stats: List[ShopStat] = []
        for sid, meta in shop_meta.items():
            a = acc[sid]
            shop_stats.append(
                ShopStat(
                    shop_id=sid,
                    shop_name=meta["name"],
                    platform=meta["platform"],
                    platform_label=PLATFORM_LABELS.get(
                        meta["platform"], meta["platform"]
                    ),
                    gmv=_r2(a["gmv"]),
                    orders=int(a["orders"]),
                    units=int(a["units"]),
                    returns=int(a["returns"]),
                    return_rate=_rate(a["returns"], a["orders"]),
                    ad_spend=_r2(a["ad_spend"]),
                    drr=_rate(a["ad_spend"], a["gmv"]),
                )
            )
        shop_stats.sort(key=lambda s: s.gmv, reverse=True)

        # 5. 平台维度
        platform_stats: List[PlatformStat] = []
        for plat in ("wildberries", "ozon"):
            members = [s for s in shop_stats if s.platform == plat]
            if not members:
                continue
            gmv = sum(s.gmv for s in members)
            orders = sum(s.orders for s in members)
            units = sum(s.units for s in members)
            returns = sum(s.returns for s in members)
            ad_spend = sum(s.ad_spend for s in members)
            platform_stats.append(
                PlatformStat(
                    platform=plat,
                    platform_label=PLATFORM_LABELS.get(plat, plat),
                    gmv=_r2(gmv),
                    orders=orders,
                    units=units,
                    returns=returns,
                    return_rate=_rate(returns, orders),
                    ad_spend=_r2(ad_spend),
                    drr=_rate(ad_spend, gmv),
                    shop_count=len(members),
                )
            )

        # 6. 全局 KPI
        total_gmv = sum(s.gmv for s in shop_stats)
        total_orders = sum(s.orders for s in shop_stats)
        total_units = sum(s.units for s in shop_stats)
        total_returns = sum(s.returns for s in shop_stats)
        total_ad = sum(s.ad_spend for s in shop_stats)
        kpi = KpiBlock(
            gmv=_r2(total_gmv),
            orders=total_orders,
            units=total_units,
            returns=total_returns,
            return_rate=_rate(total_returns, total_orders),
            ad_spend=_r2(total_ad),
            drr=_rate(total_ad, total_gmv),
            avg_order_value=_r2(total_gmv / total_orders) if total_orders else 0.0,
            shop_count=len(shop_stats),
        )

        # 7. 趋势（按日补零，分平台）
        trend = await self._build_trend(
            wb_ids=wb_ids,
            ozon_ids=ozon_ids,
            date_from=date_from,
            date_to=date_to,
            days=days,
        )

        # 8. Top 商品（两平台各取，再按 GMV 合并排序）
        top_products = await self._build_top_products(
            wb_ids=wb_ids,
            ozon_ids=ozon_ids,
            date_from=date_from,
            date_to=date_to,
            limit=top_limit,
        )

        return DashboardSummary(
            range=DateRange(
                date_from=date_from.isoformat(),
                date_to=(date_to - timedelta(days=1)).isoformat(),
                days=days,
            ),
            kpi=kpi,
            trend=trend,
            platforms=platform_stats,
            shops=shop_stats,
            top_products=top_products,
            generated_at=datetime.now().isoformat(timespec="seconds"),
        )

    async def _build_trend(
        self,
        *,
        wb_ids: List[int],
        ozon_ids: List[int],
        date_from: date,
        date_to: date,
        days: int,
    ) -> List[TrendPoint]:
        # 初始化连续日期骨架，保证前端折线不断点
        skeleton: Dict[str, TrendPoint] = {}
        for i in range(days):
            d = (date_from + timedelta(days=i)).isoformat()
            skeleton[d] = TrendPoint(date=d)

        # WB
        for row in await dashboard_crud.wb_sales_trend(
            self.db, shop_ids=wb_ids, date_from=date_from, date_to=date_to
        ):
            if row["day"] in skeleton:
                skeleton[row["day"]].wb_gmv = _r2(
                    skeleton[row["day"]].wb_gmv + row["gmv"]
                )
        for row in await dashboard_crud.wb_orders_trend(
            self.db, shop_ids=wb_ids, date_from=date_from, date_to=date_to
        ):
            if row["day"] in skeleton:
                skeleton[row["day"]].wb_orders += row["orders"]
        for row in await dashboard_crud.wb_ad_trend(
            self.db, shop_ids=wb_ids, date_from=date_from, date_to=date_to
        ):
            if row["day"] in skeleton:
                skeleton[row["day"]].wb_ad_spend = _r2(
                    skeleton[row["day"]].wb_ad_spend + row["ad_spend"]
                )
        for row in await dashboard_crud.wb_returns_trend(
            self.db, shop_ids=wb_ids, date_from=date_from, date_to=date_to
        ):
            if row["day"] in skeleton:
                skeleton[row["day"]].wb_returns += row["returns"]

        # Ozon
        for row in await dashboard_crud.ozon_sales_trend(
            self.db, shop_ids=ozon_ids, date_from=date_from, date_to=date_to
        ):
            if row["day"] in skeleton:
                skeleton[row["day"]].ozon_gmv = _r2(
                    skeleton[row["day"]].ozon_gmv + row["gmv"]
                )
        for row in await dashboard_crud.ozon_orders_trend(
            self.db, shop_ids=ozon_ids, date_from=date_from, date_to=date_to
        ):
            if row["day"] in skeleton:
                skeleton[row["day"]].ozon_orders += row["orders"]
        for row in await dashboard_crud.ozon_ad_trend(
            self.db, shop_ids=ozon_ids, date_from=date_from, date_to=date_to
        ):
            if row["day"] in skeleton:
                skeleton[row["day"]].ozon_ad_spend = _r2(
                    skeleton[row["day"]].ozon_ad_spend + row["ad_spend"]
                )
        for row in await dashboard_crud.ozon_returns_trend(
            self.db, shop_ids=ozon_ids, date_from=date_from, date_to=date_to
        ):
            if row["day"] in skeleton:
                skeleton[row["day"]].ozon_returns += row["returns"]

        return [skeleton[k] for k in sorted(skeleton)]

    async def _build_top_products(
        self,
        *,
        wb_ids: List[int],
        ozon_ids: List[int],
        date_from: date,
        date_to: date,
        limit: int,
    ) -> List[TopProduct]:
        items: List[TopProduct] = []
        for row in await dashboard_crud.wb_top_products(
            self.db, shop_ids=wb_ids, date_from=date_from, date_to=date_to, limit=limit
        ):
            items.append(
                TopProduct(
                    platform="wildberries",
                    platform_label=PLATFORM_LABELS["wildberries"],
                    ext_id=row["ext_id"],
                    name=row["name"],
                    gmv=_r2(row["gmv"]),
                    units=row["units"],
                )
            )
        for row in await dashboard_crud.ozon_top_products(
            self.db,
            shop_ids=ozon_ids,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        ):
            items.append(
                TopProduct(
                    platform="ozon",
                    platform_label=PLATFORM_LABELS["ozon"],
                    ext_id=row["ext_id"],
                    name=row["name"],
                    gmv=_r2(row["gmv"]),
                    units=row["units"],
                )
            )
        items.sort(key=lambda x: x.gmv, reverse=True)
        return items[:limit]
