"""
平台时区工具
============

WB / Ozon 的统计数据均按莫斯科时间(UTC+3，俄罗斯无夏令时)归集。
本模块提供统一的"平台当前时间"入口，替代散落各处的裸 `datetime.now()`，
使"当前时间 / 今天 / 昨天 / 当前小时"等业务日期计算显式绑定到平台时区，
与服务器/宿主机 OS 时区解耦（开发机、CI、生产行为一致）。

用法:
    from kunpeng.utils.timezone import now_platform, today_platform, platform_tz

    now = now_platform()          # tz-aware 的莫斯科当前时间
    today = today_platform()      # 莫斯科当天日期
"""
from datetime import date, datetime
from zoneinfo import ZoneInfo

from kunpeng.config import settings


def platform_tz() -> ZoneInfo:
    """返回平台业务时区对象（默认 Europe/Moscow，可由 settings.platform_timezone 覆盖）"""
    return ZoneInfo(settings.platform_timezone)


def now_platform() -> datetime:
    """平台业务时区的当前时间（tz-aware）"""
    return datetime.now(platform_tz())


def today_platform() -> date:
    """平台业务时区的当天日期"""
    return now_platform().date()
