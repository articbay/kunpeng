"""Ozon FBS unfulfilled-posting snapshot persistence and reconciliation."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.ods.ozon.utils import parse_datetime_field, safe_int, safe_str
from kunpeng.models.ods.ozon.unfulfilled_postings import ODSOzonUnfulfilledPosting

logger = logging.getLogger(__name__)


class CRUDOzonUnfulfilledPosting:
    """Atomically upsert a complete API snapshot and resolve missing rows."""

    @staticmethod
    def _extract_item_data(
        item: Dict[str, Any],
        *,
        shop_id: int,
        observed_at: datetime,
    ) -> Optional[Dict[str, Any]]:
        posting_number = safe_str(item.get("posting_number"))
        if not posting_number:
            logger.warning(
                "[ODS Ozon UnfulfilledPosting] 跳过缺少 posting_number 的记录"
            )
            return None

        delivery_method = item.get("delivery_method") or {}
        return {
            "shop_id": shop_id,
            "row_data": item,
            "posting_number": posting_number,
            "order_id": safe_int(item.get("order_id")),
            "order_number": safe_str(item.get("order_number")),
            "status": safe_str(item.get("status")),
            "substatus": safe_str(item.get("substatus")),
            "delivery_method_name": safe_str(delivery_method.get("name")),
            "in_process_at": parse_datetime_field(item.get("in_process_at")),
            "shipment_date": parse_datetime_field(item.get("shipment_date")),
            "delivering_at": parse_datetime_field(item.get("delivering_date")),
            "shipment_without_delay_at": parse_datetime_field(
                item.get("shipment_date_without_delay")
            ),
            "cutoff_at": parse_datetime_field(
                item.get("cutoff_at") or item.get("cutoff")
            ),
            "products": item.get("products"),
            "analytics_data": item.get("analytics_data"),
            "financial_data": item.get("financial_data"),
            "delivery_method": item.get("delivery_method"),
            "barcodes": item.get("barcodes"),
            "cancellation": item.get("cancellation"),
            "customer": item.get("customer"),
            "available_actions": item.get("available_actions"),
            "requirements": item.get("requirements"),
            "sorting_center": item.get("sorting_center"),
            "tracking_number": safe_str(item.get("tracking_number")),
            "integration_type_flow": safe_str(item.get("integration_type_flow")),
            "parent_posting_number": safe_str(item.get("parent_posting_number")),
            "destination_place_id": safe_int(item.get("destination_place_id")),
            "destination_place_name": safe_str(item.get("destination_place_name")),
            "is_express": item.get("is_express"),
            "is_multibox": item.get("is_multibox"),
            "multi_box_qty": safe_int(item.get("multi_box_qty")),
            "last_seen_at": observed_at,
            "is_active": True,
            "resolved_at": None,
        }

    @staticmethod
    def _upsert_statement(db: AsyncSession, records: List[Dict[str, Any]]):
        """Build the production MySQL upsert, with SQLite support for tests."""
        bind = db.get_bind()
        dialect_name = bind.dialect.name if bind is not None else "mysql"
        update_columns = {
            column: None
            for column in (
                "row_data",
                "order_id",
                "order_number",
                "status",
                "substatus",
                "delivery_method_name",
                "in_process_at",
                "shipment_date",
                "delivering_at",
                "shipment_without_delay_at",
                "cutoff_at",
                "products",
                "analytics_data",
                "financial_data",
                "delivery_method",
                "barcodes",
                "cancellation",
                "customer",
                "available_actions",
                "requirements",
                "sorting_center",
                "tracking_number",
                "integration_type_flow",
                "parent_posting_number",
                "destination_place_id",
                "destination_place_name",
                "is_express",
                "is_multibox",
                "multi_box_qty",
                "last_seen_at",
                "is_active",
                "resolved_at",
            )
        }

        if dialect_name == "sqlite":
            statement = sqlite_insert(ODSOzonUnfulfilledPosting).values(records)
            return statement.on_conflict_do_update(
                index_elements=["shop_id", "posting_number"],
                set_={
                    column: getattr(statement.excluded, column)
                    for column in update_columns
                }
                | {"update_time": func.now()},
            )

        statement = mysql_insert(ODSOzonUnfulfilledPosting).values(records)
        return statement.on_duplicate_key_update(
            **{
                column: getattr(statement.inserted, column) for column in update_columns
            },
            update_time=func.now(),
        )

    async def reconcile_snapshot(
        self,
        db: AsyncSession,
        *,
        items: List[Dict[str, Any]],
        shop_id: int,
        observed_at: datetime,
    ) -> Dict[str, int]:
        """Persist a fully fetched window and resolve missing active rows.

        The caller must only invoke this method after every API page succeeded.
        Ozon v4 filters by cutoff but does not return that cutoff as a posting
        field, so reconciliation compares the latest complete result with all
        rows that were active for the shop. Inactive rows are fetched only when
        their posting number reappears, so reactivation remains detectable.
        """
        current: Dict[str, Dict[str, Any]] = {}
        for item in items:
            if not isinstance(item, dict):
                logger.warning(
                    "[ODS Ozon UnfulfilledPosting] 跳过非对象记录: %r",
                    item,
                )
                continue
            record = self._extract_item_data(
                item,
                shop_id=shop_id,
                observed_at=observed_at,
            )
            if record is not None:
                current[record["posting_number"]] = record

        current_numbers = set(current)
        state_filter = ODSOzonUnfulfilledPosting.is_active.is_(True)
        if current_numbers:
            state_filter = or_(
                state_filter,
                ODSOzonUnfulfilledPosting.posting_number.in_(current_numbers),
            )
        existing_result = await db.execute(
            select(
                ODSOzonUnfulfilledPosting.id,
                ODSOzonUnfulfilledPosting.posting_number,
                ODSOzonUnfulfilledPosting.is_active,
            ).where(
                ODSOzonUnfulfilledPosting.shop_id == shop_id,
                state_filter,
            )
        )
        existing = {str(row.posting_number): row for row in existing_result.all()}
        existing_numbers = set(existing)
        active_before = {
            posting_number
            for posting_number, row in existing.items()
            if bool(row.is_active)
        }
        new_numbers = current_numbers - existing_numbers
        reactivated_numbers = {
            posting_number
            for posting_number in current_numbers & existing_numbers
            if not bool(existing[posting_number].is_active)
        }
        resolved_numbers = active_before - current_numbers

        records = list(current.values())
        if records:
            await db.execute(self._upsert_statement(db, records))

        if resolved_numbers:
            resolved_ids = [
                existing[posting_number].id for posting_number in resolved_numbers
            ]
            await db.execute(
                update(ODSOzonUnfulfilledPosting)
                .where(ODSOzonUnfulfilledPosting.id.in_(resolved_ids))
                .values(
                    is_active=False,
                    resolved_at=observed_at,
                    update_time=func.now(),
                )
            )

        result = {
            "count": len(current_numbers),
            "ods_count": len(records),
            "new_count": len(new_numbers),
            "reactivated_count": len(reactivated_numbers),
            "resolved_count": len(resolved_numbers),
        }
        logger.info(
            "[ODS Ozon UnfulfilledPosting] 完整快照对账完成: shop_id=%s, %s",
            shop_id,
            result,
        )
        return result


crud_ods_ozon_unfulfilled_posting = CRUDOzonUnfulfilledPosting()
