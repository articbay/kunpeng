"""Idempotent persistence for Wildberries buyers' return claims."""

import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.ods.wildberries.return_claims import ODSWBReturnClaim
from kunpeng.utils.timezone import platform_tz

logger = logging.getLogger(__name__)


def parse_claim_datetime(value: Any) -> Optional[datetime]:
    """Parse WB claim timestamps and attach the platform timezone when omitted."""
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            logger.warning("[ODS CRUD] 无法解析退货申请时间: %s", value)
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=platform_tz())
    return parsed


def _safe_decimal(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


class CRUDODSWBReturnClaim:
    """Batch upsert claims using the table's ``(shop_id, claim_id)`` key."""

    @staticmethod
    def _to_record(
        data: Dict[str, Any], shop_id: int, synced_at: datetime
    ) -> Optional[Dict[str, Any]]:
        claim_id = data.get("id")
        if not claim_id:
            logger.warning("[ODS CRUD] 跳过缺少 id 的 Wildberries 退货申请")
            return None

        row_data = {key: value for key, value in data.items() if key != "_is_archive"}
        return {
            "shop_id": shop_id,
            "row_data": row_data,
            "claim_id": str(claim_id),
            "claim_type": data.get("claim_type"),
            "status": data.get("status"),
            "status_ex": data.get("status_ex"),
            "is_archive": bool(data.get("_is_archive", False)),
            "nm_id": data.get("nm_id"),
            "srid": data.get("srid"),
            "product_name": data.get("imt_name"),
            "user_comment": data.get("user_comment"),
            "wb_comment": data.get("wb_comment"),
            "origin_id_info": data.get("origin_id_info"),
            "claim_created_at": parse_claim_datetime(data.get("dt")),
            "claim_updated_at": parse_claim_datetime(data.get("dt_update")),
            "order_at": parse_claim_datetime(data.get("order_dt")),
            "delivery_at": parse_claim_datetime(data.get("delivery_dt")),
            "last_synced_at": synced_at,
            "photos": data.get("photos"),
            "video_paths": data.get("video_paths"),
            "actions": data.get("actions"),
            "price": _safe_decimal(data.get("price")),
            "currency_code": data.get("currency_code"),
        }

    async def upsert_many(
        self,
        db: AsyncSession,
        *,
        claims_data: List[Dict[str, Any]],
        shop_id: int,
        synced_at: datetime,
    ) -> int:
        """Insert new claims and update mutable fields for existing claims."""
        records = [
            record
            for data in claims_data
            if (record := self._to_record(data, shop_id, synced_at)) is not None
        ]
        if not records:
            return 0

        stmt = insert(ODSWBReturnClaim).values(records)
        upsert_stmt = stmt.on_duplicate_key_update(
            row_data=stmt.inserted.row_data,
            claim_type=stmt.inserted.claim_type,
            status=stmt.inserted.status,
            status_ex=stmt.inserted.status_ex,
            is_archive=stmt.inserted.is_archive,
            nm_id=stmt.inserted.nm_id,
            srid=stmt.inserted.srid,
            product_name=stmt.inserted.product_name,
            user_comment=stmt.inserted.user_comment,
            wb_comment=stmt.inserted.wb_comment,
            origin_id_info=stmt.inserted.origin_id_info,
            claim_created_at=stmt.inserted.claim_created_at,
            claim_updated_at=stmt.inserted.claim_updated_at,
            order_at=stmt.inserted.order_at,
            delivery_at=stmt.inserted.delivery_at,
            last_synced_at=stmt.inserted.last_synced_at,
            photos=stmt.inserted.photos,
            video_paths=stmt.inserted.video_paths,
            actions=stmt.inserted.actions,
            price=stmt.inserted.price,
            currency_code=stmt.inserted.currency_code,
            update_time=func.now(),
        )
        await db.execute(upsert_stmt)
        await db.commit()
        logger.info(
            "[ODS CRUD] Wildberries 退货申请幂等写入完成: shop_id=%s, count=%s",
            shop_id,
            len(records),
        )
        return len(records)


crud_ods_wb_return_claim = CRUDODSWBReturnClaim()
