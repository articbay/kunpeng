import asyncio
import logging
from typing import Any, Dict, Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    wait_random,
)

logger = logging.getLogger(__name__)

_SENSITIVE_HEADER_NAMES = {
    "api-key",
    "authorization",
    "client-id",
    "cookie",
    "proxy-authorization",
    "set-cookie",
    "x-api-key",
}


def redact_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Return log-safe headers without exposing credentials or cookies."""
    return {
        name: ("***REDACTED***" if name.lower() in _SENSITIVE_HEADER_NAMES else value)
        for name, value in headers.items()
    }


class RateLimitError(Exception):
    """限流错误（不走通用 @retry 退避）。

    某些平台接口（如 Ozon Performance 异步报表：同一时刻仅允许 1 个活跃报表任务）
    的限流需要"分钟级"排队等待，base 客户端 2~10s 的指数退避重试对其无效，
    反而制造无谓的请求与噪音日志。因此这类限流不在 base 层重试，直接抛出本异常，
    交由上层业务（如提交层的长退避排队）处理。
    """

    def __init__(self, message: str, response: Optional[httpx.Response] = None):
        super().__init__(message)
        self.response = response


def _is_rate_limit_response(response: httpx.Response) -> bool:
    """判断响应是否为"活跃请求/报表数达上限"类限流。

    覆盖 HTTP 429，以及 Ozon 侧返回的 {"error": "Превышен лимит активных запросов (максимум 1)"}。
    """
    text = (response.text or "").lower()
    return response.status_code == 429 or "лимит активн" in text or "максимум 1" in text


def _is_retryable_request_error(exc: BaseException) -> bool:
    """Retry transient transport/server failures, but not permanent 4xx errors."""
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500 or exc.response.status_code in {
            408,
            425,
        }
    return False


class RateLimiter:
    """简单的限流器（令牌桶算法）"""

    def __init__(self, max_calls: int, period: float):
        self.max_calls = max_calls
        self.period = period
        self.calls = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """获取令牌"""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            # 移除过期的调用记录
            self.calls = [call for call in self.calls if call > now - self.period]
            if len(self.calls) >= self.max_calls:
                # 等待直到有令牌可用
                wait_time = self.calls[0] + self.period - now
                if wait_time > 0:
                    logger.debug(f"[限流器] 触发限流，等待 {wait_time:.2f} 秒")
                    await asyncio.sleep(wait_time)
                # 再次检查
                self.calls = [
                    call
                    for call in self.calls
                    if call > asyncio.get_event_loop().time() - self.period
                ]
            self.calls.append(asyncio.get_event_loop().time())


class BasePlatformClient:
    """平台API客户端基类"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        rate_limit_calls: int = 100,
        rate_limit_period: float = 60.0,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.rate_limiter = RateLimiter(rate_limit_calls, rate_limit_period)
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "BasePlatformClient":
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            trust_env=False,  # 数据同步直连官方API，不读环境变量代理（代理仅供爬虫使用）
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._client:
            await self._client.aclose()

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }
        logger.debug("[API客户端] 请求头: %s", redact_headers(headers))
        return headers

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10) + wait_random(0, 1),
        retry=retry_if_exception(_is_retryable_request_error),
        before_sleep=lambda retry_state: logger.warning(
            f"[API客户端] 请求失败，将在 {retry_state.next_action.sleep:.2f} 秒后重试 (尝试 {retry_state.attempt_number}/3)"
        ),
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """发送API请求（带重试和限流）"""
        # 自动初始化 client（如果没有用 async with）
        auto_close = False
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                trust_env=False,  # 数据同步直连官方API，不读环境变量代理（代理仅供爬虫使用）
            )
            auto_close = True

        try:
            await self.rate_limiter.acquire()

            url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
            logger.debug(f"[API客户端] API调用开始: {method} {url}")
            if params:
                logger.debug(f"[API客户端] 请求参数: {params}")

            headers = self._get_headers()
            logger.debug(f"[API客户端] 完整请求信息:")
            logger.debug(f"  URL: {method} {url}")
            logger.debug("  Headers: %s", redact_headers(headers))
            if params:
                logger.debug(f"  Params: {params}")
            if json:
                logger.debug(f"  JSON: {json}")

            request_kwargs: Dict[str, Any] = {
                "method": method,
                "url": url,
                "headers": headers,
                "params": params,
                "json": json,
            }
            if timeout is not None:
                request_kwargs["timeout"] = timeout
            response = await self._client.request(**request_kwargs)

            logger.debug(f"[API客户端] 响应状态码: {response.status_code}")
            logger.debug(
                "[API客户端] 响应头: %s",
                redact_headers(dict(response.headers)),
            )
            logger.debug(f"[API客户端] 响应内容: {response.text}")

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                # 限流类错误：不走通用 @retry（2~10s 退避对分钟级额度释放无效），
                # 降噪为 debug 并抛 RateLimitError 交由上层长退避排队处理。
                if _is_rate_limit_response(response):
                    logger.debug(
                        f"[API客户端] 触发限流(不重试, 交由上层退避): "
                        f"{response.status_code} {response.text}"
                    )
                    raise RateLimitError(
                        f"rate limited: {response.status_code}", response=response
                    ) from e
                logger.error(f"[API客户端] HTTP错误! 响应内容: {response.text}")
                raise

            if response.status_code == 204 or not response.text.strip():
                logger.debug("[API客户端] API 返回空响应，按空列表处理")
                return []

            result = response.json()
            logger.debug(
                f"[API客户端] API调用返回: 状态码 {response.status_code}, 数据长度 {len(str(result))} 字符"
            )
            return result
        finally:
            if auto_close and self._client:
                await self._client.aclose()
                self._client = None

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """GET请求"""
        return await self._request("GET", endpoint, params=params)

    async def post(self, endpoint: str, json: Optional[Dict[str, Any]] = None) -> Any:
        """POST请求"""
        return await self._request("POST", endpoint, json=json)
