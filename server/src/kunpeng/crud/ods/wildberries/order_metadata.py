"""Idempotent persistence for Wildberries FBS assembly order metadata."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.ods.wildberries.marketplace import ODSWBMarketplaceOrder
from kunpeng.models.ods.wildberries.order_metadata import ODSWBOrderMetadata

logger = logging.getLogger(__name__)


class CRUDODSWBOrderMetadata:
    """Read source order IDs and upsert metadata by ``(shop_id, order_id)``."""

    async def get_source_order_ids(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        window_start: datetime,
        window_end: datetime,
    ) -> List[int]:
        """Return existing Marketplace order IDs in the half-open time window."""
        result = await db.execute(
            select(ODSWBMarketplaceOrder.order_id)
            .where(
                and_(
                    ODSWBMarketplaceOrder.shop_id == shop_id,
                    ODSWBMarketplaceOrder.created_at >= window_start,
                    ODSWBMarketplaceOrder.created_at < window_end,
                )
            )
            .order_by(ODSWBMarketplaceOrder.order_id)
        )
        return [int(order_id) for order_id in result.scalars().all()]

    @staticmethod
    def _to_record(
        data: Dict[str, Any],
        *,
        shop_id: int,
        synced_at: datetime,
    ) -> Optional[Dict[str, Any]]:
        order_id = data.get("id")
        try:
            order_id = int(order_id)
        except (TypeError, ValueError):
            logger.warning("[ODS CRUD] 跳过缺少有效 id 的 Wildberries 订单元数据")
            return None

        return {
            "shop_id": shop_id,
            "order_id": order_id,
            "row_data": data,
            "meta_details": data.get("metaDetails"),
            "legacy_meta": data.get("meta"),
            "last_synced_at": synced_at,
        }

    async def upsert_many(
        self,
        db: AsyncSession,
        *,
        metadata: List[Dict[str, Any]],
        shop_id: int,
        synced_at: datetime,
    ) -> int:
        """Insert metadata and refresh mutable fields for existing orders."""
        records = [
            record
            for data in metadata
            if (
                record := self._to_record(
                    data,
                    shop_id=shop_id,
                    synced_at=synced_at,
                )
            )
            is not None
        ]
        if not records:
            return 0

        stmt = insert(ODSWBOrderMetadata).values(records)
        upsert_stmt = stmt.on_duplicate_key_update(
            row_data=stmt.inserted.row_data,
            meta_details=stmt.inserted.meta_details,
            legacy_meta=stmt.inserted.legacy_meta,
            last_synced_at=stmt.inserted.last_synced_at,
            update_time=func.now(),
        )
        await db.execute(upsert_stmt)
        await db.commit()
        logger.info(
            "[ODS CRUD] Wildberries 订单元数据幂等写入完成: shop_id=%s, count=%s",
            shop_id,
            len(records),
        )
        return len(records)


crud_ods_wb_order_metadata = CRUDODSWBOrderMetadata()
