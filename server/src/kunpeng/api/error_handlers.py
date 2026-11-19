"""
全局异常处理器
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import SQLAlchemyError
import structlog

from kunpeng.core.exceptions import (
    KunpengException,
    ShopNotFoundError,
    UnauthorizedError,
    ForbiddenError,
    ValidationError,
)

logger = structlog.get_logger(__name__)


def register_exception_handlers(app):
    """注册全局异常处理器"""

    @app.exception_handler(KunpengException)
    async def kunpeng_exception_handler(request: Request, exc: KunpengException):
        """处理自定义异常"""
        logger.warning(
            "Kunpeng exception",
            path=str(request.url.path),
            method=request.method,
            error_code=exc.code,
            error_message=exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "detail": {},
            },
        )

    @app.exception_handler(PydanticValidationError)
    async def validation_exception_handler(request: Request, exc: PydanticValidationError):
        """处理 Pydantic 验证错误"""
        logger.warning(
            "Validation error",
            path=str(request.url.path),
            method=request.method,
            errors=exc.errors(),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "code": "VALIDATION_ERROR",
                "message": "Validation error",
                "detail": exc.errors(),
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        """处理数据库错误"""
        logger.error(
            "Database error",
            path=str(request.url.path),
            method=request.method,
            error=str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "DATABASE_ERROR",
                "message": "Database error",
                "detail": {},
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """处理未捕获的异常"""
        logger.error(
            "Unhandled exception",
            path=str(request.url.path),
            method=request.method,
            error=str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "INTERNAL_ERROR",
                "message": "Internal server error",
                "detail": {},
            },
        )
