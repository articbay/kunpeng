"""Wildberries 区域销售报告 CRUD。"""

import hashlib
import json
from datetime import date
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.models.ods.wildberries.region_sale import ODSWBRegionSale
from kunpeng.utils.timezone import now_platform


def build_region_sale_row_key(data: Dict[str, Any]) -> str:
    """根据 API 的地区和商品维度生成稳定键。"""
    dimensions = {
        "city_name": data.get("cityName"),
        "country_name": data.get("countryName"),
        "fo_name": data.get("foName"),
        "nm_id": data.get("nmID") if data.get("nmID") is not None else data.get("nmId"),
        "region_name": data.get("regionName"),
        "supplier_article": data.get("sa"),
    }
    payload = json.dumps(
        dimensions,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class CRUDODSWBRegionSale(CRUDBase[ODSWBRegionSale, Dict[str, Any], Dict[str, Any]]):
    """按店铺、查询窗口和地区商品维度幂等保存报告。"""

    async def upsert_many(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        date_from: date,
        date_to: date,
        report_data: List[Dict[str, Any]],
    ) -> List[ODSWBRegionSale]:
        prepared_rows = [
            (data, build_region_sale_row_key(data)) for data in report_data
        ]
        row_keys = {row_key for _, row_key in prepared_rows}
        records_by_key: Dict[str, ODSWBRegionSale] = {}
        if row_keys:
            result = await db.execute(
                select(ODSWBRegionSale).where(
                    ODSWBRegionSale.shop_id == shop_id,
                    ODSWBRegionSale.date_from == date_from,
                    ODSWBRegionSale.date_to == date_to,
                    ODSWBRegionSale.row_key.in_(row_keys),
                )
            )
            records_by_key = {
                record.row_key: record for record in result.scalars().all()
            }

        records: List[ODSWBRegionSale] = []
        synced_at = now_platform()

        for data, row_key in prepared_rows:
            values = {
                "shop_id": shop_id,
                "date_from": date_from,
                "date_to": date_to,
                "row_key": row_key,
                "country_name": data.get("countryName"),
                "fo_name": data.get("foName"),
                "region_name": data.get("regionName"),
                "city_name": data.get("cityName"),
                "nm_id": (
                    data.get("nmID")
                    if data.get("nmID") is not None
                    else data.get("nmId")
                ),
                "supplier_article": data.get("sa"),
                "sale_invoice_cost_price": data.get("saleInvoiceCostPrice"),
                "sale_invoice_cost_price_percent": data.get("saleInvoiceCostPricePerc"),
                "sale_item_invoice_qty": data.get("saleItemInvoiceQty"),
                "row_data": data,
                "synced_at": synced_at,
            }

            existing = records_by_key.get(row_key)
            if existing:
                for field, value in values.items():
                    setattr(existing, field, value)
                record = existing
            else:
                record = ODSWBRegionSale(**values)
                db.add(record)

            records_by_key[row_key] = record
            if record not in records:
                records.append(record)

        try:
            await db.commit()
            for record in records:
                await db.refresh(record)
        except Exception:
            await db.rollback()
            raise
        return records


crud_ods_wb_region_sale = CRUDODSWBRegionSale(ODSWBRegionSale)
