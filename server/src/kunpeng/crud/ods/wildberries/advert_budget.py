"""
ODS 层 - 广告预算 CRUD 操作
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.models.ods.wildberries.balance import ODSWBAdvertBudget

logger = logging.getLogger(__name__)


class CRUDODSWBAdvertBudget(
    CRUDBase[ODSWBAdvertBudget, Dict[str, Any], Dict[str, Any]]
):
    """ODS 广告预算数据 CRUD"""

    async def _get_existing(
        self, db: AsyncSession, shop_id: int, advert_id: int, sync_date: date
    ) -> Optional[ODSWBAdvertBudget]:
        """根据唯一索引获取现有记录"""
        result = await db.execute(
            select(ODSWBAdvertBudget).where(
                (ODSWBAdvertBudget.shop_id == shop_id)
                & (ODSWBAdvertBudget.advert_id == advert_id)
                & (ODSWBAdvertBudget.sync_date == sync_date)
            )
        )
        return result.scalar_one_or_none()

    async def create_or_update(
        self,
        db: AsyncSession,
        *,
        budget_data: Dict[str, Any],
        advert_id: int,
        shop_id: int,
    ) -> ODSWBAdvertBudget:
        """创建或更新广告预算记录（按天分区）"""
        logger.debug(
            f"[ODS CRUD] 开始同步广告预算 - 店铺: {shop_id}, 广告: {advert_id}"
        )

        sync_date = date.today()
        sync_at = datetime.now().astimezone()

        # 构建 ODS 记录数据
        ods_data = {
            "shop_id": shop_id,
            "row_data": budget_data,
            "advert_id": advert_id,
            "cash": budget_data.get("cash"),
            "netting": budget_data.get("netting"),
            "total": budget_data.get("total"),
            "sync_date": sync_date,
            "sync_at": sync_at,
        }

        statement = insert(ODSWBAdvertBudget).values(**ods_data)
        await db.execute(
            statement.on_duplicate_key_update(
                row_data=statement.inserted.row_data,
                cash=statement.inserted.cash,
                netting=statement.inserted.netting,
                total=statement.inserted.total,
                sync_at=statement.inserted.sync_at,
            )
        )
        await db.commit()

        result = await self._get_existing(db, shop_id, advert_id, sync_date)
        if result is None:
            raise RuntimeError("广告预算 upsert 后未找到持久化记录")
        logger.debug(f"[ODS CRUD] 广告预算同步完成")
        return result


# CRUD 实例
crud_ods_wb_advert_budget = CRUDODSWBAdvertBudget(ODSWBAdvertBudget)
