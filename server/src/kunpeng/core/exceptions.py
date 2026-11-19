"""
自定义异常模块
"""


class KunpengException(Exception):
    """基础异常类"""

    code: str = "INTERNAL_ERROR"
    message: str = "Internal server error"
    status_code: int = 500

    def __init__(self, message: str | None = None):
        if message:
            self.message = message
        super().__init__(self.message)


class ShopNotFoundError(KunpengException):
    """店铺不存在"""
    code = "SHOP_NOT_FOUND"
    message = "Shop not found"
    status_code = 404


class UnauthorizedError(KunpengException):
    """未授权"""
    code = "UNAUTHORIZED"
    message = "Unauthorized"
    status_code = 401


class ForbiddenError(KunpengException):
    """无权限"""
    code = "FORBIDDEN"
    message = "Forbidden"
    status_code = 403


class ValidationError(KunpengException):
    """验证错误"""
    code = "VALIDATION_ERROR"
    message = "Validation error"
    status_code = 400
