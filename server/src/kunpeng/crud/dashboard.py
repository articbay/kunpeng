"""
仪表盘数据层（只读聚合）

职责：只做数据库聚合查询，返回轻量的原始聚合结果（dict/list），
业务口径与百分比计算放在 service 层。所有查询均为只读 SELECT。

数据来源（ODS 层）：
- WB 销售:   ods_wb_supplier_sales   (price_with_disc 求和为 GMV)
- WB 订单:   ods_wb_supplier_orders
- WB 退货:   ods_wb_goods_returns
- WB 广告:   ods_wb_advert_stats     (sum_cost 为花费)
- Ozon 订单: ods_ozon_fbo_postings + ods_ozon_fbs_postings 及其商品明细
- Ozon 退货: ods_ozon_returns
- Ozon 广告: ods_ozon_adv_stats_daily (money_spent 为花费)
"""

from datetime import date, datetime
from typing import Any, Dict, List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.ods.ozon.adverts import ODSOzonAdvStatDaily
from kunpeng.models.ods.ozon.fbo_postings import (
    ODSOzonFBOPosting,
    ODSOzonFBOPostingProduct,
)
from kunpeng.models.ods.ozon.postings import ODSOzonFBSPosting, ODSOzonFBSPostingProduct
from kunpeng.models.ods.ozon.returns import ODSOzonReturn
from kunpeng.models.ods.wildberries.adverts import ODSWBAdvertStat
from kunpeng.models.ods.wildberries.returns import ODSWBGoodsReturn
from kunpeng.models.ods.wildberries.sales import ODSWBSupplierOrder, ODSWBSupplierSale


def _f(value: Any) -> float:
    """把 Decimal/None 安全转为 float"""
    return float(value) if value is not None else 0.0


def _i(value: Any) -> int:
    """把 None 安全转为 int"""
    return int(value) if value is not None else 0


class DashboardCRUD:
    """仪表盘只读聚合查询集合"""

    # ==================== Wildberries ====================

    async def wb_sales_by_shop(
        self, db: AsyncSession, *, shop_ids: List[int], date_from: date, date_to: date
    ) -> List[Dict[str, Any]]:
        """WB 各店铺销售额与件数（按 price_with_disc 求和）"""
        if not shop_ids:
            return []
        stmt = (
            select(
                ODSWBSupplierSale.shop_id.label("shop_id"),
                func.coalesce(func.sum(ODSWBSupplierSale.price_with_disc), 0).label(
                    "gmv"
                ),
                func.count().label("units"),
            )
            .where(
                ODSWBSupplierSale.shop_id.in_(shop_ids),
                ODSWBSupplierSale.date >= date_from,
                ODSWBSupplierSale.date < date_to,
            )
            .group_by(ODSWBSupplierSale.shop_id)
        )
        rows = (await db.execute(stmt)).all()
        return [
            {"shop_id": r.shop_id, "gmv": _f(r.gmv), "units": _i(r.units)} for r in rows
        ]

    async def wb_orders_by_shop(
        self, db: AsyncSession, *, shop_ids: List[int], date_from: date, date_to: date
    ) -> List[Dict[str, Any]]:
        """WB 各店铺订单量"""
        if not shop_ids:
            return []
        stmt = (
            select(
                ODSWBSupplierOrder.shop_id.label("shop_id"),
                func.count().label("orders"),
            )
            .where(
                ODSWBSupplierOrder.shop_id.in_(shop_ids),
                ODSWBSupplierOrder.date >= date_from,
                ODSWBSupplierOrder.date < date_to,
            )
            .group_by(ODSWBSupplierOrder.shop_id)
        )
        rows = (await db.execute(stmt)).all()
        return [{"shop_id": r.shop_id, "orders": _i(r.orders)} for r in rows]

    async def wb_returns_by_shop(
        self, db: AsyncSession, *, shop_ids: List[int], date_from: date, date_to: date
    ) -> List[Dict[str, Any]]:
        """WB 各店铺退货量（按订单日期 order_dt）"""
        if not shop_ids:
            return []
        stmt = (
            select(
                ODSWBGoodsReturn.shop_id.label("shop_id"),
                func.count().label("returns"),
            )
            .where(
                ODSWBGoodsReturn.shop_id.in_(shop_ids),
                ODSWBGoodsReturn.order_dt >= date_from,
                ODSWBGoodsReturn.order_dt < date_to,
            )
            .group_by(ODSWBGoodsReturn.shop_id)
        )
        rows = (await db.execute(stmt)).all()
        return [{"shop_id": r.shop_id, "returns": _i(r.returns)} for r in rows]

    async def wb_ad_spend_by_shop(
        self, db: AsyncSession, *, shop_ids: List[int], date_from: date, date_to: date
    ) -> List[Dict[str, Any]]:
        """WB 各店铺广告花费（sum_cost）"""
        if not shop_ids:
            return []
        stmt = (
            select(
                ODSWBAdvertStat.shop_id.label("shop_id"),
                func.coalesce(func.sum(ODSWBAdvertStat.sum_cost), 0).label("ad_spend"),
            )
            .where(
                ODSWBAdvertStat.shop_id.in_(shop_ids),
                ODSWBAdvertStat.stat_date >= date_from,
                ODSWBAdvertStat.stat_date < date_to,
            )
            .group_by(ODSWBAdvertStat.shop_id)
        )
        rows = (await db.execute(stmt)).all()
        return [{"shop_id": r.shop_id, "ad_spend": _f(r.ad_spend)} for r in rows]

    async def wb_sales_trend(
        self, db: AsyncSession, *, shop_ids: List[int], date_from: date, date_to: date
    ) -> List[Dict[str, Any]]:
        """WB 按日销售额/件数"""
        if not shop_ids:
            return []
        day = func.date(ODSWBSupplierSale.date).label("day")
        stmt = (
            select(
                day,
                func.coalesce(func.sum(ODSWBSupplierSale.price_with_disc), 0).label(
                    "gmv"
                ),
                func.count().label("units"),
            )
            .where(
                ODSWBSupplierSale.shop_id.in_(shop_ids),
                ODSWBSupplierSale.date >= date_from,
                ODSWBSupplierSale.date < date_to,
            )
            .group_by(day)
        )
        rows = (await db.execute(stmt)).all()
        return [
            {"day": str(r.day), "gmv": _f(r.gmv), "units": _i(r.units)} for r in rows
        ]

    async def wb_orders_trend(
        self, db: AsyncSession, *, shop_ids: List[int], date_from: date, date_to: date
    ) -> List[Dict[str, Any]]:
        """WB 按日订单量"""
        if not shop_ids:
            return []
        day = func.date(ODSWBSupplierOrder.date).label("day")
        stmt = (
            select(day, func.count().label("orders"))
            .where(
                ODSWBSupplierOrder.shop_id.in_(shop_ids),
                ODSWBSupplierOrder.date >= date_from,
                ODSWBSupplierOrder.date < date_to,
            )
            .group_by(day)
        )
        rows = (await db.execute(stmt)).all()
        return [{"day": str(r.day), "orders": _i(r.orders)} for r in rows]

    async def wb_ad_trend(
        self, db: AsyncSession, *, shop_ids: List[int], date_from: date, date_to: date
    ) -> List[Dict[str, Any]]:
        """WB 按日广告花费"""
        if not shop_ids:
            return []
        day = ODSWBAdvertStat.stat_date.label("day")
        stmt = (
            select(
                day,
                func.coalesce(func.sum(ODSWBAdvertStat.sum_cost), 0).label("ad_spend"),
            )
            .where(
                ODSWBAdvertStat.shop_id.in_(shop_ids),
                ODSWBAdvertStat.stat_date >= date_from,
                ODSWBAdvertStat.stat_date < date_to,
            )
            .group_by(day)
        )
        rows = (await db.execute(stmt)).all()
        return [{"day": str(r.day), "ad_spend": _f(r.ad_spend)} for r in rows]

    async def wb_returns_trend(
        self, db: AsyncSession, *, shop_ids: List[int], date_from: date, date_to: date
    ) -> List[Dict[str, Any]]:
        """WB 按日退货量"""
        if not shop_ids:
            return []
        day = ODSWBGoodsReturn.order_dt.label("day")
        stmt = (
            select(day, func.count().label("returns"))
            .where(
                ODSWBGoodsReturn.shop_id.in_(shop_ids),
                ODSWBGoodsReturn.order_dt >= date_from,
                ODSWBGoodsReturn.order_dt < date_to,
            )
            .group_by(day)
        )
        rows = (await db.execute(stmt)).all()
        return [{"day": str(r.day), "returns": _i(r.returns)} for r in rows]

    async def wb_top_products(
        self,
        db: AsyncSession,
        *,
        shop_ids: List[int],
        date_from: date,
        date_to: date,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """WB 热销商品 Top（按 nm_id 聚合）"""
        if not shop_ids:
            return []
        stmt = (
            select(
                ODSWBSupplierSale.nm_id.label("ext_id"),
                func.max(ODSWBSupplierSale.subject).label("name"),
                func.coalesce(func.sum(ODSWBSupplierSale.price_with_disc), 0).label(
                    "gmv"
                ),
                func.count().label("units"),
            )
            .where(
                ODSWBSupplierSale.shop_id.in_(shop_ids),
                ODSWBSupplierSale.date >= date_from,
                ODSWBSupplierSale.date < date_to,
                ODSWBSupplierSale.nm_id.isnot(None),
            )
            .group_by(ODSWBSupplierSale.nm_id)
            .order_by(func.sum(ODSWBSupplierSale.price_with_disc).desc())
            .limit(limit)
        )
        rows = (await db.execute(stmt)).all()
        return [
            {
                "ext_id": str(r.ext_id),
                "name": r.name or "",
                "gmv": _f(r.gmv),
                "units": _i(r.units),
            }
            for r in rows
        ]

    # ==================== Ozon ====================
    # Ozon 订单来自 FBO + FBS 两张表，销售额从各自商品明细表求和。

    async def _ozon_gmv_units_by_shop(
        self,
        db: AsyncSession,
        posting_model,
        product_model,
        date_col,
        *,
        shop_ids: List[int],
        date_from: date,
        date_to: date,
    ) -> Dict[int, Dict[str, float]]:
        """通用：按店铺聚合某类 Ozon 订单的 GMV 与件数"""
        if not shop_ids:
            return {}
        price_col = (
            ODSOzonFBOPostingProduct.price
            if product_model is ODSOzonFBOPostingProduct
            else ODSOzonFBSPostingProduct.price_amount
        )
        stmt = (
            select(
                posting_model.shop_id.label("shop_id"),
                func.coalesce(
                    func.sum(price_col * func.coalesce(product_model.quantity, 0)), 0
                ).label("gmv"),
                func.coalesce(func.sum(product_model.quantity), 0).label("units"),
            )
            .join(
                product_model,
                (product_model.posting_number == posting_model.posting_number)
                & (product_model.shop_id == posting_model.shop_id),
            )
            .where(
                posting_model.shop_id.in_(shop_ids),
                date_col >= date_from,
                date_col < date_to,
            )
            .group_by(posting_model.shop_id)
        )
        rows = (await db.execute(stmt)).all()
        return {r.shop_id: {"gmv": _f(r.gmv), "units": _i(r.units)} for r in rows}

    async def _ozon_orders_by_shop(
        self,
        db: AsyncSession,
        posting_model,
        date_col,
        *,
        shop_ids: List[int],
        date_from: date,
        date_to: date,
    ) -> Dict[int, int]:
        """通用：按店铺聚合某类 Ozon 订单量"""
        if not shop_ids:
            return {}
        stmt = (
            select(
                posting_model.shop_id.label("shop_id"),
                func.count().label("orders"),
            )
            .where(
                posting_model.shop_id.in_(shop_ids),
                date_col >= date_from,
                date_col < date_to,
            )
            .group_by(posting_model.shop_id)
        )
        rows = (await db.execute(stmt)).all()
        return {r.shop_id: _i(r.orders) for r in rows}

    async def ozon_sales_by_shop(
        self, db: AsyncSession, *, shop_ids: List[int], date_from: date, date_to: date
    ) -> List[Dict[str, Any]]:
        """Ozon 各店铺销售额与件数（FBO + FBS 合并）"""
        fbo = await self._ozon_gmv_units_by_shop(
            db,
            ODSOzonFBOPosting,
            ODSOzonFBOPostingProduct,
            ODSOzonFBOPosting.created_at,
            shop_ids=shop_ids,
            date_from=date_from,
            date_to=date_to,
        )
        fbs = await self._ozon_gmv_units_by_shop(
            db,
            ODSOzonFBSPosting,
            ODSOzonFBSPostingProduct,
            ODSOzonFBSPosting.in_process_at,
            shop_ids=shop_ids,
            date_from=date_from,
            date_to=date_to,
        )
        merged: Dict[int, Dict[str, float]] = {}
        for source in (fbo, fbs):
            for shop_id, vals in source.items():
                acc = merged.setdefault(shop_id, {"gmv": 0.0, "units": 0})
                acc["gmv"] += vals["gmv"]
                acc["units"] += vals["units"]
        return [
            {"shop_id": sid, "gmv": v["gmv"], "units": int(v["units"])}
            for sid, v in merged.items()
        ]

    async def ozon_orders_by_shop(
        self, db: AsyncSession, *, shop_ids: List[int], date_from: date, date_to: date
    ) -> List[Dict[str, Any]]:
        """Ozon 各店铺订单量（FBO + FBS 合并）"""
        fbo = await self._ozon_orders_by_shop(
            db,
            ODSOzonFBOPosting,
            ODSOzonFBOPosting.created_at,
            shop_ids=shop_ids,
            date_from=date_from,
            date_to=date_to,
        )
        fbs = await self._ozon_orders_by_shop(
            db,
            ODSOzonFBSPosting,
            ODSOzonFBSPosting.in_process_at,
            shop_ids=shop_ids,
            date_from=date_from,
            date_to=date_to,
        )
        merged: Dict[int, int] = {}
        for source in (fbo, fbs):
            for shop_id, orders in source.items():
                merged[shop_id] = merged.get(shop_id, 0) + orders
        return [{"shop_id": sid, "orders": o} for sid, o in merged.items()]

    async def ozon_returns_by_shop(
        self, db: AsyncSession, *, shop_ids: List[int], date_from: date, date_to: date
    ) -> List[Dict[str, Any]]:
        """Ozon 各店铺退货量"""
        if not shop_ids:
            return []
        stmt = (
            select(
                ODSOzonReturn.shop_id.label("shop_id"),
                func.count().label("returns"),
            )
            .where(
                ODSOzonReturn.shop_id.in_(shop_ids),
                ODSOzonReturn.return_date >= date_from,
                ODSOzonReturn.return_date < date_to,
            )
            .group_by(ODSOzonReturn.shop_id)
        )
        rows = (await db.execute(stmt)).all()
        return [{"shop_id": r.shop_id, "returns": _i(r.returns)} for r in rows]

    async def ozon_ad_spend_by_shop(
        self, db: AsyncSession, *, shop_ids: List[int], date_from: date, date_to: date
    ) -> List[Dict[str, Any]]:
        """Ozon 各店铺广告花费（money_spent）"""
        if not shop_ids:
            return []
        stmt = (
            select(
                ODSOzonAdvStatDaily.shop_id.label("shop_id"),
                func.coalesce(func.sum(ODSOzonAdvStatDaily.money_spent), 0).label(
                    "ad_spend"
                ),
            )
            .where(
                ODSOzonAdvStatDaily.shop_id.in_(shop_ids),
                ODSOzonAdvStatDaily.stat_date >= date_from,
                ODSOzonAdvStatDaily.stat_date < date_to,
            )
            .group_by(ODSOzonAdvStatDaily.shop_id)
        )
        rows = (await db.execute(stmt)).all()
        return [{"shop_id": r.shop_id, "ad_spend": _f(r.ad_spend)} for r in rows]

    async def _ozon_gmv_trend(
        self,
        db: AsyncSession,
        posting_model,
        product_model,
        date_col,
        *,
        shop_ids: List[int],
        date_from: date,
        date_to: date,
    ) -> Dict[str, float]:
        """通用：按日聚合某类 Ozon 订单 GMV"""
        if not shop_ids:
            return {}
        price_col = (
            ODSOzonFBOPostingProduct.price
            if product_model is ODSOzonFBOPostingProduct
            else ODSOzonFBSPostingProduct.price_amount
        )
        day = func.date(date_col).label("day")
        stmt = (
            select(
                day,
                func.coalesce(
                    func.sum(price_col * func.coalesce(product_model.quantity, 0)), 0
                ).label("gmv"),
            )
            .join(
                product_model,
                (product_model.posting_number == posting_model.posting_number)
                & (product_model.shop_id == posting_model.shop_id),
            )
            .where(
                posting_model.shop_id.in_(shop_ids),
                date_col >= date_from,
                date_col < date_to,
            )
            .group_by(day)
        )
        rows = (await db.execute(stmt)).all()
        return {str(r.day): _f(r.gmv) for r in rows}

    async def ozon_sales_trend(
        self, db: AsyncSession, *, shop_ids: List[int], date_from: date, date_to: date
    ) -> List[Dict[str, Any]]:
        """Ozon 按日销售额（FBO + FBS 合并）"""
        fbo = await self._ozon_gmv_trend(
            db,
            ODSOzonFBOPosting,
            ODSOzonFBOPostingProduct,
            ODSOzonFBOPosting.created_at,
            shop_ids=shop_ids,
            date_from=date_from,
            date_to=date_to,
        )
        fbs = await self._ozon_gmv_trend(
            db,
            ODSOzonFBSPosting,
            ODSOzonFBSPostingProduct,
            ODSOzonFBSPosting.in_process_at,
            shop_ids=shop_ids,
            date_from=date_from,
            date_to=date_to,
        )
        days = set(fbo) | set(fbs)
        return [
            {"day": d, "gmv": fbo.get(d, 0.0) + fbs.get(d, 0.0)} for d in sorted(days)
        ]

    async def _ozon_orders_trend(
        self,
        db: AsyncSession,
        posting_model,
        date_col,
        *,
        shop_ids: List[int],
        date_from: date,
        date_to: date,
    ) -> Dict[str, int]:
        """通用：按日聚合某类 Ozon 订单量"""
        if not shop_ids:
            return {}
        day = func.date(date_col).label("day")
        stmt = (
            select(day, func.count().label("orders"))
            .where(
                posting_model.shop_id.in_(shop_ids),
                date_col >= date_from,
                date_col < date_to,
            )
            .group_by(day)
        )
        rows = (await db.execute(stmt)).all()
        return {str(r.day): _i(r.orders) for r in rows}

    async def ozon_orders_trend(
        self, db: AsyncSession, *, shop_ids: List[int], date_from: date, date_to: date
    ) -> List[Dict[str, Any]]:
        """Ozon 按日订单量（FBO + FBS 合并）"""
        fbo = await self._ozon_orders_trend(
            db,
            ODSOzonFBOPosting,
            ODSOzonFBOPosting.created_at,
            shop_ids=shop_ids,
            date_from=date_from,
            date_to=date_to,
        )
        fbs = await self._ozon_orders_trend(
            db,
            ODSOzonFBSPosting,
            ODSOzonFBSPosting.in_process_at,
            shop_ids=shop_ids,
            date_from=date_from,
            date_to=date_to,
        )
        days = set(fbo) | set(fbs)
        return [
            {"day": d, "orders": fbo.get(d, 0) + fbs.get(d, 0)} for d in sorted(days)
        ]

    async def ozon_ad_trend(
        self, db: AsyncSession, *, shop_ids: List[int], date_from: date, date_to: date
    ) -> List[Dict[str, Any]]:
        """Ozon 按日广告花费"""
        if not shop_ids:
            return []
        day = ODSOzonAdvStatDaily.stat_date.label("day")
        stmt = (
            select(
                day,
                func.coalesce(func.sum(ODSOzonAdvStatDaily.money_spent), 0).label(
                    "ad_spend"
                ),
            )
            .where(
                ODSOzonAdvStatDaily.shop_id.in_(shop_ids),
                ODSOzonAdvStatDaily.stat_date >= date_from,
                ODSOzonAdvStatDaily.stat_date < date_to,
            )
            .group_by(day)
        )
        rows = (await db.execute(stmt)).all()
        return [{"day": str(r.day), "ad_spend": _f(r.ad_spend)} for r in rows]

    async def ozon_returns_trend(
        self, db: AsyncSession, *, shop_ids: List[int], date_from: date, date_to: date
    ) -> List[Dict[str, Any]]:
        """Ozon 按日退货量"""
        if not shop_ids:
            return []
        day = func.date(ODSOzonReturn.return_date).label("day")
        stmt = (
            select(day, func.count().label("returns"))
            .where(
                ODSOzonReturn.shop_id.in_(shop_ids),
                ODSOzonReturn.return_date >= date_from,
                ODSOzonReturn.return_date < date_to,
            )
            .group_by(day)
        )
        rows = (await db.execute(stmt)).all()
        return [{"day": str(r.day), "returns": _i(r.returns)} for r in rows]

    async def ozon_top_products(
        self,
        db: AsyncSession,
        *,
        shop_ids: List[int],
        date_from: date,
        date_to: date,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Ozon 热销商品 Top（FBO + FBS 按 SKU 合并）"""
        if not shop_ids:
            return []
        merged: Dict[str, Dict[str, Any]] = {}
        specs = [
            (
                ODSOzonFBOPosting,
                ODSOzonFBOPostingProduct,
                ODSOzonFBOPostingProduct.price,
                ODSOzonFBOPosting.created_at,
            ),
            (
                ODSOzonFBSPosting,
                ODSOzonFBSPostingProduct,
                ODSOzonFBSPostingProduct.price_amount,
                ODSOzonFBSPosting.in_process_at,
            ),
        ]
        for posting_model, product_model, price_col, date_col in specs:
            stmt = (
                select(
                    product_model.sku.label("ext_id"),
                    func.max(product_model.name).label("name"),
                    func.coalesce(
                        func.sum(price_col * func.coalesce(product_model.quantity, 0)),
                        0,
                    ).label("gmv"),
                    func.coalesce(func.sum(product_model.quantity), 0).label("units"),
                )
                .join(
                    posting_model,
                    (product_model.posting_number == posting_model.posting_number)
                    & (product_model.shop_id == posting_model.shop_id),
                )
                .where(
                    posting_model.shop_id.in_(shop_ids),
                    date_col >= date_from,
                    date_col < date_to,
                    product_model.sku.isnot(None),
                )
                .group_by(product_model.sku)
            )
            rows = (await db.execute(stmt)).all()
            for r in rows:
                key = str(r.ext_id)
                acc = merged.setdefault(
                    key, {"ext_id": key, "name": r.name or "", "gmv": 0.0, "units": 0}
                )
                acc["gmv"] += _f(r.gmv)
                acc["units"] += _i(r.units)
                if not acc["name"] and r.name:
                    acc["name"] = r.name
        ranked = sorted(merged.values(), key=lambda x: x["gmv"], reverse=True)
        return ranked[:limit]


dashboard_crud = DashboardCRUD()
