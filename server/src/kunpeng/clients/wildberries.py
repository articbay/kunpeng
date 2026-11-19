"""
Wildberries API 客户端
支持多个 API 域名：
- statistics-api.wildberries.ru - 统计数据 (旧财务API已废弃)
- seller-analytics-api.wildberries.ru - 分析数据
- advert-api.wildberries.ru - 广告数据
- feedbacks-api.wildberries.ru - 评价和提问
- buyer-chat-api.wildberries.ru - 买家聊天
- returns-api.wildberries.ru - 买家退货申请
- marketplace-api.wildberries.ru - 市场订单数据
- finance-api.wildberries.ru - 财务数据 (新API)
"""

import asyncio
import logging
import time
from datetime import datetime
from json import JSONDecodeError
from typing import Any, Dict, List, Optional

from kunpeng.clients.base import BasePlatformClient, RateLimiter, RateLimitError

logger = logging.getLogger(__name__)


class WildberriesStatisticsClient(BasePlatformClient):
    """Wildberries 统计数据 API 客户端"""

    BASE_URL = "https://statistics-api.wildberries.ru"

    def __init__(self, api_key: str):
        super().__init__(
            api_key=api_key,
            base_url=self.BASE_URL,
            rate_limit_calls=100,
            rate_limit_period=60.0,
        )

    async def get_supplier_orders(
        self,
        date_from: str,
        flag: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        获取供应商订单数据

        Args:
            date_from: 起始日期 (YYYY-MM-DD)
            flag: 0=获取所有订单, 1=仅获取新增订单

        Returns:
            订单数据列表
        """
        params = {
            "dateFrom": date_from,
            "flag": flag,
        }
        return await self._request("GET", "/api/v1/supplier/orders", params=params)

    async def get_supplier_sales(
        self,
        date_from: str,
        flag: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        获取供应商销售数据

        Args:
            date_from: 起始日期 (YYYY-MM-DD)
            flag: 0=获取所有销售, 1=仅获取新增销售

        Returns:
            销售数据列表
        """
        params = {
            "dateFrom": date_from,
            "flag": flag,
        }
        return await self._request("GET", "/api/v1/supplier/sales", params=params)

    async def get_financial_report_detail(
        self,
        date_from: str,
        date_to: str,
        period: str = "weekly",
        limit: int = 100000,
        rrdid: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        获取财务报告明细数据

        Args:
            date_from: 起始日期 (YYYY-MM-DD)
            date_to: 结束日期 (YYYY-MM-DD)
            period: 周期 (weekly=周, daily=日)
            limit: 每页记录数
            rrdid: 起始记录ID (用于分页)

        Returns:
            财务报告明细列表
        """
        params = {
            "dateFrom": date_from,
            "dateTo": date_to,
            "period": period,
            "limit": limit,
            "rrdid": rrdid,
        }
        return await self._request(
            "GET", "/api/v5/supplier/reportDetailByPeriod", params=params
        )


class WildberriesAnalyticsClient(BasePlatformClient):
    """Wildberries 分析数据 API 客户端"""

    BASE_URL = "https://seller-analytics-api.wildberries.ru"

    def __init__(self, api_key: str):
        super().__init__(
            api_key=api_key,
            base_url=self.BASE_URL,
            rate_limit_calls=100,
            rate_limit_period=60.0,
        )
        # 商品搜索分析接口限制为 3 次/分钟，且两次请求至少间隔 20 秒。
        self.product_search_rate_limiter = RateLimiter(1, 20.0)
        # 销售漏斗接口同样限制为 3 次/分钟，分页时必须至少间隔 20 秒。
        self.sales_funnel_rate_limiter = RateLimiter(1, 20.0)

    async def _request_product_search(
        self,
        endpoint: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """按商品搜索报告的独立额度请求，并在 429 后等待额度恢复。"""
        for attempt in range(3):
            await self.product_search_rate_limiter.acquire()
            try:
                return await self._request("POST", endpoint, json=payload)
            except RateLimitError:
                if attempt == 2:
                    raise
                logger.warning(
                    "[WB分析] %s 触发限流，20 秒后重试（%s/3）",
                    endpoint,
                    attempt + 1,
                )
                await asyncio.sleep(20)
        raise RuntimeError("商品搜索报告请求重试流程异常")

    async def get_sales_funnel(
        self,
        start_date: str,
        end_date: str,
        limit: int = 1000,
        offset: int = 0,
        order_by: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        获取销售漏斗数据

        Args:
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            limit: 返回数量限制
            offset: 分页偏移量
            order_by: 排序配置

        Returns:
            销售漏斗数据
        """
        payload = {
            "selectedPeriod": {
                "start": start_date,
                "end": end_date,
            },
            "limit": limit,
            "offset": offset,
        }
        if order_by:
            payload["orderBy"] = order_by
        await self.sales_funnel_rate_limiter.acquire()
        return await self._request(
            "POST",
            "/api/analytics/v3/sales-funnel/products",
            json=payload,
            timeout=120.0,
        )

    async def get_goods_return(
        self,
        date_from: str,
        date_to: str,
    ) -> List[Dict[str, Any]]:
        """
        获取退货商品报告

        Args:
            date_from: 起始日期 (YYYY-MM-DD)
            date_to: 结束日期 (YYYY-MM-DD)

        Returns:
            退货数据列表
        """
        params = {
            "dateFrom": date_from,
            "dateTo": date_to,
        }
        return await self._request(
            "GET", "/api/v1/analytics/goods-return", params=params
        )

    async def get_region_sales(
        self,
        date_from: str,
        date_to: str,
    ) -> Dict[str, Any]:
        """获取按国家地区、城市和商品聚合的区域销售报告。"""
        params = {
            "dateFrom": date_from,
            "dateTo": date_to,
        }
        return await self._request(
            "GET",
            "/api/v1/analytics/region-sale",
            params=params,
        )

    async def get_search_report_products(
        self,
        date_from: str,
        date_to: str,
        *,
        limit: int = 1000,
        offset: int = 0,
        position_cluster: str = "all",
        past_date_from: Optional[str] = None,
        past_date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """分页获取搜索报告中的商品，用于发现需要查询的 nmId。"""
        payload = {
            "currentPeriod": {"start": date_from, "end": date_to},
            "orderBy": {"field": "openCard", "mode": "desc"},
            "positionCluster": position_cluster,
            "includeSubstitutedSKUs": True,
            "includeSearchTexts": True,
            "limit": limit,
            "offset": offset,
        }
        if past_date_from and past_date_to:
            payload["pastPeriod"] = {
                "start": past_date_from,
                "end": past_date_to,
            }
        return await self._request_product_search(
            "/api/v2/search-report/table/details",
            payload,
        )

    async def get_product_search_texts(
        self,
        date_from: str,
        date_to: str,
        nm_ids: List[int],
        *,
        top_order_by: str = "openCard",
        limit: int = 30,
    ) -> Dict[str, Any]:
        """获取指定商品最近周期内的自然搜索词表现。"""
        if not nm_ids or len(nm_ids) > 50:
            raise ValueError("nm_ids 数量必须为 1 至 50")

        payload = {
            "currentPeriod": {"start": date_from, "end": date_to},
            "nmIds": nm_ids,
            "topOrderBy": top_order_by,
            "includeSubstitutedSKUs": True,
            "includeSearchTexts": True,
            "orderBy": {"field": top_order_by, "mode": "desc"},
            "limit": limit,
        }
        return await self._request_product_search(
            "/api/v2/search-report/product/search-texts",
            payload,
        )


class WildberriesAdvertClient(BasePlatformClient):
    """Wildberries 广告数据 API 客户端"""

    BASE_URL = "https://advert-api.wildberries.ru"

    # 广告统计接口(/adv/v3/fullstats)官方额度(每卖家账号)：常规密钥类型为
    # 3 请求/分钟，且要求 20s 最小间隔(burst=1)；纯 Base 密钥仅 1 请求/小时。
    # 之前 100/60s 的限流形同虚设，多店铺/多任务并发会被打到 429。
    # 这里按“1 请求 / 20s”(=3/min 且满足 20s 间隔)收紧令牌桶，并在统计接口上
    # 叠加 429 长退避排队(见 _request_with_backoff)兜底偶发限流。
    RATE_LIMIT_CALLS = 1
    RATE_LIMIT_PERIOD = 20.0
    # /adv/v3/fullstats 单次请求的广告活动数量上限(官方限制 50)，超过需分批。
    FULLSTATS_MAX_IDS = 50
    NORMQUERY_MAX_ITEMS = 100

    def __init__(self, api_key: str):
        super().__init__(
            api_key=api_key,
            base_url=self.BASE_URL,
            rate_limit_calls=self.RATE_LIMIT_CALLS,
            rate_limit_period=self.RATE_LIMIT_PERIOD,
        )

    @staticmethod
    def _normalize_normquery_items(
        items: List[Dict[str, Any]], *, camel_case: bool
    ) -> List[Dict[str, int]]:
        """标准化、去重并过滤无效的广告活动-商品组合。"""
        normalized: List[Dict[str, int]] = []
        seen = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            advert_id = item.get("advertId") or item.get("advert_id")
            nm_id = item.get("nmId") or item.get("nm_id")
            if not advert_id or not nm_id:
                continue
            key = (int(advert_id), int(nm_id))
            if key in seen:
                continue
            seen.add(key)
            if camel_case:
                normalized.append({"advertId": key[0], "nmId": key[1]})
            else:
                normalized.append({"advert_id": key[0], "nm_id": key[1]})
        return normalized

    @classmethod
    def _extract_normquery_items_from_adverts(
        cls, adverts_data: List[Dict[str, Any]], *, camel_case: bool
    ) -> List[Dict[str, int]]:
        """从当前 adverts v2 响应提取广告活动-商品组合。"""
        raw_items: List[Dict[str, Any]] = []
        for advert in adverts_data:
            if not isinstance(advert, dict):
                continue
            advert_id = advert.get("id") or advert.get("advertId")
            if not advert_id:
                continue

            nm_ids: List[Any] = []
            direct_nm_ids = advert.get("nm") or advert.get("nms") or []
            if isinstance(direct_nm_ids, list):
                for nm_item in direct_nm_ids:
                    if isinstance(nm_item, dict):
                        nm_ids.append(nm_item.get("nm_id") or nm_item.get("nmId"))
                    else:
                        nm_ids.append(nm_item)

            nm_settings = advert.get("nm_settings") or advert.get("nmSettings") or []
            if isinstance(nm_settings, list):
                for nm_setting in nm_settings:
                    if isinstance(nm_setting, dict):
                        nm_ids.append(
                            nm_setting.get("nm_id") or nm_setting.get("nmId")
                        )

            raw_items.extend(
                {"advert_id": advert_id, "nm_id": nm_id}
                for nm_id in nm_ids
                if nm_id
            )

        return cls._normalize_normquery_items(raw_items, camel_case=camel_case)

    async def _get_normquery_items(self, *, camel_case: bool) -> List[Dict[str, int]]:
        adverts_result = await self.get_adverts_list()
        adverts_data = (
            adverts_result.get("adverts", [])
            if isinstance(adverts_result, dict)
            else adverts_result
        )
        if not isinstance(adverts_data, list):
            return []
        items = self._extract_normquery_items_from_adverts(
            adverts_data, camel_case=camel_case
        )
        logger.info("[normquery] 有效广告商品组合数: %s", len(items))
        return items

    async def _post_normquery_batches(
        self,
        endpoint: str,
        items: List[Dict[str, int]],
        *,
        response_field: str,
        extra_payload: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for offset in range(0, len(items), self.NORMQUERY_MAX_ITEMS):
            batch = items[offset : offset + self.NORMQUERY_MAX_ITEMS]
            payload = dict(extra_payload or {})
            payload["items"] = batch
            response = await self._request("POST", endpoint, json=payload)
            batch_results: Any = response
            if isinstance(response, dict):
                batch_results = response.get(response_field, [])
            if isinstance(batch_results, list):
                results.extend(item for item in batch_results if isinstance(item, dict))
        logger.info(
            "[normquery] 接口 %s 请求组合数=%s，返回记录数=%s",
            endpoint,
            len(items),
            len(results),
        )
        return results

    async def _request_with_backoff(
        self,
        method: str,
        endpoint: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        max_wait: float = 300.0,
        retry_interval: float = 60.0,
    ) -> Any:
        """针对广告统计类接口的 429 长退避排队请求。

        base 客户端把 429 识别为 RateLimitError(不走 2~10s 指数退避)，广告接口
        额度是分钟级释放，这里在客户端层排队等待后重试，避免任务因偶发 429 直接失败。

        Args:
            max_wait: 累计等待上限(秒)，超时则抛出最后一次 RateLimitError。
            retry_interval: 每次 429 后的等待间隔(秒)。
        """
        waited = 0.0
        while True:
            try:
                return await self._request(method, endpoint, params=params, json=json)
            except RateLimitError:
                if waited >= max_wait:
                    logger.warning(
                        f"[WB广告] {endpoint} 触发限流且等待超时(已等待 {waited:.0f}s/"
                        f"{max_wait:.0f}s)，放弃本次请求"
                    )
                    raise
                logger.warning(
                    f"[WB广告] {endpoint} 触发限流(429)，将在 {retry_interval:.0f} 秒后重试 "
                    f"(已等待 {waited:.0f}s/{max_wait:.0f}s)"
                )
                await asyncio.sleep(retry_interval)
                waited += retry_interval

    async def get_adverts_list(
        self,
        status: Optional[int] = None,
        type_: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        获取广告活动列表

        Args:
            status: 活动状态筛选
            type_: 活动类型筛选

        Returns:
            广告活动列表
        """
        params = {}
        if status is not None:
            params["status"] = status
        if type_ is not None:
            params["type"] = type_
        return await self._request("GET", "/api/advert/v2/adverts", params=params)

    async def get_advert_stats(
        self,
        advert_ids: List[int],
        begin_date: str,
        end_date: str,
    ) -> List[Dict[str, Any]]:
        """
        获取广告统计数据

        Args:
            advert_ids: 广告活动ID列表
            begin_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            广告统计数据列表
        """
        # WB 限制单次最多 50 个广告活动("number of advert cannot be more than 50")，
        # 超过会返回 400。按 50 分批请求并合并结果。
        merged: List[Dict[str, Any]] = []
        for i in range(0, len(advert_ids), self.FULLSTATS_MAX_IDS):
            batch = advert_ids[i : i + self.FULLSTATS_MAX_IDS]
            params = {
                "ids": ",".join(map(str, batch)),
                "beginDate": begin_date,
                "endDate": end_date,
            }
            result = await self._request_with_backoff(
                "GET", "/adv/v3/fullstats", params=params
            )
            if isinstance(result, list):
                merged.extend(result)
            elif result:
                merged.append(result)
        return merged

    async def get_advert_budget(self, advert_id: int) -> Dict[str, Any]:
        """
        获取广告活动预算

        Args:
            advert_id: 广告活动ID

        Returns:
            预算信息
        """
        params = {"id": advert_id}
        return await self._request("GET", "/adv/v1/budget", params=params)

    async def get_normquery_stats(
        self,
        advert_nm_map: Dict[int, List[int]],
        begin_date: str,
        end_date: str,
    ) -> List[Dict[str, Any]]:
        """
        获取搜索关键字维度的广告统计

        Args:
            advert_nm_map: {advert_id: [nm_id1, nm_id2, ...]} 映射
            begin_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            关键字统计数据列表
        """
        # 构建 items 数组（v1 API 使用 camelCase 字段名）
        all_items = []
        for advert_id, nm_ids in advert_nm_map.items():
            for nm_id in nm_ids:
                all_items.append({"advertId": advert_id, "nmId": nm_id})

        logger.debug(f"[NormQuery] 总 items 数量: {len(all_items)}")

        # v1 API 对 items 数量限制为 30 个，分批处理
        batch_size = 30
        all_results = []

        for i in range(0, len(all_items), batch_size):
            batch = all_items[i : i + batch_size]
            payload = {
                "from": begin_date,
                "to": end_date,
                "items": batch,
            }
            logger.debug(
                f"[NormQuery] 发送批次 {i//batch_size + 1}: {len(batch)} 个 items, payload={payload}"
            )
            try:
                result = await self._request_with_backoff(
                    "POST", "/adv/v1/normquery/stats", json=payload
                )
                logger.debug(
                    f"[NormQuery] 批次 {i//batch_size + 1} 原始响应类型: {type(result)}"
                )
                if result:
                    # 打印响应结构样本（前2条）用于调试
                    if isinstance(result, list) and len(result) > 0:
                        logger.debug(
                            f"[NormQuery] 响应是列表，长度={len(result)}, 首元素keys={list(result[0].keys()) if isinstance(result[0], dict) else '非字典'}"
                        )
                        if len(result) > 1:
                            logger.debug(
                                f"[NormQuery] 第2元素keys={list(result[1].keys()) if isinstance(result[1], dict) else '非字典'}"
                            )
                    elif isinstance(result, dict):
                        logger.debug(
                            f"[NormQuery] 响应是字典，keys={list(result.keys())}"
                        )
                        # 打印每个key对应的值的类型
                        for k, v in result.items():
                            logger.debug(
                                f"[NormQuery]   key='{k}' -> type={type(v)}, len={len(v) if hasattr(v, '__len__') else 'N/A'}"
                            )
                            if (
                                isinstance(v, list)
                                and len(v) > 0
                                and isinstance(v[0], dict)
                            ):
                                logger.debug(
                                    f"[NormQuery]     首元素keys={list(v[0].keys())}"
                                )

                    batch_results = []
                    # v1 响应格式适配：尝试多种可能的字段名
                    if isinstance(result, dict):
                        # 尝试多种可能的顶层字段名
                        for field_name in [
                            "stats",
                            "data",
                            "items",
                            "clusters",
                            "queries",
                            "keywords",
                            "results",
                            "list",
                        ]:
                            if field_name in result and isinstance(
                                result[field_name], list
                            ):
                                batch_results = result[field_name]
                                logger.debug(
                                    f"[NormQuery] 从 dict['{field_name}'] 提取到 {len(batch_results)} 条"
                                )
                                break
                        if not batch_results:
                            # 如果都没有，尝试所有值为列表的字段
                            for k, v in result.items():
                                if isinstance(v, list):
                                    batch_results.extend(v)
                                    logger.debug(
                                        f"[NormQuery] 从 dict['{k}'] 提取到 {len(v)} 条"
                                    )
                    elif isinstance(result, list):
                        batch_results = result
                        logger.debug(
                            f"[NormQuery] 响应是列表，共 {len(batch_results)} 条"
                        )

                    # 展平嵌套结构
                    for item in batch_results:
                        if not isinstance(item, dict):
                            continue
                        advert_id = item.get("advertId") or item.get("advert_id")
                        nm_id = item.get("nmId") or item.get("nm_id")

                        # v1 实际结构: {"advertId", "nmId", "stat": {"views", "clicks", ...}}
                        stat_dict = item.get("stat")
                        if isinstance(stat_dict, dict) and len(stat_dict) > 0:
                            flat = dict(stat_dict)
                            if (
                                advert_id is not None
                                and "advertId" not in flat
                                and "advert_id" not in flat
                            ):
                                flat["advertId"] = advert_id
                            if (
                                nm_id is not None
                                and "nmId" not in flat
                                and "nm_id" not in flat
                            ):
                                flat["nmId"] = nm_id
                            all_results.append(flat)
                            continue

                        # 尝试其他可能的嵌套字段名（列表或字典形式）
                        nested_found = False
                        for nested_field in [
                            "dailyStats",
                            "stats",
                            "clusters",
                            "queries",
                            "keywords",
                            "items",
                            "data",
                            "results",
                        ]:
                            nested = item.get(nested_field)
                            if nested is None:
                                continue
                            if isinstance(nested, list) and len(nested) > 0:
                                logger.debug(
                                    f"[NormQuery] 展平嵌套列表 '{nested_field}', advertId={advert_id}, nmId={nm_id}, 数量={len(nested)}"
                                )
                                for stat in nested:
                                    if isinstance(stat, dict):
                                        if (
                                            advert_id is not None
                                            and "advertId" not in stat
                                            and "advert_id" not in stat
                                        ):
                                            stat["advertId"] = advert_id
                                        if (
                                            nm_id is not None
                                            and "nmId" not in stat
                                            and "nm_id" not in stat
                                        ):
                                            stat["nmId"] = nm_id
                                        all_results.append(stat)
                                nested_found = True
                                break
                            elif isinstance(nested, dict) and len(nested) > 0:
                                logger.debug(
                                    f"[NormQuery] 展平嵌套字典 '{nested_field}', advertId={advert_id}, nmId={nm_id}, 键数={len(nested)}"
                                )
                                for date_key, stat in nested.items():
                                    if isinstance(stat, dict):
                                        if "date" not in stat:
                                            stat["date"] = date_key
                                        if (
                                            advert_id is not None
                                            and "advertId" not in stat
                                            and "advert_id" not in stat
                                        ):
                                            stat["advertId"] = advert_id
                                        if (
                                            nm_id is not None
                                            and "nmId" not in stat
                                            and "nm_id" not in stat
                                        ):
                                            stat["nmId"] = nm_id
                                        all_results.append(stat)
                                nested_found = True
                                break
                        if not nested_found:
                            # 没有嵌套数据：item 只有 advertId+nmId，丢弃
                            logger.debug(
                                f"[NormQuery] 丢弃空项: advertId={advert_id}, nmId={nm_id}, keys={list(item.keys())}"
                            )

                    logger.debug(
                        f"[NormQuery] 批次 {i//batch_size + 1} 解析后累计: {len(all_results)} 条"
                    )
                    if all_results:
                        logger.debug(
                            f"[NormQuery] 首条结果keys={list(all_results[0].keys())}"
                        )
            except Exception as e:
                logger.warning(f"[NormQuery] 批次 {i//batch_size + 1} 失败: {e}")
                import traceback

                logger.warning(f"[NormQuery] 错误堆栈: {traceback.format_exc()}")
                continue

        logger.debug(f"[NormQuery] 总计解析: {len(all_results)} 条")
        if all_results:
            logger.debug(f"[NormQuery] 最终首条样本: {all_results[0]}")
        return all_results

    async def get_balance(self) -> Dict[str, Any]:
        """
        获取账户余额

        Returns:
            余额信息
        """
        return await self._request("GET", "/adv/v1/balance")

    async def get_norm_query_bids(
        self,
        items: Optional[List[Dict[str, int]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取标准查询竞价 (POST)

        Args:
            items: 数组，每项含 advert_id、nm_id

        Returns:
            bids 数组，每项含 advert_id、nm_id、norm_query、bid、bid_kopecks、currency
        """
        if items is None:
            items = await self._get_normquery_items(camel_case=False)
        else:
            items = self._normalize_normquery_items(items, camel_case=False)

        if not items:
            logger.warning("[normquery] 没有可用的 (advert_id, nm_id) 组合")
            return []

        return await self._post_normquery_batches(
            "/adv/v0/normquery/get-bids", items, response_field="bids"
        )

    async def get_norm_query_minus(
        self,
        items: Optional[List[Dict[str, int]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取排除关键词 (POST)

        Args:
            items: 数组，每项含 advert_id、nm_id

        Returns:
            items 数组，每项含 advert_id、nm_id、norm_queries（排除词字符串数组）
        """
        if items is None:
            items = await self._get_normquery_items(camel_case=False)
        else:
            items = self._normalize_normquery_items(items, camel_case=False)

        if not items:
            logger.warning("[normquery] 没有可用的 (advert_id, nm_id) 组合")
            return []

        return await self._post_normquery_batches(
            "/adv/v0/normquery/get-minus", items, response_field="items"
        )

    async def get_norm_query_list(
        self,
        items: Optional[List[Dict[str, int]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取标准查询列表 (POST)

        Args:
            items: 数组，每项含 advertId、nmId

        Returns:
            items 数组，每项含 advertId、nmId、normQueries（含 active、excluded、archived 三个集群数组）
        """
        if items is None:
            items = await self._get_normquery_items(camel_case=True)
        else:
            items = self._normalize_normquery_items(items, camel_case=True)

        if not items:
            logger.warning("[normquery] 没有可用的 (advertId, nmId) 组合")
            return []

        return await self._post_normquery_batches(
            "/adv/v0/normquery/list", items, response_field="items"
        )

    async def get_norm_query_stats(
        self,
        from_date: str,
        to_date: str,
        items: Optional[List[Dict[str, int]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取标准查询统计 (POST)

        Args:
            from_date: 开始日期 (YYYY-MM-DD)
            to_date: 结束日期 (YYYY-MM-DD)
            items: 数组，每项含 advert_id、nm_id

        Returns:
            stats 数组，每项含 advert_id、nm_id、stats 数组
        """
        if items is None:
            normalized_items = await self._get_normquery_items(camel_case=True)
        else:
            normalized_items = self._normalize_normquery_items(
                items, camel_case=True
            )

        if not normalized_items:
            logger.warning("[normquery] 没有可用的 (advert_id, nm_id) 组合")
            return []

        parents = await self._post_normquery_batches(
            "/adv/v1/normquery/stats",
            normalized_items,
            response_field="items",
            extra_payload={"from": from_date, "to": to_date},
        )
        flattened: List[Dict[str, Any]] = []
        for parent in parents:
            advert_id = parent.get("advertId") or parent.get("advert_id")
            nm_id = parent.get("nmId") or parent.get("nm_id")
            daily_stats = parent.get("dailyStats") or parent.get("daily_stats") or []
            if not isinstance(daily_stats, list):
                continue
            for daily_stat in daily_stats:
                if not isinstance(daily_stat, dict):
                    continue
                stat = daily_stat.get("stat")
                if not isinstance(stat, dict) or not stat:
                    continue
                flattened.append(
                    {
                        "advertId": advert_id,
                        "nmId": nm_id,
                        "date": daily_stat.get("date"),
                        "stat": dict(stat),
                    }
                )
        logger.info(
            "[normquery] v1 统计父记录数=%s，展开关键词统计数=%s",
            len(parents),
            len(flattened),
        )
        return flattened

    async def get_promotion_count(self) -> Dict[str, Any]:
        """
        获取促销计数 (GET)

        Returns:
            adverts 数组（每项含 type、status、count、advert_list）、all（总数量）
        """
        return await self._request("GET", "/adv/v1/promotion/count")

    async def get_bid_recommendations(
        self,
        nm_id: Optional[int] = None,
        advert_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        获取竞价推荐 (GET)

        Args:
            nm_id: 商品ID (可选)
            advert_id: 活动ID (可选)

        Returns:
            advertId、nmId、base、normQueries 数组
        """
        params = {}
        if nm_id is not None:
            params["nmId"] = nm_id
        if advert_id is not None:
            params["advertId"] = advert_id
        return await self._request(
            "GET", "/api/advert/v0/bids/recommendations", params=params
        )

    async def get_advert_fullstats(
        self,
        advert_ids: List[int],
        begin_date: str,
        end_date: str,
    ) -> List[Dict[str, Any]]:
        """
        获取广告完整统计 (分批处理)

        Args:
            advert_ids: 广告活动ID列表
            begin_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            完整统计数据列表
        """
        merged: List[Dict[str, Any]] = []
        for i in range(0, len(advert_ids), self.FULLSTATS_MAX_IDS):
            batch = advert_ids[i : i + self.FULLSTATS_MAX_IDS]
            params = {
                "ids": ",".join(map(str, batch)),
                "beginDate": begin_date,
                "endDate": end_date,
            }
            result = await self._request_with_backoff(
                "GET", "/adv/v3/fullstats", params=params
            )
            if isinstance(result, list):
                merged.extend(result)
            elif result:
                merged.append(result)
        return merged

    async def get_adverts_v2(
        self,
        status: Optional[int] = None,
        type_: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        获取广告活动列表V2

        Args:
            status: 活动状态筛选
            type_: 活动类型筛选

        Returns:
            广告活动列表
        """
        params = {}
        if status is not None:
            params["status"] = status
        if type_ is not None:
            params["type"] = type_
        return await self._request("GET", "/api/advert/v2/adverts", params=params)


class WildberriesFeedbacksClient(BasePlatformClient):
    """Wildberries 评价和提问 API 客户端"""

    BASE_URL = "https://feedbacks-api.wildberries.ru"

    def __init__(self, api_key: str):
        super().__init__(
            api_key=api_key,
            base_url=self.BASE_URL,
            rate_limit_calls=100,
            rate_limit_period=60.0,
        )

    async def get_feedbacks(
        self,
        is_answered: bool,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        take: int = 5000,
        skip: int = 0,
    ) -> Dict[str, Any]:
        """
        获取评价列表

        Args:
            is_answered: 是否已回复筛选 (required)
            date_from: 开始日期 (YYYY-MM-DD)
            date_to: 结束日期 (YYYY-MM-DD)
            take: 获取数量 (max 5000)
            skip: 跳过数量

        Returns:
            评价数据
        """

        # 将日期转换为 Unix 时间戳（秒）
        def date_to_timestamp(date_str: str) -> int:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return int(time.mktime(dt.timetuple()))

        params = {
            "isAnswered": "true" if is_answered else "false",
            "take": take,
            "skip": skip,
        }
        if date_from is not None:
            params["dateFrom"] = date_to_timestamp(date_from)
        if date_to is not None:
            params["dateTo"] = date_to_timestamp(date_to)
        return await self._request("GET", "/api/v1/feedbacks", params=params)

    async def get_archive_feedbacks(
        self,
        nm_id: Optional[int] = None,
        take: int = 50,
        skip: int = 0,
    ) -> Dict[str, Any]:
        """
        获取归档评价

        Args:
            nm_id: 商品ID筛选
            take: 获取数量
            skip: 跳过数量

        Returns:
            归档评价数据
        """
        params = {
            "take": take,
            "skip": skip,
        }
        if nm_id is not None:
            params["nmId"] = nm_id
        return await self._request("GET", "/api/v1/feedbacks/archive", params=params)

    async def get_feedback_pins(
        self,
        *,
        state: str,
        next_id: Optional[int] = None,
        limit: int = 500,
    ) -> Dict[str, Any]:
        """Get one state of pinned-feedback operations."""
        if state not in {"pinned", "unpinned"}:
            raise ValueError("state must be 'pinned' or 'unpinned'")
        params: Dict[str, Any] = {
            "state": state,
            "limit": limit,
        }
        if next_id is not None:
            params["next"] = next_id
        return await self._request(
            "GET",
            "/api/feedbacks/v1/pins",
            params=params,
        )

    async def get_questions(
        self,
        is_answered: bool,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        take: int = 5000,
        skip: int = 0,
    ) -> Dict[str, Any]:
        """
        获取提问列表

        Args:
            is_answered: 是否已回复筛选 (required)
            date_from: 开始日期 (YYYY-MM-DD)
            date_to: 结束日期 (YYYY-MM-DD)
            take: 获取数量 (max 5000)
            skip: 跳过数量

        Returns:
            提问数据
        """

        # 将日期转换为 Unix 时间戳（秒）
        def date_to_timestamp(date_str: str) -> int:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return int(time.mktime(dt.timetuple()))

        params = {
            "isAnswered": "true" if is_answered else "false",
            "take": take,
            "skip": skip,
        }
        if date_from is not None:
            params["dateFrom"] = date_to_timestamp(date_from)
        if date_to is not None:
            params["dateTo"] = date_to_timestamp(date_to)
        return await self._request("GET", "/api/v1/questions", params=params)


class WildberriesBuyerChatClient(BasePlatformClient):
    """Wildberries 买家聊天 API 客户端。"""

    BASE_URL = "https://buyer-chat-api.wildberries.ru"

    def __init__(self, api_key: str):
        # Personal/Service 额度为每 10 秒 10 次、请求间隔 1 秒、突发 10 次。
        super().__init__(
            api_key=api_key,
            base_url=self.BASE_URL,
            rate_limit_calls=10,
            rate_limit_period=10.0,
        )

    async def get_events(self, *, next_: Optional[int] = None) -> Dict[str, Any]:
        """按毫秒游标获取所有聊天的下一批事件。"""
        if next_ is not None and next_ < 0:
            raise ValueError("next must be non-negative")

        params = {"next": next_} if next_ is not None else None
        return await self._request(
            "GET",
            "/api/v1/seller/events",
            params=params,
        )


class WildberriesReturnsClient(BasePlatformClient):
    """Wildberries 买家退货申请 API 客户端。"""

    BASE_URL = "https://returns-api.wildberries.ru"

    def __init__(self, api_key: str):
        # 官方额度为 20 次/分钟、突发 10 次；用 10 次/30 秒的滚动窗口
        # 同时约束平均速率和突发量。
        super().__init__(
            api_key=api_key,
            base_url=self.BASE_URL,
            rate_limit_calls=10,
            rate_limit_period=30.0,
        )

    async def get_claims(
        self,
        *,
        is_archive: bool,
        limit: int = 200,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """分页获取最近 14 天的买家退货申请。"""
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        if offset < 0:
            raise ValueError("offset must be non-negative")

        params = {
            "is_archive": "true" if is_archive else "false",
            "limit": limit,
            "offset": offset,
        }
        return await self._request("GET", "/api/v1/claims", params=params)


class WildberriesMarketplaceClient(BasePlatformClient):
    """Wildberries 市场订单 API 客户端"""

    BASE_URL = "https://marketplace-api.wildberries.ru"

    def __init__(self, api_key: str):
        super().__init__(
            api_key=api_key,
            base_url=self.BASE_URL,
            rate_limit_calls=100,
            rate_limit_period=60.0,
        )

    async def get_orders(
        self,
        date_from: str,
        date_to: str,
        limit: int = 1000,
        next_: int = 0,
    ) -> Dict[str, Any]:
        """
        获取订单列表

        Args:
            date_from: 起始日期 (YYYY-MM-DD)
            date_to: 结束日期 (YYYY-MM-DD)
            limit: 每页数量 (最大 1000)
            next_: 下一页游标

        Returns:
            订单数据 (包含 orders 和 next 游标)
        """

        # 将日期转换为 Unix 时间戳（秒）
        def date_to_timestamp(date_str: str) -> int:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return int(time.mktime(dt.timetuple()))

        params = {
            "dateFrom": date_to_timestamp(date_from),
            "dateTo": date_to_timestamp(date_to),
            "limit": limit,
            "next": next_,
        }
        return await self._request("GET", "/api/v3/orders", params=params)

    async def get_new_orders(self) -> Dict[str, Any]:
        """
        获取新的组装订单（待处理订单）

        对应官方接口: GET /api/v3/orders/new
        文档: https://dev.wildberries.ru/en/docs/openapi/orders-fbs

        说明:
            返回当前所有"新的组装订单"，即卖家收到后仍需人工处理
            （分配到供货 supply -> 转交配送）的 FBS 订单。
            该接口无日期参数、不分页，每次调用返回的就是"当前待处理清单"，
            适合作为"新订单提醒"的数据源，无需维护时间窗口。

        Returns:
            订单数据，结构为 {"orders": [...]}
        """
        return await self._request("GET", "/api/v3/orders/new")

    async def get_supplies(
        self,
        *,
        limit: int = 1000,
        next_: int = 0,
    ) -> Dict[str, Any]:
        """Get one page of FBS supplies."""
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        if next_ < 0:
            raise ValueError("next must be non-negative")

        return await self._request(
            "GET",
            "/api/v3/supplies",
            params={"limit": limit, "next": next_},
        )

    async def get_reshipment_orders(self) -> Dict[str, Any]:
        """Get all FBS assembly orders currently requiring reshipment."""
        return await self._request(
            "GET",
            "/api/v3/supplies/orders/reshipment",
        )

    async def get_orders_metadata(
        self,
        order_ids: List[int],
    ) -> Dict[str, Any]:
        """Get FBS assembly order metadata for at most 100 order IDs."""
        if not order_ids:
            raise ValueError("order_ids must not be empty")
        if len(order_ids) > 100:
            raise ValueError("order_ids must contain at most 100 items")

        payload = {"orders": [int(order_id) for order_id in order_ids]}
        return await self._request(
            "POST",
            "/api/marketplace/v3/orders/meta",
            json=payload,
        )

    async def get_orders_status(
        self,
        order_ids: List[int],
    ) -> Dict[str, Any]:
        """
        获取订单状态

        Args:
            order_ids: 订单ID列表

        Returns:
            订单状态数据
        """
        payload = {"orders": order_ids}
        return await self._request("POST", "/api/v3/orders/status", json=payload)

    async def get_orders_status_history(
        self,
        order_ids: List[int],
    ) -> Dict[str, Any]:
        """
        获取订单状态历史

        Args:
            order_ids: 订单ID列表

        Returns:
            订单状态历史数据
        """
        payload = {"orders": order_ids}
        return await self._request(
            "POST", "/api/v3/orders/status/history", json=payload
        )


class WildberriesFinanceClient(BasePlatformClient):
    """Wildberries 财务数据 API 客户端 (新API)"""

    BASE_URL = "https://finance-api.wildberries.ru"

    def __init__(self, api_key: str):
        super().__init__(
            api_key=api_key,
            base_url=self.BASE_URL,
            rate_limit_calls=60,
            rate_limit_period=60.0,
        )

    async def get_sales_reports_detailed(
        self,
        date_from: str,
        date_to: str,
        limit: int = 100000,
        next_id: Optional[int] = None,
        period: Optional[str] = None,
    ) -> Any:
        """
        获取销售报告详情 (按周期)

        Args:
            date_from: 起始日期 (YYYY-MM-DD)
            date_to: 结束日期 (YYYY-MM-DD)
            limit: 每页记录数 (最大 100000)
            next_id: 下一页起始ID (用于分页)
            period: 报表周期，按日明细传 ``daily``

        Returns:
            销售报告详情数据
        """
        payload = {
            "dateFrom": date_from,
            "dateTo": date_to,
            "limit": limit,
        }
        if next_id is not None:
            payload["next"] = next_id
        if period is not None:
            payload["period"] = period
        return await self._request(
            "POST", "/api/finance/v1/sales-reports/detailed", json=payload
        )

    async def get_sales_reports_list(
        self,
        date_from: str,
        date_to: str,
        *,
        limit: int = 1000,
        offset: int = 0,
        period: str = "weekly",
    ) -> Any:
        """获取指定期间的财务报表列表。"""
        payload = {
            "dateFrom": date_from,
            "dateTo": date_to,
            "limit": limit,
            "offset": offset,
            "period": period,
        }
        try:
            return await self._request(
                "POST",
                "/api/finance/v1/sales-reports/list",
                json=payload,
            )
        except JSONDecodeError:
            # Wildberries 用 204 + 空响应体表示指定期间没有报表。
            return []

    async def get_balance(self) -> Dict[str, Any]:
        """
        获取账户余额

        Returns:
            余额信息
        """
        return await self._request("GET", "/api/v1/account/balance")


class WildberriesClient:
    """
    Wildberries 综合 API 客户端
    封装所有 Wildberries API 调用
    """

    def __init__(
        self,
        statistics_api_key: Optional[str] = None,
        analytics_api_key: Optional[str] = None,
        advert_api_key: Optional[str] = None,
        feedbacks_api_key: Optional[str] = None,
        buyer_chat_api_key: Optional[str] = None,
        returns_api_key: Optional[str] = None,
        marketplace_api_key: Optional[str] = None,
        finance_api_key: Optional[str] = None,
    ):
        self.statistics = (
            WildberriesStatisticsClient(statistics_api_key)
            if statistics_api_key
            else None
        )
        self.analytics = (
            WildberriesAnalyticsClient(analytics_api_key) if analytics_api_key else None
        )
        self.advert = (
            WildberriesAdvertClient(advert_api_key) if advert_api_key else None
        )
        self.feedbacks = (
            WildberriesFeedbacksClient(feedbacks_api_key) if feedbacks_api_key else None
        )
        self.buyer_chat = (
            WildberriesBuyerChatClient(buyer_chat_api_key)
            if buyer_chat_api_key
            else None
        )
        self.returns = (
            WildberriesReturnsClient(returns_api_key) if returns_api_key else None
        )
        self.marketplace = (
            WildberriesMarketplaceClient(marketplace_api_key)
            if marketplace_api_key
            else None
        )
        self.finance = (
            WildberriesFinanceClient(finance_api_key) if finance_api_key else None
        )

    async def __aenter__(self) -> "WildberriesClient":
        """异步上下文管理器入口"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器出口"""
        pass
