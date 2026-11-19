from unittest.mock import AsyncMock, Mock

import pytest

from kunpeng.crud.ods.wildberries.adv_enhanced import (CRUDODSWBNormQueryList,
                                                       CRUDODSWBNormQueryStat)
from kunpeng.models.ods.wildberries.adv_enhanced import (ODSWBNormQueryList,
                                                         ODSWBNormQueryStat)


def make_db():
    db = Mock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_norm_query_list_preserves_explicit_false():
    crud = CRUDODSWBNormQueryList(ODSWBNormQueryList)
    crud._get_existing = AsyncMock(return_value=None)
    db = make_db()

    records = await crud.upsert_many(
        db,
        shop_id=1,
        list_data=[
            {
                "advertId": 10,
                "nmId": 20,
                "normQueries": {
                    "active": [{"normQuery": "keyword", "isActive": False}]
                },
            }
        ],
    )

    assert len(records) == 1
    assert records[0].is_active is False


@pytest.mark.asyncio
async def test_norm_query_stats_maps_nested_v1_stat_and_zero_values():
    crud = CRUDODSWBNormQueryStat(ODSWBNormQueryStat)
    crud._get_existing = AsyncMock(return_value=None)
    db = make_db()

    records = await crud.upsert_many(
        db,
        shop_id=1,
        stats_data=[
            {
                "advertId": 10,
                "nmId": 20,
                "date": "2026-08-27",
                "stat": {
                    "normQuery": "keyword",
                    "views": 0,
                    "clicks": 0,
                    "spend": 12.5,
                    "cpc": 0,
                },
            }
        ],
    )

    assert len(records) == 1
    assert records[0].norm_query == "keyword"
    assert records[0].views == 0
    assert records[0].clicks == 0
    assert records[0].sum_cost == 12.5
    assert records[0].cpc == 0
