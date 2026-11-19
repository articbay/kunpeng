import httpx

from kunpeng.clients.base import _is_retryable_request_error


def _status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.test/data")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError("request failed", request=request, response=response)


def test_transport_and_server_errors_are_retryable() -> None:
    assert _is_retryable_request_error(httpx.ConnectError("tls interrupted"))
    assert _is_retryable_request_error(httpx.ConnectTimeout("connect timeout"))
    assert _is_retryable_request_error(_status_error(503))


def test_permanent_permission_error_is_not_retryable() -> None:
    assert not _is_retryable_request_error(_status_error(403))
