"""Wildberries 卖家余额快照 CRUD。"""

from datetime import date
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.models.ods.wildberries.seller_balance import ODSWBSellerBalance
from kunpeng.utils.timezone import now_platform, today_platform


class CRUDODSWBSellerBalance(
    CRUDBase[ODSWBSellerBalance, Dict[str, Any], Dict[str, Any]]
):
    """按店铺和平台日期幂等保存卖家余额快照。"""

    async def get_by_shop_and_date(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        snapshot_date: date,
    ) -> Optional[ODSWBSellerBalance]:
        result = await db.execute(
            select(ODSWBSellerBalance).where(
                ODSWBSellerBalance.shop_id == shop_id,
                ODSWBSellerBalance.snapshot_date == snapshot_date,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_snapshot(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        balance_data: Dict[str, Any],
    ) -> ODSWBSellerBalance:
        snapshot_date = today_platform()
        values = {
            "shop_id": shop_id,
            "row_data": balance_data,
            "currency": balance_data.get("currency"),
            "current": balance_data.get("current"),
            "for_withdraw": balance_data.get("for_withdraw"),
            "snapshot_date": snapshot_date,
            "synced_at": now_platform(),
        }
        existing = await self.get_by_shop_and_date(
            db,
            shop_id=shop_id,
            snapshot_date=snapshot_date,
        )
        if existing:
            for field, value in values.items():
                setattr(existing, field, value)
            record = existing
        else:
            record = ODSWBSellerBalance(**values)
            db.add(record)

        try:
            await db.commit()
            await db.refresh(record)
        except Exception:
            await db.rollback()
            raise
        return record


crud_ods_wb_seller_balance = CRUDODSWBSellerBalance(ODSWBSellerBalance)
