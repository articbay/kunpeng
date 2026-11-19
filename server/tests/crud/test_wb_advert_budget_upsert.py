"""Wildberries 广告预算 MySQL 原子 upsert 回归测试。"""

from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.dialects import mysql
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.ods.wildberries.advert_budget import crud_ods_wb_advert_budget


@pytest.mark.asyncio
async def test_create_or_update_uses_mysql_atomic_upsert():
    """并发安全依赖单条 ON DUPLICATE KEY UPDATE，而不是先查再插。"""
    db = AsyncMock(spec=AsyncSession)
    persisted = Mock()
    select_result = Mock()
    select_result.scalar_one_or_none.return_value = persisted
    db.execute.side_effect = [Mock(), select_result]

    result = await crud_ods_wb_advert_budget.create_or_update(
        db,
        budget_data={"cash": 100, "netting": 20, "total": 120},
        advert_id=456,
        shop_id=123,
    )

    upsert_stmt = db.execute.await_args_list[0].args[0]
    sql = str(upsert_stmt.compile(dialect=mysql.dialect()))

    assert "ON DUPLICATE KEY UPDATE" in sql
    assert "row_data = VALUES(row_data)" in sql
    assert "cash = VALUES(cash)" in sql
    assert "netting = VALUES(netting)" in sql
    assert "total = VALUES(total)" in sql
    assert "sync_at = VALUES(sync_at)" in sql
    assert result is persisted
    db.commit.assert_awaited_once()
    assert db.execute.await_count == 2
