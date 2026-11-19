"""
Ozon ODS 层 - 销售实现报告相关表 CRUD
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.crud.ods.ozon.utils import (parse_datetime_field,
                                         parse_iso_datetime, safe_decimal,
                                         safe_int, safe_str)
from kunpeng.models.ods.ozon.realization import (
    ODSOzonFinanceRealizationHeader, ODSOzonFinanceRealizationRow)

logger = logging.getLogger(__name__)


# ============================================================================
# Finance Realization Header 销售实现报告头表 CRUD
# ============================================================================
class CRUDOzonFinanceRealizationHeader(
    CRUDBase[ODSOzonFinanceRealizationHeader, Dict[str, Any], Dict[str, Any]]
):
    """ODS 销售实现报告头表 CRUD"""

    async def _get_existing_item(
        self,
        db: AsyncSession,
        shop_id: int,
        report_number: str,
    ) -> Optional[ODSOzonFinanceRealizationHeader]:
        """根据唯一约束获取现有记录"""
        query = select(ODSOzonFinanceRealizationHeader).where(
            (ODSOzonFinanceRealizationHeader.shop_id == shop_id)
            & (ODSOzonFinanceRealizationHeader.report_number == report_number)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    def _extract_item_data(
        self,
        item: Dict[str, Any],
        shop_id: int,
    ) -> Dict[str, Any]:
        """从API响应中提取数据到模型字段"""
        raw_header = item.get("header") or {}
        header = (
            raw_header.get("header")
            if isinstance(raw_header.get("header"), dict)
            else raw_header
        )
        payer = header.get("payer") or {}
        receiver = header.get("receiver") or {}

        def pick(*keys: str):
            for key in keys:
                value = header.get(key)
                if value not in (None, ""):
                    return value
            return None

        return {
            "shop_id": shop_id,
            "row_data": item,
            "report_number": safe_str(pick("num", "report_number")),
            "doc_date": parse_iso_datetime(pick("doc_date")),
            "start_date": parse_iso_datetime(pick("start_date")),
            "stop_date": parse_iso_datetime(pick("stop_date")),
            "contract_date": parse_iso_datetime(pick("contract_date")),
            "contract_number": safe_str(pick("contract_num", "contract_number")),
            "currency": safe_str(pick("currency_sys_name", "currency")),
            "payer_name": safe_str(pick("payer_name") or payer.get("name")),
            "payer_inn": safe_str(pick("payer_inn") or payer.get("inn")),
            "payer_kpp": safe_str(pick("payer_kpp") or payer.get("kpp")),
            "receiver_name": safe_str(
                pick("rcv_name", "receiver_name") or receiver.get("name")
            ),
            "receiver_inn": safe_str(
                pick("rcv_inn", "receiver_inn") or receiver.get("inn")
            ),
            "receiver_kpp": safe_str(
                pick("rcv_kpp", "receiver_kpp") or receiver.get("kpp")
            ),
        }

    async def create_or_update(
        self,
        db: AsyncSession,
        *,
        item: Dict[str, Any],
        shop_id: int,
    ) -> ODSOzonFinanceRealizationHeader:
        """创建或更新销售实现报告头表"""
        item_data = self._extract_item_data(item, shop_id)
        report_number = item_data.get("report_number")

        existing = None
        if report_number is not None:
            existing = await self._get_existing_item(db, shop_id, report_number)

        if existing:
            for field, value in item_data.items():
                if field != "id" and hasattr(existing, field):
                    setattr(existing, field, value)
            return existing
        else:
            new_item = ODSOzonFinanceRealizationHeader(**item_data)
            db.add(new_item)
            return new_item


# ============================================================================
# Finance Realization Row 销售实现报告行表 CRUD
# ============================================================================
class CRUDOzonFinanceRealizationRow(
    CRUDBase[ODSOzonFinanceRealizationRow, Dict[str, Any], Dict[str, Any]]
):
    """ODS 销售实现报告行表 CRUD"""

    async def _get_existing_item(
        self,
        db: AsyncSession,
        shop_id: int,
        header_id: int,
        row_number: int,
    ) -> Optional[ODSOzonFinanceRealizationRow]:
        """根据唯一约束获取现有记录"""
        query = select(ODSOzonFinanceRealizationRow).where(
            (ODSOzonFinanceRealizationRow.shop_id == shop_id)
            & (ODSOzonFinanceRealizationRow.header_id == header_id)
            & (ODSOzonFinanceRealizationRow.row_number == row_number)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    def _extract_item_data(
        self,
        item: Dict[str, Any],
        shop_id: int,
        header_id: int,
    ) -> Dict[str, Any]:
        """从API响应中提取数据到模型字段"""
        product = item.get("item") or {}
        delivery = item.get("delivery_commission") or {}
        return_data = item.get("return_commission") or {}

        row_number = item.get("rowNumber")
        if row_number is None:
            row_number = item.get("row_number")

        return {
            "shop_id": shop_id,
            "row_data": item,
            "header_id": header_id,
            "row_number": safe_int(row_number),
            "product_name": safe_str(product.get("name")),
            "offer_id": safe_str(product.get("offer_id")),
            "sku": safe_int(product.get("sku")),
            "barcode": safe_str(product.get("barcode")),
            "seller_price_per_instance": safe_decimal(
                item.get("seller_price_per_instance")
            ),
            "is_return": bool(return_data),
            "sold_price_per_instance": safe_decimal(delivery.get("price_per_instance")),
            "sold_quantity": safe_int(delivery.get("quantity")),
            "sold_amount": safe_decimal(delivery.get("amount")),
            "sold_standard_fee": safe_decimal(delivery.get("standard_fee")),
            "sold_bonus": safe_decimal(delivery.get("bonus")),
            "sold_bank_coinvestment": safe_decimal(delivery.get("bank_coinvestment")),
            "sold_total": safe_decimal(delivery.get("total")),
            "return_price_per_instance": safe_decimal(
                return_data.get("price_per_instance")
            ),
            "return_quantity": safe_int(return_data.get("quantity")),
            "return_amount": safe_decimal(return_data.get("amount")),
            "return_standard_fee": safe_decimal(return_data.get("standard_fee")),
            "return_bonus": safe_decimal(return_data.get("bonus")),
            "return_bank_coinvestment": safe_decimal(
                return_data.get("bank_coinvestment")
            ),
            "return_total": safe_decimal(return_data.get("total")),
            "commission_ratio": safe_decimal(item.get("commission_ratio")),
        }

    async def create_many_for_header(
        self,
        db: AsyncSession,
        *,
        items: List[Dict[str, Any]],
        shop_id: int,
        header_id: int,
    ) -> List[ODSOzonFinanceRealizationRow]:
        """为单个报告头创建/更新行数据"""
        result_list = []
        for item in items:
            item_data = self._extract_item_data(item, shop_id, header_id)
            row_number = item_data.get("row_number")

            existing = None
            if row_number is not None:
                existing = await self._get_existing_item(
                    db, shop_id, header_id, row_number
                )

            if existing:
                for field, value in item_data.items():
                    if field != "id" and hasattr(existing, field):
                        setattr(existing, field, value)
                result_list.append(existing)
            else:
                new_item = ODSOzonFinanceRealizationRow(**item_data)
                db.add(new_item)
                result_list.append(new_item)

        await db.flush()
        return result_list


# ============================================================================
# CRUD实例
# ============================================================================
crud_ods_ozon_finance_realization_header = CRUDOzonFinanceRealizationHeader(
    ODSOzonFinanceRealizationHeader
)
crud_ods_ozon_finance_realization_row = CRUDOzonFinanceRealizationRow(
    ODSOzonFinanceRealizationRow
)
