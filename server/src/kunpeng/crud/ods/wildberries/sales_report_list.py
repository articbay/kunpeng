"""Wildberries 财务报表列表 CRUD。"""

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.models.ods.wildberries.sales_report_list import \
    ODSWBSalesReportList
from kunpeng.utils.timezone import now_platform


def _to_date(value: Any) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value).split("T", maxsplit=1)[0])
    except (TypeError, ValueError):
        return None


def _to_decimal(value: Any) -> Optional[Decimal]:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


class CRUDODSWBSalesReportList(
    CRUDBase[ODSWBSalesReportList, Dict[str, Any], Dict[str, Any]]
):
    """按店铺和报表 ID 幂等保存财务报表汇总。"""

    async def get_by_shop_and_report(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        report_id: int,
    ) -> Optional[ODSWBSalesReportList]:
        result = await db.execute(
            select(ODSWBSalesReportList).where(
                ODSWBSalesReportList.shop_id == shop_id,
                ODSWBSalesReportList.report_id == report_id,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_many(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        reports: List[Dict[str, Any]],
    ) -> List[ODSWBSalesReportList]:
        records: List[ODSWBSalesReportList] = []
        synced_at = now_platform()

        for item in reports:
            try:
                report_id = int(item["reportId"])
            except (KeyError, TypeError, ValueError):
                continue

            date_from = _to_date(item.get("dateFrom"))
            date_to = _to_date(item.get("dateTo"))
            if date_from is None or date_to is None:
                continue

            values = {
                "shop_id": shop_id,
                "report_id": report_id,
                "seller_finance_name": item.get("sellerFinanceName"),
                "date_from": date_from,
                "date_to": date_to,
                "create_date": _to_date(item.get("createDate")),
                "currency": item.get("currency"),
                "report_type": item.get("reportType"),
                "retail_amount_sum": _to_decimal(item.get("retailAmountSum")),
                "for_pay_sum": _to_decimal(item.get("forPaySum")),
                "avg_sale_percent": _to_decimal(item.get("avgSalePercent")),
                "delivery_service_sum": _to_decimal(item.get("deliveryServiceSum")),
                "paid_storage_sum": _to_decimal(item.get("paidStorageSum")),
                "paid_acceptance_sum": _to_decimal(item.get("paidAcceptanceSum")),
                "deduction_sum": _to_decimal(item.get("deductionSum")),
                "penalty_sum": _to_decimal(item.get("penaltySum")),
                "additional_payment_sum": _to_decimal(item.get("additionalPaymentSum")),
                "cashback_amount_sum": _to_decimal(item.get("cashbackAmountSum")),
                "cashback_discount_sum": _to_decimal(item.get("cashbackDiscountSum")),
                "cashback_commission_change_sum": _to_decimal(
                    item.get("cashbackCommissionChangeSum")
                ),
                "payment_schedule": (
                    str(item["paymentSchedule"])
                    if item.get("paymentSchedule") is not None
                    else None
                ),
                "bank_payment_sum": _to_decimal(item.get("bankPaymentSum")),
                "row_data": item,
                "synced_at": synced_at,
            }
            existing = await self.get_by_shop_and_report(
                db,
                shop_id=shop_id,
                report_id=report_id,
            )
            if existing:
                for field, value in values.items():
                    setattr(existing, field, value)
                record = existing
            else:
                record = ODSWBSalesReportList(**values)
                db.add(record)
            records.append(record)

        try:
            await db.commit()
            for record in records:
                await db.refresh(record)
        except Exception:
            await db.rollback()
            raise
        return records


crud_ods_wb_sales_report_list = CRUDODSWBSalesReportList(ODSWBSalesReportList)
