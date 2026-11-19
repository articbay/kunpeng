"""
Ozon ODS 层 - CRUD 通用工具函数
"""

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def parse_iso_datetime(date_str: Optional[str]) -> Optional[date]:
    """
    解析 ISO 8601 格式的日期时间字符串，只提取日期部分
    """
    if not date_str or date_str == "":
        return None

    try:
        if "T" in date_str:
            date_part = date_str.split("T")[0]
            return date.fromisoformat(date_part)
        return date.fromisoformat(date_str)
    except (ValueError, AttributeError):
        logger.warning(f"无法解析日期: {date_str}")
        return None


def parse_datetime_field(date_str: Optional[str]) -> Optional[datetime]:
    """
    解析 ISO 8601 格式的日期时间字符串，保存完整时间
    """
    if not date_str or date_str == "":
        return None

    try:
        if "+" in date_str:
            datetime_part = date_str.split("+")[0]
        elif "Z" in date_str:
            datetime_part = date_str.replace("Z", "")
        else:
            datetime_part = date_str
        parsed = datetime.fromisoformat(datetime_part)
        return None if parsed.year <= 1970 else parsed
    except (ValueError, AttributeError):
        logger.warning(f"无法解析日期时间: {date_str}")
        return None


def safe_decimal(value: Any) -> Optional[Decimal]:
    """
    安全转换为 Decimal，处理字符串和数字类型
    """
    if value is None or value == "":
        return None

    # Handle dict/object case (sometimes API returns nested objects)
    if isinstance(value, dict):
        # Try common keys
        for key in ["value", "amount", "price", "total"]:
            if key in value and value[key] is not None:
                return safe_decimal(value[key])
        return None

    try:
        # If it's a string, strip whitespace first
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None

        return Decimal(str(value))
    except (ValueError, TypeError, Exception):
        logger.warning(f"无法转换为 Decimal: {value!r} (type: {type(value)})")
        return None


def safe_int(value: Any) -> Optional[int]:
    """
    安全转换为 int
    """
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def safe_str(value: Any) -> Optional[str]:
    """
    安全转换为 str
    """
    if value is None:
        return None
    return str(value)


def parse_ru_decimal(value: Any) -> Optional[Decimal]:
    """
    解析 Ozon Performance API 返回的俄式小数字符串。

    Performance API 用逗号作为小数分隔符（如 "119,36"、"6000,00"），
    还可能出现千分位空格（如 "1 234,56"）。统一转换为标准 Decimal。
    """
    if value is None or value == "":
        return None
    if isinstance(value, (int, float, Decimal)):
        return safe_decimal(value)
    if isinstance(value, str):
        normalized = value.strip().replace("\xa0", "").replace(" ", "")
        if not normalized:
            return None
        # 俄式：逗号为小数分隔符
        normalized = normalized.replace(",", ".")
        return safe_decimal(normalized)
    return safe_decimal(value)


def parse_ru_date(date_str: Optional[str]) -> Optional[date]:
    """
    解析 Ozon Performance 报表的日期字符串。

    异步报表返回 `DD.MM.YYYY`（如 `20.06.2026`），daily/json 返回 `YYYY-MM-DD`。
    两种格式都兼容。
    """
    if not date_str or not isinstance(date_str, str):
        return None
    s = date_str.strip()
    if not s:
        return None
    # DD.MM.YYYY
    if "." in s:
        parts = s.split(".")
        if len(parts) == 3:
            try:
                d, m, y = parts
                if len(y) == 2:
                    y = "20" + y
                return date(int(y), int(m), int(d))
            except (ValueError, TypeError):
                logger.warning(f"无法解析俄式日期: {date_str}")
                return None
    # YYYY-MM-DD
    return parse_iso_datetime(s)
