from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageResponse(BaseModel, Generic[T]):
    """分页响应"""

    items: List[T] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


class MessageResponse(BaseModel):
    """消息响应"""

    message: str
    data: Optional[Any] = None
