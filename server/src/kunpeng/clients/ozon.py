"""
Ozon API 客户端
支持多个 API 端点：
- https://api-seller.ozon.ru - 卖家API
  - /v4/posting/fbs/list - FBS订单列表
  - /v3/posting/fbo/list - FBO订单列表
  - /v1/returns/list - 退货列表
  - /v2/review/list - 评价列表
  - /v1/finance/accrual/by-day - 按天获取应计明细
  - /v1/finance/accrual/types - 获取应计类型字典
  - /v1/finance/accrual/postings - 按订单获取应计数据
  - /v2/finance/realization - 获取销售实现报告
  - /v3/product/list - 商品ID列表（分页）
  - /v3/product/info/list - 商品详情（批量）
  - /v1/analytics/data - SKU日经营分析
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from weakref import WeakKeyDictionary

import httpx
from tenacity import RetryError

from kunpeng.clients.base import BasePlatformClient, RateLimitError

_PERFORMANCE_REPORT_LOCKS: WeakKeyDictionary = WeakKeyDictionary()


def _performance_report_lock(client_id: str) -> asyncio.Lock:
    """Return one report lock per event loop and Performance credential."""
    loop = asyncio.get_running_loop()
    loop_locks = _PERFORMANCE_REPORT_LOCKS.setdefault(loop, {})
    return loop_locks.setdefault(client_id, asyncio.Lock())


def _is_report_limit_error(exc: BaseException) -> bool:
    """判断异常是否为 Performance API 的“活跃报表任务数已达上限”限流。

    该限流由 Ozon 侧对异步统计报表施加：同一时刻仅允许 1 个活跃报表任务，
    超限时提交接口返回类似 {"error": "Превышен лимит активных запросов (максимум 1)"}。
    base 客户端的 @retry 会把 HTTPStatusError 包装成 RetryError，这里统一解包判断。
    """
    if isinstance(exc, RetryError):
        try:
            exc = exc.last_attempt.exception()
        except Exception:  # noqa: BLE001
            return False
    # base 层已将限流识别为 RateLimitError（不再走 @retry），优先判断。
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        text = (exc.response.text or "").lower()
        return (
            exc.response.status_code == 429
            or "лимит активн" in text  # "лимит активн"
            or "максимум 1" in text  # "максимум 1"
        )
    return False


logger = logging.getLogger(__name__)

OZON_ANALYTICS_DIMENSIONS = ["sku", "day"]
OZON_ANALYTICS_CORE_METRICS = [
    "revenue",
    "ordered_units",
    "hits_view_search",
    "hits_view_pdp",
    "hits_view",
    "hits_tocart_search",
    "hits_tocart_pdp",
    "hits_tocart",
    "session_view_search",
    "session_view_pdp",
    "session_view",
    "conv_tocart_search",
    "conv_tocart_pdp",
    "conv_tocart",
]
OZON_ANALYTICS_OUTCOME_METRICS = [
    "returns",
    "cancellations",
    "delivered_units",
    "position_category",
]


class OzonPostingClient(BasePlatformClient):
    """Ozon 订单（Posting）API 客户端"""

    BASE_URL = "https://api-seller.ozon.ru"

    def __init__(self, client_id: str, api_key: str):
        super().__init__(
            api_key=api_key,
            base_url=self.BASE_URL,
            rate_limit_calls=100,
            rate_limit_period=60.0,
        )
        self.client_id = client_id

    def _get_headers(self) -> Dict[str, str]:
        """获取Ozon专用请求头"""
        headers = {
            "Client-Id": self.client_id,
            "Api-Key": self.api_key,
            "Content-Type": "application/json",
        }
        return headers

    async def get_fbs_postings(
        self,
        since: str,
        to: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        cursor: str = "",
        sort_dir: str = "ASC",
        translit: bool = False,
        with_analytics: bool = True,
        with_barcodes: bool = True,
        with_financial: bool = True,
        with_legal: bool = True,
    ) -> Dict[str, Any]:
        """
        获取FBS订单列表

        **官方文档**: https://docs.ozon.ru/api/seller/zh/#operation/PostingFbsList

        Args:
            since: 起始时间 (RFC3339格式，如 2026-04-13T00:00:00Z)
            to: 结束时间 (RFC3339格式)
            status: 订单状态筛选
            limit: 每页数量 (最大 100)
            cursor: 下一页游标，第一页传空字符串
            sort_dir: 排序方向 (ASC/DESC)
            translit: 是否将西里尔字母转为拉丁字母

        Returns:
            订单数据
        """
        payload: Dict[str, Any] = {
            "cursor": cursor,
            "filter": {
                "since": since,
            },
            "limit": limit,
            "sort_dir": sort_dir.upper(),
            "translit": translit,
            "with": {
                "analytics_data": with_analytics,
                "barcodes": with_barcodes,
                "financial_data": with_financial,
                "legal_info": with_legal,
                "translit": translit,
            },
        }
        if to:
            payload["filter"]["to"] = to
        if status:
            payload["filter"]["statuses"] = [status]

        return await self._request("POST", "/v4/posting/fbs/list", json=payload)

    async def get_fbo_postings(
        self,
        since: str,
        to: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        cursor: str = "",
        sort_dir: str = "ASC",
        translit: bool = False,
        with_analytics: bool = True,
        with_financial: bool = True,
        with_legal: bool = True,
    ) -> Dict[str, Any]:
        """
        获取FBO订单列表（来自 Ozon 仓库的订单）

        **官方文档**: https://docs.ozon.ru/api/seller/zh/

        `/v2/posting/fbo/list` 已被 Ozon 标记为废弃；当前统一使用 v3
        的 cursor 分页协议。

        Args:
            since: 起始时间 (RFC3339格式，如 2026-04-13T00:00:00Z)
            to: 结束时间 (RFC3339格式)
            status: 订单状态筛选
            limit: 每页数量 (最大 1000)
            cursor: 下一页游标，第一页传空字符串
            sort_dir: 排序方向 (ASC/DESC)
            translit: 是否将西里尔字母转为拉丁字母
            with_analytics: 是否返回分析数据
            with_financial: 是否返回财务数据

        Returns:
            订单数据，结构为 {"postings": [...], "cursor": "...", "has_next": bool}
        """
        payload: Dict[str, Any] = {
            "cursor": cursor,
            "filter": {
                "since": since,
            },
            "limit": limit,
            "sort_dir": sort_dir.upper(),
            "translit": translit,
            "with": {
                "analytics_data": with_analytics,
                "financial_data": with_financial,
                "legal_info": with_legal,
            },
        }
        if to:
            payload["filter"]["to"] = to
        if status:
            payload["filter"]["statuses"] = [status]

        return await self._request("POST", "/v3/posting/fbo/list", json=payload)

    async def get_fbs_posting(self, posting_number: str) -> Dict[str, Any]:
        """获取单个 FBS posting 的只读详情。"""
        return await self._request(
            "POST",
            "/v3/posting/fbs/get",
            json={
                "posting_number": posting_number,
                "with": {"analytics_data": True, "financial_data": True},
            },
        )

    async def get_fbo_posting(self, posting_number: str) -> Dict[str, Any]:
        """获取单个 FBO posting 的只读详情。"""
        return await self._request(
            "POST",
            "/v2/posting/fbo/get",
            json={
                "posting_number": posting_number,
                "with": {"analytics_data": True, "financial_data": True},
            },
        )

    async def get_fbs_cancel_reasons(self) -> Dict[str, Any]:
        """获取 FBS 取消原因只读字典。"""
        return await self._request(
            "POST", "/v2/posting/fbs/cancel-reason/list", json={}
        )

    async def get_fbo_cancel_reasons(self) -> Dict[str, Any]:
        """获取 FBO 取消原因只读字典。"""
        return await self._request(
            "POST", "/v1/posting/fbo/cancel-reason/list", json={}
        )

    async def get_unfulfilled_postings(
        self,
        cutoff_from: str,
        cutoff_to: str,
        limit: int = 100,
        cursor: str = "",
        dir: str = "ASC",
        with_analytics: bool = True,
        with_financial: bool = True,
    ) -> Dict[str, Any]:
        """
        获取待处理（未发货）FBS 订单列表

        **官方文档**: https://docs.ozon.ru/api/seller/zh/#operation/PostingAPI_GetFbsPostingUnfulfilledList

        说明:
            该接口返回"卖家仍需人工处理（组装/发货）的新订单"，即客户需要
            及时提醒的"新订单"。用 cutoff（订单需完成组装的截止时间）区间过滤。
            v4 接口使用 cursor/has_next 分页，postings、count、cursor 和
            has_next 均位于响应根节点。

        Args:
            cutoff_from: 组装截止起始时间 (RFC3339, 如 2026-04-13T00:00:00.000Z)
            cutoff_to: 组装截止结束时间 (RFC3339)
            limit: 每页数量
            cursor: 上一页返回的游标；第一页传空字符串
            dir: 排序方向 (ASC/DESC)
            with_analytics: 是否返回分析数据
            with_financial: 是否返回财务数据

        Returns:
            根节点包含 postings、count、cursor 和 has_next 的订单数据
        """
        payload: Dict[str, Any] = {
            "dir": dir,
            "filter": {
                "cutoff_from": cutoff_from,
                "cutoff_to": cutoff_to,
            },
            "limit": limit,
            "cursor": cursor,
            "with": {
                "analytics_data": with_analytics,
                "financial_data": with_financial,
            },
        }

        return await self._request(
            "POST", "/v4/posting/fbs/unfulfilled/list", json=payload
        )


class OzonReportClient(BasePlatformClient):
    """Ozon Seller API asynchronous report client."""

    BASE_URL = "https://api-seller.ozon.ru"

    def __init__(self, client_id: str, api_key: str):
        super().__init__(
            api_key=api_key,
            base_url=self.BASE_URL,
            rate_limit_calls=50,
            rate_limit_period=60.0,
        )
        self.client_id = client_id

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Client-Id": self.client_id,
            "Api-Key": self.api_key,
            "Content-Type": "application/json",
        }

    async def create_postings_report(
        self,
        *,
        processed_at_from: str,
        processed_at_to: str,
        fulfillment_type: str,
        language: str = "RU",
    ) -> Dict[str, Any]:
        """Create one FBS or FBO shipment report task."""
        normalized_type = fulfillment_type.lower()
        if normalized_type not in {"fbs", "fbo"}:
            raise ValueError("fulfillment_type must be FBS or FBO")
        return await self._request(
            "POST",
            "/v1/report/postings/create",
            json={
                "filter": {
                    "processed_at_from": processed_at_from,
                    "processed_at_to": processed_at_to,
                    "delivery_schema": [normalized_type],
                },
                "language": language,
            },
        )

    async def get_report_info(self, code: str) -> Dict[str, Any]:
        """Get the current state and file URL of a report task."""
        return await self._request("POST", "/v1/report/info", json={"code": code})

    async def download_report(self, file_url: str) -> bytes:
        """Download a completed report from the signed HTTPS URL returned by Ozon."""
        if not isinstance(file_url, str) or not file_url.startswith("https://"):
            raise ValueError("Ozon report file URL must use HTTPS")
        async with httpx.AsyncClient(
            timeout=60.0,
            follow_redirects=True,
            trust_env=False,
        ) as downloader:
            response = await downloader.get(file_url)
            response.raise_for_status()
            return response.content


class OzonReturnClient(BasePlatformClient):
    """Ozon 退货 API 客户端"""

    BASE_URL = "https://api-seller.ozon.ru"

    def __init__(self, client_id: str, api_key: str):
        super().__init__(
            api_key=api_key,
            base_url=self.BASE_URL,
            rate_limit_calls=100,
            rate_limit_period=60.0,
        )
        self.client_id = client_id

    def _get_headers(self) -> Dict[str, str]:
        """获取Ozon专用请求头"""
        headers = {
            "Client-Id": self.client_id,
            "Api-Key": self.api_key,
            "Content-Type": "application/json",
        }
        return headers

    async def get_returns_list(
        self,
        date_from: str,
        date_to: str,
        limit: int = 100,
        last_id=None,
        time_filter: str = "logistic_return_date",
    ) -> Dict[str, Any]:
        """
        获取退货列表

        **官方文档**: https://docs.ozon.ru/api/seller/zh/#operation/returnsList

        Args:
            date_from: 起始日期 (RFC3339格式，如 2026-02-01T00:00:00Z)
            date_to: 结束日期 (RFC3339格式，如 2026-02-01T00:00:00Z)
            limit: 每页数量
            last_id: 最后加载的退货ID（用于分页）

        Returns:
            退货数据
        """
        allowed_time_filters = {
            "logistic_return_date",
            "visual_status_change_moment",
            "storage_tariffication_start_date",
        }
        if time_filter not in allowed_time_filters:
            raise ValueError(f"Unsupported Ozon return time filter: {time_filter}")

        payload = {
            "filter": {time_filter: {"time_from": date_from, "time_to": date_to}},
            "limit": limit,
        }
        if last_id is not None:
            payload["last_id"] = last_id
        return await self._request("POST", "/v1/returns/list", json=payload)

    async def get_giveout_list(self, last_id: Optional[str] = None) -> Dict[str, Any]:
        """获取 FBO/FBS 退回卖家批次列表；不生成或重置领取码。"""
        payload: Dict[str, Any] = {}
        if last_id:
            payload["last_id"] = last_id
        return await self._request("POST", "/v1/return/giveout/list", json=payload)

    async def get_giveout_info(self, giveout_id: str) -> Dict[str, Any]:
        """获取单个退回卖家批次详情。"""
        return await self._request(
            "POST", "/v1/return/giveout/info", json={"giveout_id": giveout_id}
        )


class OzonReviewClient(BasePlatformClient):
    """Ozon 评价 API 客户端"""

    BASE_URL = "https://api-seller.ozon.ru"

    def __init__(self, client_id: str, api_key: str):
        super().__init__(
            api_key=api_key,
            base_url=self.BASE_URL,
            rate_limit_calls=100,
            rate_limit_period=60.0,
        )
        self.client_id = client_id

    def _get_headers(self) -> Dict[str, str]:
        """获取Ozon专用请求头"""
        headers = {
            "Client-Id": self.client_id,
            "Api-Key": self.api_key,
            "Content-Type": "application/json",
        }
        return headers

    async def get_review_list(
        self,
        date_from: str,
        date_to: str,
        limit: int = 100,
        last_id=None,
        rating_from: Optional[int] = None,
        rating_to: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        获取评价列表 (v2接口)

        **官方文档**: https://docs.ozon.ru/api/seller/zh/#operation/ReviewListV2

        Args:
            date_from: 起始日期 (RFC3339格式，如 2026-02-01T00:00:00Z)
            date_to: 结束日期 (RFC3339格式，如 2026-02-01T00:00:00Z)
            limit: 每页数量
            last_id: 最后加载的评价ID（用于分页）
            rating_from: 最低评分 (1-5)
            rating_to: 最高评分 (1-5)

        Returns:
            评价数据
        """
        payload: Dict[str, Any] = {
            "filter": {
                "date_from": date_from,
                "date_to": date_to,
            },
            "limit": limit,
        }
        if last_id is not None:
            payload["last_id"] = last_id
        if rating_from is not None or rating_to is not None:
            payload["filter"]["rating"] = {}
            if rating_from is not None:
                payload["filter"]["rating"]["from"] = rating_from
            if rating_to is not None:
                payload["filter"]["rating"]["to"] = rating_to

        return await self._request("POST", "/v1/review/list", json=payload)

    async def get_review_info(self, review_id: str) -> Dict[str, Any]:
        """获取评价只读详情。"""
        return await self._request(
            "POST", "/v1/review/info", json={"review_id": review_id}
        )

    async def get_review_comments(
        self, review_id: str, limit: int = 100, offset: int = 0
    ) -> Dict[str, Any]:
        """获取评价下的评论/回复记录；不会发送或删除评论。"""
        return await self._request(
            "POST",
            "/v1/review/comment/list",
            json={"review_id": review_id, "limit": limit, "offset": offset},
        )

    async def get_review_count(self) -> Dict[str, Any]:
        """获取各状态评价数量。"""
        return await self._request("POST", "/v1/review/count", json={})


class OzonQuestionClient(BasePlatformClient):
    """Ozon 商品问题与回答只读 API 客户端。"""

    BASE_URL = "https://api-seller.ozon.ru"

    def __init__(self, client_id: str, api_key: str):
        super().__init__(api_key=api_key, base_url=self.BASE_URL)
        self.client_id = client_id

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Client-Id": self.client_id,
            "Api-Key": self.api_key,
            "Content-Type": "application/json",
        }

    async def get_question_list(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        last_id: str = "",
        sort_dir: str = "ASC",
    ) -> Dict[str, Any]:
        """获取商品问题列表，使用 last_id/has_next 分页。"""
        question_filter: Dict[str, Any] = {}
        if date_from:
            question_filter["date_from"] = date_from
        if date_to:
            question_filter["date_to"] = date_to
        if status:
            question_filter["status"] = status
        payload: Dict[str, Any] = {
            "limit": limit,
            "last_id": last_id,
            "sort_dir": sort_dir,
        }
        if question_filter:
            payload["filter"] = question_filter
        return await self._request("POST", "/v1/question/list", json=payload)

    async def get_question_info(self, question_id: str) -> Dict[str, Any]:
        """获取单个问题详情。"""
        return await self._request(
            "POST", "/v1/question/info", json={"question_id": question_id}
        )

    async def get_question_answers(
        self, question_id: str, limit: int = 100, last_id: str = ""
    ) -> Dict[str, Any]:
        """获取问题的回答列表；不会创建、修改或删除回答。"""
        return await self._request(
            "POST",
            "/v1/question/answer/list",
            json={"question_id": question_id, "limit": limit, "last_id": last_id},
        )

    async def get_question_count(self) -> Dict[str, Any]:
        """获取各状态问题数量。"""
        return await self._request("POST", "/v1/question/count", json={})


class OzonChatClient(BasePlatformClient):
    """Ozon 买家聊天只读 API 客户端。"""

    BASE_URL = "https://api-seller.ozon.ru"

    def __init__(self, client_id: str, api_key: str):
        super().__init__(api_key=api_key, base_url=self.BASE_URL)
        self.client_id = client_id

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Client-Id": self.client_id,
            "Api-Key": self.api_key,
            "Content-Type": "application/json",
        }

    async def get_chat_list(
        self,
        limit: int = 100,
        cursor: str = "",
        chat_status: Optional[str] = None,
        unread_only: Optional[bool] = None,
        posting_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """获取聊天列表（v3）；已移除的 v2 不再兼容。"""
        chat_filter: Dict[str, Any] = {}
        if chat_status:
            chat_filter["chat_status"] = chat_status
        if unread_only is not None:
            chat_filter["unread_only"] = unread_only
        if posting_number:
            chat_filter["posting_number"] = posting_number
        payload: Dict[str, Any] = {"limit": limit, "cursor": cursor}
        if chat_filter:
            payload["filter"] = chat_filter
        return await self._request("POST", "/v3/chat/list", json=payload)

    async def get_chat_history(
        self,
        chat_id: str,
        limit: int = 100,
        from_message_id: Optional[str] = None,
        direction: str = "Forward",
    ) -> Dict[str, Any]:
        """获取聊天消息历史（v3），不改变已读状态。"""
        payload: Dict[str, Any] = {
            "chat_id": chat_id,
            "limit": limit,
            "direction": direction,
        }
        if from_message_id:
            payload["from_message_id"] = from_message_id
        return await self._request("POST", "/v3/chat/history", json=payload)


class OzonFinanceClient(BasePlatformClient):
    """Ozon 财务 API 客户端"""

    BASE_URL = "https://api-seller.ozon.ru"

    def __init__(self, client_id: str, api_key: str):
        super().__init__(
            api_key=api_key,
            base_url=self.BASE_URL,
            rate_limit_calls=100,
            rate_limit_period=60.0,
        )
        self.client_id = client_id

    def _get_headers(self) -> Dict[str, str]:
        """获取Ozon专用请求头"""
        headers = {
            "Client-Id": self.client_id,
            "Api-Key": self.api_key,
            "Content-Type": "application/json",
        }
        return headers

    async def get_accrual_types(self) -> Dict[str, Any]:
        """
        获取应计类型字典

        **官方文档**: https://docs.ozon.ru/api/seller/zh/#operation/GetFinanceAccrualTypes

        Returns:
            应计类型字典数据
        """
        return await self._request("POST", "/v1/finance/accrual/types", json={})

    async def get_accrual_by_day(
        self, date: str, last_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        按天获取应计明细数据

        **官方文档**: https://docs.ozon.ru/api/seller/zh/#operation/GetFinanceAccrualByDay

        Args:
            date: 日期 (YYYY-MM-DD格式)
            last_id: 上一页最后一条记录ID，用于分页

        Returns:
            应计明细数据
        """
        payload = {
            "date": date,
        }
        if last_id:
            payload["last_id"] = last_id
        return await self._request("POST", "/v1/finance/accrual/by-day", json=payload)

    async def get_accrual_postings(
        self,
        posting_numbers: List[str],
    ) -> Dict[str, Any]:
        """
        按订单号获取应计数据

        **官方文档**: https://docs.ozon.ru/api/seller/zh/#operation/GetFinanceAccrualPostings

        Args:
            posting_numbers: 订单号列表

        Returns:
            应计数据
        """
        payload = {
            "posting_numbers": posting_numbers,
        }
        return await self._request("POST", "/v1/finance/accrual/postings", json=payload)

    async def get_realization_report(
        self,
        year: int,
        month: int,
    ) -> Dict[str, Any]:
        """
        获取销售实现报告

        **官方文档**: https://docs.ozon.ru/api/seller/zh/#operation/FinanceAPI_GetRealizationReportV2

        Args:
            year: 年份
            month: 月份 (1-12)

        Returns:
            销售实现报告数据
        """
        payload = {
            "year": year,
            "month": month,
        }
        return await self._request("POST", "/v2/finance/realization", json=payload)


class OzonProductClient(BasePlatformClient):
    """Ozon 商品 API 客户端"""

    BASE_URL = "https://api-seller.ozon.ru"

    def __init__(self, client_id: str, api_key: str):
        super().__init__(
            api_key=api_key,
            base_url=self.BASE_URL,
            rate_limit_calls=100,
            rate_limit_period=60.0,
        )
        self.client_id = client_id

    def _get_headers(self) -> Dict[str, str]:
        """获取Ozon专用请求头"""
        headers = {
            "Client-Id": self.client_id,
            "Api-Key": self.api_key,
            "Content-Type": "application/json",
        }
        return headers

    async def get_product_list(
        self,
        last_id: str = "",
        limit: int = 1000,
        visibility: str = "ALL",
    ) -> Dict[str, Any]:
        """
        获取商品ID列表（轻量，用于分页拿到 product_id/offer_id/sku）

        **官方文档**: https://docs.ozon.ru/api/seller/zh/#operation/ProductAPI_GetProductList

        Args:
            last_id: 最后一条记录的ID（用于分页）
            limit: 每页数量 (最大 1000)
            visibility: 可见性筛选，默认 ALL 全部

        Returns:
            商品ID列表数据，结构为 {"result": {"items": [...], "last_id": "...", "total": N}}
        """
        payload = {
            "filter": {"visibility": visibility},
            "last_id": last_id,
            "limit": limit,
        }
        return await self._request("POST", "/v3/product/list", json=payload)

    async def get_product_info_list(
        self,
        product_ids: Optional[List[int]] = None,
        offer_ids: Optional[List[str]] = None,
        skus: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        批量获取商品详情

        **官方文档**: https://docs.ozon.ru/api/seller/zh/#operation/ProductAPI_GetProductInfoListV3

        说明: 旧的 `/v2/product/info/list` 已下线（返回 404），改用 `/v3/product/info/list`。
        该接口需要传入 offer_id / product_id / sku 三者之一，单次最多 1000 个。

        Args:
            product_ids: 商品ID列表
            offer_ids: 商家货号列表
            skus: Ozon SKU 列表

        Returns:
            商品详情数据，结构为 {"items": [...]}
        """
        payload: Dict[str, Any] = {}
        if product_ids:
            payload["product_id"] = product_ids
        if offer_ids:
            payload["offer_id"] = offer_ids
        if skus:
            payload["sku"] = skus
        return await self._request("POST", "/v3/product/info/list", json=payload)

    async def get_description_category_tree(
        self,
        language: str = "DEFAULT",
    ) -> Dict[str, Any]:
        """Get the Ozon description-category and product-type tree."""
        return await self._request(
            "POST",
            "/v1/description-category/tree",
            json={"language": language},
        )


class OzonPerformanceClient(BasePlatformClient):
    """
    Ozon Performance（广告）API 客户端

    与 Seller API 是两套体系：
    - 独立域名 https://api-performance.ozon.ru
    - OAuth2 client_credentials 鉴权（换取 Bearer token，有效期 1800 秒）
    - 凭证为 Performance 专用的 Client-Id / Client-Secret

    **官方文档**: https://docs.ozon.ru/api/performance/zh/
    """

    BASE_URL = "https://api-performance.ozon.ru"

    def __init__(self, client_id: str, client_secret: str):
        # Performance API 用 Bearer token，api_key 字段这里存放 client_secret 仅为复用基类
        super().__init__(
            api_key=client_secret,
            base_url=self.BASE_URL,
            rate_limit_calls=60,
            rate_limit_period=60.0,
        )
        self.perf_client_id = client_id
        self.client_secret = client_secret
        self._access_token: Optional[str] = None
        self._token_expire_at: float = 0.0

    def _get_headers(self) -> Dict[str, str]:
        """带 Bearer token 的请求头"""
        headers = {
            "Content-Type": "application/json",
        }
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        return headers

    async def _ensure_token(self) -> str:
        """
        确保存在有效的 access_token（带 60 秒安全边界的缓存刷新）

        **官方文档**: https://docs.ozon.ru/api/performance/zh/#operation/TokenService_Token
        """
        import time

        now = time.time()
        if self._access_token and now < self._token_expire_at - 60:
            return self._access_token

        payload = {
            "client_id": self.perf_client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
        }
        # 换 token 时不能带旧的 Authorization 头
        auto_close = False
        if not self._client:
            import httpx

            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                trust_env=False,
            )
            auto_close = True
        try:
            await self.rate_limiter.acquire()
            url = f"{self.base_url.rstrip('/')}/api/client/token"
            response = await self._client.request(
                method="POST",
                url=url,
                headers={"Content-Type": "application/json"},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        finally:
            if auto_close and self._client:
                await self._client.aclose()
                self._client = None

        self._access_token = data.get("access_token")
        expires_in = data.get("expires_in", 1800)
        self._token_expire_at = time.time() + float(expires_in)
        logger.debug(
            f"[Ozon Performance] 获取 access_token 成功，有效期 {expires_in} 秒"
        )
        return self._access_token

    async def get_campaigns(self) -> Dict[str, Any]:
        """
        获取广告活动列表

        **官方文档**: https://docs.ozon.ru/api/performance/zh/#operation/ListCampaigns

        Returns:
            {"list": [{"id", "title", "state", "advObjectType", "placement", ...}]}
        """
        await self._ensure_token()
        return await self._request("GET", "/api/client/campaign")

    async def get_campaign_objects(self, campaign_id: str) -> Dict[str, Any]:
        """
        获取广告活动下投放的对象（SKU）列表

        **官方文档**: https://docs.ozon.ru/api/performance/zh/#operation/ListCampaignObjects

        Args:
            campaign_id: 广告活动ID

        Returns:
            {"list": [{"id": "<sku>"}]}
        """
        await self._ensure_token()
        return await self._request("GET", f"/api/client/campaign/{campaign_id}/objects")

    async def get_statistics_daily(
        self,
        date_from: str,
        date_to: str,
        campaign_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        获取按天的广告统计（活动 x 日期维度）

        **官方文档**: https://docs.ozon.ru/api/performance/zh/#operation/DailyJson

        Args:
            date_from: 起始日期 (YYYY-MM-DD)
            date_to: 结束日期 (YYYY-MM-DD)
            campaign_ids: 广告活动ID列表（不传则返回全部活动）

        Returns:
            {"rows": [{"id", "title", "date", "views", "clicks", "moneySpent", "orders", "ordersMoney"}]}
        """
        await self._ensure_token()
        params: Dict[str, Any] = {
            "dateFrom": date_from,
            "dateTo": date_to,
        }
        if campaign_ids:
            params["campaignId"] = campaign_ids
        return await self._request(
            "GET", "/api/client/statistics/daily/json", params=params
        )

    async def request_statistics_report(
        self,
        campaign_ids: List[str],
        date_from: str,
        date_to: str,
        group_by: str = "DATE",
    ) -> Dict[str, Any]:
        """
        提交异步统计报表任务（SKU 级明细，含 CTR/toCart/DRR 等派生指标）

        **官方文档**: https://docs.ozon.ru/api/performance/zh/#operation/SubmitRequest

        Args:
            campaign_ids: 广告活动ID列表
            date_from: 起始日期 (YYYY-MM-DD)
            date_to: 结束日期 (YYYY-MM-DD)
            group_by: 分组维度 (DATE / NO_GROUP_BY 等)

        Returns:
            {"UUID": "<报表任务ID>"}
        """
        await self._ensure_token()
        payload = {
            "campaigns": campaign_ids,
            "dateFrom": date_from,
            "dateTo": date_to,
            "groupBy": group_by,
        }
        return await self._request("POST", "/api/client/statistics/json", json=payload)

    async def get_statistics_report_status(self, uuid: str) -> Dict[str, Any]:
        """
        查询异步报表任务状态

        **官方文档**: https://docs.ozon.ru/api/performance/zh/#operation/StatisticsCheck

        Args:
            uuid: 报表任务ID

        Returns:
            {"UUID", "state"(NOT_STARTED/IN_PROGRESS/OK/ERROR), "link", ...}
        """
        await self._ensure_token()
        return await self._request("GET", f"/api/client/statistics/{uuid}")

    async def download_statistics_report(self, uuid: str) -> Dict[str, Any]:
        """
        下载已完成的异步报表内容（JSON）

        **官方文档**: https://docs.ozon.ru/api/performance/zh/#operation/DownloadStatistics

        Args:
            uuid: 报表任务ID

        Returns:
            {"<campaignId>": {"title": ..., "report": {"rows": [...]}}}
        """
        await self._ensure_token()
        return await self._request(
            "GET", "/api/client/statistics/report", params={"UUID": uuid}
        )

    async def _submit_report_with_backoff(
        self,
        campaign_ids: List[str],
        date_from: str,
        date_to: str,
        group_by: str,
        submit_timeout: float,
        submit_interval: float,
    ) -> Dict[str, Any]:
        """提交报表任务，遇到“活跃报表数达上限”限流时长退避排队重试。

        Performance API 同一时刻仅允许 1 个活跃报表任务。批量同步多个活动时，
        上一个任务尚未下载释放就提交下一个会被限流。base 客户端的 @retry 退避
        最多 10 秒，不足以等待额度释放，这里在提交层做更长的排队等待。

        Args:
            submit_timeout: 排队等待额度的最长时间（秒），超时抛出 TimeoutError
            submit_interval: 每次重试提交的间隔（秒）

        Returns:
            提交成功的响应 {"UUID": ...}
        """
        import asyncio

        waited = 0.0
        while True:
            try:
                return await self.request_statistics_report(
                    campaign_ids=campaign_ids,
                    date_from=date_from,
                    date_to=date_to,
                    group_by=group_by,
                )
            except Exception as exc:  # noqa: BLE001
                if not _is_report_limit_error(exc):
                    raise
                if waited >= submit_timeout:
                    raise TimeoutError(
                        f"等待报表额度释放超时 (已等待 {waited:.0f}s, 上限 {submit_timeout:.0f}s)"
                    ) from exc
                logger.warning(
                    f"[Ozon Performance] 活跃报表额度已满，将在 {submit_interval:.0f} 秒后重试提交 "
                    f"(已等待 {waited:.0f}s/{submit_timeout:.0f}s)"
                )
                await asyncio.sleep(submit_interval)
                waited += submit_interval

    async def fetch_statistics_report(
        self,
        campaign_ids: List[str],
        date_from: str,
        date_to: str,
        group_by: str = "DATE",
        poll_interval: float = 5.0,
        max_wait: float = 300.0,
        submit_timeout: float = 600.0,
        submit_interval: float = 30.0,
    ) -> Dict[str, Any]:
        """Serialize the full submit/poll/download lifecycle for one credential."""
        async with _performance_report_lock(self.perf_client_id):
            return await self._fetch_statistics_report_unlocked(
                campaign_ids=campaign_ids,
                date_from=date_from,
                date_to=date_to,
                group_by=group_by,
                poll_interval=poll_interval,
                max_wait=max_wait,
                submit_timeout=submit_timeout,
                submit_interval=submit_interval,
            )

    async def _fetch_statistics_report_unlocked(
        self,
        campaign_ids: List[str],
        date_from: str,
        date_to: str,
        group_by: str = "DATE",
        poll_interval: float = 5.0,
        max_wait: float = 300.0,
        submit_timeout: float = 600.0,
        submit_interval: float = 30.0,
    ) -> Dict[str, Any]:
        """
        一站式获取异步报表：提交 -> 轮询 -> 下载。

        报表任务在 Ozon 侧排队处理，实测可能需要数分钟；通过轮询状态直到 OK 再下载。
        提交阶段遇到“活跃报表数达上限”限流时，会自动长退避排队等待额度释放，
        使批量同步多个活动时不会因限流直接失败。

        Args:
            campaign_ids: 广告活动ID列表
            date_from: 起始日期 (YYYY-MM-DD)
            date_to: 结束日期 (YYYY-MM-DD)
            group_by: 分组维度
            poll_interval: 轮询任务状态的间隔（秒）
            max_wait: 单个任务从提交成功到完成的最长等待时间（秒），超时抛出 TimeoutError
            submit_timeout: 提交阶段等待“活跃报表额度”释放的最长时间（秒）
            submit_interval: 提交阶段限流重试的间隔（秒）

        Returns:
            报表内容 dict；若任务失败或超时则抛异常
        """
        submit = await self._submit_report_with_backoff(
            campaign_ids=campaign_ids,
            date_from=date_from,
            date_to=date_to,
            group_by=group_by,
            submit_timeout=submit_timeout,
            submit_interval=submit_interval,
        )
        uuid = submit.get("UUID")
        if not uuid:
            raise ValueError(f"提交报表任务失败，未返回 UUID: {submit}")

        waited = 0.0
        while waited < max_wait:
            status = await self.get_statistics_report_status(uuid)
            state = status.get("state")
            if state == "OK":
                return await self.download_statistics_report(uuid)
            if state == "ERROR":
                raise RuntimeError(f"报表任务失败 (UUID={uuid}): {status}")
            await asyncio.sleep(poll_interval)
            waited += poll_interval

        raise TimeoutError(f"报表任务等待超时 (UUID={uuid}, 已等待 {waited:.0f}s)")


class OzonAnalyticsClient(BasePlatformClient):
    """Seller Analytics client with the endpoint-specific one-call/minute limit."""

    BASE_URL = "https://api-seller.ozon.ru"

    def __init__(self, client_id: str, api_key: str):
        # Ozon documents one call/minute for this method. A small safety margin
        # avoids a new request landing on the server-side window boundary.
        super().__init__(
            api_key=api_key,
            base_url=self.BASE_URL,
            rate_limit_calls=1,
            rate_limit_period=65.0,
        )
        self.client_id = client_id

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Client-Id": self.client_id,
            "Api-Key": self.api_key,
            "Content-Type": "application/json",
        }

    @staticmethod
    def _retry_after_seconds(exc: RateLimitError) -> float:
        response = exc.response
        if response is not None:
            value = response.headers.get("Retry-After")
            if value:
                try:
                    return max(65.0, float(value))
                except ValueError:
                    pass
        return 65.0

    async def get_analytics_data(
        self,
        *,
        date_from: str,
        date_to: str,
        metrics: List[str],
        offset: int = 0,
        limit: int = 1000,
        sort_key: Optional[str] = None,
        max_attempts: int = 3,
    ) -> Dict[str, Any]:
        """Fetch one analytics page and use minute-scale backoff on HTTP 429."""
        if not 1 <= len(metrics) <= 14:
            raise ValueError("Ozon analytics metrics count must be between 1 and 14")
        if not 1 <= limit <= 1000:
            raise ValueError("Ozon analytics limit must be between 1 and 1000")
        sort_key = sort_key or metrics[0]
        if sort_key not in metrics:
            raise ValueError("Ozon analytics sort_key must be requested as a metric")

        payload = {
            "date_from": date_from,
            "date_to": date_to,
            "metrics": list(metrics),
            "dimension": list(OZON_ANALYTICS_DIMENSIONS),
            "filters": [],
            "sort": [{"key": sort_key, "order": "DESC"}],
            "limit": limit,
            "offset": offset,
        }
        for attempt in range(1, max_attempts + 1):
            try:
                return await self.post("/v1/analytics/data", json=payload)
            except RateLimitError as exc:
                if attempt >= max_attempts:
                    raise
                wait_seconds = self._retry_after_seconds(exc)
                logger.warning(
                    "[Ozon Analytics] 触发限流，第 %s/%s 次请求失败，等待 %.0f 秒",
                    attempt,
                    max_attempts,
                    wait_seconds,
                )
                await asyncio.sleep(wait_seconds)

        raise RuntimeError("unreachable analytics retry state")


class OzonClient:
    """
    Ozon 综合 API 客户端
    封装所有 Ozon API 调用
    """

    def __init__(
        self,
        client_id: str,
        api_key: str,
        performance_client_id: Optional[str] = None,
        performance_client_secret: Optional[str] = None,
    ):
        self.client_id = client_id
        self.api_key = api_key
        self.posting = OzonPostingClient(client_id, api_key)
        self.report = OzonReportClient(client_id, api_key)
        self.return_ = OzonReturnClient(client_id, api_key)
        self.review = OzonReviewClient(client_id, api_key)
        self.question = OzonQuestionClient(client_id, api_key)
        self.chat = OzonChatClient(client_id, api_key)
        self.finance = OzonFinanceClient(client_id, api_key)
        self.product = OzonProductClient(client_id, api_key)
        self.analytics = OzonAnalyticsClient(client_id, api_key)
        # 广告（Performance）API 客户端，仅在配置了独立凭证时可用
        self.performance: Optional[OzonPerformanceClient] = None
        if performance_client_id and performance_client_secret:
            self.performance = OzonPerformanceClient(
                performance_client_id, performance_client_secret
            )

    async def __aenter__(self) -> "OzonClient":
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器出口"""
        pass
