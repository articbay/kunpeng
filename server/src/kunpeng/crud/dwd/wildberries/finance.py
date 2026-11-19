"""DWD 层 - Wildberries 财务结算明细 CRUD。"""

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.dwd.wildberries.finance import DWDWBSalesReportDetail
from kunpeng.models.ods.wildberries.finance import ODSWBSalesReport

# 最终表头映射表中可直接从 ODS 独立列读取的 73 个字段。
DIRECT_ODS_FIELDS = (
    "date_from",
    "rrd_id",
    "gi_id",
    "subject_name",
    "nm_id",
    "brand_name",
    "vendor_code",
    "title",
    "tech_size",
    "sku",
    "doc_type_name",
    "seller_oper_name",
    "order_dt",
    "sale_dt",
    "quantity",
    "retail_price",
    "retail_amount",
    "sale_percent",
    "seller_promo",
    "product_discount_for_report",
    "retail_price_with_disc",
    "sup_rating_up",
    "is_kgvp_v2",
    "spp",
    "commission_percent",
    "kvw_base",
    "kvw",
    "ppvz_sales_commission",
    "ppvz_reward",
    "acquiring_fee",
    "acquiring_percent",
    "payment_processing",
    "vw",
    "vw_nds",
    "for_pay",
    "delivery_amount",
    "return_amount",
    "delivery_service",
    "dlv_prc",
    "fix_tariff_date_from",
    "fix_tariff_date_to",
    "srv_dbs",
    "penalty",
    "additional_payment",
    "bonus_type_name",
    "shk_id",
    "acquiring_bank",
    "ppvz_office_id",
    "ppvz_office_name",
    "ppvz_supplier_inn",
    "ppvz_supplier_name",
    "office_name",
    "country",
    "gi_box_type_name",
    "declaration_number",
    "order_id",
    "sticker_id",
    "srid",
    "rebill_logistic_cost",
    "rebill_logistic_org",
    "paid_storage",
    "deduction",
    "paid_acceptance",
    "is_b2b",
    "trbx_id",
    "installment_cofinancing_amount",
    "wibes_discount_percent",
    "cashback_discount",
    "cashback_commission_change",
    "cashback_amount",
    "order_uid",
    "payment_schedule",
    "delivery_method",
)
DWD_BUSINESS_FIELDS = DIRECT_ODS_FIELDS[:56] + ("kiz",) + DIRECT_ODS_FIELDS[56:]


class CRUDDWDWBSalesReportDetail:
    """从 ODS 财务报告构建 DWD 财务结算明细。"""

    @staticmethod
    async def get_source_batch(
        db: AsyncSession,
        *,
        after_id: int,
        batch_size: int,
        shop_id: int | None = None,
    ) -> list[ODSWBSalesReport]:
        """按 ODS 主键游标读取一批源数据。"""
        statement = select(ODSWBSalesReport).where(ODSWBSalesReport.id > after_id)
        if shop_id is not None:
            statement = statement.where(ODSWBSalesReport.shop_id == shop_id)
        statement = statement.order_by(ODSWBSalesReport.id).limit(batch_size)
        result = await db.execute(statement)
        return list(result.scalars().all())

    @staticmethod
    def build_dwd_data(source: ODSWBSalesReport) -> dict[str, Any]:
        """严格按最终表头映射表提取一个 DWD 行。"""
        data = {field: getattr(source, field) for field in DIRECT_ODS_FIELDS}
        row_data = source.row_data
        data["kiz"] = row_data.get("kiz") if isinstance(row_data, Mapping) else None
        data["source_ods_id"] = source.id
        data["shop_id"] = source.shop_id
        return data

    @staticmethod
    async def upsert_source_batch(
        db: AsyncSession,
        *,
        sources: Sequence[ODSWBSalesReport],
    ) -> dict[str, int]:
        """按 (shop_id, rrd_id) 幂等新增或更新一批 DWD 行。"""
        latest_sources = {(source.shop_id, source.rrd_id): source for source in sources}
        if not latest_sources:
            return {"created": 0, "updated": 0}

        statement = select(DWDWBSalesReportDetail).where(
            tuple_(
                DWDWBSalesReportDetail.shop_id,
                DWDWBSalesReportDetail.rrd_id,
            ).in_(latest_sources)
        )
        result = await db.execute(statement)
        existing_by_key = {
            (item.shop_id, item.rrd_id): item for item in result.scalars().all()
        }

        created = 0
        updated = 0
        for key, source in latest_sources.items():
            item_data = CRUDDWDWBSalesReportDetail.build_dwd_data(source)
            existing = existing_by_key.get(key)
            if existing is None:
                db.add(DWDWBSalesReportDetail(**item_data))
                created += 1
                continue

            for field, value in item_data.items():
                setattr(existing, field, value)
            updated += 1

        await db.flush()
        return {"created": created, "updated": updated}

    @staticmethod
    def _apply_report_filters(
        statement: Any,
        *,
        shop_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
        nm_id: int | None = None,
        vendor_code: str | None = None,
        rrd_id: int | None = None,
        order_id: int | None = None,
        seller_oper_name: str | None = None,
        doc_type_name: str | None = None,
        brand_name: str | None = None,
    ) -> Any:
        """为列表和导出复用同一套财务明细筛选条件。"""
        statement = statement.where(DWDWBSalesReportDetail.shop_id == shop_id)
        if date_from is not None:
            statement = statement.where(DWDWBSalesReportDetail.date_from >= date_from)
        if date_to is not None:
            statement = statement.where(DWDWBSalesReportDetail.date_from <= date_to)
        if nm_id is not None:
            statement = statement.where(DWDWBSalesReportDetail.nm_id == nm_id)
        if vendor_code:
            statement = statement.where(
                DWDWBSalesReportDetail.vendor_code.contains(
                    vendor_code,
                    autoescape=True,
                )
            )
        if rrd_id is not None:
            statement = statement.where(DWDWBSalesReportDetail.rrd_id == rrd_id)
        if order_id is not None:
            statement = statement.where(DWDWBSalesReportDetail.order_id == order_id)
        if seller_oper_name:
            statement = statement.where(
                DWDWBSalesReportDetail.seller_oper_name == seller_oper_name
            )
        if doc_type_name:
            statement = statement.where(
                DWDWBSalesReportDetail.doc_type_name == doc_type_name
            )
        if brand_name:
            statement = statement.where(
                DWDWBSalesReportDetail.brand_name.contains(
                    brand_name,
                    autoescape=True,
                )
            )
        return statement

    async def list_report_details(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        page: int,
        page_size: int,
        date_from: date | None = None,
        date_to: date | None = None,
        nm_id: int | None = None,
        vendor_code: str | None = None,
        rrd_id: int | None = None,
        order_id: int | None = None,
        seller_oper_name: str | None = None,
        doc_type_name: str | None = None,
        brand_name: str | None = None,
    ) -> tuple[list[DWDWBSalesReportDetail], int]:
        """按固定顺序返回一页财务报告明细及总记录数。"""
        filters = {
            "shop_id": shop_id,
            "date_from": date_from,
            "date_to": date_to,
            "nm_id": nm_id,
            "vendor_code": vendor_code,
            "rrd_id": rrd_id,
            "order_id": order_id,
            "seller_oper_name": seller_oper_name,
            "doc_type_name": doc_type_name,
            "brand_name": brand_name,
        }
        count_statement = self._apply_report_filters(
            select(func.count()).select_from(DWDWBSalesReportDetail),
            **filters,
        )
        total = int((await db.execute(count_statement)).scalar_one())

        statement = self._apply_report_filters(
            select(DWDWBSalesReportDetail),
            **filters,
        )
        statement = (
            statement.order_by(
                DWDWBSalesReportDetail.date_from.desc(),
                DWDWBSalesReportDetail.rrd_id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(statement)
        return list(result.scalars().all()), total

    async def list_report_details_for_export(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
        nm_id: int | None = None,
        vendor_code: str | None = None,
        rrd_id: int | None = None,
        order_id: int | None = None,
        seller_oper_name: str | None = None,
        doc_type_name: str | None = None,
        brand_name: str | None = None,
    ) -> list[DWDWBSalesReportDetail]:
        """导出符合筛选条件的全部财务明细。"""
        statement = self._apply_report_filters(
            select(DWDWBSalesReportDetail),
            shop_id=shop_id,
            date_from=date_from,
            date_to=date_to,
            nm_id=nm_id,
            vendor_code=vendor_code,
            rrd_id=rrd_id,
            order_id=order_id,
            seller_oper_name=seller_oper_name,
            doc_type_name=doc_type_name,
            brand_name=brand_name,
        ).order_by(
            DWDWBSalesReportDetail.date_from.desc(),
            DWDWBSalesReportDetail.rrd_id.desc(),
        )
        result = await db.execute(statement)
        return list(result.scalars().all())


crud_dwd_wb_sales_report_detail = CRUDDWDWBSalesReportDetail()
