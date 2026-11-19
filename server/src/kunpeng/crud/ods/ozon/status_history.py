"""Ozon 状态历史的不可变、幂等写入。"""

import hashlib
import json
from typing import Any, Dict, List

from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.ods.ozon.utils import parse_iso_datetime, safe_int, safe_str
from kunpeng.models.ods.ozon.status_history import (
    ODSOzonPostingStatusHistory,
    ODSOzonReturnStatusHistory,
)
from kunpeng.utils.timezone import now_platform


def _state_key(parts: List[Any]) -> str:
    raw = json.dumps(parts, ensure_ascii=False, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class CRUDOzonPostingStatusHistory:
    async def record_many(
        self,
        db: AsyncSession,
        *,
        items: List[Dict[str, Any]],
        shop_id: int,
        mode: str,
    ) -> int:
        observed_at = now_platform()
        rows = []
        for item in items:
            posting_number = safe_str(item.get("posting_number"))
            if not posting_number:
                continue
            status = safe_str(item.get("status"))
            substatus = safe_str(item.get("substatus"))
            changed_at_raw = item.get("status_changed_at") or item.get("updated_at")
            key = _state_key([status, substatus, changed_at_raw])
            rows.append(
                {
                    "shop_id": shop_id,
                    "mode": mode,
                    "posting_number": posting_number,
                    "order_id": safe_int(item.get("order_id")),
                    "status": status,
                    "substatus": substatus,
                    "state_key": key,
                    "source_changed_at": parse_iso_datetime(changed_at_raw),
                    "first_observed_at": observed_at,
                    "row_data": item,
                }
            )
        if not rows:
            return 0
        statement = insert(ODSOzonPostingStatusHistory).values(rows)
        await db.execute(statement.on_duplicate_key_update(state_key=statement.inserted.state_key))
        return len(rows)


class CRUDOzonReturnStatusHistory:
    async def record_many(
        self, db: AsyncSession, *, items: List[Dict[str, Any]], shop_id: int
    ) -> int:
        observed_at = now_platform()
        rows = []
        for item in items:
            return_id = safe_int(item.get("id") or item.get("return_id"))
            if return_id is None:
                continue
            visual = item.get("visual") or {}
            status = visual.get("status") or {}
            changed_at_raw = visual.get("change_moment")
            status_id = safe_int(status.get("id"))
            status_sys_name = safe_str(status.get("sys_name"))
            key = _state_key([status_id, status_sys_name, changed_at_raw])
            rows.append(
                {
                    "shop_id": shop_id,
                    "return_id": return_id,
                    "posting_number": safe_str(item.get("posting_number")),
                    "status_id": status_id,
                    "status_sys_name": status_sys_name,
                    "status_display_name": safe_str(status.get("display_name")),
                    "state_key": key,
                    "source_changed_at": parse_iso_datetime(changed_at_raw),
                    "first_observed_at": observed_at,
                    "row_data": item,
                }
            )
        if not rows:
            return 0
        statement = insert(ODSOzonReturnStatusHistory).values(rows)
        await db.execute(statement.on_duplicate_key_update(state_key=statement.inserted.state_key))
        return len(rows)


crud_ods_ozon_posting_status_history = CRUDOzonPostingStatusHistory()
crud_ods_ozon_return_status_history = CRUDOzonReturnStatusHistory()
