"""
ODS 层 - 销售漏斗和退货数据 CRUD 操作
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.models.ods.wildberries.funnel import ODSWBSalesFunnel
from kunpeng.models.ods.wildberries.returns import ODSWBGoodsReturn

logger = logging.getLogger(__name__)


def parse_iso_datetime(date_str: Optional[str]) -> Optional[datetime]:
    """
    解析 ISO 8601 格式的日期时间字符串

    支持格式:
    - "2026-04-19T16:56:32Z"
    - "2026-04-19T16:56:32.123Z"
    - "2026-04-19T16:56:32+00:00"
    """
    if not date_str:
        return None

    try:
        # 处理 'Z' 后缀
        if date_str.endswith("Z"):
            date_str = date_str[:-1] + "+00:00"
        return datetime.fromisoformat(date_str)
    except (ValueError, AttributeError):
        logger.warning(f"无法解析日期时间: {date_str}")
        return None


class CRUDODSWBSalesFunnel(CRUDBase[ODSWBSalesFunnel, Dict[str, Any], Dict[str, Any]]):
    """ODS 销售漏斗数据 CRUD"""

    async def list_sales_funnels(
        self,
        db: AsyncSession,
        *,
        shop_id: Optional[int] = None,
        allowed_shop_ids: Optional[Sequence[int]] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        nm_id: Optional[int] = None,
        vendor_code: Optional[str] = None,
        brand_name: Optional[str] = None,
        subject_name: Optional[str] = None,
    ) -> List[ODSWBSalesFunnel]:
        query = select(ODSWBSalesFunnel)

        if allowed_shop_ids is not None:
            if not allowed_shop_ids:
                return []
            query = query.where(ODSWBSalesFunnel.shop_id.in_(allowed_shop_ids))

        if shop_id is not None:
            query = query.where(ODSWBSalesFunnel.shop_id == shop_id)
        if date_from is not None:
            query = query.where(ODSWBSalesFunnel.date_from >= date_from)
        if date_to is not None:
            query = query.where(ODSWBSalesFunnel.date_to <= date_to)
        if nm_id is not None:
            query = query.where(ODSWBSalesFunnel.nm_id == nm_id)
        if vendor_code:
            query = query.where(ODSWBSalesFunnel.vendor_code == vendor_code)
        if brand_name:
            query = query.where(ODSWBSalesFunnel.brand_name == brand_name)
        if subject_name:
            query = query.where(ODSWBSalesFunnel.subject_name == subject_name)

        query = query.order_by(
            ODSWBSalesFunnel.date_from.desc(),
            ODSWBSalesFunnel.date_to.desc(),
            ODSWBSalesFunnel.nm_id.asc(),
        )
        result = await db.execute(query)
        return list(result.scalars().all())

    async def _get_existing(
        self,
        db: AsyncSession,
        shop_id: int,
        date_from: Optional[date],
        date_to: Optional[date],
        nm_id: Optional[int],
    ) -> Optional[ODSWBSalesFunnel]:
        """根据唯一索引获取现有记录"""
        if not date_from or not date_to or not nm_id:
            return None
        result = await db.execute(
            select(ODSWBSalesFunnel).where(
                (ODSWBSalesFunnel.shop_id == shop_id)
                & (ODSWBSalesFunnel.date_from == date_from)
                & (ODSWBSalesFunnel.date_to == date_to)
                & (ODSWBSalesFunnel.nm_id == nm_id)
            )
        )
        return result.scalar_one_or_none()

    async def create_many(
        self,
        db: AsyncSession,
        *,
        funnel_data: List[Dict[str, Any]],
        shop_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[ODSWBSalesFunnel]:
        """批量创建/更新 ODS 销售漏斗数据（幂等同步）"""
        logger.debug(
            f"[ODS CRUD] 开始幂等同步销售漏斗数据 - 店铺: {shop_id}, 数据量: {len(funnel_data)}"
        )

        result_list = []
        # Keep objects already resolved in this batch. API responses can contain
        # the same product more than once; querying the database alone does not
        # reliably find a newly-added (still pending) SQLAlchemy object.
        records_by_nm_id: Dict[int, ODSWBSalesFunnel] = {}

        for data in funnel_data:
            # 提取嵌套数据
            product = data.get("product", {})
            # WB returns nmId under product. Keep the top-level fallback for
            # older/flattened payloads, but use the same value for lookup and
            # persistence so the unique key is checked correctly.
            nm_id = product.get("nmId")
            if nm_id is None:
                nm_id = data.get("nmId")
            statistic = data.get("statistic", {})
            selected = statistic.get("selected", {})
            conversions = selected.get("conversions", {})
            wb_club = selected.get("wbClub", {})
            stocks = product.get("stocks", {})
            time_to_ready = selected.get("timeToReady", {})

            # 构建 ODS 记录数据
            ods_data = {
                "shop_id": shop_id,
                "date_from": date_from,
                "date_to": date_to,
                "row_data": data,  # 原始 JSON
                # product 字段
                "nm_id": nm_id,
                "vendor_code": product.get("vendorCode"),
                "subject_name": product.get("subjectName"),
                "brand_name": product.get("brandName"),
                "title": product.get("title"),
                "subject_id": product.get("subjectId"),
                "product_rating": product.get("productRating"),
                "feedback_rating": product.get("feedbackRating"),
                "tags": product.get("tags"),
                # timeToReady 字段
                "time_to_ready_days": time_to_ready.get("days"),
                "time_to_ready_hours": time_to_ready.get("hours"),
                "time_to_ready_mins": time_to_ready.get("mins"),
                # product.stocks 字段
                "stocks_wb": stocks.get("wb"),
                "stocks_mp": stocks.get("mp"),
                "stocks_balance_sum": stocks.get("balanceSum"),
                # statistic.selected 字段
                "open_count": selected.get("openCount"),
                "cart_count": selected.get("cartCount"),
                "order_count": selected.get("orderCount"),
                "order_sum": selected.get("orderSum"),
                "buyout_count": selected.get("buyoutCount"),
                "buyout_sum": selected.get("buyoutSum"),
                "cancel_count": selected.get("cancelCount"),
                "cancel_sum": selected.get("cancelSum"),
                "avg_price": selected.get("avgPrice"),
                "avg_orders_count_per_day": selected.get("avgOrdersCountPerDay"),
                "share_order_percent": selected.get("shareOrderPercent"),
                "add_to_wishlist": selected.get("addToWishlist"),
                "localization_percent": selected.get("localizationPercent"),
                # statistic.selected.conversions 字段
                "add_to_cart_percent": conversions.get("addToCartPercent"),
                "cart_to_order_percent": conversions.get("cartToOrderPercent"),
                "buyout_percent": conversions.get("buyoutPercent"),
                # statistic.selected.wbClub 字段
                "wb_club_order_count": wb_club.get("orderCount"),
                "wb_club_order_sum": wb_club.get("orderSum"),
                "wb_club_buyout_count": wb_club.get("buyoutCount"),
                "wb_club_buyout_sum": wb_club.get("buyoutSum"),
                "wb_club_cancel_count": wb_club.get("cancelCount"),
                "wb_club_cancel_sum": wb_club.get("cancelSum"),
                "wb_club_avg_price": wb_club.get("avgPrice"),
                "wb_club_buyout_percent": wb_club.get("buyoutPercent"),
                "wb_club_avg_order_count_per_day": wb_club.get("avgOrderCountPerDay"),
            }

            if date_from and date_to and nm_id is not None:
                # 检查是否已存在
                if nm_id in records_by_nm_id:
                    existing = records_by_nm_id[nm_id]
                else:
                    existing = await self._get_existing(
                        db, shop_id, date_from, date_to, nm_id
                    )

                if existing:
                    # 更新现有记录
                    for field, value in ods_data.items():
                        if hasattr(existing, field):
                            setattr(existing, field, value)
                    if nm_id not in records_by_nm_id:
                        records_by_nm_id[nm_id] = existing
                        result_list.append(existing)
                    continue

            # 创建新记录
            ods_record = ODSWBSalesFunnel(**ods_data)
            db.add(ods_record)
            result_list.append(ods_record)
            if date_from and date_to and nm_id is not None:
                records_by_nm_id[nm_id] = ods_record

        logger.debug(f"[ODS CRUD] 准备提交数据库 - 总记录: {len(result_list)}")
        try:
            await db.commit()
        except Exception:
            # Leave the shared scheduler session usable after a failed flush or
            # commit instead of leaking SQLAlchemy PendingRollback state.
            await db.rollback()
            raise
        logger.debug(f"[ODS CRUD] 数据库提交成功")
        for record in result_list:
            await db.refresh(record)
        logger.debug(f"[ODS CRUD] 幂等同步完成 - 总计: {len(result_list)}")
        return result_list


class CRUDODSWBGoodsReturn(CRUDBase[ODSWBGoodsReturn, Dict[str, Any], Dict[str, Any]]):
    """ODS 退货数据 CRUD"""

    async def _get_existing(
        self, db: AsyncSession, shop_id: int, srid: Optional[str]
    ) -> Optional[ODSWBGoodsReturn]:
        """根据唯一索引获取现有记录"""
        if not srid:
            return None
        result = await db.execute(
            select(ODSWBGoodsReturn).where(
                (ODSWBGoodsReturn.shop_id == shop_id) & (ODSWBGoodsReturn.srid == srid)
            )
        )
        return result.scalar_one_or_none()

    async def create_many(
        self,
        db: AsyncSession,
        *,
        returns_data: List[Dict[str, Any]],
        shop_id: int,
    ) -> List[ODSWBGoodsReturn]:
        """批量创建/更新 ODS 退货数据（幂等同步）"""
        logger.debug(
            f"[ODS CRUD] 开始幂等同步退货数据 - 店铺: {shop_id}, 数据量: {len(returns_data)}"
        )

        result_list = []

        for data in returns_data:
            srid = data.get("srid")
            # 构建 ODS 记录数据
            ods_data = {
                "shop_id": shop_id,
                "row_data": data,  # 原始 JSON
                # 展开的常用字段 from actual response
                "barcode": data.get("barcode"),
                "brand": data.get("brand"),
                "completed_dt": parse_iso_datetime(data.get("completedDt")),
                "dst_office_address": data.get("dstOfficeAddress"),
                "dst_office_id": data.get("dstOfficeId"),
                "expired_dt": parse_iso_datetime(data.get("expiredDt")),
                "is_status_active": data.get("isStatusActive"),
                "nm_id": data.get("nmId"),
                "order_dt": parse_iso_datetime(data.get("orderDt")),
                "order_id": data.get("orderId"),
                "ready_to_return_dt": parse_iso_datetime(data.get("readyToReturnDt")),
                "reason": data.get("reason"),
                "return_type": data.get("returnType"),
                "shk_id": data.get("shkId"),
                "srid": srid,
                "status": data.get("status"),
                "sticker_id": data.get("stickerId"),
                "subject_name": data.get("subjectName"),
                "tech_size": data.get("techSize"),
            }

            if srid:
                # 检查是否已存在
                existing = await self._get_existing(db, shop_id, srid)

                if existing:
                    # 更新现有记录
                    for field, value in ods_data.items():
                        if hasattr(existing, field):
                            setattr(existing, field, value)
                    result_list.append(existing)
                    continue

            # 创建新记录
            ods_record = ODSWBGoodsReturn(**ods_data)
            db.add(ods_record)
            result_list.append(ods_record)

        logger.debug(f"[ODS CRUD] 准备提交数据库 - 总记录: {len(result_list)}")
        await db.commit()
        logger.debug(f"[ODS CRUD] 数据库提交成功")
        for record in result_list:
            await db.refresh(record)
        logger.debug(f"[ODS CRUD] 幂等同步完成 - 总计: {len(result_list)}")
        return result_list


# CRUD 实例
crud_ods_wb_sales_funnel = CRUDODSWBSalesFunnel(ODSWBSalesFunnel)
crud_ods_wb_goods_return = CRUDODSWBGoodsReturn(ODSWBGoodsReturn)
