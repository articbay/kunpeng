"""Reviewed business translations for Wildberries order statuses."""

from typing import Optional

from kunpeng.constants.wb_order_status import (WB_ORDER_STATUS_CN,
                                               WB_SUPPLIER_STATUS_CN)


def reviewed_wb_order_status_cn(status: Optional[str]) -> Optional[str]:
    """Return the reviewed translation for a known WB order status."""
    normalized_status = (status or "").strip().lower()
    return WB_ORDER_STATUS_CN.get(normalized_status)


def reviewed_wb_supplier_status_cn(status: Optional[str]) -> Optional[str]:
    """Return the lifecycle translation for a known supplier status."""
    normalized_status = (status or "").strip().lower()
    return WB_SUPPLIER_STATUS_CN.get(normalized_status)


def resolve_wb_order_status_cn(
    *,
    status: Optional[str],
    stored_translation: Optional[str],
) -> Optional[str]:
    """Prefer reviewed terminology while preserving unknown translations."""
    return reviewed_wb_order_status_cn(status) or stored_translation


def resolve_wb_supplier_status_cn(
    *,
    status: Optional[str],
    stored_translation: Optional[str],
) -> Optional[str]:
    """Prefer lifecycle terminology while preserving unknown translations."""
    return reviewed_wb_supplier_status_cn(status) or stored_translation
