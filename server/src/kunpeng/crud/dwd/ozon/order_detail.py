"""Build the unified Ozon FBS/FBO order DWD table from ODS."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Optional

from sqlalchemy import case, select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from kunpeng.models.dwd.ozon import DWDOzonOrderDetail
from kunpeng.models.ods.ozon.fbo_postings import (ODSOzonFBOPosting,
                                                  ODSOzonFBOPostingProduct)
from kunpeng.models.ods.ozon.posting_reports import ODSOzonPostingReportRow
from kunpeng.models.ods.ozon.postings import (ODSOzonFBSPosting,
                                              ODSOzonFBSPostingCancellation,
                                              ODSOzonFBSPostingDelivery,
                                              ODSOzonFBSPostingProduct)

_STATUS_NAMES_CN = {
    "acceptance_in_progress": "验收入库中",
    "arbitration": "争议处理中",
    "awaiting_approve": "等待确认",
    "awaiting_deliver": "等待发货",
    "awaiting_packaging": "等待备货",
    "awaiting_registration": "等待登记",
    "awaiting_verification": "等待验证",
    "cancelled": "已取消",
    "client_arbitration": "买家争议处理中",
    "delivered": "已送达",
    "delivering": "配送中",
    "driver_pickup": "等待司机取货",
    "not_accepted": "未验收",
    "sent_by_seller": "卖家已发货",
}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _decimal(value: Any) -> Optional[Decimal]:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.0001"))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _money(value: Any) -> tuple[Optional[Decimal], Optional[str]]:
    if isinstance(value, dict):
        amount = value.get("amount", value.get("value"))
        currency = value.get("currency_code", value.get("currency"))
        return _decimal(amount), str(currency) if currency else None
    return _decimal(value), None


def _datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        if parsed.year <= 1970:
            return None
        return parsed
    except ValueError:
        return None


def _hours(start: Optional[datetime], end: Optional[datetime]) -> Optional[Decimal]:
    if start and start.tzinfo is not None:
        start = start.astimezone(timezone.utc).replace(tzinfo=None)
    if end and end.tzinfo is not None:
        end = end.astimezone(timezone.utc).replace(tzinfo=None)
    if start is None or end is None or end < start:
        return None
    return (Decimal(str((end - start).total_seconds())) / Decimal("3600")).quantize(
        Decimal("0.01")
    )


def _month_start(value: Optional[datetime]) -> Optional[date]:
    return date(value.year, value.month, 1) if value else None


def _delivery_level(hours: Optional[Decimal]) -> Optional[str]:
    if hours is None or hours < 0:
        return None
    for upper_bound, label in (
        (Decimal("5"), "01.(0,5h)"),
        (Decimal("12"), "02.(5h,12h)"),
        (Decimal("24"), "03.(12h,24h)"),
        (Decimal("48"), "04.(24h,48h)"),
        (Decimal("72"), "05.(48h,72h)"),
        (Decimal("96"), "06.(72h,96h)"),
    ):
        if hours < upper_bound:
            return label
    return "07.(96h,+)"


def _delivery_metrics(
    process_at: Optional[datetime],
    transferred_to_delivery_at: Optional[datetime],
    delivery_date: Optional[datetime],
) -> dict[str, Any]:
    duration_1 = _hours(process_at, transferred_to_delivery_at)
    duration_2 = _hours(process_at, delivery_date)
    return {
        "delivery_duration_1_hours": duration_1,
        "delivery_duration_2_hours": duration_2,
        "delivery_level_1": _delivery_level(duration_1),
        "delivery_level_2": _delivery_level(duration_2),
    }


def _financial_product(financial_data: Any, sku: Any) -> dict[str, Any]:
    products = _dict(financial_data).get("products") or []
    for item in products:
        if not isinstance(item, dict):
            continue
        product_id = item.get("product_id", item.get("sku"))
        if str(product_id) == str(sku):
            return item
    return {}


def _first_text(data: dict[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _address_text(value: Any) -> Optional[str]:
    if isinstance(value, str):
        return value or None
    if isinstance(value, dict):
        return _first_text(value, "address", "full_address", "address_tail")
    return None


def _common_record(
    *,
    fulfillment_type: str,
    posting: Any,
    product: Any,
    process_at: Optional[datetime],
    delivery_date: Optional[datetime],
    analytics: dict[str, Any],
    financial_product: dict[str, Any],
) -> dict[str, Any]:
    seller_price, product_currency = _money(
        getattr(product, "price_amount", None)
        if fulfillment_type == "FBS"
        else getattr(product, "price", None)
    )
    product_currency = (
        product_currency
        or getattr(product, "price_currency", None)
        or getattr(product, "currency_code", None)
    )

    shipment_amount, shipment_currency = _money(financial_product.get("price"))
    if shipment_amount is None:
        shipment_amount = seller_price
    shipment_currency = shipment_currency or product_currency

    buyer_paid_amount, buyer_currency = _money(
        financial_product.get("customer_price", financial_product.get("payout"))
    )
    buyer_currency = buyer_currency or shipment_currency
    old_price, _ = _money(financial_product.get("old_price"))
    discount_amount, _ = _money(financial_product.get("total_discount_value"))

    financial_data = _dict(getattr(posting, "financial_data", None))
    row_data = _dict(getattr(posting, "row_data", None))
    transferred_at = _datetime(row_data.get("received_at_sorting_center"))
    shipment_date = getattr(posting, "shipment_date", None)

    record = {
        "shop_id": posting.shop_id,
        "fulfillment_type": fulfillment_type,
        "posting_number": posting.posting_number,
        "sku": product.sku,
        "source_posting_id": posting.id,
        "source_product_id": product.id,
        "order_type_name": (
            "来自我的仓库" if fulfillment_type == "FBS" else "来自Ozon仓库"
        ),
        "order_id": posting.order_id,
        "order_number": posting.order_number,
        "in_process_month": _month_start(process_at),
        "in_process_date": process_at.date() if process_at else None,
        "in_process_hour": process_at.hour if process_at else None,
        "in_process_at": process_at,
        "shipment_date": shipment_date,
        "status_code": posting.status,
        "substatus_code": posting.substatus,
        "status_name_cn": _STATUS_NAMES_CN.get(posting.status, posting.status),
        "delivery_date": delivery_date,
        "transferred_to_delivery_at": transferred_at,
        "product_name": product.name,
        "offer_id": product.offer_id,
        "seller_price": seller_price,
        "product_currency": product_currency,
        "shipment_amount": shipment_amount,
        "shipment_currency": shipment_currency,
        "buyer_paid_amount": buyer_paid_amount,
        "buyer_currency": buyer_currency,
        "quantity": product.quantity,
        "related_posting_number": row_data.get("parent_posting_number"),
        "is_marketplace_buyout": _dict(product.row_data).get("is_marketplace_buyout"),
        "old_price": old_price,
        "discount_percent": _decimal(financial_product.get("total_discount_percent")),
        "discount_amount": discount_amount,
        "promotion_actions": financial_product.get("actions") or None,
        "cluster_from": financial_data.get("cluster_from"),
        "cluster_to": financial_data.get("cluster_to"),
        "delivery_region": _first_text(analytics, "region", "region_name"),
        "delivery_city": analytics.get("city"),
        "delivery_type": analytics.get("delivery_type"),
        "is_premium": analytics.get("is_premium"),
        "is_legal": analytics.get("is_legal"),
        "payment_type": analytics.get("payment_type_group_name"),
        "shipment_volume_weight": _decimal(row_data.get("volume_weight")),
    }
    record.update(_delivery_metrics(process_at, transferred_at, delivery_date))
    return record


class CRUDDWDOzonOrderDetail:
    """Idempotently build unified order-product rows from FBS and FBO ODS."""

    _batch_size = 500

    async def _merge_report_records(
        self,
        db: AsyncSession,
        records: list[dict[str, Any]],
        shop_id: Optional[int],
    ) -> list[dict[str, Any]]:
        """Overlay report values only when the ordinary ODS row already exists."""
        query = select(ODSOzonPostingReportRow)
        if shop_id is not None:
            query = query.where(ODSOzonPostingReportRow.shop_id == shop_id)
        report_rows = (await db.execute(query)).scalars().all()
        indexed = {
            (
                record["shop_id"],
                record["fulfillment_type"],
                record["posting_number"],
                record["sku"],
            ): record
            for record in records
        }
        overlay_fields = (
            "order_number",
            "in_process_at",
            "shipment_date",
            "shipment_date_without_delay",
            "delivery_date",
            "transferred_to_delivery_at",
            "cancellation_at",
            "shipment_amount",
            "shipment_currency",
            "product_name",
            "product_color",
            "product_size",
            "offer_id",
            "seller_price",
            "product_currency",
            "buyer_paid_amount",
            "buyer_currency",
            "quantity",
            "delivery_fee",
            "is_marketplace_buyout",
            "old_price",
            "discount_percent",
            "discount_amount",
            "promotion_actions",
            "product_volume_weight",
        )
        for report in report_rows:
            key = (
                report.shop_id,
                report.fulfillment_type,
                report.posting_number,
                report.sku,
            )
            record = indexed.get(key)
            if record is None:
                continue
            for field in overlay_fields:
                value = getattr(report, field)
                if value is not None:
                    record[field] = value
            if report.related_posting_number:
                record["related_posting_number"] = report.related_posting_number[:100]

            process_at = record.get("in_process_at")
            delivery_date = record.get("delivery_date")
            transferred_at = record.get("transferred_to_delivery_at")
            record["in_process_month"] = _month_start(process_at)
            record["in_process_date"] = process_at.date() if process_at else None
            record["in_process_hour"] = process_at.hour if process_at else None
            record.update(_delivery_metrics(process_at, transferred_at, delivery_date))
        return list(indexed.values())

    async def _fbs_records(
        self, db: AsyncSession, shop_id: Optional[int]
    ) -> list[dict[str, Any]]:
        query = (
            select(
                ODSOzonFBSPosting,
                ODSOzonFBSPostingProduct,
                ODSOzonFBSPostingDelivery,
                ODSOzonFBSPostingCancellation,
            )
            .join(
                ODSOzonFBSPostingProduct,
                (ODSOzonFBSPostingProduct.shop_id == ODSOzonFBSPosting.shop_id)
                & (
                    ODSOzonFBSPostingProduct.posting_number
                    == ODSOzonFBSPosting.posting_number
                ),
            )
            .outerjoin(
                ODSOzonFBSPostingDelivery,
                (ODSOzonFBSPostingDelivery.shop_id == ODSOzonFBSPosting.shop_id)
                & (
                    ODSOzonFBSPostingDelivery.posting_number
                    == ODSOzonFBSPosting.posting_number
                ),
            )
            .outerjoin(
                ODSOzonFBSPostingCancellation,
                (ODSOzonFBSPostingCancellation.shop_id == ODSOzonFBSPosting.shop_id)
                & (
                    ODSOzonFBSPostingCancellation.posting_number
                    == ODSOzonFBSPosting.posting_number
                ),
            )
            .where(
                ODSOzonFBSPosting.posting_number.is_not(None),
                ODSOzonFBSPostingProduct.sku.is_not(None),
            )
        )
        if shop_id is not None:
            query = query.where(ODSOzonFBSPosting.shop_id == shop_id)

        records: list[dict[str, Any]] = []
        for posting, product, delivery, cancellation in (await db.execute(query)).all():
            row_data = _dict(posting.row_data)
            analytics = _dict(posting.analytics_data)
            customer = _dict(posting.customer)
            addressee = _dict(posting.addressee)
            financial_product = _financial_product(posting.financial_data, product.sku)
            delivery_date = posting.delivering_date
            record = _common_record(
                fulfillment_type="FBS",
                posting=posting,
                product=product,
                process_at=posting.in_process_at,
                delivery_date=delivery_date,
                analytics=analytics,
                financial_product=financial_product,
            )
            customer_address = _address_text(customer.get("address"))
            cancellation_data = _dict(cancellation.row_data) if cancellation else {}
            record.update(
                {
                    "promised_delivery_at": _datetime(
                        row_data.get("delivery_date_end")
                        or analytics.get("client_delivery_date_end")
                    ),
                    "seller_warehouse_name": (
                        delivery.warehouse_name if delivery else None
                    ),
                    "shipment_method": posting.delivery_schema or "FBS",
                    "logistics_company": delivery.tpl_provider if delivery else None,
                    "delivery_method_name": (
                        delivery.delivery_name if delivery else None
                    ),
                    "shipment_date_without_delay": posting.shipment_date_without_delay,
                    "cancellation_at": _datetime(
                        cancellation_data.get("cancelled_at")
                        or cancellation_data.get("cancellation_date")
                    ),
                    "product_volume_weight": _decimal(product.weight),
                    "product_color": product.product_color,
                    "buyer_address": customer_address,
                    "buyer_name": customer.get("name"),
                    "buyer_email": customer.get("customer_email"),
                    "addressee_name": addressee.get("name"),
                    "buyer_phone": customer.get("phone"),
                    "delivery_address": customer_address,
                    "postal_code": _first_text(customer, "postal_code", "zip_code"),
                }
            )
            records.append(record)
        return records

    async def _fbo_records(
        self, db: AsyncSession, shop_id: Optional[int]
    ) -> list[dict[str, Any]]:
        query = (
            select(ODSOzonFBOPosting, ODSOzonFBOPostingProduct)
            .join(
                ODSOzonFBOPostingProduct,
                (ODSOzonFBOPostingProduct.shop_id == ODSOzonFBOPosting.shop_id)
                & (
                    ODSOzonFBOPostingProduct.posting_number
                    == ODSOzonFBOPosting.posting_number
                ),
            )
            .where(ODSOzonFBOPostingProduct.sku.is_not(None))
        )
        if shop_id is not None:
            query = query.where(ODSOzonFBOPosting.shop_id == shop_id)

        records: list[dict[str, Any]] = []
        for posting, product in (await db.execute(query)).all():
            analytics = _dict(posting.analytics_data)
            financial_product = _financial_product(posting.financial_data, product.sku)
            process_at = posting.in_process_at or posting.created_at
            delivery_date = _datetime(analytics.get("client_delivery_date_end"))
            record = _common_record(
                fulfillment_type="FBO",
                posting=posting,
                product=product,
                process_at=process_at,
                delivery_date=delivery_date,
                analytics=analytics,
                financial_product=financial_product,
            )
            record.update(
                {
                    "promised_delivery_at": delivery_date,
                    "ozon_warehouse_name": analytics.get("warehouse_name"),
                    "shipment_method": "FBO",
                    "delivery_method_name": analytics.get("delivery_type"),
                    "cancellation_at": _datetime(
                        _dict(posting.row_data).get("cancelled_at")
                    ),
                }
            )
            records.append(record)
        return records

    async def upsert_from_ods(
        self, db: AsyncSession, *, shop_id: Optional[int] = None
    ) -> dict[str, int]:
        """Insert new rows and refresh source-owned fields on existing rows."""
        records = await self._fbs_records(db, shop_id)
        fbo_records = await self._fbo_records(db, shop_id)
        records.extend(fbo_records)
        records = await self._merge_report_records(db, records, shop_id)
        fbs_count = sum(record["fulfillment_type"] == "FBS" for record in records)
        fbo_count = sum(record["fulfillment_type"] == "FBO" for record in records)
        if not records:
            return {
                "source_count": 0,
                "fbs_count": 0,
                "fbo_count": 0,
                "affected_rows": 0,
            }

        primary_keys = {"shop_id", "fulfillment_type", "posting_number", "sku"}
        preserved_fields = {
            "product_name_cn",
            "delivery_city_cn",
            "create_time",
        }
        writable_fields = [
            column.name
            for column in DWDOzonOrderDetail.__table__.columns
            if column.name not in preserved_fields | {"update_time"}
        ]
        normalized_records = [
            {field: record.get(field) for field in writable_fields}
            for record in records
        ]
        affected_rows = 0
        for batch in self._batches(normalized_records, self._batch_size):
            statement = mysql_insert(DWDOzonOrderDetail).values(batch)
            # Evaluate this before replacing the source city. A changed city
            # clears its stale translation for the translation worker.
            updates = {
                "delivery_city_cn": case(
                    (
                        DWDOzonOrderDetail.delivery_city
                        == statement.inserted.delivery_city,
                        DWDOzonOrderDetail.delivery_city_cn,
                    ),
                    else_=None,
                )
            }
            updates.update({
                column.name: getattr(statement.inserted, column.name)
                for column in DWDOzonOrderDetail.__table__.columns
                if column.name in writable_fields and column.name not in primary_keys
            })
            updates["update_time"] = func.now()
            result = await db.execute(statement.on_duplicate_key_update(**updates))
            affected_rows += max(result.rowcount or 0, 0)

        await db.flush()
        return {
            "source_count": len(records),
            "fbs_count": fbs_count,
            "fbo_count": fbo_count,
            "affected_rows": affected_rows,
        }

    @staticmethod
    def _batches(
        records: list[dict[str, Any]], size: int
    ) -> Iterable[list[dict[str, Any]]]:
        for offset in range(0, len(records), size):
            yield records[offset : offset + size]


crud_dwd_ozon_order_detail = CRUDDWDOzonOrderDetail()
