"""
中间件模块
"""
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """API 请求日志中间件"""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method
        logger.debug(f"API 请求开始: {method} {path}")

        response = await call_next(request)

        status_code = response.status_code
        logger.debug(f"API 请求返回: {method} {path} - 状态码: {status_code}")
        return response
