"""
ODS 层 - 财务数据 CRUD 操作 (新API版本)
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.models.ods.wildberries.finance import ODSWBSalesReport

logger = logging.getLogger(__name__)


def parse_iso_datetime(date_str: Optional[str]) -> Optional[date]:
    """
    解析 ISO 8601 格式的日期时间字符串，只提取日期部分
    """
    if not date_str or date_str == "":
        return None

    try:
        # 如果有 T，只取前面的日期部分
        if "T" in date_str:
            date_part = date_str.split("T")[0]
            return date.fromisoformat(date_part)
        return date.fromisoformat(date_str)
    except (ValueError, AttributeError):
        logger.warning(f"无法解析日期: {date_str}")
        return None


def parse_datetime_field(date_str: Optional[str]) -> Optional[datetime]:
    """
    解析 ISO 8601 格式的日期时间字符串，保存完整时间
    """
    if not date_str or date_str == "":
        return None

    try:
        # 去掉时区部分（+03:00 或 Z），只保留日期时间部分
        if "+" in date_str:
            datetime_part = date_str.split("+")[0]
            # 尝试解析不带时区的时间
            return datetime.fromisoformat(datetime_part)
        elif "Z" in date_str:
            datetime_part = date_str.replace("Z", "")
            return datetime.fromisoformat(datetime_part)
        else:
            return datetime.fromisoformat(date_str)
    except (ValueError, AttributeError):
        logger.warning(f"无法解析日期时间: {date_str}")
        return None


def safe_decimal(value: Any) -> Optional[Decimal]:
    """
    安全转换为 Decimal，处理字符串和数字类型
    """
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (ValueError, TypeError):
        return None


def safe_int(value: Any) -> Optional[int]:
    """
    安全转换为 int
    """
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def safe_str(value: Any) -> Optional[str]:
    """
    安全转换为 str
    """
    if value is None:
        return None
    return str(value)


class CRUDODSWBSalesReport(CRUDBase[ODSWBSalesReport, Dict[str, Any], Dict[str, Any]]):
    """ODS 销售报告 CRUD (新API版本)"""

    async def _get_existing_item(
        self,
        db: AsyncSession,
        shop_id: int,
        date_from: date,
        date_to: date,
        rrd_id: int,
    ) -> Optional[ODSWBSalesReport]:
        """根据唯一约束获取现有记录"""
        query = select(self.model).where(
            (self.model.shop_id == shop_id)
            & (self.model.date_from == date_from)
            & (self.model.date_to == date_to)
            & (self.model.rrd_id == rrd_id)
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    def _extract_item_data(
        self,
        item: Dict[str, Any],
        shop_id: int,
    ) -> Dict[str, Any]:
        """
        从新API响应中提取数据到模型字段
        字段映射：API驼峰命名 -> 模型下划线命名
        """
        return {
            "shop_id": shop_id,
            "date_from": safe_str(item.get("dateFrom")),
            "date_to": safe_str(item.get("dateTo")),
            "row_data": item,
            # ========== 报告基本信息 ==========
            "report_id": safe_int(item.get("reportId")),
            "create_date": parse_iso_datetime(item.get("createDate")),
            "currency": safe_str(item.get("currency")),
            "report_type": safe_int(item.get("reportType")),
            # ========== 记录ID ==========
            "rrd_id": safe_int(item.get("rrdId")),
            "gi_id": safe_int(item.get("giId")),
            # ========== 商品信息 ==========
            "nm_id": safe_int(item.get("nmId")),
            "brand_name": safe_str(item.get("brandName")),
            "vendor_code": safe_str(item.get("vendorCode")),
            "title": safe_str(item.get("title")),
            "tech_size": safe_str(item.get("techSize")),
            "sku": safe_str(item.get("sku")),
            "subject_name": safe_str(item.get("subjectName")),
            # ========== 文档和操作类型 ==========
            "doc_type_name": safe_str(item.get("docTypeName")),
            "seller_oper_name": safe_str(item.get("sellerOperName")),
            "bonus_type_name": safe_str(item.get("bonusTypeName")),
            # ========== 数量 ==========
            "quantity": safe_int(item.get("quantity")),
            "delivery_amount": safe_int(item.get("deliveryAmount")),
            "return_amount": safe_int(item.get("returnAmount")),
            "dlv_prc": safe_int(item.get("dlvPrc")),
            # ========== 价格和金额 ==========
            "retail_price": safe_decimal(item.get("retailPrice")),
            "retail_amount": safe_decimal(item.get("retailAmount")),
            "retail_price_with_disc": safe_decimal(item.get("retailPriceWithDisc")),
            "sale_percent": safe_decimal(item.get("salePercent")),
            # ========== 佣金 ==========
            "commission_percent": safe_decimal(item.get("commissionPercent")),
            "spp": safe_decimal(item.get("spp")),
            "kvw_base": safe_decimal(item.get("kvwBase")),
            "kvw": safe_decimal(item.get("kvw")),
            "ppvz_sales_commission": safe_decimal(item.get("ppvzSalesCommission")),
            "vw": safe_decimal(item.get("vw")),
            "vw_nds": safe_decimal(item.get("vwNds")),
            # ========== 支付和结算 ==========
            "for_pay": safe_decimal(item.get("forPay")),
            "ppvz_reward": safe_decimal(item.get("ppvzReward")),
            "acquiring_fee": safe_decimal(item.get("acquiringFee")),
            "acquiring_percent": safe_decimal(item.get("acquiringPercent")),
            "payment_schedule": safe_str(item.get("paymentSchedule")),
            # ========== 物流和仓库 ==========
            "delivery_service": safe_decimal(item.get("deliveryService")),
            "paid_storage": safe_decimal(item.get("paidStorage")),
            "paid_acceptance": safe_decimal(item.get("paidAcceptance")),
            "rebill_logistic_cost": safe_decimal(item.get("rebillLogisticCost")),
            "rebill_logistic_org": safe_str(item.get("rebillLogisticOrg")),
            "gi_box_type_name": safe_str(item.get("giBoxTypeName")),
            "office_name": safe_str(item.get("officeName")),
            "ppvz_office_name": safe_str(item.get("ppvzOfficeName")),
            "ppvz_office_id": safe_int(item.get("ppvzOfficeId")),
            # ========== 折扣和促销 ==========
            "product_discount_for_report": safe_decimal(
                item.get("productDiscountForReport")
            ),
            "seller_promo": safe_decimal(item.get("sellerPromo")),
            "seller_promo_id": safe_int(item.get("sellerPromoId")),
            "seller_promo_discount": safe_decimal(item.get("sellerPromoDiscount")),
            "wibes_discount_percent": safe_decimal(item.get("wibesDiscountPercent")),
            "cashback_amount": safe_decimal(item.get("cashbackAmount")),
            "cashback_discount": safe_decimal(item.get("cashbackDiscount")),
            "cashback_commission_change": safe_decimal(
                item.get("cashbackCommissionChange")
            ),
            "loyalty_id": safe_int(item.get("loyaltyId")),
            "loyalty_discount": safe_decimal(item.get("loyaltyDiscount")),
            "uuid_promocode": safe_str(item.get("uuidPromocode")),
            "sale_price_promocode_discount_prc": safe_decimal(
                item.get("salePricePromocodeDiscountPrc")
            ),
            "sale_price_affiliated_discount_prc": safe_decimal(
                item.get("salePriceAffiliatedDiscountPrc")
            ),
            "sale_price_wholesale_discount_prc": safe_decimal(
                item.get("salePriceWholesaleDiscountPrc")
            ),
            "article_substitution": safe_str(item.get("articleSubstitution")),
            # ========== 日期和时间 ==========
            "order_dt": parse_datetime_field(item.get("orderDt")),
            "sale_dt": parse_datetime_field(item.get("saleDt")),
            "rr_date": parse_datetime_field(item.get("rrDate")),
            "fix_tariff_date_from": safe_str(item.get("fixTariffDateFrom")),
            "fix_tariff_date_to": safe_str(item.get("fixTariffDateTo")),
            # ========== 标识和条码 ==========
            "shk_id": safe_int(item.get("shkId")),
            "sticker_id": safe_str(item.get("stickerId")),
            "order_id": safe_int(item.get("orderId")),
            "order_uid": safe_str(item.get("orderUid")),
            "srid": safe_str(item.get("srid")),
            "trbx_id": safe_str(item.get("trbxId")),
            # ========== 供应商和支付信息 ==========
            "ppvz_supplier_name": safe_str(item.get("ppvzSupplierName")),
            "ppvz_supplier_inn": safe_str(item.get("ppvzSupplierInn")),
            "declaration_number": safe_str(item.get("declarationNumber")),
            "acquiring_bank": safe_str(item.get("acquiringBank")),
            "payment_processing": safe_str(item.get("paymentProcessing")),
            # ========== 国家和类型 ==========
            "country": safe_str(item.get("country")),
            "is_b2b": item.get("isB2b"),
            "srv_dbs": item.get("srvDbs"),
            "is_kgvp_v2": safe_int(item.get("isKgvpV2")),
            "sup_rating_up": safe_int(item.get("supRatingUp")),
            # ========== 费用和惩罚 ==========
            "penalty": safe_decimal(item.get("penalty")),
            "additional_payment": safe_decimal(item.get("additionalPayment")),
            "deduction": safe_decimal(item.get("deduction")),
            "installment_cofinancing_amount": safe_decimal(
                item.get("installmentCofinancingAmount")
            ),
            # ========== 物流配送 ==========
            "delivery_method": safe_str(item.get("deliveryMethod")),
        }

    async def create_many(
        self,
        db: AsyncSession,
        *,
        items: List[Dict[str, Any]],
        shop_id: int,
    ) -> List[ODSWBSalesReport]:
        """批量创建/更新销售报告 (新API版本)"""
        logger.debug(
            f"[ODS Finance] 开始同步销售报告 - 店铺: {shop_id}, 数据量: {len(items)}"
        )

        result_list = []
        updated_count = 0
        created_count = 0

        for item in items:
            # 提取数据
            item_data = self._extract_item_data(
                item,
                shop_id,
            )

            rrd_id = item_data.get("rrd_id")
            # 查找现有记录
            existing = None
            if rrd_id is not None:
                date_from = item_data.get("date_from")
                date_to = item_data.get("date_to")
                existing = await self._get_existing_item(
                    db, shop_id, date_from, date_to, rrd_id
                )

            if existing:
                # 更新现有记录
                for field, value in item_data.items():
                    if field != "id" and hasattr(existing, field):
                        setattr(existing, field, value)
                result_list.append(existing)
                updated_count += 1
            else:
                # 创建新记录
                new_item = self.model(**item_data)
                db.add(new_item)
                result_list.append(new_item)
                created_count += 1

        await db.flush()

        logger.debug(
            f"[ODS Finance] 同步完成 - 新增: {created_count}, 更新: {updated_count}, 总计: {len(result_list)}"
        )
        return result_list


# CRUD 实例
crud_ods_wb_sales_report = CRUDODSWBSalesReport(ODSWBSalesReport)
