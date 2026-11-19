"""
Ozon ODS 层 - 财务应计相关表 CRUD
"""
import logging
from typing import Any, Dict, List, Optional
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.models.ods.ozon.finance import (
    ODSOzonFinanceAccrual,
    ODSOzonAccrualFee,
)
from kunpeng.crud.ods.ozon.utils import safe_int, safe_str, safe_decimal, parse_iso_datetime, parse_datetime_field

logger = logging.getLogger(__name__)


def _assign_money(
    data: Dict[str, Any],
    money: Any,
    amount_key: str,
    currency_key: str,
) -> None:
    """把 Ozon 的 {"amount": "...", "currency": "..."} 嵌套对象拆分到金额/币种两列"""
    if not isinstance(money, dict):
        return
    if money.get('amount') is not None:
        data[amount_key] = safe_decimal(money.get('amount'))
    if money.get('currency') is not None:
        data[currency_key] = safe_str(money.get('currency'))


def _money_amount(money: Any) -> Optional[Decimal]:
    """从 Ozon 的 {"amount": "...", "currency": "..."} 对象中取金额(卢布)。"""
    if not isinstance(money, dict):
        return None
    return safe_decimal(money.get('amount')) if money.get('amount') is not None else None


def _parse_commission_ratio(value: Any) -> Optional[Decimal]:
    """解析佣金比例。

    Ozon by-day 返回形如 'value:"0.400000"' 的字符串，需剥离外层包装后取数字；
    也兼容直接是数字/普通数字字符串的情况。
    """
    if value is None:
        return None
    if isinstance(value, str) and 'value:' in value:
        import re
        m = re.search(r'-?\d+(?:\.\d+)?', value)
        return safe_decimal(m.group(0)) if m else None
    return safe_decimal(value)


# ============================================================================
# Finance Accrual 财务应计主表 CRUD
# ============================================================================
class CRUDOzonFinanceAccrual(CRUDBase[ODSOzonFinanceAccrual, Dict[str, Any], Dict[str, Any]]):
    """ODS 财务应计主表 CRUD"""

    async def _get_existing_item(
        self,
        db: AsyncSession,
        shop_id: int,
        accrual_id: int,
    ) -> Optional[ODSOzonFinanceAccrual]:
        """根据唯一约束 (shop_id, accrual_id) 获取现有记录"""
        query = select(ODSOzonFinanceAccrual).where(
            (ODSOzonFinanceAccrual.shop_id == shop_id) &
            (ODSOzonFinanceAccrual.accrual_id == accrual_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    def _extract_item_data(
        self,
        item: Dict[str, Any],
        shop_id: int,
        accrual_date: date,
        source_api: str,
    ) -> Dict[str, Any]:
        """从API响应中提取数据到模型字段"""
        # 只提取模型中实际存在的字段
        data = {
            'shop_id': shop_id,
            'row_data': item,
            'accrual_date': parse_iso_datetime(accrual_date) if isinstance(accrual_date, str) else accrual_date,
            'source_api': source_api,
        }

        # by-day 接口以 accrual_id 唯一标识每条应计记录
        if 'accrual_id' in item:
            data['accrual_id'] = safe_int(item.get('accrual_id'))

        # 应计类型：by-day 顶层不返回统一 type_id。
        # 仅 NON_ITEM 类别有单一类型（non_item_fee.type_id）；POSTING/ITEM 为多类型，明细见子表。
        non_item_fee = item.get('non_item_fee')
        if isinstance(non_item_fee, dict) and non_item_fee.get('type_id') is not None:
            data['accrual_type_id'] = safe_int(non_item_fee.get('type_id'))

        # 发货模式在 posting.delivery_schema，兼容历史顶层 delivery_schema
        posting = item.get('posting')
        if isinstance(posting, dict) and posting.get('delivery_schema') is not None:
            data['delivery_schema'] = safe_str(posting.get('delivery_schema'))
        elif 'delivery_schema' in item:
            data['delivery_schema'] = safe_str(item.get('delivery_schema'))

        # 总金额：by-day 返回嵌套对象 {"amount": "...", "currency": "..."}
        total_amount = item.get('total_amount')
        if isinstance(total_amount, dict):
            data['total_amount'] = safe_decimal(total_amount.get('amount'))
            if total_amount.get('currency') is not None:
                data['total_currency'] = safe_str(total_amount.get('currency'))
        elif 'total_amount' in item:
            data['total_amount'] = safe_decimal(item.get('total_amount'))
        if 'total_currency' in item:
            data['total_currency'] = safe_str(item.get('total_currency'))
        if 'currency' in item:
            data['total_currency'] = safe_str(item.get('currency'))
        if 'unit_number' in item:
            data['unit_number'] = safe_str(item.get('unit_number'))
        if 'accrued_category' in item:
            data['accrued_category'] = safe_str(item.get('accrued_category'))

        return data

    async def create_many(
        self,
        db: AsyncSession,
        *,
        items: List[Dict[str, Any]],
        shop_id: int,
        accrual_date: date,
        source_api: str,
    ) -> List[ODSOzonFinanceAccrual]:
        """批量创建/更新财务应计主表"""
        logger.debug(
            f"[ODS Ozon Finance Accrual] 开始同步 - 店铺: {shop_id}, 日期: {accrual_date}, 数据量: {len(items)}"
        )

        result_list = []
        updated_count = 0
        created_count = 0

        for item in items:
            item_data = self._extract_item_data(item, shop_id, accrual_date, source_api)
            accrual_id = item_data.get('accrual_id')

            existing = None
            if accrual_id is not None:
                existing = await self._get_existing_item(db, shop_id, accrual_id)

            if existing:
                for field, value in item_data.items():
                    if field != 'id' and hasattr(existing, field):
                        setattr(existing, field, value)
                result_list.append(existing)
                updated_count += 1
            else:
                new_item = ODSOzonFinanceAccrual(**item_data)
                db.add(new_item)
                result_list.append(new_item)
                created_count += 1

        await db.flush()

        logger.debug(
            f"[ODS Ozon Finance Accrual] 同步完成 - 新增: {created_count}, 更新: {updated_count}, 总计: {len(result_list)}"
        )
        return result_list


# ============================================================================
# Accrual Fee 应计费用明细表 CRUD（统一拆平 POSTING/ITEM/NON_ITEM 的费用行）
# ============================================================================
class CRUDOzonAccrualFee(CRUDBase[ODSOzonAccrualFee, Dict[str, Any], Dict[str, Any]]):
    """ODS 应计费用明细表 CRUD"""

    @staticmethod
    def build_fee_lines(
        accrual: Dict[str, Any],
        shop_id: int,
        accrual_id: int,
        accrual_date: Any,
        type_dict: Optional[Dict[int, Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """把一条 by-day 应计记录拆成"一条费用一行"的明细列表。

        费用来源见模型文档。金额均取嵌套 {"amount","currency"}；
        营收(revenue)为合成行(type_id=-1)；bonus/coinvestment 不计入(不产生费用行)。
        """
        type_dict = type_dict or {}
        unit_number = safe_str(accrual.get("unit_number"))
        accrued_category = safe_str(accrual.get("accrued_category"))
        parsed_date = parse_iso_datetime(accrual_date) if isinstance(accrual_date, str) else accrual_date

        lines: List[Dict[str, Any]] = []

        def _add(fee_source: str, sku: Any, type_id: Any, money: Any, raw: Any,
                 delivery_schema: Any = None, extra: Optional[Dict[str, Any]] = None) -> None:
            data: Dict[str, Any] = {
                "shop_id": shop_id,
                "accrual_id": accrual_id,
                "accrual_date": parsed_date,
                "unit_number": unit_number,
                "accrued_category": accrued_category,
                "fee_source": fee_source,
                "sku": safe_int(sku) if sku is not None else None,
                "type_id": safe_int(type_id) if type_id is not None else None,
                "delivery_schema": safe_str(delivery_schema) if delivery_schema is not None else None,
                "row_data": raw,
            }
            if extra:
                data.update(extra)
            _assign_money(data, money, "amount", "currency")
            # 冗余类型名称
            tid = data.get("type_id")
            if tid is not None and tid in type_dict:
                data["type_name"] = type_dict[tid].get("name")
                data["type_desc"] = type_dict[tid].get("description")
            elif tid == -1:
                data["type_name"] = "Revenue"
                data["type_desc"] = "营收"
            lines.append(data)

        # POSTING：营收 + 销售佣金 + 各条物流服务费
        posting = accrual.get("posting")
        if isinstance(posting, dict):
            delivery_schema = posting.get("delivery_schema")
            for product in (posting.get("products") or []):
                sku = product.get("sku")
                commission = product.get("commission")
                if isinstance(commission, dict):
                    if commission.get("sale_amount") is not None:
                        _add("revenue", sku, -1, commission.get("sale_amount"),
                             {"sale_amount": commission.get("sale_amount")}, delivery_schema,
                             extra={
                                 "seller_price": _money_amount(commission.get("seller_price")),
                                 "commission_ratio": _parse_commission_ratio(commission.get("commission_ratio")),
                             })
                    if commission.get("sale_commission") is not None:
                        _add("sale_commission", sku, 69, commission.get("sale_commission"),
                             {"sale_commission": commission.get("sale_commission")}, delivery_schema)
                delivery = product.get("delivery")
                if isinstance(delivery, dict):
                    for service in (delivery.get("services") or []):
                        _add("posting_service", sku, service.get("type_id"),
                             service.get("accrued"), service, delivery_schema)

        # ITEM：商品费用
        item_fees = accrual.get("item_fees")
        if isinstance(item_fees, dict):
            for fee_group in (item_fees.get("fees") or []):
                sku = fee_group.get("sku")
                for fee in (fee_group.get("fees") or []):
                    _add("item_fee", sku, fee.get("type_id"), fee.get("accrued"), fee)

        # NON_ITEM：非商品费用(单对象)
        non_item_fee = accrual.get("non_item_fee")
        if isinstance(non_item_fee, dict):
            _add("non_item_fee", None, non_item_fee.get("type_id"),
                 non_item_fee.get("accrued"), non_item_fee)

        return lines

    async def replace_for_accrual(
        self,
        db: AsyncSession,
        *,
        accrual: Dict[str, Any],
        shop_id: int,
        accrual_id: int,
        accrual_date: Any,
        type_dict: Optional[Dict[int, Dict[str, Any]]] = None,
    ) -> List[ODSOzonAccrualFee]:
        """幂等写入：先删该 accrual_id 的旧费用行，再插入最新拆解结果。"""
        await db.execute(
            delete(ODSOzonAccrualFee).where(
                (ODSOzonAccrualFee.shop_id == shop_id) &
                (ODSOzonAccrualFee.accrual_id == accrual_id)
            )
        )
        lines = self.build_fee_lines(accrual, shop_id, accrual_id, accrual_date, type_dict)
        result_list = []
        for data in lines:
            new_item = ODSOzonAccrualFee(**data)
            db.add(new_item)
            result_list.append(new_item)
        await db.flush()
        return result_list


# ============================================================================
# CRUD实例
# ============================================================================
crud_ods_ozon_finance_accrual = CRUDOzonFinanceAccrual(ODSOzonFinanceAccrual)
crud_ods_ozon_accrual_fee = CRUDOzonAccrualFee(ODSOzonAccrualFee)
