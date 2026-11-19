from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from kunpeng.services.shop_access_service import ShopAccessService


@pytest.mark.asyncio
async def test_get_options_marks_only_existing_grants():
    service = ShopAccessService()
    shops = [
        SimpleNamespace(id=11, name="WB A", platform="wildberries"),
        SimpleNamespace(id=12, name="Ozon B", platform="ozon"),
    ]

    with (
        patch(
            "kunpeng.services.shop_access_service.user_crud.get",
            new=AsyncMock(return_value=SimpleNamespace(id=7)),
        ),
        patch(
            "kunpeng.services.shop_access_service.shop_crud.get_by_user",
            new=AsyncMock(return_value=shops),
        ),
        patch(
            "kunpeng.services.shop_access_service.shop_crud.get_granted_shop_ids",
            new=AsyncMock(return_value=[12]),
        ),
    ):
        response = await service.get_options(AsyncMock(), owner_id=1, user_id=7)

    assert response.user_id == 7
    assert [(item.shop_id, item.granted) for item in response.shops] == [
        (11, False),
        (12, True),
    ]


@pytest.mark.asyncio
async def test_replace_grants_rejects_shop_not_owned_by_admin():
    service = ShopAccessService()
    options = SimpleNamespace(
        shops=[SimpleNamespace(shop_id=11), SimpleNamespace(shop_id=12)]
    )

    with patch.object(service, "get_options", new=AsyncMock(return_value=options)):
        with pytest.raises(HTTPException) as exc_info:
            await service.replace_grants(
                AsyncMock(), owner_id=1, user_id=7, shop_ids=[11, 99]
            )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_replace_grants_only_replaces_current_admin_shops():
    service = ShopAccessService()
    before = SimpleNamespace(
        shops=[SimpleNamespace(shop_id=11), SimpleNamespace(shop_id=12)]
    )
    after = SimpleNamespace(shops=[])

    with (
        patch.object(
            service, "get_options", new=AsyncMock(side_effect=[before, after])
        ),
        patch(
            "kunpeng.services.shop_access_service.shop_crud.replace_grants_for_owner",
            new=AsyncMock(),
        ) as replace_grants,
    ):
        response = await service.replace_grants(
            AsyncMock(), owner_id=1, user_id=7, shop_ids=[12]
        )

    assert response is after
    assert replace_grants.await_args.kwargs == {
        "user_id": 7,
        "owner_shop_ids": [11, 12],
        "granted_shop_ids": [12],
    }
