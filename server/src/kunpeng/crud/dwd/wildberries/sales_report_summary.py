"""Wildberries 财务报告周汇总 ODS-to-DWD 转换。"""

from collections.abc import Sequence
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.dwd.wildberries.sales_report_summary import DWDWBSalesReportSummary
from kunpeng.models.ods.wildberries.sales_report_list import ODSWBSalesReportList

SUMMARY_FIELDS = (
    "report_id",
    "seller_finance_name",
    "date_from",
    "date_to",
    "create_date",
    "report_type",
    "retail_amount_sum",
    "cashback_discount_sum",
    "for_pay_sum",
    "avg_sale_percent",
    "delivery_service_sum",
    "paid_storage_sum",
    "paid_acceptance_sum",
    "deduction_sum",
    "penalty_sum",
    "additional_payment_sum",
    "cashback_commission_change_sum",
    "cashback_amount_sum",
    "payment_schedule",
    "bank_payment_sum",
    "currency",
)


def _to_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


class CRUDDWDWBSalesReportSummary:
    """按报告粒度幂等构建财务报告周汇总 DWD。"""

    @staticmethod
    async def get_source_batch(
        db: AsyncSession,
        *,
        after_id: int,
        batch_size: int,
        shop_id: int | None = None,
    ) -> list[ODSWBSalesReportList]:
        statement = select(ODSWBSalesReportList).where(
            ODSWBSalesReportList.id > after_id
        )
        if shop_id is not None:
            statement = statement.where(ODSWBSalesReportList.shop_id == shop_id)
        statement = statement.order_by(ODSWBSalesReportList.id).limit(batch_size)
        result = await db.execute(statement)
        return list(result.scalars().all())

    @staticmethod
    def build_dwd_data(source: ODSWBSalesReportList) -> dict[str, Any]:
        data = {field: getattr(source, field) for field in SUMMARY_FIELDS}
        data["payment_schedule"] = _to_decimal(source.payment_schedule)
        data["source_ods_id"] = source.id
        data["shop_id"] = source.shop_id
        return data

    @staticmethod
    async def upsert_source_batch(
        db: AsyncSession,
        *,
        sources: Sequence[ODSWBSalesReportList],
    ) -> dict[str, int]:
        latest_sources = {
            (source.shop_id, source.report_id): source for source in sources
        }
        if not latest_sources:
            return {"created": 0, "updated": 0}

        statement = select(DWDWBSalesReportSummary).where(
            tuple_(
                DWDWBSalesReportSummary.shop_id,
                DWDWBSalesReportSummary.report_id,
            ).in_(latest_sources)
        )
        result = await db.execute(statement)
        existing_by_key = {
            (item.shop_id, item.report_id): item for item in result.scalars().all()
        }

        created = 0
        updated = 0
        for key, source in latest_sources.items():
            item_data = CRUDDWDWBSalesReportSummary.build_dwd_data(source)
            existing = existing_by_key.get(key)
            if existing is None:
                db.add(DWDWBSalesReportSummary(**item_data))
                created += 1
                continue

            for field, value in item_data.items():
                setattr(existing, field, value)
            updated += 1

        await db.flush()
        return {"created": created, "updated": updated}

    @staticmethod
    def _apply_summary_filters(
        statement: Any,
        *,
        shop_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
        create_date_from: date | None = None,
        create_date_to: date | None = None,
        report_id: int | None = None,
        seller_finance_name: str | None = None,
        report_type: int | None = None,
        currency: str | None = None,
    ) -> Any:
        """为列表和导出复用同一套财务周汇总筛选条件。"""
        statement = statement.where(DWDWBSalesReportSummary.shop_id == shop_id)
        if date_from is not None:
            statement = statement.where(DWDWBSalesReportSummary.date_from >= date_from)
        if date_to is not None:
            statement = statement.where(DWDWBSalesReportSummary.date_to <= date_to)
        if create_date_from is not None:
            statement = statement.where(
                DWDWBSalesReportSummary.create_date >= create_date_from
            )
        if create_date_to is not None:
            statement = statement.where(
                DWDWBSalesReportSummary.create_date <= create_date_to
            )
        if report_id is not None:
            statement = statement.where(DWDWBSalesReportSummary.report_id == report_id)
        if seller_finance_name:
            statement = statement.where(
                DWDWBSalesReportSummary.seller_finance_name.contains(
                    seller_finance_name,
                    autoescape=True,
                )
            )
        if report_type is not None:
            statement = statement.where(
                DWDWBSalesReportSummary.report_type == report_type
            )
        if currency:
            statement = statement.where(DWDWBSalesReportSummary.currency == currency)
        return statement

    async def list_summaries(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        page: int,
        page_size: int,
        date_from: date | None = None,
        date_to: date | None = None,
        create_date_from: date | None = None,
        create_date_to: date | None = None,
        report_id: int | None = None,
        seller_finance_name: str | None = None,
        report_type: int | None = None,
        currency: str | None = None,
    ) -> tuple[list[DWDWBSalesReportSummary], int]:
        """返回一页财务报告周汇总及总记录数。"""
        filters = {
            "shop_id": shop_id,
            "date_from": date_from,
            "date_to": date_to,
            "create_date_from": create_date_from,
            "create_date_to": create_date_to,
            "report_id": report_id,
            "seller_finance_name": seller_finance_name,
            "report_type": report_type,
            "currency": currency,
        }
        count_statement = self._apply_summary_filters(
            select(func.count()).select_from(DWDWBSalesReportSummary),
            **filters,
        )
        total = int((await db.execute(count_statement)).scalar_one())

        statement = self._apply_summary_filters(
            select(DWDWBSalesReportSummary),
            **filters,
        )
        statement = (
            statement.order_by(
                DWDWBSalesReportSummary.date_from.desc(),
                DWDWBSalesReportSummary.date_to.desc(),
                DWDWBSalesReportSummary.report_id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(statement)
        return list(result.scalars().all()), total

    async def list_summaries_for_export(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
        create_date_from: date | None = None,
        create_date_to: date | None = None,
        report_id: int | None = None,
        seller_finance_name: str | None = None,
        report_type: int | None = None,
        currency: str | None = None,
    ) -> list[DWDWBSalesReportSummary]:
        """导出符合筛选条件的全部财务报告周汇总。"""
        statement = self._apply_summary_filters(
            select(DWDWBSalesReportSummary),
            shop_id=shop_id,
            date_from=date_from,
            date_to=date_to,
            create_date_from=create_date_from,
            create_date_to=create_date_to,
            report_id=report_id,
            seller_finance_name=seller_finance_name,
            report_type=report_type,
            currency=currency,
        ).order_by(
            DWDWBSalesReportSummary.date_from.desc(),
            DWDWBSalesReportSummary.date_to.desc(),
            DWDWBSalesReportSummary.report_id.desc(),
        )
        result = await db.execute(statement)
        return list(result.scalars().all())


crud_dwd_wb_sales_report_summary = CRUDDWDWBSalesReportSummary()
