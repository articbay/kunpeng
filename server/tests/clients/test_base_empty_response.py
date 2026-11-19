"""平台客户端空响应处理测试。"""

from unittest.mock import AsyncMock

import httpx
import pytest

from kunpeng.clients.base import BasePlatformClient


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "content"),
    [(204, b""), (200, b"   \r\n")],
)
async def test_request_maps_empty_success_response_to_empty_list(
    status_code: int, content: bytes
):
    client = BasePlatformClient("test-key", "https://example.test")
    request = httpx.Request("GET", "https://example.test/empty")
    client._client = AsyncMock()
    client._client.request.return_value = httpx.Response(
        status_code,
        content=content,
        request=request,
    )

    result = await client._request("GET", "/empty")

    assert result == []
