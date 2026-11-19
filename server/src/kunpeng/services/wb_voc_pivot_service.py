"""Read-only customer-voice export assembled directly from three DWD tables."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud import shop_crud
from kunpeng.crud.dwd.wildberries.return_detail import \
    crud_dwd_wb_return_detail
from kunpeng.crud.dwd.wildberries.voc_feedback import \
    crud_dwd_wb_voc_feedback_detail
from kunpeng.crud.dwd.wildberries.voc_question import \
    crud_dwd_wb_voc_question_detail
from kunpeng.schemas.wb_voc_pivot import (WBVOCPivotExportRequest,
                                          WBVOCPivotFilters)
from kunpeng.services.wb_voc_pivot_workbook import \
    build_customer_voice_workbook
from kunpeng.utils.timezone import platform_tz

KNOWN_STATUS_TRANSLATIONS = {
    "Выдано": "已领取",
    "Отмена по задержке": "取消（因延迟）",
    "Неподбор": "未匹配到商品",
    "В пути в пвз": "正在运输至取件点途中",
    "Истек срок хранения на пвз": "在取件点存放期限已过",
}

_REFUSAL_MARKERS = ("отказ", "не забрал", "не забрала", "拒收", "拒绝收货")
_DEFECT_MARKERS = (
    "брак",
    "дефект",
    "повреж",
    "неисправ",
    "瑕疵",
    "损坏",
    "破损",
    "故障",
)


def classify_return_reason(reason: Optional[str], reason_cn: Optional[str]) -> str:
    """Classify a return reason for the workbook without persisting the result."""
    normalized = " ".join(value for value in (reason, reason_cn) if value).lower()
    if any(marker in normalized for marker in _REFUSAL_MARKERS):
        return "买家拒收"
    if any(marker in normalized for marker in _DEFECT_MARKERS):
        return "瑕疵品"
    return "未分类"


def _platform_datetime(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(platform_tz()).replace(tzinfo=None)


def _business_date(value: Optional[datetime]) -> Optional[date]:
    localized = _platform_datetime(value)
    return localized.date() if localized else None


def _answered(value: Optional[str]) -> bool:
    return bool(value and value.strip())


def _moscow_date_to_utc_naive(value: date) -> datetime:
    local_value = datetime.combine(value, time.min, tzinfo=platform_tz())
    return local_value.astimezone(timezone.utc).replace(tzinfo=None)


def _utc_bounds(
    filters: WBVOCPivotFilters,
) -> tuple[Optional[datetime], Optional[datetime]]:
    created_from = (
        _moscow_date_to_utc_naive(filters.date_from) if filters.date_from else None
    )
    created_to = (
        _moscow_date_to_utc_naive(filters.date_to + timedelta(days=1))
        if filters.date_to
        else None
    )
    return created_from, created_to


class WBVOCPivotService:
    """Authorize and combine DWD rows in memory; never write to the database."""

    @staticmethod
    def _feedback_row(record: Any) -> dict[str, Any]:
        is_answered = _answered(record.answer)
        return {
            "shop_id": record.shop_id,
            "record_type": "feedback",
            "record_id": record.feedback_id,
            "business_date": _business_date(record.created_date),
            "event_date": _platform_datetime(record.created_date),
            "supplier_article": record.supplier_article,
            "nm_id": record.nm_id,
            "brand_name": record.brand_name,
            "rating": record.product_valuation,
            "feedback_text": record.text,
            "feedback_text_cn": record.text_cn,
            "pros": record.pros,
            "pros_cn": record.pros_cn,
            "cons": record.cons,
            "cons_cn": record.cons_cn,
            "user_name": record.user_name,
            "color": record.color,
            "color_cn": record.color_cn,
            "size": record.size,
            "size_cn": record.size_cn,
            "answer": record.answer,
            "answer_cn": record.answer_cn,
            "answer_status": "已回复" if is_answered else "未回复",
            "parent_feedback_id": record.parent_feedback_id,
            "child_feedback_id": record.child_feedback_id,
            "quantity": 1,
        }

    @staticmethod
    def _question_row(record: Any) -> dict[str, Any]:
        is_answered = _answered(record.answer)
        return {
            "shop_id": record.shop_id,
            "record_type": "question",
            "record_id": record.question_id,
            "business_date": _business_date(record.created_date),
            "event_date": _platform_datetime(record.created_date),
            "supplier_article": record.supplier_article,
            "nm_id": record.nm_id,
            "brand_name": record.brand_name,
            "question_text": record.text,
            "question_text_cn": record.text_cn,
            "answer": record.answer,
            "answer_cn": record.answer_cn,
            "answer_status": "已回复" if is_answered else "未回复",
            "quantity": 1,
        }

    @staticmethod
    def _return_row(record: Any) -> dict[str, Any]:
        event_date = (
            record.ready_to_return_dt or record.completed_dt or record.expired_dt
        )
        business_date = record.order_dt or _business_date(event_date)
        return {
            "shop_id": record.shop_id,
            "record_type": "return",
            "record_id": record.srid,
            "business_date": business_date,
            "event_date": _platform_datetime(event_date),
            "order_date": record.order_dt,
            "nm_id": record.nm_id,
            "brand_name": record.brand,
            "barcode_ori": record.barcode_ori,
            "barcode_hand": record.barcode_hand,
            "return_type": record.return_type,
            "return_type_cn": record.return_type_cn,
            "reason": record.reason,
            "reason_cn": record.reason_cn,
            "reason_category": classify_return_reason(record.reason, record.reason_cn),
            "status": record.status,
            "status_cn": record.status_cn
            or KNOWN_STATUS_TRANSLATIONS.get(record.status or ""),
            "order_id": record.order_id,
            "srid": record.srid,
            "quantity": 1,
        }

    async def export_workbook(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        export_request: WBVOCPivotExportRequest,
    ) -> bytes:
        allowed_shop_ids = await shop_crud.get_accessible_ids_by_user_platform(
            db, user_id=user_id, platform="wildberries"
        )
        filters = export_request.filters
        created_from, created_to = _utc_bounds(filters)

        feedbacks = await crud_dwd_wb_voc_feedback_detail.list_feedbacks_for_export(
            db,
            allowed_shop_ids=allowed_shop_ids,
            shop_id=filters.shop_id,
            created_from=created_from,
            created_to=created_to,
            supplier_article=filters.supplier_article,
            nm_id=filters.nm_id,
            brand_name=filters.brand_name,
            sort_order="desc",
        )
        questions = await crud_dwd_wb_voc_question_detail.list_questions_for_export(
            db,
            allowed_shop_ids=allowed_shop_ids,
            shop_id=filters.shop_id,
            created_from=created_from,
            created_to=created_to,
            supplier_article=filters.supplier_article,
            nm_id=filters.nm_id,
            brand_name=filters.brand_name,
            sort_order="desc",
        )

        # Return DWD has no supplier_article. If that filter is supplied, return rows
        # cannot match it and are intentionally omitted from this export.
        returns = []
        if not filters.supplier_article:
            returns = await crud_dwd_wb_return_detail.list_returns_for_export(
                db,
                allowed_shop_ids=allowed_shop_ids,
                shop_id=filters.shop_id,
                date_from=filters.date_from,
                date_to=filters.date_to,
                nm_id=filters.nm_id,
                brand=filters.brand_name,
                sort_order="desc",
            )

        rows = [self._feedback_row(record) for record in feedbacks]
        rows.extend(self._question_row(record) for record in questions)
        rows.extend(self._return_row(record) for record in returns)
        rows.sort(
            key=lambda row: (
                row.get("business_date") or date.min,
                row.get("record_type") or "",
                row.get("record_id") or "",
            ),
            reverse=True,
        )
        return build_customer_voice_workbook(rows)


wb_voc_pivot_service = WBVOCPivotService()
