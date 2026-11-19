"""
ODS 层 - 销售数据 CRUD 操作
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.models.ods.wildberries.sales import ODSWBSupplierOrder, ODSWBSupplierSale

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


class CRUDODSWBSupplierSale(
    CRUDBase[ODSWBSupplierSale, Dict[str, Any], Dict[str, Any]]
):
    """ODS 销售数据 CRUD"""

    async def _get_existing(
        self, db: AsyncSession, shop_id: int, srid: str
    ) -> Optional[ODSWBSupplierSale]:
        """根据唯一索引获取现有记录"""
        result = await db.execute(
            select(ODSWBSupplierSale).where(
                (ODSWBSupplierSale.shop_id == shop_id)
                & (ODSWBSupplierSale.srid == srid)
            )
        )
        return result.scalar_one_or_none()

    async def create_many(
        self,
        db: AsyncSession,
        *,
        sales_data: List[Dict[str, Any]],
        shop_id: int,
        date_from: Optional[date] = None,  # 向后兼容
        date_to: Optional[date] = None,  # 向后兼容
    ) -> List[ODSWBSupplierSale]:
        """批量创建/更新 ODS 销售数据（幂等同步）"""
        logger.debug(
            f"[ODS CRUD] 开始幂等同步销售数据 - 店铺: {shop_id}, 数据量: {len(sales_data)}"
        )

        result_list = []

        for data in sales_data:
            srid = data.get("srid")
            if not srid:
                logger.warning(f"[ODS CRUD] 销售数据缺少srid，跳过: {data}")
                continue

            # 构建 ODS 记录数据
            ods_data = {
                "shop_id": shop_id,
                "row_data": data,  # 原始 JSON
                # 展开的常用字段
                "date": parse_iso_datetime(data.get("date")),
                "last_change_date": parse_iso_datetime(data.get("lastChangeDate")),
                "warehouse_name": data.get("warehouseName"),
                "warehouse_type": data.get("warehouseType"),
                "country_name": data.get("countryName"),
                "oblast_okrug_name": data.get("oblastOkrugName"),
                "region_name": data.get("regionName"),
                "supplier_article": data.get("supplierArticle"),
                "nm_id": data.get("nmId"),
                "barcode": data.get("barcode"),
                "category": data.get("category"),
                "subject": data.get("subject"),
                "brand": data.get("brand"),
                "tech_size": data.get("techSize"),
                "income_id": data.get("incomeID", data.get("incomeId")),
                "is_supply": data.get("isSupply"),
                "is_realization": data.get("isRealization"),
                "total_price": data.get("totalPrice"),
                "discount_percent": data.get("discountPercent"),
                "spp": data.get("spp"),
                "payment_sale_amount": data.get("paymentSaleAmount"),
                "for_pay": data.get("forPay"),
                "finished_price": data.get("finishedPrice"),
                "price_with_disc": data.get("priceWithDisc"),
                "sale_id": data.get("saleID", data.get("saleId")),
                "sticker": data.get("sticker"),
                "g_number": data.get("gNumber"),
                "srid": srid,
            }

            # 检查是否已存在
            existing = await self._get_existing(db, shop_id, srid)

            if existing:
                # 更新现有记录
                for field, value in ods_data.items():
                    if hasattr(existing, field):
                        setattr(existing, field, value)
                result_list.append(existing)
            else:
                # 创建新记录
                ods_record = ODSWBSupplierSale(**ods_data)
                db.add(ods_record)
                result_list.append(ods_record)

        logger.debug(f"[ODS CRUD] 准备提交数据库 - 总记录: {len(result_list)}")
        await db.commit()
        logger.debug(f"[ODS CRUD] 数据库提交成功")
        for record in result_list:
            await db.refresh(record)
        logger.debug(f"[ODS CRUD] 幂等同步完成 - 总计: {len(result_list)}")
        return result_list


class CRUDODSWBSupplierOrder(
    CRUDBase[ODSWBSupplierOrder, Dict[str, Any], Dict[str, Any]]
):
    """ODS 订单数据 CRUD"""

    async def _get_existing(
        self, db: AsyncSession, shop_id: int, srid: str
    ) -> Optional[ODSWBSupplierOrder]:
        """根据唯一索引获取现有记录"""
        if not srid:
            return None
        result = await db.execute(
            select(ODSWBSupplierOrder).where(
                (ODSWBSupplierOrder.shop_id == shop_id)
                & (ODSWBSupplierOrder.srid == srid)
            )
        )
        return result.scalar_one_or_none()

    async def create_many(
        self,
        db: AsyncSession,
        *,
        orders_data: List[Dict[str, Any]],
        shop_id: int,
        date_from: Optional[date] = None,  # 向后兼容
        date_to: Optional[date] = None,  # 向后兼容
    ) -> List[ODSWBSupplierOrder]:
        """批量创建/更新 ODS 订单数据（幂等同步）"""
        logger.debug(
            f"[ODS CRUD] 开始幂等同步订单数据 - 店铺: {shop_id}, 数据量: {len(orders_data)}"
        )

        result_list = []

        for data in orders_data:
            srid = data.get("srid")
            # 构建 ODS 记录数据
            ods_data = {
                "shop_id": shop_id,
                "row_data": data,  # 原始 JSON
                # 展开的常用字段
                "date": parse_iso_datetime(data.get("date")),
                "last_change_date": parse_iso_datetime(data.get("lastChangeDate")),
                "warehouse_name": data.get("warehouseName"),
                "country_name": data.get("countryName"),
                "oblast_okrug_name": data.get("oblastOkrugName"),
                "region_name": data.get("regionName"),
                "supplier_article": data.get("supplierArticle"),
                "nm_id": data.get("nmId"),
                "barcode": data.get("barcode"),
                "category": data.get("category"),
                "subject": data.get("subject"),
                "brand": data.get("brand"),
                "tech_size": data.get("techSize"),
                "income_id": data.get("incomeID", data.get("incomeId")),
                "is_supply": data.get("isSupply"),
                "is_realization": data.get("isRealization"),
                "total_price": data.get("totalPrice"),
                "discount_percent": data.get("discountPercent"),
                "spp": data.get("spp"),
                "finished_price": data.get("finishedPrice"),
                "price_with_disc": data.get("priceWithDisc"),
                "is_cancel": data.get("isCancel"),
                "cancel_date": parse_iso_datetime(data.get("cancelDate")),
                "order_type": data.get("orderType"),
                "sticker": data.get("sticker"),
                "g_number": data.get("gNumber"),
                "srid": srid,
                "odid": data.get("odid"),
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
            ods_record = ODSWBSupplierOrder(**ods_data)
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
crud_ods_wb_supplier_sale = CRUDODSWBSupplierSale(ODSWBSupplierSale)
crud_ods_wb_supplier_order = CRUDODSWBSupplierOrder(ODSWBSupplierOrder)
