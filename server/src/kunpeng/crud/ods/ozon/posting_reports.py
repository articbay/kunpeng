"""Parse and persist Ozon shipment-report CSV data."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.ods.ozon.utils import parse_ru_decimal, safe_int
from kunpeng.models.ods.ozon.fbo_postings import ODSOzonFBOPostingProduct
from kunpeng.models.ods.ozon.posting_reports import (
    ODSOzonPostingReportRow,
    ODSOzonPostingReportTask,
)
from kunpeng.models.ods.ozon.postings import ODSOzonFBSPostingProduct


def _text(value: Any) -> Optional[str]:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _datetime(value: Any) -> Optional[datetime]:
    normalized = _text(value)
    if not normalized:
        return None
    normalized = normalized.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        return None if parsed.year <= 1970 else parsed
    except ValueError:
        pass
    for date_format in (
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%d.%m.%Y",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            parsed = datetime.strptime(normalized, date_format)
            return None if parsed.year <= 1970 else parsed
        except ValueError:
            continue
    return None


def _boolean(value: Any) -> Optional[bool]:
    normalized = (_text(value) or "").lower()
    if normalized in {"да", "yes", "true", "1"}:
        return True
    if normalized in {"нет", "no", "false", "0"}:
        return False
    return None


class CRUDOzonPostingReportTask:
    """Create and update asynchronous report task metadata."""

    async def create_or_update(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        report_code: str,
        fulfillment_type: str,
        period_from: datetime,
        period_to: datetime,
        status: str,
        report_type: Optional[str] = None,
        file_name: Optional[str] = None,
        error_message: Optional[str] = None,
        report_params: Optional[dict[str, Any]] = None,
        response_data: Optional[dict[str, Any]] = None,
        row_count: Optional[int] = None,
        completed_at: Optional[datetime] = None,
    ) -> ODSOzonPostingReportTask:
        task = (
            await db.execute(
                select(ODSOzonPostingReportTask).where(
                    ODSOzonPostingReportTask.shop_id == shop_id,
                    ODSOzonPostingReportTask.report_code == report_code,
                )
            )
        ).scalar_one_or_none()
        values = {
            "fulfillment_type": fulfillment_type,
            "period_from": period_from,
            "period_to": period_to,
            "status": status,
            "report_type": report_type,
            "file_name": file_name,
            "error_message": error_message,
            "report_params": report_params,
            "response_data": response_data,
            "row_count": row_count,
            "completed_at": completed_at,
        }
        if task is None:
            task = ODSOzonPostingReportTask(
                shop_id=shop_id,
                report_code=report_code,
                **values,
            )
            db.add(task)
        else:
            for field, value in values.items():
                setattr(task, field, value)
        await db.flush()
        return task


class CRUDOzonPostingReportRow:
    """Parse report CSV rows and idempotently persist product details."""

    _headers = {
        "order_number": "Номер заказа",
        "posting_number": "Номер отправления",
        "in_process_at": "Принят в обработку",
        "shipment_date": "Дата отгрузки",
        "shipment_date_without_delay": "Дата отгрузки без просрочки",
        "report_status": "Статус",
        "delivery_date": "Дата доставки",
        "transferred_to_delivery_at": "Фактическая дата передачи в доставку",
        "cancellation_at": "Дата отмены",
        "shipment_amount": "Сумма отправления",
        "shipment_currency": "Код валюты отправления",
        "product_name": "Название товара",
        "product_color": "Цвет товара",
        "product_size": "Размер товара",
        "sku": "SKU",
        "offer_id": "Артикул",
        "additional_packaging": "Доупаковка",
        "sealing": "Пломбирование",
        "seller_price": "Ваша цена",
        "product_currency": "Код валюты товара",
        "buyer_paid_amount": "Оплачено покупателем",
        "buyer_currency": "Код валюты покупателя",
        "quantity": "Количество",
        "delivery_fee": "Стоимость доставки",
        "related_posting_number": "Связанные отправления",
        "is_marketplace_buyout": "Выкуп товара",
        "old_price": "Цена товара до скидок",
        "discount_percent": "Скидка %",
        "discount_amount": "Скидка руб",
        "promotion_actions": "Акции",
        "actual_tariffication": "Фактическая тарификация",
        "floor_lift_fee": "Подъем на этаж",
        "product_volume_weight": "Объемный вес товаров, кг",
    }
    _datetime_fields = {
        "in_process_at",
        "shipment_date",
        "shipment_date_without_delay",
        "delivery_date",
        "transferred_to_delivery_at",
        "cancellation_at",
    }
    _decimal_fields = {
        "shipment_amount",
        "additional_packaging",
        "sealing",
        "seller_price",
        "buyer_paid_amount",
        "delivery_fee",
        "old_price",
        "discount_percent",
        "discount_amount",
        "floor_lift_fee",
        "product_volume_weight",
    }

    def parse_csv(self, content: bytes) -> list[dict[str, Any]]:
        """Decode Ozon UTF-8 semicolon CSV without logging row values."""
        decoded = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(decoded), delimiter=";")
        rows: list[dict[str, Any]] = []
        for source in reader:
            normalized_source = {
                str(key).strip(): value
                for key, value in source.items()
                if key is not None
            }
            record: dict[str, Any] = {"row_data": normalized_source}
            for field, header in self._headers.items():
                raw_value = normalized_source.get(header)
                if field in self._datetime_fields:
                    value = _datetime(raw_value)
                elif field in self._decimal_fields:
                    decimal_value = raw_value
                    if field == "discount_percent" and isinstance(raw_value, str):
                        decimal_value = raw_value.replace("%", "")
                    if (_text(decimal_value) or "").lower() in {
                        "нет",
                        "-",
                        "—",
                    }:
                        value = None
                    else:
                        value = parse_ru_decimal(decimal_value)
                elif field in {"sku", "quantity"}:
                    value = safe_int(raw_value)
                elif field == "is_marketplace_buyout":
                    value = _boolean(raw_value)
                else:
                    value = _text(raw_value)
                record[field] = value
            if record.get("posting_number") and record.get("sku") is not None:
                rows.append(record)
        return rows

    async def upsert_many(
        self,
        db: AsyncSession,
        *,
        rows: list[dict[str, Any]],
        shop_id: int,
        task_id: int,
        report_code: str,
        fulfillment_type: str,
    ) -> int:
        count = 0
        for row in rows:
            existing = (
                await db.execute(
                    select(ODSOzonPostingReportRow).where(
                        ODSOzonPostingReportRow.shop_id == shop_id,
                        ODSOzonPostingReportRow.fulfillment_type == fulfillment_type,
                        ODSOzonPostingReportRow.posting_number == row["posting_number"],
                        ODSOzonPostingReportRow.sku == row["sku"],
                    )
                )
            ).scalar_one_or_none()
            values = {
                **row,
                "shop_id": shop_id,
                "task_id": task_id,
                "report_code": report_code,
                "fulfillment_type": fulfillment_type,
            }
            if existing is None:
                db.add(ODSOzonPostingReportRow(**values))
            else:
                for field, value in values.items():
                    if field != "id":
                        setattr(existing, field, value)
            count += 1
        await db.flush()
        return count

    async def list_unmatched(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        report_codes: Optional[set[str]] = None,
    ) -> list[ODSOzonPostingReportRow]:
        """Return report rows without the same posting/SKU in ordinary ODS."""
        query = select(ODSOzonPostingReportRow).where(
            ODSOzonPostingReportRow.shop_id == shop_id
        )
        if report_codes:
            query = query.where(ODSOzonPostingReportRow.report_code.in_(report_codes))
        report_rows = (await db.execute(query)).scalars().all()

        fbs_keys = set(
            (
                await db.execute(
                    select(
                        ODSOzonFBSPostingProduct.posting_number,
                        ODSOzonFBSPostingProduct.sku,
                    ).where(ODSOzonFBSPostingProduct.shop_id == shop_id)
                )
            ).all()
        )
        fbo_keys = set(
            (
                await db.execute(
                    select(
                        ODSOzonFBOPostingProduct.posting_number,
                        ODSOzonFBOPostingProduct.sku,
                    ).where(ODSOzonFBOPostingProduct.shop_id == shop_id)
                )
            ).all()
        )
        return [
            row
            for row in report_rows
            if (row.posting_number, row.sku)
            not in (fbs_keys if row.fulfillment_type == "FBS" else fbo_keys)
        ]


crud_ods_ozon_posting_report_task = CRUDOzonPostingReportTask()
crud_ods_ozon_posting_report_row = CRUDOzonPostingReportRow()
