"""
Ozon 数据同步服务 (ODS层)
"""

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.clients.ozon import (OZON_ANALYTICS_CORE_METRICS,
                                  OZON_ANALYTICS_OUTCOME_METRICS, OzonClient)
from kunpeng.crud.dwd.ozon import (crud_dwd_ozon_advert_efficiency_detail,
                                   crud_dwd_ozon_order_detail,
                                   crud_dwd_ozon_return_detail,
                                   crud_dwd_ozon_sales_funnel_detail)
from kunpeng.crud.dwd.ozon.customer_voice import \
    crud_dwd_ozon_customer_voice_detail
from kunpeng.crud.ods.ozon.accrual_types import crud_ods_ozon_accrual_types
from kunpeng.crud.ods.ozon.advert_stats_hourly import \
    crud_ods_ozon_adv_stat_product_hourly
from kunpeng.crud.ods.ozon.adverts import (
    crud_ods_ozon_adv_campaign, crud_ods_ozon_adv_stat_daily,
    crud_ods_ozon_adv_stat_product_daily)
from kunpeng.crud.ods.ozon.analytics import (
    crud_ods_ozon_analytics_data_daily, crud_ods_ozon_analytics_totals_window)
from kunpeng.crud.ods.ozon.customer_engagement import (
    crud_ods_ozon_chat, crud_ods_ozon_chat_message, crud_ods_ozon_question,
    crud_ods_ozon_question_answer, crud_ods_ozon_review_comment)
from kunpeng.crud.ods.ozon.fbo_postings import (
    crud_ods_ozon_fbo_posting, crud_ods_ozon_fbo_posting_product)
from kunpeng.crud.ods.ozon.finance import (crud_ods_ozon_accrual_fee,
                                           crud_ods_ozon_finance_accrual)
from kunpeng.crud.ods.ozon.posting_reports import (
    crud_ods_ozon_posting_report_row, crud_ods_ozon_posting_report_task)
from kunpeng.crud.ods.ozon.postings import (
    crud_ods_ozon_fbs_posting, crud_ods_ozon_fbs_posting_cancellation,
    crud_ods_ozon_fbs_posting_delivery, crud_ods_ozon_fbs_posting_external,
    crud_ods_ozon_fbs_posting_optional, crud_ods_ozon_fbs_posting_product)
from kunpeng.crud.ods.ozon.products import crud_ods_ozon_product
from kunpeng.crud.ods.ozon.realization import (
    crud_ods_ozon_finance_realization_header,
    crud_ods_ozon_finance_realization_row)
from kunpeng.crud.ods.ozon.returns import (crud_ods_ozon_return,
                                           crud_ods_ozon_return_product,
                                           crud_ods_ozon_return_storage)
from kunpeng.crud.ods.ozon.reviews import crud_ods_ozon_review
from kunpeng.crud.ods.ozon.status_history import (
    crud_ods_ozon_posting_status_history, crud_ods_ozon_return_status_history)
from kunpeng.crud.ods.ozon.unfulfilled_postings import \
    crud_ods_ozon_unfulfilled_posting
from kunpeng.crud.ods.ozon.utils import parse_datetime_field, safe_int
from kunpeng.models.shop import Shop
from kunpeng.services.ozon_advert_efficiency_translation_service import \
    ozon_advert_efficiency_translation_service
from kunpeng.services.ozon_customer_voice_translation_service import \
    ozon_customer_voice_translation_service
from kunpeng.services.ozon_delivery_city_translation_service import \
    ozon_delivery_city_translation_service
from kunpeng.services.ozon_product_translation_service import \
    ozon_product_translation_service
from kunpeng.services.ozon_sales_funnel_translation_service import \
    ozon_sales_funnel_translation_service
from kunpeng.services.wb_dwd_translation_service import \
    wb_dwd_translation_service
from kunpeng.utils.timezone import now_platform, platform_tz

logger = logging.getLogger(__name__)

ProductCategoryKey = tuple[int, Optional[int]]
AnalyticsRowKey = tuple[int, date]


def parse_ozon_analytics_page(
    response: Dict[str, Any], metric_names: List[str]
) -> Dict[str, Any]:
    """Validate and label one positional ``/v1/analytics/data`` response page."""
    if not isinstance(response, dict):
        raise ValueError("Ozon analytics response must be an object")
    result = response.get("result")
    if not isinstance(result, dict):
        raise ValueError("Ozon analytics response.result must be an object")
    data = result.get("data")
    totals = result.get("totals")
    if not isinstance(data, list):
        raise ValueError("Ozon analytics result.data must be an array")
    if not isinstance(totals, list) or len(totals) > len(metric_names):
        raise ValueError("Ozon analytics totals contain unexpected metrics")
    # Without Premium, Ozon silently returns only the available prefix of the
    # requested array. Preserve those values and leave unavailable fields NULL.
    returned_metric_names = metric_names[: len(totals)]

    api_timestamp = parse_datetime_field(response.get("timestamp"))
    rows: Dict[AnalyticsRowKey, Dict[str, Any]] = {}
    for row in data:
        if not isinstance(row, dict):
            raise ValueError("Ozon analytics data row must be an object")
        dimensions = row.get("dimensions")
        metrics = row.get("metrics")
        if not isinstance(dimensions, list) or len(dimensions) != 2:
            raise ValueError("Ozon analytics dimensions length must be 2")
        if not isinstance(metrics, list) or len(metrics) != len(totals):
            raise ValueError(
                "Ozon analytics row metrics length does not match returned totals"
            )

        sku_dimension, day_dimension = dimensions
        if not isinstance(sku_dimension, dict) or not isinstance(day_dimension, dict):
            raise ValueError("Ozon analytics dimensions must be objects")
        sku = safe_int(sku_dimension.get("id"))
        if sku is None:
            raise ValueError("Ozon analytics row contains invalid SKU")
        try:
            stat_date = date.fromisoformat(str(day_dimension.get("id")))
        except (TypeError, ValueError) as exc:
            raise ValueError("Ozon analytics row contains invalid day") from exc

        key = (sku, stat_date)
        if key in rows:
            raise ValueError(f"Ozon analytics page contains duplicate key: {key}")
        rows[key] = {
            "sku": sku,
            "sku_name": sku_dimension.get("name"),
            "stat_date": stat_date,
            "metrics": dict(zip(returned_metric_names, metrics)),
            "row_data": row,
            "api_timestamp": api_timestamp,
        }

    return {
        "rows": rows,
        "totals": dict(zip(returned_metric_names, totals)),
        "raw_totals": totals,
        "api_timestamp": api_timestamp,
        "row_count": len(data),
    }


def build_product_category_name_map(
    nodes: List[Dict[str, Any]],
    *,
    parent_category_id: Optional[int] = None,
    parent_category_name: Optional[str] = None,
) -> Dict[ProductCategoryKey, str]:
    """Flatten Ozon's category tree into category/type lookup keys."""
    result: Dict[ProductCategoryKey, str] = {}
    for node in nodes or []:
        category_id = node.get("description_category_id") or parent_category_id
        category_name = node.get("category_name") or parent_category_name
        type_id = node.get("type_id")
        type_name = node.get("type_name")

        if category_id is not None and category_name:
            result[(int(category_id), None)] = str(category_name)
        if category_id is not None and type_id is not None:
            precise_name = type_name or category_name
            if precise_name:
                result[(int(category_id), int(type_id))] = str(precise_name)

        result.update(
            build_product_category_name_map(
                node.get("children") or [],
                parent_category_id=(
                    int(category_id) if category_id is not None else None
                ),
                parent_category_name=(str(category_name) if category_name else None),
            )
        )
    return result


def enrich_products_with_category_names(
    products: List[Dict[str, Any]],
    category_names: Dict[ProductCategoryKey, str],
) -> List[Dict[str, Any]]:
    """Attach the most precise category/type name to product API records."""
    enriched = []
    for item in products:
        product = dict(item)
        category_id = item.get("description_category_id") or item.get("category_id")
        type_id = item.get("type_id")
        category_name = None
        if category_id is not None:
            normalized_category_id = int(category_id)
            normalized_type_id = int(type_id) if type_id is not None else None
            category_name = category_names.get(
                (normalized_category_id, normalized_type_id)
            ) or category_names.get((normalized_category_id, None))
        product["_category_name"] = category_name
        enriched.append(product)
    return enriched


class OzonSyncService:
    """Ozon 数据同步服务"""

    def __init__(self, db: AsyncSession, shop: Shop):
        self.db = db
        self.shop = shop
        self.client = self._init_client()

    def _init_client(self) -> OzonClient:
        """初始化 API 客户端"""
        from kunpeng.config import settings

        client_id = getattr(self.shop, "platform_shop_id", "")
        api_key = str(self.shop.api_key or "")

        logger.debug(f"[Ozon同步服务] 初始化客户端 - Shop ID: {self.shop.id}")
        logger.debug(
            "[Ozon同步服务] Seller API 凭证状态: client_id=%s, api_key=%s",
            bool(client_id),
            bool(api_key),
        )

        # 广告 Performance API 凭证独立于 Seller API（形如 <id>@advertising.performance.ozon.ru）
        # 优先使用店铺级凭证，未配置时回退全局配置，支持多店铺各自独立的广告账号
        perf_client_id = (
            getattr(self.shop, "performance_client_id", None)
            or settings.ozon_performance_client_id
        )
        perf_client_secret = (
            getattr(self.shop, "performance_client_secret", None)
            or settings.ozon_performance_client_secret
        )

        return OzonClient(
            client_id=client_id,
            api_key=api_key,
            performance_client_id=perf_client_id,
            performance_client_secret=perf_client_secret,
        )

    async def _get_date_range(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> tuple[str, str]:
        """获取日期范围"""
        if not date_to:
            date_to = now_platform().strftime("%Y-%m-%d")
        if not date_from:
            date_from = (now_platform() - timedelta(days=30)).strftime("%Y-%m-%d")
        return date_from, date_to

    async def _translate_order_dwd_fields(self) -> Dict[str, Any]:
        """Fill missing Chinese product names and delivery cities."""
        return {
            "product_name": (
                await ozon_product_translation_service.translate_all_missing(
                    self.db,
                    shop_id=self.shop.id,
                    batch_size=500,
                    max_batches=10,
                )
            ),
            "delivery_city": (
                await ozon_delivery_city_translation_service.translate_all_missing(
                    self.db,
                    shop_id=self.shop.id,
                    batch_size=200,
                    max_batches=10,
                )
            ),
        }

    async def _translate_return_dwd_fields(self) -> Dict[str, Any]:
        """Fill all missing Chinese return fields for the current Ozon shop."""
        return await wb_dwd_translation_service.translate_all_missing(
            self.db,
            shop_id=self.shop.id,
            batch_size=50,
            max_batches=20,
        )

    async def sync_accrual_types(self) -> Dict[str, Any]:
        """同步应计类型字典"""
        logger.info(f"[Ozon同步服务] 开始同步应计类型字典 (全局维度表)")

        try:
            async with self.client:
                response = await self.client.finance.get_accrual_types()
                types_data = response.get("accrual_types", [])

                logger.debug(f"[Ozon同步服务] 获取到 {len(types_data)} 个应计类型")

                if types_data:
                    await crud_ods_ozon_accrual_types.create_many(
                        self.db,
                        items=types_data,
                    )
                    await self.db.flush()

                await self.db.commit()

                result = {
                    "status": "success",
                    "message": f"同步了 {len(types_data)} 个应计类型",
                    "count": len(types_data),
                }
                logger.info(f"[Ozon同步服务] 应计类型字典同步完成: {result}")
                return result

        except Exception as e:
            logger.error(
                f"[Ozon同步服务] 同步应计类型字典失败: {str(e)}", exc_info=True
            )
            return {"status": "error", "message": f"同步失败: {str(e)}"}

    async def sync_postings(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """同步订单数据"""
        logger.info(
            f"[Ozon同步服务] 开始同步订单数据 - 店铺: {self.shop.id}, 日期: {date_from}~{date_to}"
        )

        date_from, date_to = await self._get_date_range(date_from, date_to)

        since_dt = datetime.strptime(date_from, "%Y-%m-%d")
        since = since_dt.strftime("%Y-%m-%dT00:00:00Z")
        to_dt = datetime.strptime(date_to, "%Y-%m-%d")
        to = to_dt.strftime("%Y-%m-%dT23:59:59Z")

        total_postings = 0
        cursor = ""
        limit = 100
        max_iterations = 1000
        processed_numbers = set()
        seen_cursors = set()
        iteration = 0

        try:
            async with self.client:
                while True:
                    iteration += 1
                    if iteration > max_iterations:
                        logger.warning(
                            f"[Ozon同步服务] 达到最大迭代次数 {max_iterations}，停止同步"
                        )
                        break

                    response = await self.client.posting.get_fbs_postings(
                        since=since,
                        to=to,
                        limit=limit,
                        cursor=cursor,
                    )

                    if "postings" not in response:
                        raise ValueError("Ozon FBS v4 list 响应缺少 postings 字段")
                    postings_data = response.get("postings", []) or []
                    if not isinstance(postings_data, list):
                        raise ValueError("Ozon FBS v4 list 返回的 postings 不是列表")

                    new_postings = []
                    for posting in postings_data:
                        pn = posting.get("posting_number", "")
                        if pn and pn not in processed_numbers:
                            new_postings.append(posting)
                            processed_numbers.add(pn)

                    logger.debug(
                        f"[Ozon同步服务] cursor={cursor!r}, 本次获取到 {len(postings_data)} 个订单，"
                        f"其中 {len(new_postings)} 个新数据，累计: {total_postings + len(new_postings)}, "
                        f"has_next={response.get('has_next', False)}"
                    )

                    if new_postings:
                        await crud_ods_ozon_fbs_posting.create_many(
                            self.db,
                            items=new_postings,
                            shop_id=self.shop.id,
                        )
                        await self.db.flush()

                        for posting in new_postings:
                            posting_number = posting.get("posting_number", "")
                            if posting_number:
                                products = posting.get("products", [])
                                if products:
                                    await crud_ods_ozon_fbs_posting_product.create_many_for_posting(
                                        self.db,
                                        products=products,
                                        shop_id=self.shop.id,
                                        posting_number=posting_number,
                                    )
                                    await self.db.flush()

                                delivery_method = posting.get("delivery_method", {})
                                if delivery_method:
                                    await crud_ods_ozon_fbs_posting_delivery.create_or_update_for_posting(
                                        self.db,
                                        delivery_method=delivery_method,
                                        shop_id=self.shop.id,
                                        posting_number=posting_number,
                                    )
                                    await self.db.flush()

                                cancellation = posting.get("cancellation", {})
                                if cancellation:
                                    await crud_ods_ozon_fbs_posting_cancellation.create_or_update_for_posting(
                                        self.db,
                                        cancellation=cancellation,
                                        shop_id=self.shop.id,
                                        posting_number=posting_number,
                                    )
                                    await self.db.flush()

                                optional_fields = posting.get(
                                    "optional"
                                ) or posting.get("optional_fields", {})
                                if optional_fields:
                                    await crud_ods_ozon_fbs_posting_optional.create_or_update_for_posting(
                                        self.db,
                                        optional_fields=optional_fields,
                                        shop_id=self.shop.id,
                                        posting_number=posting_number,
                                    )
                                    await self.db.flush()

                                external_order = posting.get("external_order") or {}
                                external = {
                                    "posting_number": posting_number,
                                    "is_external": external_order.get(
                                        "is_external", posting.get("is_external", False)
                                    ),
                                    "platform_name": external_order.get(
                                        "platform_name",
                                        posting.get("platform_name", ""),
                                    ),
                                }
                                if external.get("is_external") or external.get(
                                    "platform_name"
                                ):
                                    await crud_ods_ozon_fbs_posting_external.create_or_update_for_posting(
                                        self.db,
                                        item=external,
                                        shop_id=self.shop.id,
                                        posting_number=posting_number,
                                    )
                                    await self.db.flush()

                    total_postings += len(new_postings)

                    # 每页提交一次：单页失败不会回滚已成功的页，且 CRUD 按
                    # (shop_id, posting_number) upsert，重跑天然幂等。
                    await self.db.commit()

                    if not response.get("has_next", False):
                        logger.info(f"[Ozon同步服务] has_next=False，没有更多订单数据")
                        break

                    next_cursor = response.get("cursor", "") or ""
                    if (
                        not next_cursor
                        or next_cursor == cursor
                        or next_cursor in seen_cursors
                    ):
                        raise ValueError("Ozon FBS v4 list 游标未推进")

                    seen_cursors.add(cursor)
                    cursor = next_cursor

                order_dwd_result = await crud_dwd_ozon_order_detail.upsert_from_ods(
                    self.db,
                    shop_id=self.shop.id,
                )
                return_dwd_result = await crud_dwd_ozon_return_detail.upsert_from_ods(
                    self.db,
                    shop_id=self.shop.id,
                )
                await self.db.commit()
                translation_result = {
                    "order": await self._translate_order_dwd_fields(),
                    "return": await self._translate_return_dwd_fields(),
                }

                result = {
                    "status": "success",
                    "message": f"同步了 {total_postings} 个订单，并刷新订单及退货DWD",
                    "count": total_postings,
                    "order_dwd": order_dwd_result,
                    "return_dwd": return_dwd_result,
                    "translation": translation_result,
                }
                logger.info(f"[Ozon同步服务] 订单数据同步完成: {result}")
                return result

        except Exception as e:
            logger.error(f"[Ozon同步服务] 同步订单数据失败: {str(e)}", exc_info=True)
            return {"status": "error", "message": f"同步失败: {str(e)}"}

    async def sync_fbo_postings(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步 FBO 订单数据（来自 Ozon 仓库的订单）

        来源接口 /v3/posting/fbo/list，响应结构为顶层 postings + cursor。
        主表按 (shop_id, posting_number) 幂等 upsert，商品子表按 (shop_id, posting_number, sku)。
        """
        logger.info(
            f"[Ozon同步服务] 开始同步FBO订单 - 店铺: {self.shop.id}, 日期: {date_from}~{date_to}"
        )

        date_from, date_to = await self._get_date_range(date_from, date_to)
        since = datetime.strptime(date_from, "%Y-%m-%d").strftime("%Y-%m-%dT00:00:00Z")
        to = datetime.strptime(date_to, "%Y-%m-%d").strftime("%Y-%m-%dT23:59:59Z")

        total_postings = 0
        cursor = ""
        limit = 100
        max_iterations = 1000
        processed_numbers = set()
        seen_cursors = set()
        iteration = 0

        try:
            async with self.client:
                while True:
                    iteration += 1
                    if iteration > max_iterations:
                        logger.warning(
                            f"[Ozon同步服务] FBO 达到最大迭代次数 {max_iterations}，停止同步"
                        )
                        break

                    response = await self.client.posting.get_fbo_postings(
                        since=since,
                        to=to,
                        limit=limit,
                        cursor=cursor,
                    )
                    if "postings" not in response:
                        raise ValueError("Ozon FBO v3 list 响应缺少 postings 字段")
                    postings_data = response.get("postings", []) or []
                    if not isinstance(postings_data, list):
                        raise ValueError("Ozon FBO v3 list 返回的 postings 不是列表")

                    new_postings = []
                    for posting in postings_data:
                        pn = posting.get("posting_number", "")
                        if pn and pn not in processed_numbers:
                            new_postings.append(posting)
                            processed_numbers.add(pn)

                    if new_postings:
                        await crud_ods_ozon_fbo_posting.create_many(
                            self.db, items=new_postings, shop_id=self.shop.id
                        )
                        await self.db.flush()

                        for posting in new_postings:
                            posting_number = posting.get("posting_number", "")
                            products = posting.get("products", []) or []
                            if posting_number and products:
                                await crud_ods_ozon_fbo_posting_product.create_many(
                                    self.db,
                                    items=products,
                                    shop_id=self.shop.id,
                                    posting_number=posting_number,
                                )
                                await self.db.flush()

                        total_postings += len(new_postings)
                        await self.db.commit()

                    if not response.get("has_next", False):
                        logger.debug("[Ozon同步服务] FBO 没有更多订单数据")
                        break

                    next_cursor = response.get("cursor", "") or ""
                    if (
                        not next_cursor
                        or next_cursor == cursor
                        or next_cursor in seen_cursors
                    ):
                        raise ValueError("Ozon FBO v3 list 游标未推进")

                    seen_cursors.add(cursor)
                    cursor = next_cursor

                order_dwd_result = await crud_dwd_ozon_order_detail.upsert_from_ods(
                    self.db,
                    shop_id=self.shop.id,
                )
                return_dwd_result = await crud_dwd_ozon_return_detail.upsert_from_ods(
                    self.db,
                    shop_id=self.shop.id,
                )
                await self.db.commit()
                translation_result = {
                    "order": await self._translate_order_dwd_fields(),
                    "return": await self._translate_return_dwd_fields(),
                }

                result = {
                    "status": "success",
                    "message": f"同步了 {total_postings} 个FBO订单，并刷新订单及退货DWD",
                    "count": total_postings,
                    "order_dwd": order_dwd_result,
                    "return_dwd": return_dwd_result,
                    "translation": translation_result,
                }
                logger.info(f"[Ozon同步服务] FBO订单数据同步完成: {result}")
                return result

        except Exception as e:
            logger.error(f"[Ozon同步服务] 同步FBO订单失败: {str(e)}", exc_info=True)
            return {"status": "error", "message": f"同步失败: {str(e)}"}

    async def sync_unfulfilled_postings(
        self,
        *,
        window_start: Optional[datetime] = None,
        window_end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Sync a complete v4 unfulfilled-posting cutoff window.

        Ozon's cutoff filter represents the fulfillment deadline, not the
        posting creation time. V4 does not return that cutoff on each posting,
        so the latest complete result is reconciled against the shop's
        previously active rows.
        """
        window_end = window_end or now_platform()
        if window_end.tzinfo is None:
            window_end = window_end.replace(tzinfo=platform_tz())
        window_start = window_start or (window_end - timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        if window_start.tzinfo is None:
            window_start = window_start.replace(tzinfo=platform_tz())
        if window_start >= window_end:
            return {
                "status": "error",
                "message": "未履约订单同步窗口起点必须早于终点",
            }

        start_utc = window_start.astimezone(timezone.utc)
        end_utc = window_end.astimezone(timezone.utc)
        cutoff_from = start_utc.isoformat(timespec="milliseconds").replace(
            "+00:00", "Z"
        )
        cutoff_to = end_utc.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        database_window_end = end_utc.replace(tzinfo=None)

        limit = 100
        max_pages = 500
        cursor = ""
        seen_cursors = {cursor}
        postings_by_number: Dict[str, Dict[str, Any]] = {}
        scanned_count = 0
        page_count = 0
        reported_count = 0

        logger.info(
            "[Ozon同步服务] 开始同步 v4 未履约订单 - 店铺: %s, " "cutoff窗口: %s ~ %s",
            self.shop.id,
            window_start,
            window_end,
        )

        try:
            async with self.client:
                while True:
                    if page_count >= max_pages:
                        raise RuntimeError(
                            f"Ozon v4 未履约订单分页超过安全上限 {max_pages}"
                        )

                    response = await self.client.posting.get_unfulfilled_postings(
                        cutoff_from=cutoff_from,
                        cutoff_to=cutoff_to,
                        limit=limit,
                        cursor=cursor,
                    )
                    if not isinstance(response, dict):
                        raise ValueError("Ozon v4 未履约订单响应不是对象")

                    required_fields = {
                        "postings",
                        "count",
                        "cursor",
                        "has_next",
                    }
                    missing_fields = required_fields - response.keys()
                    if missing_fields:
                        raise ValueError(
                            "Ozon v4 未履约订单响应缺少字段: "
                            + ", ".join(sorted(missing_fields))
                        )

                    postings = response["postings"]
                    has_next = response["has_next"]
                    next_cursor = response["cursor"]
                    count = response["count"]
                    if not isinstance(postings, list):
                        raise ValueError("Ozon v4 未履约订单 postings 不是列表")
                    if not isinstance(has_next, bool):
                        raise ValueError("Ozon v4 未履约订单 has_next 不是布尔值")
                    if not isinstance(count, int) or isinstance(count, bool):
                        raise ValueError("Ozon v4 未履约订单 count 不是整数")

                    page_count += 1
                    reported_count = count
                    scanned_count += len(postings)
                    for posting in postings:
                        if not isinstance(posting, dict):
                            raise ValueError(
                                "Ozon v4 未履约订单 postings 包含非对象记录"
                            )
                        posting_number = posting.get("posting_number")
                        if not posting_number:
                            raise ValueError(
                                "Ozon v4 未履约订单记录缺少 posting_number"
                            )
                        postings_by_number[str(posting_number)] = posting

                    if not has_next:
                        break
                    if (
                        not isinstance(next_cursor, str)
                        or not next_cursor
                        or next_cursor in seen_cursors
                    ):
                        raise ValueError("Ozon v4 未履约订单分页游标为空或重复")
                    seen_cursors.add(next_cursor)
                    cursor = next_cursor

            reconciliation = await crud_ods_ozon_unfulfilled_posting.reconcile_snapshot(
                self.db,
                items=list(postings_by_number.values()),
                shop_id=self.shop.id,
                observed_at=database_window_end,
            )
            await self.db.commit()
            result = {
                "status": "success",
                "message": (
                    f"完整获取 {scanned_count} 条未履约订单，"
                    f"幂等写入 {reconciliation['ods_count']} 条"
                ),
                "count": len(postings_by_number),
                "scanned_count": scanned_count,
                "reported_count": reported_count,
                "page_count": page_count,
                "window_start": window_start.isoformat(),
                "window_end": window_end.isoformat(),
                **reconciliation,
            }
            logger.info(
                "[Ozon同步服务] v4 未履约订单同步完成: %s",
                result,
            )
            return result
        except Exception as exc:
            await self.db.rollback()
            logger.exception(
                "[Ozon同步服务] v4 未履约订单同步失败 - 店铺: %s",
                self.shop.id,
            )
            return {
                "status": "error",
                "message": f"同步失败: {exc}",
            }

    async def sync_returns(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        *,
        time_filter: str = "logistic_return_date",
    ) -> Dict[str, Any]:
        """同步退货数据"""
        logger.info(
            f"[Ozon同步服务] 开始同步退货数据 - 店铺: {self.shop.id}, 日期: {date_from}~{date_to}"
        )

        date_from, date_to = await self._get_date_range(date_from, date_to)

        # 转换为 RFC3339 格式
        since_dt = datetime.strptime(date_from, "%Y-%m-%d")
        date_from_rfc = since_dt.strftime("%Y-%m-%dT00:00:00Z")
        to_dt = datetime.strptime(date_to, "%Y-%m-%d")
        date_to_rfc = to_dt.strftime("%Y-%m-%dT23:59:59Z")

        total_returns = 0
        last_id = None
        limit = 100
        max_iterations = 1000  # 防止死循环的最大迭代次数
        iterations = 0
        processed_ids = set()  # 记录已处理的ID，防止重复处理
        empty_count = 0  # 连续空结果计数
        max_empty = 3  # 允许连续空结果的最大次数
        same_id_count = 0  # 连续相同last_id计数
        max_same_id = 3  # 允许连续相同last_id的最大次数

        try:
            async with self.client:
                while True:
                    iterations += 1
                    prev_last_id = last_id

                    # 防止死循环检查
                    if iterations > max_iterations:
                        logger.warning(
                            f"[Ozon同步服务] 达到最大迭代次数 {max_iterations}，停止同步"
                        )
                        break

                    response = await self.client.return_.get_returns_list(
                        date_from=date_from_rfc,
                        date_to=date_to_rfc,
                        limit=limit,
                        last_id=last_id,
                        time_filter=time_filter,
                    )

                    returns_data = response.get("returns", [])
                    has_next = response.get("has_next", False)

                    if not returns_data:
                        empty_count += 1
                        logger.debug(
                            f"[Ozon同步服务] 没有获取到退货数据 (连续空结果: {empty_count}/{max_empty})"
                        )
                        if empty_count >= max_empty:
                            logger.info(
                                f"[Ozon同步服务] 连续 {max_empty} 次空结果，停止同步"
                            )
                            break
                        # 即使没有数据，如果has_next=True也尝试继续，但使用空计数限制
                        if not has_next:
                            break
                        # 强制递增last_id来避免卡住？不，我们使用same_id_count来检测
                        continue

                    # 重置空结果计数
                    empty_count = 0

                    # 检查是否有新数据（去重）
                    new_returns = []
                    for item in returns_data:
                        item_id = item.get("id")
                        if item_id is not None and item_id not in processed_ids:
                            new_returns.append(item)
                            processed_ids.add(item_id)

                    if not new_returns:
                        logger.debug(f"[Ozon同步服务] 本次获取的数据全部已处理过")
                        # 继续尝试，但记录相同ID情况
                    else:
                        logger.debug(
                            f"[Ozon同步服务] last_id={last_id}, 本次获取到 {len(returns_data)} 个退货，其中 {len(new_returns)} 个新数据，累计: {total_returns + len(new_returns)}, has_next={has_next}"
                        )

                    if new_returns:
                        await crud_ods_ozon_return.create_many(
                            self.db,
                            items=new_returns,
                            shop_id=self.shop.id,
                        )
                        await self.db.flush()

                        for return_item in new_returns:
                            return_id = return_item.get("id")
                            if return_id is not None:
                                await crud_ods_ozon_return_product.create_many_for_return(
                                    self.db,
                                    item=return_item,
                                    shop_id=self.shop.id,
                                    return_id=return_id,
                                )
                                await self.db.flush()

                                await crud_ods_ozon_return_storage.create_or_update_for_return(
                                    self.db,
                                    item=return_item,
                                    shop_id=self.shop.id,
                                    return_id=return_id,
                                )
                                await self.db.flush()

                    total_returns += len(new_returns)

                    # 每页提交一次（按 return id upsert，幂等）
                    await self.db.commit()

                    # Ozon 明确返回下一页 last_id；仅为兼容旧 mock 才回退到末行 id。
                    new_last_id = response.get("last_id")
                    if new_last_id is None:
                        new_last_id = returns_data[-1].get("id")

                    # 检查last_id是否变化
                    if new_last_id == prev_last_id and prev_last_id is not None:
                        same_id_count += 1
                        logger.warning(
                            f"[Ozon同步服务] last_id没有变化 (连续: {same_id_count}/{max_same_id})"
                        )
                        if same_id_count >= max_same_id:
                            logger.warning(
                                f"[Ozon同步服务] 连续 {max_same_id} 次相同last_id，可能陷入死循环，停止同步"
                            )
                            break
                    else:
                        same_id_count = 0

                    last_id = new_last_id

                    # 使用has_next字段判断是否还有下一页
                    if not has_next:
                        logger.info(f"[Ozon同步服务] has_next=False，没有更多退货数据")
                        break

                storage_backfilled = (
                    await crud_ods_ozon_return_storage.backfill_missing_from_returns(
                        self.db,
                        shop_id=self.shop.id,
                    )
                )
                dwd_result = await crud_dwd_ozon_return_detail.upsert_from_ods(
                    self.db,
                    shop_id=self.shop.id,
                )
                await self.db.commit()
                translation_result = await self._translate_return_dwd_fields()

                result = {
                    "status": "success",
                    "message": f"同步了 {total_returns} 个退货 (ODS/DWD)",
                    "count": total_returns,
                    "storage_backfilled": storage_backfilled,
                    "dwd": dwd_result,
                    "translation": translation_result,
                }
                logger.info(f"[Ozon同步服务] 退货数据同步完成: {result}")
                return result

        except Exception as e:
            await self.db.rollback()
            logger.error(f"[Ozon同步服务] 同步退货数据失败: {str(e)}", exc_info=True)
            return {"status": "error", "message": f"同步失败: {str(e)}"}

    async def sync_return_status_changes(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """按可视状态变更时间增量补抓退货，不改变现有物流日期同步。"""
        return await self.sync_returns(
            date_from,
            date_to,
            time_filter="visual_status_change_moment",
        )

    async def sync_reviews(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """同步评价数据"""
        logger.info(
            f"[Ozon同步服务] 开始同步评价数据 - 店铺: {self.shop.id}, 日期: {date_from}~{date_to}"
        )

        date_from, date_to = await self._get_date_range(date_from, date_to)

        # 转换为 RFC3339 格式
        since_dt = datetime.strptime(date_from, "%Y-%m-%d")
        date_from_rfc = since_dt.strftime("%Y-%m-%dT00:00:00Z")
        to_dt = datetime.strptime(date_to, "%Y-%m-%d")
        date_to_rfc = to_dt.strftime("%Y-%m-%dT23:59:59Z")

        total_reviews = 0
        last_id = None
        limit = 100
        max_iterations = 1000  # 防止死循环的最大迭代次数
        iterations = 0
        processed_ids = set()  # 记录已处理的ID，防止重复处理
        empty_count = 0  # 连续空结果计数
        max_empty = 3  # 允许连续空结果的最大次数
        same_id_count = 0  # 连续相同last_id计数
        max_same_id = 3  # 允许连续相同last_id的最大次数

        try:
            async with self.client:
                while True:
                    iterations += 1
                    prev_last_id = last_id

                    # 防止死循环检查
                    if iterations > max_iterations:
                        logger.warning(
                            f"[Ozon同步服务] 达到最大迭代次数 {max_iterations}，停止同步"
                        )
                        break

                    response = await self.client.review.get_review_list(
                        date_from=date_from_rfc,
                        date_to=date_to_rfc,
                        limit=limit,
                        last_id=last_id,
                    )

                    reviews_data = response.get("reviews", [])
                    has_next = response.get("has_next", False)

                    if not reviews_data:
                        empty_count += 1
                        logger.debug(
                            f"[Ozon同步服务] 没有获取到评价数据 (连续空结果: {empty_count}/{max_empty})"
                        )
                        if empty_count >= max_empty:
                            logger.info(
                                f"[Ozon同步服务] 连续 {max_empty} 次空结果，停止同步"
                            )
                            break
                        # 即使没有数据，如果has_next=True也尝试继续，但使用空计数限制
                        if not has_next:
                            break
                        continue

                    # 重置空结果计数
                    empty_count = 0

                    # 检查是否有新数据（去重）
                    new_reviews = []
                    for item in reviews_data:
                        item_id = item.get("id")
                        if item_id is not None and item_id not in processed_ids:
                            new_reviews.append(item)
                            processed_ids.add(item_id)

                    if not new_reviews:
                        logger.debug(f"[Ozon同步服务] 本次获取的数据全部已处理过")
                        # 继续尝试，但记录相同ID情况
                    else:
                        logger.debug(
                            f"[Ozon同步服务] last_id={last_id}, 本次获取到 {len(reviews_data)} 个评价，其中 {len(new_reviews)} 个新数据，累计: {total_reviews + len(new_reviews)}, has_next={has_next}"
                        )

                    if new_reviews:
                        await crud_ods_ozon_review.create_many(
                            self.db,
                            items=new_reviews,
                            shop_id=self.shop.id,
                        )
                        await self.db.flush()

                    total_reviews += len(new_reviews)

                    # 每页提交一次（按 review id upsert，幂等）
                    await self.db.commit()

                    # 优先使用 API 返回的游标，兼容旧响应时再回退到末行 id。
                    new_last_id = response.get("last_id")
                    if new_last_id is None:
                        new_last_id = reviews_data[-1].get("id")

                    # 检查last_id是否变化
                    if new_last_id == prev_last_id and prev_last_id is not None:
                        same_id_count += 1
                        logger.warning(
                            f"[Ozon同步服务] last_id没有变化 (连续: {same_id_count}/{max_same_id})"
                        )
                        if same_id_count >= max_same_id:
                            logger.warning(
                                f"[Ozon同步服务] 连续 {max_same_id} 次相同last_id，可能陷入死循环，停止同步"
                            )
                            break
                    else:
                        same_id_count = 0

                    last_id = new_last_id

                    # 使用has_next字段判断是否还有下一页
                    if not has_next:
                        logger.info(f"[Ozon同步服务] has_next=False，没有更多评价数据")
                        break

                await self.db.commit()

                result = {
                    "status": "success",
                    "message": f"同步了 {total_reviews} 个评价 (ODS)",
                    "count": total_reviews,
                }
                dwd_result = await self.sync_customer_voice_dwd(date_from, date_to)
                result["customer_voice_dwd"] = dwd_result
                if dwd_result.get("status") != "success":
                    result["status"] = "error"
                    dwd_message = dwd_result.get("message", "未知错误")
                    result["message"] += f"；客户声音DWD构建失败: {dwd_message}"
                logger.info(f"[Ozon同步服务] 评价数据同步完成: {result}")
                return result

        except Exception as e:
            await self.db.rollback()
            logger.error(f"[Ozon同步服务] 同步评价数据失败: {str(e)}", exc_info=True)
            return {"status": "error", "message": f"同步失败: {str(e)}"}

    async def sync_review_comments(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """补齐已有评价的只读详情和评论记录。"""
        from sqlalchemy import select

        from kunpeng.models.ods.ozon.reviews import ODSOzonReview

        date_from, date_to = await self._get_date_range(date_from, date_to)
        start = datetime.strptime(date_from, "%Y-%m-%d")
        end = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
        query = select(ODSOzonReview.review_id).where(
            ODSOzonReview.shop_id == self.shop.id,
            ODSOzonReview.published_at >= start,
            ODSOzonReview.published_at < end,
        )
        review_ids = list((await self.db.execute(query)).scalars().all())
        saved_comments = 0
        enriched_reviews = 0

        try:
            async with self.client:
                for review_id in review_ids:
                    detail_response = await self.client.review.get_review_info(
                        str(review_id)
                    )
                    detail = detail_response.get("review") or detail_response.get(
                        "result"
                    )
                    if isinstance(detail, dict):
                        await crud_ods_ozon_review.create_many(
                            self.db, items=[detail], shop_id=self.shop.id
                        )
                        enriched_reviews += 1

                    offset = 0
                    limit = 100
                    while True:
                        response = await self.client.review.get_review_comments(
                            str(review_id), limit=limit, offset=offset
                        )
                        comments = (
                            response.get("comments") or response.get("result") or []
                        )
                        if isinstance(comments, dict):
                            comments = (
                                comments.get("comments") or comments.get("items") or []
                            )
                        if not isinstance(comments, list) or not comments:
                            break
                        saved_comments += (
                            await crud_ods_ozon_review_comment.upsert_many(
                                self.db,
                                items=comments,
                                shop_id=self.shop.id,
                                review_id=review_id,
                            )
                        )
                        if len(comments) < limit:
                            break
                        offset += limit
                    await self.db.commit()
            return {
                "status": "success",
                "count": saved_comments,
                "reviews": enriched_reviews,
            }
        except Exception as exc:
            await self.db.rollback()
            logger.error("[Ozon同步服务] 同步评价评论失败", exc_info=True)
            return {"status": "error", "message": f"同步失败: {exc}"}

    async def sync_questions(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """同步商品问题及只读回答列表。"""
        date_from, date_to = await self._get_date_range(date_from, date_to)
        date_from_rfc = f"{date_from}T00:00:00Z"
        date_to_rfc = f"{date_to}T23:59:59Z"
        cursor = ""
        saved_questions = 0
        saved_answers = 0
        seen_cursors: set[str] = set()

        try:
            async with self.client:
                while True:
                    response = await self.client.question.get_question_list(
                        date_from=date_from_rfc,
                        date_to=date_to_rfc,
                        limit=100,
                        last_id=cursor,
                    )
                    question_page = response.get("result") or response
                    if not isinstance(question_page, dict):
                        raise ValueError("Ozon question/list 返回根节点不是对象")
                    questions = question_page.get("questions") or []
                    if not isinstance(questions, list):
                        raise ValueError("Ozon question/list 返回 questions 不是列表")
                    saved_questions += await crud_ods_ozon_question.upsert_many(
                        self.db, items=questions, shop_id=self.shop.id
                    )

                    for question in questions:
                        question_id = str(
                            question.get("id") or question.get("question_id") or ""
                        )
                        if not question_id:
                            continue
                        answer_cursor = ""
                        seen_answer_cursors: set[str] = set()
                        while True:
                            answer_response = (
                                await self.client.question.get_question_answers(
                                    question_id, limit=100, last_id=answer_cursor
                                )
                            )
                            answer_page = (
                                answer_response.get("result") or answer_response
                            )
                            if not isinstance(answer_page, dict):
                                raise ValueError(
                                    "Ozon question/answer/list 返回根节点不是对象"
                                )
                            answers = answer_page.get("answers") or []
                            if not isinstance(answers, list):
                                raise ValueError(
                                    "Ozon question/answer/list 返回 answers 不是列表"
                                )
                            saved_answers += (
                                await crud_ods_ozon_question_answer.upsert_many(
                                    self.db,
                                    items=answers,
                                    shop_id=self.shop.id,
                                    question_id=question_id,
                                )
                            )
                            next_answer_cursor = str(answer_page.get("last_id") or "")
                            if not answer_page.get("has_next"):
                                break
                            if (
                                not next_answer_cursor
                                or next_answer_cursor in seen_answer_cursors
                            ):
                                raise ValueError("Ozon 回答分页游标为空或重复")
                            seen_answer_cursors.add(next_answer_cursor)
                            answer_cursor = next_answer_cursor

                    await self.db.commit()
                    next_cursor = str(question_page.get("last_id") or "")
                    if not question_page.get("has_next"):
                        break
                    if not next_cursor or next_cursor in seen_cursors:
                        raise ValueError("Ozon 问题分页游标为空或重复")
                    seen_cursors.add(next_cursor)
                    cursor = next_cursor
            return {
                "status": "success",
                "count": saved_questions,
                "answers": saved_answers,
            }
        except Exception as exc:
            await self.db.rollback()
            logger.error("[Ozon同步服务] 同步问题和回答失败", exc_info=True)
            return {"status": "error", "message": f"同步失败: {exc}"}

    async def sync_chats(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """同步能明确关联现有 FBS/FBO posting 的聊天和消息。"""
        from sqlalchemy import select

        from kunpeng.models.ods.ozon.fbo_postings import ODSOzonFBOPosting
        from kunpeng.models.ods.ozon.postings import ODSOzonFBSPosting

        del date_from, date_to
        cursor = ""
        seen_cursors: set[str] = set()
        saved_chats = 0
        saved_messages = 0

        try:
            async with self.client:
                while True:
                    response = await self.client.chat.get_chat_list(
                        limit=100, cursor=cursor
                    )
                    chats = response.get("chats") or []
                    if not isinstance(chats, list):
                        raise ValueError("Ozon chat/list 返回 chats 不是列表")

                    posting_numbers = set()
                    for item in chats:
                        chat = (
                            item.get("chat")
                            if isinstance(item.get("chat"), dict)
                            else item
                        )
                        posting_number = chat.get("posting_number") or item.get(
                            "posting_number"
                        )
                        if posting_number:
                            posting_numbers.add(str(posting_number))

                    linked_numbers: set[str] = set()
                    if posting_numbers:
                        fbs = await self.db.execute(
                            select(ODSOzonFBSPosting.posting_number).where(
                                ODSOzonFBSPosting.shop_id == self.shop.id,
                                ODSOzonFBSPosting.posting_number.in_(posting_numbers),
                            )
                        )
                        fbo = await self.db.execute(
                            select(ODSOzonFBOPosting.posting_number).where(
                                ODSOzonFBOPosting.shop_id == self.shop.id,
                                ODSOzonFBOPosting.posting_number.in_(posting_numbers),
                            )
                        )
                        linked_numbers.update(str(value) for value in fbs.scalars())
                        linked_numbers.update(str(value) for value in fbo.scalars())

                    linked_chats = []
                    for item in chats:
                        chat = (
                            item.get("chat")
                            if isinstance(item.get("chat"), dict)
                            else item
                        )
                        posting_number = str(
                            chat.get("posting_number")
                            or item.get("posting_number")
                            or ""
                        )
                        if posting_number in linked_numbers:
                            linked_chats.append(item)

                    for item in linked_chats:
                        chat = (
                            item.get("chat")
                            if isinstance(item.get("chat"), dict)
                            else item
                        )
                        chat_id = str(chat.get("chat_id") or chat.get("id") or "")
                        posting_number = str(
                            chat.get("posting_number")
                            or item.get("posting_number")
                            or ""
                        )
                        if not chat_id:
                            continue
                        from_message_id = (
                            await crud_ods_ozon_chat.get_latest_message_id(
                                self.db, shop_id=self.shop.id, chat_id=chat_id
                            )
                        )
                        seen_message_cursors: set[str] = set()
                        while True:
                            history = await self.client.chat.get_chat_history(
                                chat_id,
                                limit=100,
                                from_message_id=from_message_id,
                            )
                            message_page = history.get("result") or history
                            if not isinstance(message_page, dict):
                                raise ValueError("Ozon chat/history 返回根节点不是对象")
                            messages = message_page.get("messages") or []
                            if not isinstance(messages, list):
                                raise ValueError(
                                    "Ozon chat/history 返回 messages 不是列表"
                                )
                            saved_messages += (
                                await crud_ods_ozon_chat_message.upsert_many(
                                    self.db,
                                    items=messages,
                                    shop_id=self.shop.id,
                                    chat_id=chat_id,
                                    posting_number=posting_number,
                                )
                            )
                            if not message_page.get("has_next"):
                                break
                            next_message_id = str(
                                message_page.get("from_message_id")
                                or message_page.get("last_message_id")
                                or (messages[-1].get("message_id") if messages else "")
                                or (messages[-1].get("id") if messages else "")
                            )
                            if (
                                not next_message_id
                                or next_message_id in seen_message_cursors
                            ):
                                raise ValueError("Ozon 聊天历史分页游标为空或重复")
                            seen_message_cursors.add(next_message_id)
                            from_message_id = next_message_id
                    saved_chats += await crud_ods_ozon_chat.upsert_many(
                        self.db, items=linked_chats, shop_id=self.shop.id
                    )
                    await self.db.commit()

                    next_cursor = str(response.get("cursor") or "")
                    if not response.get("has_next"):
                        break
                    if not next_cursor or next_cursor in seen_cursors:
                        raise ValueError("Ozon 聊天分页游标为空或重复")
                    seen_cursors.add(next_cursor)
                    cursor = next_cursor
            return {
                "status": "success",
                "count": saved_chats,
                "messages": saved_messages,
            }
        except Exception as exc:
            await self.db.rollback()
            logger.error("[Ozon同步服务] 同步聊天失败", exc_info=True)
            return {"status": "error", "message": f"同步失败: {exc}"}

    async def _load_accrual_type_dict(self) -> Dict[int, Dict[str, Any]]:
        """加载应计类型字典 type_id -> {name, description}，用于费用明细行冗余类型名称。"""
        from sqlalchemy import select

        from kunpeng.models.ods.ozon.accrual_types import \
            ODSOzonFinanceAccrualType

        result = await self.db.execute(
            select(
                ODSOzonFinanceAccrualType.type_id,
                ODSOzonFinanceAccrualType.name,
                ODSOzonFinanceAccrualType.description,
            )
        )
        type_dict: Dict[int, Dict[str, Any]] = {}
        for type_id, name, description in result.all():
            if type_id is not None:
                type_dict[int(type_id)] = {"name": name, "description": description}
        return type_dict

    async def sync_finance_accruals(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """同步财务应计数据"""
        logger.info(
            f"[Ozon同步服务] 开始同步财务应计数据 - 店铺: {self.shop.id}, 日期: {date_from}~{date_to}"
        )

        date_from, date_to = await self._get_date_range(date_from, date_to)

        start_date = datetime.strptime(date_from, "%Y-%m-%d")
        end_date = datetime.strptime(date_to, "%Y-%m-%d")

        total_accruals = 0
        current_date = start_date

        # 预加载应计类型字典（type_id -> {name, description}），用于费用明细行冗余类型名称
        type_dict = await self._load_accrual_type_dict()

        try:
            async with self.client:
                while current_date <= end_date:
                    date_str = current_date.strftime("%Y-%m-%d")
                    logger.debug(f"[Ozon同步服务] 获取 {date_str} 的应计数据")

                    last_id = None
                    day_iterations = 0
                    while True:
                        day_iterations += 1
                        if day_iterations > 1000:
                            logger.warning(
                                f"[Ozon同步服务] {date_str} 应计分页达到最大迭代次数，停止当天同步"
                            )
                            break

                        response = await self.client.finance.get_accrual_by_day(
                            date=date_str, last_id=last_id
                        )
                        accruals_data = response.get("accruals", [])
                        next_last_id = response.get("last_id")

                        if not accruals_data:
                            break

                        logger.debug(
                            f"[Ozon同步服务] {date_str} 获取到 {len(accruals_data)} 条应计记录"
                        )

                        saved_accruals = (
                            await crud_ods_ozon_finance_accrual.create_many(
                                self.db,
                                items=accruals_data,
                                shop_id=self.shop.id,
                                accrual_date=date_str,
                                source_api="by-day",
                            )
                        )
                        await self.db.flush()

                        for accrual, saved_accrual in zip(
                            accruals_data, saved_accruals
                        ):
                            accrual_id = accrual.get("accrual_id")
                            if not accrual_id:
                                logger.warning(
                                    f"[Ozon同步服务] 应计记录缺少 accrual_id，跳过费用明细拆解: unit_number={accrual.get('unit_number')}"
                                )
                                continue
                            # 把该应计拆成"一条费用一行"写入统一明细表(幂等：先删后插)
                            await crud_ods_ozon_accrual_fee.replace_for_accrual(
                                self.db,
                                accrual=accrual,
                                shop_id=self.shop.id,
                                accrual_id=accrual_id,
                                accrual_date=date_str,
                                type_dict=type_dict,
                            )

                        total_accruals += len(accruals_data)

                        if not next_last_id or next_last_id == last_id:
                            break
                        last_id = next_last_id

                    # 每天提交一次
                    await self.db.commit()

                    current_date += timedelta(days=1)

                result = {
                    "status": "success",
                    "message": f"同步了 {total_accruals} 条应计记录 (ODS)",
                    "count": total_accruals,
                }
                logger.info(f"[Ozon同步服务] 财务应计数据同步完成: {result}")
                return result

        except Exception as e:
            logger.error(
                f"[Ozon同步服务] 同步财务应计数据失败: {str(e)}", exc_info=True
            )
            return {"status": "error", "message": f"同步失败: {str(e)}"}

    async def sync_products(self) -> Dict[str, Any]:
        """同步商品信息"""
        logger.info(f"[Ozon同步服务] 开始同步商品信息 - 店铺: {self.shop.id}")

        total_products = 0
        last_id = ""
        limit = 1000
        max_iterations = 1000
        iterations = 0

        try:
            async with self.client:
                category_names: Dict[ProductCategoryKey, str] = {}
                try:
                    category_response = (
                        await self.client.product.get_description_category_tree()
                    )
                    category_names = build_product_category_name_map(
                        category_response.get("result") or []
                    )
                except Exception:
                    logger.warning(
                        "[Ozon同步服务] 商品品类树同步失败，将保留已有品类名称 - 店铺: %s",
                        self.shop.id,
                        exc_info=True,
                    )

                while True:
                    iterations += 1
                    if iterations > max_iterations:
                        logger.warning(
                            f"[Ozon同步服务] 商品同步达到最大迭代次数 {max_iterations}，停止同步"
                        )
                        break

                    # 第一步：/v3/product/list 拉取商品ID分页列表
                    list_response = await self.client.product.get_product_list(
                        last_id=last_id,
                        limit=limit,
                    )
                    list_result = list_response.get("result", {}) or {}
                    list_items = list_result.get("items", []) or []
                    next_last_id = list_result.get("last_id") or ""

                    if not list_items:
                        logger.debug("[Ozon同步服务] 没有获取到商品ID列表")
                        break

                    product_ids = [
                        item.get("product_id")
                        for item in list_items
                        if item.get("product_id")
                    ]

                    # 第二步：/v3/product/info/list 按 product_id 批量拉取商品详情
                    products_data = []
                    if product_ids:
                        info_response = await self.client.product.get_product_info_list(
                            product_ids=product_ids,
                        )
                        products_data = enrich_products_with_category_names(
                            info_response.get("items", []) or [],
                            category_names,
                        )

                    if not products_data:
                        logger.debug("[Ozon同步服务] 没有获取到商品详情数据")
                        if not next_last_id or next_last_id == last_id:
                            break
                        last_id = next_last_id
                        continue

                    saved_products = await crud_ods_ozon_product.create_many(
                        self.db,
                        items=products_data,
                        shop_id=self.shop.id,
                    )
                    await self.db.commit()

                    total_products += len(saved_products)
                    logger.debug(
                        f"[Ozon同步服务] 本页同步商品 {len(saved_products)} 个，累计: {total_products}, last_id={next_last_id}"
                    )

                    if not next_last_id or next_last_id == last_id:
                        break

                    last_id = next_last_id

                dwd_result = await crud_dwd_ozon_return_detail.upsert_from_ods(
                    self.db,
                    shop_id=self.shop.id,
                )
                await self.db.commit()

                result = {
                    "status": "success",
                    "message": f"同步了 {total_products} 个商品，并刷新退货DWD",
                    "count": total_products,
                    "return_dwd": dwd_result,
                }
                logger.info(f"[Ozon同步服务] 商品信息同步完成: {result}")
                return result

        except Exception as e:
            logger.error(f"[Ozon同步服务] 同步商品信息失败: {str(e)}", exc_info=True)
            return {"status": "error", "message": f"同步失败: {str(e)}"}

    async def sync_realization_report(
        self, year: Optional[int] = None, month: Optional[int] = None
    ) -> Dict[str, Any]:
        """同步销售实现报告"""
        logger.info(
            f"[Ozon同步服务] 开始同步销售实现报告 - 店铺: {self.shop.id}, 年月: {year}年{month}月"
        )

        if not year:
            year = now_platform().year
        if not month:
            month = now_platform().month

        try:
            async with self.client:
                response = await self.client.finance.get_realization_report(
                    year=year, month=month
                )

                result_data = response.get("result", {})

                if not result_data:
                    logger.debug(f"[Ozon同步服务] 没有获取到销售实现报告数据")
                    return {
                        "status": "success",
                        "message": "没有数据",
                        "count": 0,
                    }

                header_data = {
                    "header": result_data,
                }

                header = (
                    await crud_ods_ozon_finance_realization_header.create_or_update(
                        self.db,
                        item=header_data,
                        shop_id=self.shop.id,
                    )
                )
                await self.db.flush()

                rows = result_data.get("rows", [])
                row_count = 0
                if rows:
                    await crud_ods_ozon_finance_realization_row.create_many_for_header(
                        self.db,
                        items=rows,
                        shop_id=self.shop.id,
                        header_id=header.id if header else 0,
                    )
                    await self.db.flush()
                    row_count = len(rows)

                await self.db.commit()

                result = {
                    "status": "success",
                    "message": f"同步了 1 个报告头和 {row_count} 条报告行 (ODS)",
                    "count": row_count,
                    "header_count": 1,
                }
                logger.info(f"[Ozon同步服务] 销售实现报告同步完成: {result}")
                return result

        except Exception as e:
            logger.error(
                f"[Ozon同步服务] 同步销售实现报告失败: {str(e)}", exc_info=True
            )
            return {"status": "error", "message": f"同步失败: {str(e)}"}

    async def sync_adverts(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        同步广告数据（Ozon Performance API）

        步骤:
        1. 拉取广告活动列表并 upsert 到 ods_ozon_adv_campaigns
        2. 拉取按天统计并 upsert 到 ods_ozon_adv_stats_daily

        说明: Performance API 走独立 OAuth 鉴权，凭证在全局配置中；未配置时跳过。
        """
        logger.info(
            f"[Ozon同步服务] 开始同步广告数据 - 店铺: {self.shop.id}, 日期: {date_from}~{date_to}"
        )

        if not self.client.performance:
            logger.warning("[Ozon同步服务] 未配置 Performance API 凭证，跳过广告同步")
            return {"status": "skipped", "message": "未配置 Performance API 凭证"}

        date_from, date_to = await self._get_date_range(date_from, date_to)

        try:
            perf = self.client.performance
            async with perf:
                # 1. 广告活动列表
                campaign_resp = await perf.get_campaigns()
                campaigns = campaign_resp.get("list", []) or []
                saved_campaigns = []
                if campaigns:
                    saved_campaigns = await crud_ods_ozon_adv_campaign.create_many(
                        self.db, items=campaigns, shop_id=self.shop.id
                    )
                    await self.db.commit()

                # 2. 按天统计（不传 campaignId 则返回全部活动）
                stats_resp = await perf.get_statistics_daily(
                    date_from=date_from, date_to=date_to
                )
                stat_rows = stats_resp.get("rows", []) or []
                saved_stats = []
                if stat_rows:
                    saved_stats = await crud_ods_ozon_adv_stat_daily.create_many(
                        self.db, items=stat_rows, shop_id=self.shop.id
                    )
                    await self.db.commit()

            result = {
                "status": "success",
                "message": f"同步了 {len(saved_campaigns)} 个广告活动, {len(saved_stats)} 条日统计 (ODS)",
                "campaigns": len(saved_campaigns),
                "stats": len(saved_stats),
            }
            logger.info(f"[Ozon同步服务] 广告数据同步完成: {result}")
            return result

        except Exception as e:
            logger.error(f"[Ozon同步服务] 同步广告数据失败: {str(e)}", exc_info=True)
            return {"status": "error", "message": f"同步失败: {str(e)}"}

    # Ozon Performance API 同一时刻仅允许 1 个活跃报表任务，逐个活动串行提交会
    # 反复争抢额度并触发限流。SubmitRequest 的 campaigns 支持一次提交多个活动，
    # 下载接口(DownloadStatistics)返回按 campaignId 分组的结构，天然支持批量。
    # 这里批量提交(默认每批 10 个)，批失败则回退到该批内逐个重试，兼顾速度与健壮性。
    ADV_REPORT_BATCH_SIZE = 10

    @staticmethod
    def _supports_product_statistics(campaign: Dict[str, Any]) -> bool:
        """Return whether a campaign supports the product statistics report.

        Ozon exposes SEARCH_PROMO/CPO campaigns in the same campaign list, but
        rejects them at ``/api/client/statistics/json``. Product-level reports
        are valid only for SKU campaigns.
        """
        return campaign.get("advObjectType", "SKU") == "SKU"

    async def _fetch_reports_batched(
        self,
        perf: Any,
        campaign_ids: List[str],
        date_from: str,
        date_to: str,
        *,
        group_by: str = "DATE",
        max_wait: float = 900.0,
        batch_size: Optional[int] = None,
    ) -> tuple[Dict[str, Any], List[str]]:
        """批量拉取多个活动的 SKU 报表，返回 (合并结果, 失败活动ID列表)。

        - 合并结果形如 {"<campaignId>": {"title":..., "report": {"rows": [...]}}}
        - 批量提交失败时回退到该批内逐个提交，最大化成功活动数并隔离故障活动。
        """
        batch_size = batch_size or self.ADV_REPORT_BATCH_SIZE
        merged: Dict[str, Any] = {}
        failed: List[str] = []
        ids = [str(cid) for cid in campaign_ids if cid]

        for start in range(0, len(ids), batch_size):
            batch = ids[start : start + batch_size]
            try:
                report = await perf.fetch_statistics_report(
                    campaign_ids=batch,
                    date_from=date_from,
                    date_to=date_to,
                    group_by=group_by,
                    max_wait=max_wait,
                )
                merged.update(report or {})
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    f"[Ozon同步服务] 批量报表获取失败(批含 {len(batch)} 个活动)，"
                    f"回退逐个重试: {e}"
                )
                for cid in batch:
                    try:
                        one = await perf.fetch_statistics_report(
                            campaign_ids=[cid],
                            date_from=date_from,
                            date_to=date_to,
                            group_by=group_by,
                            max_wait=max_wait,
                        )
                        merged.update(one or {})
                    except Exception as e2:  # noqa: BLE001
                        logger.error(f"[Ozon同步服务] 活动 {cid} 报表获取失败: {e2}")
                        failed.append(cid)

        return merged, failed

    async def sync_advert_products(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        campaign_ids: Optional[List[str]] = None,
        only_active: bool = True,
    ) -> Dict[str, Any]:
        """
        同步 SKU 级广告明细（Performance API 异步报表）

        对每个广告活动提交异步报表任务，轮询完成后下载 SKU 级明细并入库，
        补齐 Excel《推广分析》的 SKU、加购(toCart)、CTR、DRR 等指标。

        注意: 异步报表在 Ozon 侧排队，单个活动可能耗时数分钟，此方法为耗时任务，
        建议低频（每天/手动）触发。未配置 Performance 凭证时跳过。

        Args:
            date_from: 起始日期 (YYYY-MM-DD)
            date_to: 结束日期 (YYYY-MM-DD)
            campaign_ids: 指定活动ID列表；为空则同步全部（默认仅活跃活动）
            only_active: 为空 campaign_ids 时是否仅取运行中的活动
        """
        logger.info(
            f"[Ozon同步服务] 开始同步广告SKU明细 - 店铺: {self.shop.id}, 日期: {date_from}~{date_to}"
        )

        if not self.client.performance:
            logger.warning(
                "[Ozon同步服务] 未配置 Performance API 凭证，跳过广告SKU明细同步"
            )
            return {"status": "skipped", "message": "未配置 Performance API 凭证"}

        date_from, date_to = await self._get_date_range(date_from, date_to)

        try:
            perf = self.client.performance
            total_rows = 0
            processed_campaigns = 0
            failed_campaigns = []
            async with perf:
                # 确定要同步的活动列表
                target_ids = campaign_ids
                if not target_ids:
                    campaign_resp = await perf.get_campaigns()
                    campaigns = campaign_resp.get("list", []) or []
                    if only_active:
                        target_ids = [
                            c.get("id")
                            for c in campaigns
                            if c.get("state") == "CAMPAIGN_STATE_RUNNING"
                            and self._supports_product_statistics(c)
                            and c.get("id")
                        ]
                    else:
                        target_ids = [
                            c.get("id")
                            for c in campaigns
                            if self._supports_product_statistics(c) and c.get("id")
                        ]

                logger.info(f"[Ozon同步服务] 待同步SKU明细的活动数: {len(target_ids)}")

                # 批量提交报表(批失败回退逐个)，减少对唯一活跃报表额度的争抢
                # max_wait 调大：单活动报表在 Ozon 侧偶尔处理 >300s
                report, failed_campaigns = await self._fetch_reports_batched(
                    perf,
                    target_ids,
                    date_from=date_from,
                    date_to=date_to,
                    group_by="DATE",
                    max_wait=900.0,
                )

                # 报表结构: {"<campaignId>": {"title":..., "report": {"rows": [...]}}}
                for campaign_id in target_ids:
                    if str(campaign_id) in failed_campaigns:
                        continue
                    campaign_block = report.get(str(campaign_id)) or {}
                    rows = (campaign_block.get("report") or {}).get("rows", []) or []
                    if rows:
                        await crud_ods_ozon_adv_stat_product_daily.create_many(
                            self.db,
                            items=rows,
                            shop_id=self.shop.id,
                            campaign_id=str(campaign_id),
                        )
                        await self.db.commit()
                        total_rows += len(rows)
                    processed_campaigns += 1

            result = {
                "status": "success",
                "message": f"同步了 {processed_campaigns} 个活动的 {total_rows} 条SKU明细 (ODS)",
                "campaigns": processed_campaigns,
                "rows": total_rows,
                "failed_campaigns": failed_campaigns,
            }
            dwd_result = await self.sync_advert_efficiency_dwd(date_from, date_to)
            result["advert_efficiency_dwd"] = dwd_result
            if dwd_result.get("status") != "success":
                result["status"] = "error"
                dwd_message = dwd_result.get("message", "未知错误")
                result["message"] += f"；广告效率DWD构建失败: {dwd_message}"
            logger.info(f"[Ozon同步服务] 广告SKU明细同步完成: {result}")
            return result

        except Exception as e:
            logger.error(f"[Ozon同步服务] 同步广告SKU明细失败: {str(e)}", exc_info=True)
            return {"status": "error", "message": f"同步失败: {str(e)}"}

    async def sync_advert_products_hourly(self) -> Dict[str, Any]:
        """
        同步 SKU 级广告明细（小时维度）

        口径参照 Wildberries 广告小时统计（sync_advert_stats_hourly）:
        Ozon Performance API 仅提供「按天累计」数据，无原生小时接口。故:
        1. 确定结算的日期与小时（跨天边界：00:00-00:10 结算昨天 23:00）
        2. 对活跃活动提交异步报表，拉取当天(累计)的 SKU 级明细
        3. 查询当天已写入的小时累计（排除当前小时）
        4. 以「当天累计 - 已写入累计」计算当前小时增量（负数置 0）
        5. 幂等写入小时表 ods_ozon_adv_stats_product_hourly

        说明: 累加型指标(views/clicks/toCart/moneySpent/orders/ordersMoney/models/
        modelsMoney/productGmv)做增量；派生/快照型指标(price/ctr/avgBid/drr/generalDrr)
        直接保留当天累计快照值。异步报表耗时，故此任务按小时低频触发。
        """
        logger.info(f"[Ozon同步服务] 开始同步广告SKU小时明细 - 店铺: {self.shop.id}")

        if not self.client.performance:
            logger.warning(
                "[Ozon同步服务] 未配置 Performance API 凭证，跳过广告SKU小时明细同步"
            )
            return {"status": "skipped", "message": "未配置 Performance API 凭证"}

        # 按平台业务时区(莫斯科)判定当前小时/日期
        now = now_platform()
        # 跨天边界处理：00:00-00:10 执行时，结算昨天的 23:00 数据
        if now.hour == 0 and now.minute < 10:
            stat_date = (now - timedelta(days=1)).date()
            stat_hour = 23
        else:
            stat_date = now.date()
            stat_hour = now.hour
        day_str = stat_date.strftime("%Y-%m-%d")

        # 累加型指标（做增量计算的字段）
        cumulative_fields = [
            "views",
            "clicks",
            "to_cart",
            "money_spent",
            "orders",
            "orders_money",
            "models",
            "models_money",
            "product_gmv",
        ]

        try:
            perf = self.client.performance
            total_rows = 0
            processed_campaigns = 0
            failed_campaigns: List[str] = []

            async with perf:
                # 1. 确定活跃活动列表
                campaign_resp = await perf.get_campaigns()
                campaigns = campaign_resp.get("list", []) or []
                target_ids = [
                    c.get("id")
                    for c in campaigns
                    if c.get("state") == "CAMPAIGN_STATE_RUNNING"
                    and self._supports_product_statistics(c)
                    and c.get("id")
                ]

                if not target_ids:
                    return {
                        "status": "success",
                        "message": "没有运行中的广告活动",
                        "count": 0,
                    }

                logger.info(
                    f"[Ozon同步服务] 待同步SKU小时明细的活动数: {len(target_ids)}"
                )

                # 2. 查询当天已写入的小时累计（排除当前小时），一次查询覆盖全部活动
                hourly_sums = await crud_ods_ozon_adv_stat_product_hourly.get_hourly_sum_before_hour(
                    self.db, self.shop.id, stat_date, stat_hour
                )

                # 批量提交报表(批失败回退逐个)，减少对唯一活跃报表额度的争抢
                report, failed_campaigns = await self._fetch_reports_batched(
                    perf,
                    target_ids,
                    date_from=day_str,
                    date_to=day_str,
                    group_by="DATE",
                )

                for campaign_id in target_ids:
                    if str(campaign_id) in failed_campaigns:
                        continue
                    campaign_block = report.get(str(campaign_id)) or {}
                    rows = (campaign_block.get("report") or {}).get("rows", []) or []
                    if not rows:
                        processed_campaigns += 1
                        continue

                    # 3-4. 展平并计算当前小时增量
                    hourly_records = []
                    for row in rows:
                        record = crud_ods_ozon_adv_stat_product_hourly.extract_row(
                            row, self.shop.id, str(campaign_id)
                        )
                        sku = record.get("sku")
                        if sku is None or record.get("stat_date") is None:
                            continue

                        written = hourly_sums.get((str(campaign_id), sku), {})
                        has_delta = False
                        for field in cumulative_fields:
                            cumulative = record.get(field) or 0
                            delta = cumulative - (written.get(field) or 0)
                            if delta < 0:
                                delta = 0
                            record[field] = delta
                            if delta:
                                has_delta = True

                        # 跳过增量全为 0 的记录
                        if has_delta:
                            hourly_records.append(record)

                    # 5. 幂等写入
                    if hourly_records:
                        written_count = (
                            await crud_ods_ozon_adv_stat_product_hourly.upsert_many(
                                self.db,
                                records=hourly_records,
                                shop_id=self.shop.id,
                                stat_date=stat_date,
                                stat_hour=stat_hour,
                            )
                        )
                        total_rows += written_count
                    processed_campaigns += 1

            result = {
                "status": "success",
                "message": (
                    f"同步了 {processed_campaigns} 个活动的 {total_rows} 条SKU小时明细 (ODS), "
                    f"日期: {day_str}, 小时: {stat_hour}"
                ),
                "campaigns": processed_campaigns,
                "count": total_rows,
                "failed_campaigns": failed_campaigns,
            }
            logger.info(f"[Ozon同步服务] 广告SKU小时明细同步完成: {result}")
            return result

        except Exception as e:
            logger.error(
                f"[Ozon同步服务] 同步广告SKU小时明细失败: {str(e)}", exc_info=True
            )
            return {"status": "error", "message": f"同步失败: {str(e)}"}

    async def sync_order_dwd(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """仅使用现有 ODS 数据重建当前店铺的统一订单 DWD。"""
        del date_from, date_to
        try:
            dwd_result = await crud_dwd_ozon_order_detail.upsert_from_ods(
                self.db,
                shop_id=self.shop.id,
            )
            await self.db.commit()
            translation_result = await self._translate_order_dwd_fields()
            return {
                "status": "success",
                "message": f"构建了 {dwd_result['source_count']} 条订单商品DWD明细",
                "count": dwd_result["source_count"],
                "order_dwd": dwd_result,
                "translation": translation_result,
            }
        except Exception as exc:
            await self.db.rollback()
            logger.error("[Ozon同步服务] 构建订单DWD失败: %s", exc, exc_info=True)
            return {"status": "error", "message": f"构建失败: {exc}"}

    async def sync_customer_voice_dwd(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """使用现有评价和商品 ODS 构建客户声音 DWD，并补齐中文翻译。"""
        del date_from, date_to
        try:
            dwd_result = await crud_dwd_ozon_customer_voice_detail.upsert_from_ods(
                self.db, shop_id=self.shop.id
            )
            translation_result = (
                await ozon_customer_voice_translation_service.translate_all_missing(
                    self.db,
                    shop_id=self.shop.id,
                    batch_size=200,
                    max_batches=10,
                )
            )
            return {
                "status": "success",
                "message": f"构建了 {dwd_result['source_count']} 条客户声音DWD明细",
                "count": dwd_result["source_count"],
                "customer_voice_dwd": dwd_result,
                "translation": translation_result,
            }
        except Exception as exc:
            await self.db.rollback()
            logger.error("[Ozon同步服务] 构建客户声音DWD失败: %s", exc, exc_info=True)
            return {"status": "error", "message": f"构建失败: {exc}"}

    async def sync_advert_efficiency_dwd(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """使用现有广告、商品 ODS 构建广告效率 SKU 日 DWD。"""
        try:
            parsed_from = date.fromisoformat(date_from) if date_from else None
            parsed_to = date.fromisoformat(date_to) if date_to else None
            dwd_result = await crud_dwd_ozon_advert_efficiency_detail.upsert_from_ods(
                self.db,
                shop_id=self.shop.id,
                date_from=parsed_from,
                date_to=parsed_to,
            )
            translation_result = (
                await ozon_advert_efficiency_translation_service.translate_all_missing(
                    self.db,
                    shop_id=self.shop.id,
                    batch_size=200,
                    max_batches=10,
                )
            )
            return {
                "status": "success",
                "message": f"构建了 {dwd_result['source_count']} 条广告效率DWD明细",
                "count": dwd_result["source_count"],
                "advert_efficiency_dwd": dwd_result,
                "translation": translation_result,
            }
        except Exception as exc:
            await self.db.rollback()
            logger.error("[Ozon同步服务] 构建广告效率DWD失败: %s", exc, exc_info=True)
            return {"status": "error", "message": f"构建失败: {exc}"}

    async def sync_sales_funnel_dwd(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """使用经营分析和商品 ODS 构建 Ozon 原生销售漏斗 DWD。"""
        try:
            parsed_from = date.fromisoformat(date_from) if date_from else None
            parsed_to = date.fromisoformat(date_to) if date_to else None
            dwd_result = await crud_dwd_ozon_sales_funnel_detail.upsert_from_ods(
                self.db,
                shop_id=self.shop.id,
                date_from=parsed_from,
                date_to=parsed_to,
            )
            translation_result = (
                await ozon_sales_funnel_translation_service.translate_all_missing(
                    self.db,
                    shop_id=self.shop.id,
                    batch_size=200,
                    max_batches=10,
                )
            )
            return {
                "status": "success",
                "message": f"构建了 {dwd_result['source_count']} 条销售漏斗DWD明细",
                "count": dwd_result["source_count"],
                "sales_funnel_dwd": dwd_result,
                "translation": translation_result,
            }
        except Exception as exc:
            await self.db.rollback()
            logger.error("[Ozon同步服务] 构建销售漏斗DWD失败: %s", exc, exc_info=True)
            return {"status": "error", "message": f"构建失败: {exc}"}

    async def sync_product_name_translations(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Translate and cache missing product names for the current shop."""
        del date_from, date_to
        try:
            translation_result = (
                await ozon_product_translation_service.translate_all_missing(
                    self.db,
                    shop_id=self.shop.id,
                    batch_size=500,
                    max_batches=10,
                )
            )
            await self.db.commit()
            return {
                "status": "success",
                "message": (
                    "处理了 "
                    f"{translation_result['unique_products']} 个Ozon唯一商品名称"
                ),
                "count": translation_result["updated_dwd_rows"],
                "translation": translation_result,
            }
        except Exception as exc:
            await self.db.rollback()
            logger.error("[Ozon同步服务] 商品名称翻译失败: %s", exc, exc_info=True)
            return {"status": "error", "message": f"翻译失败: {exc}"}

    async def _sync_posting_report_type(
        self,
        *,
        fulfillment_type: str,
        period_from: datetime,
        period_to: datetime,
    ) -> tuple[int, str]:
        """Generate, download and persist one FBS/FBO shipment report."""
        from urllib.parse import urlparse

        processed_at_from = period_from.strftime("%Y-%m-%dT%H:%M:%SZ")
        processed_at_to = period_to.strftime("%Y-%m-%dT%H:%M:%SZ")
        created = await self.client.report.create_postings_report(
            processed_at_from=processed_at_from,
            processed_at_to=processed_at_to,
            fulfillment_type=fulfillment_type,
            language="RU",
        )
        report_code = (created.get("result") or {}).get("code") or created.get("code")
        if not report_code:
            raise ValueError("Ozon发货报表创建响应缺少任务编码")

        task = await crud_ods_ozon_posting_report_task.create_or_update(
            self.db,
            shop_id=self.shop.id,
            report_code=str(report_code),
            fulfillment_type=fulfillment_type,
            period_from=period_from,
            period_to=period_to,
            status="WAITING",
            report_params={
                "processed_at_from": processed_at_from,
                "processed_at_to": processed_at_to,
                "fulfillment_type": fulfillment_type,
            },
            response_data=created,
        )
        await self.db.commit()

        info_result: Dict[str, Any] = {}
        for _ in range(36):
            info = await self.client.report.get_report_info(str(report_code))
            info_result = info.get("result") or {}
            status = str(info_result.get("status") or "").upper()
            if status in {"SUCCESS", "FAILED"}:
                break
            await asyncio.sleep(5)
        else:
            raise TimeoutError("Ozon发货报表生成超过180秒")

        status = str(info_result.get("status") or "").upper()
        file_url = info_result.get("file")
        safe_response = {
            key: value for key, value in info_result.items() if key != "file"
        }
        file_name = None
        if isinstance(file_url, str):
            file_name = urlparse(file_url).path.rsplit("/", 1)[-1] or None

        if status != "SUCCESS" or not file_url:
            await crud_ods_ozon_posting_report_task.create_or_update(
                self.db,
                shop_id=self.shop.id,
                report_code=str(report_code),
                fulfillment_type=fulfillment_type,
                period_from=period_from,
                period_to=period_to,
                status=status or "FAILED",
                report_type=info_result.get("report_type"),
                file_name=file_name,
                error_message=info_result.get("error"),
                report_params=info_result.get("params"),
                response_data=safe_response,
            )
            await self.db.commit()
            raise RuntimeError(
                f"Ozon {fulfillment_type} 发货报表生成失败: "
                f"{info_result.get('error') or status}"
            )

        content = await self.client.report.download_report(file_url)
        rows = crud_ods_ozon_posting_report_row.parse_csv(content)
        row_count = await crud_ods_ozon_posting_report_row.upsert_many(
            self.db,
            rows=rows,
            shop_id=self.shop.id,
            task_id=task.id,
            report_code=str(report_code),
            fulfillment_type=fulfillment_type,
        )
        await crud_ods_ozon_posting_report_task.create_or_update(
            self.db,
            shop_id=self.shop.id,
            report_code=str(report_code),
            fulfillment_type=fulfillment_type,
            period_from=period_from,
            period_to=period_to,
            status="SUCCESS",
            report_type=info_result.get("report_type"),
            file_name=file_name,
            report_params=info_result.get("params"),
            response_data=safe_response,
            row_count=row_count,
            completed_at=now_platform().replace(tzinfo=None),
        )
        await self.db.commit()
        return row_count, str(report_code)

    @staticmethod
    def _posting_from_detail(response: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize the response shape used by Ozon posting detail APIs."""
        posting = response.get("result") or response.get("posting") or response
        return posting if isinstance(posting, dict) else {}

    async def _persist_posting_detail(
        self, *, fulfillment_type: str, response: Dict[str, Any]
    ) -> bool:
        """Persist one posting detail into the same ordinary ODS tables."""
        posting = self._posting_from_detail(response)
        posting_number = posting.get("posting_number")
        if not posting_number:
            return False

        products = posting.get("products") or []
        if fulfillment_type == "FBS":
            await crud_ods_ozon_fbs_posting.create_many(
                self.db, items=[posting], shop_id=self.shop.id
            )
            if products:
                await crud_ods_ozon_fbs_posting_product.create_many_for_posting(
                    self.db,
                    products=products,
                    shop_id=self.shop.id,
                    posting_number=posting_number,
                )
            delivery_method = posting.get("delivery_method") or {}
            if delivery_method:
                await crud_ods_ozon_fbs_posting_delivery.create_or_update_for_posting(
                    self.db,
                    delivery_method=delivery_method,
                    shop_id=self.shop.id,
                    posting_number=posting_number,
                )
            cancellation = posting.get("cancellation") or {}
            if cancellation:
                await crud_ods_ozon_fbs_posting_cancellation.create_or_update_for_posting(
                    self.db,
                    cancellation=cancellation,
                    shop_id=self.shop.id,
                    posting_number=posting_number,
                )
        else:
            await crud_ods_ozon_fbo_posting.create_many(
                self.db, items=[posting], shop_id=self.shop.id
            )
            if products:
                await crud_ods_ozon_fbo_posting_product.create_many(
                    self.db,
                    items=products,
                    shop_id=self.shop.id,
                    posting_number=posting_number,
                )
        await self.db.flush()
        return bool(products)

    async def _hydrate_unmatched_report_rows(
        self, *, report_codes: set[str]
    ) -> Dict[str, int]:
        """Fetch ordinary posting details for current report rows still unmatched."""
        unmatched = await crud_ods_ozon_posting_report_row.list_unmatched(
            self.db,
            shop_id=self.shop.id,
            report_codes=report_codes,
        )
        posting_keys = {(row.fulfillment_type, row.posting_number) for row in unmatched}
        hydrated = 0
        failed = 0
        for fulfillment_type, posting_number in posting_keys:
            try:
                if fulfillment_type == "FBS":
                    response = await self.client.posting.get_fbs_posting(posting_number)
                else:
                    response = await self.client.posting.get_fbo_posting(posting_number)
                if await self._persist_posting_detail(
                    fulfillment_type=fulfillment_type,
                    response=response,
                ):
                    hydrated += 1
                else:
                    failed += 1
            except Exception:
                failed += 1
                logger.warning(
                    "[Ozon同步服务] 单订单详情补拉失败，履约类型=%s；"
                    "订单标识不写入日志",
                    fulfillment_type,
                )
        await self.db.commit()
        remaining = await crud_ods_ozon_posting_report_row.list_unmatched(
            self.db,
            shop_id=self.shop.id,
            report_codes=report_codes,
        )
        return {
            "attempted_postings": len(posting_keys),
            "hydrated_postings": hydrated,
            "failed_postings": failed,
            "remaining_rows": len(remaining),
        }

    async def sync_posting_reports(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sync ordinary postings first, then overlay matched shipment reports."""
        date_from, date_to = await self._get_date_range(date_from, date_to)
        period_from = datetime.strptime(date_from, "%Y-%m-%d")
        period_to = datetime.strptime(date_to, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59
        )
        try:
            ordinary_results: Dict[str, Any] = {}
            for fulfillment_type, sync_function in (
                ("FBS", self.sync_postings),
                ("FBO", self.sync_fbo_postings),
            ):
                result = await sync_function(date_from, date_to)
                ordinary_results[fulfillment_type] = result
                if result.get("status") != "success":
                    raise RuntimeError(
                        f"{fulfillment_type}普通订单ODS同步失败: "
                        f"{result.get('message') or '未知错误'}"
                    )

            counts: Dict[str, int] = {}
            report_codes: set[str] = set()
            async with self.client:
                for fulfillment_type in ("FBS", "FBO"):
                    row_count, report_code = await self._sync_posting_report_type(
                        fulfillment_type=fulfillment_type,
                        period_from=period_from,
                        period_to=period_to,
                    )
                    counts[fulfillment_type] = row_count
                    report_codes.add(report_code)
                hydration = await self._hydrate_unmatched_report_rows(
                    report_codes=report_codes
                )
            dwd_result = await crud_dwd_ozon_order_detail.upsert_from_ods(
                self.db,
                shop_id=self.shop.id,
            )
            await self.db.commit()
            translation_result = await self._translate_order_dwd_fields()
            total = sum(counts.values())
            return {
                "status": "success",
                "message": f"同步了 {total} 条Ozon发货报表明细并刷新订单DWD",
                "count": total,
                "counts": counts,
                "ordinary_orders": ordinary_results,
                "hydration": hydration,
                "order_dwd": dwd_result,
                "translation": translation_result,
            }
        except Exception as exc:
            await self.db.rollback()
            logger.error("[Ozon同步服务] 同步发货报表失败: %s", exc, exc_info=True)
            return {"status": "error", "message": f"同步失败: {exc}"}

    async def _fetch_analytics_metric_group(
        self,
        *,
        date_from: str,
        date_to: str,
        metrics: List[str],
        sort_key: str,
    ) -> Dict[str, Any]:
        """Fetch and validate every offset page for one fixed metric group."""
        limit = 1000
        offset = 0
        page_count = 0
        max_pages = 1000
        all_rows: Dict[AnalyticsRowKey, Dict[str, Any]] = {}
        raw_totals: Optional[List[Any]] = None
        totals: Optional[Dict[str, Any]] = None
        totals_timestamp: Optional[datetime] = None

        while True:
            page_count += 1
            if page_count > max_pages:
                raise RuntimeError("Ozon analytics pagination exceeded 1000 pages")
            response = await self.client.analytics.get_analytics_data(
                date_from=date_from,
                date_to=date_to,
                metrics=metrics,
                sort_key=sort_key,
                limit=limit,
                offset=offset,
            )
            parsed = parse_ozon_analytics_page(response, metrics)
            if raw_totals is None:
                raw_totals = parsed["raw_totals"]
                totals = parsed["totals"]
                totals_timestamp = parsed["api_timestamp"]
            elif raw_totals != parsed["raw_totals"]:
                raise ValueError("Ozon analytics totals changed between pages")

            for key, item in parsed["rows"].items():
                if key in all_rows:
                    raise ValueError(
                        f"Ozon analytics pagination returned duplicate key: {key}"
                    )
                all_rows[key] = item

            if parsed["row_count"] < limit:
                break
            offset += limit

        return {
            "rows": all_rows,
            "totals": totals or {},
            "raw_totals": raw_totals or [],
            "api_timestamp": totals_timestamp,
            "page_count": page_count,
        }

    async def sync_analytics_data(self, date_from: str, date_to: str) -> Dict[str, Any]:
        """Synchronize all 18 analytics metrics at shop x SKU x day grain."""
        shop_id = self.shop.id
        logger.info(
            "[Ozon同步服务] 开始同步经营分析 - 店铺: %s, 日期: %s ~ %s",
            shop_id,
            date_from,
            date_to,
        )
        try:
            window_start = date.fromisoformat(date_from)
            window_end = date.fromisoformat(date_to)
            if window_start > window_end:
                raise ValueError("analytics date_from must not be after date_to")

            async with self.client:
                core = await self._fetch_analytics_metric_group(
                    date_from=date_from,
                    date_to=date_to,
                    metrics=OZON_ANALYTICS_CORE_METRICS,
                    sort_key="revenue",
                )
                outcome_unavailable = False
                try:
                    outcome = await self._fetch_analytics_metric_group(
                        date_from=date_from,
                        date_to=date_to,
                        metrics=OZON_ANALYTICS_OUTCOME_METRICS,
                        sort_key="delivered_units",
                    )
                except httpx.HTTPStatusError as exc:
                    response = exc.response
                    if not (
                        response.status_code == 400
                        and "deprecated metrics used" in response.text.lower()
                    ):
                        raise
                    # Some non-Premium shops accept the core request but reject
                    # this entire metric group. Keep the valid core rows and
                    # represent unavailable outcome fields as NULL, never zero.
                    logger.warning(
                        "[Ozon同步服务] 店铺 %s 不支持结果指标组，仅保存已返回的基础指标",
                        shop_id,
                    )
                    outcome_unavailable = True
                    outcome = {
                        "rows": {},
                        "totals": {},
                        "raw_totals": [],
                        "api_timestamp": None,
                        "page_count": 0,
                    }

            records: List[Dict[str, Any]] = []
            for key in sorted(set(core["rows"]) | set(outcome["rows"])):
                core_row = core["rows"].get(key)
                outcome_row = outcome["rows"].get(key)
                source_row = core_row or outcome_row
                metric_values = {
                    **(core_row["metrics"] if core_row else {}),
                    **(outcome_row["metrics"] if outcome_row else {}),
                }
                records.append(
                    {
                        "sku": source_row["sku"],
                        "sku_name": source_row.get("sku_name"),
                        "stat_date": source_row["stat_date"],
                        "metrics": metric_values,
                        "requested_metrics_core": list(OZON_ANALYTICS_CORE_METRICS),
                        "requested_metrics_outcome": list(
                            OZON_ANALYTICS_OUTCOME_METRICS
                        ),
                        "row_data_core": (
                            core_row.get("row_data") if core_row else None
                        ),
                        "row_data_outcome": (
                            outcome_row.get("row_data") if outcome_row else None
                        ),
                        "has_core_metrics": core_row is not None,
                        "has_outcome_metrics": outcome_row is not None,
                        "api_timestamp_core": (
                            core_row.get("api_timestamp") if core_row else None
                        ),
                        "api_timestamp_outcome": (
                            outcome_row.get("api_timestamp") if outcome_row else None
                        ),
                    }
                )

            saved = await crud_ods_ozon_analytics_data_daily.upsert_many(
                self.db,
                shop_id=shop_id,
                date_from=window_start,
                date_to=window_end,
                items=records,
            )
            totals_metrics = {**core["totals"], **outcome["totals"]}
            await crud_ods_ozon_analytics_totals_window.upsert(
                self.db,
                shop_id=shop_id,
                date_from=window_start,
                date_to=window_end,
                item={
                    "metrics": totals_metrics,
                    "requested_metrics_core": list(OZON_ANALYTICS_CORE_METRICS),
                    "requested_metrics_outcome": list(OZON_ANALYTICS_OUTCOME_METRICS),
                    "raw_totals_core": core["raw_totals"],
                    "raw_totals_outcome": outcome["raw_totals"],
                    "api_timestamp_core": core["api_timestamp"],
                    "api_timestamp_outcome": outcome["api_timestamp"],
                },
            )
            await self.db.commit()
            dwd_result = await self.sync_sales_funnel_dwd(date_from, date_to)
            if dwd_result.get("status") != "success":
                raise RuntimeError(
                    f"销售漏斗DWD构建失败: {dwd_result.get('message', 'unknown error')}"
                )
            result = {
                "status": "success",
                "count": len(saved),
                "core_pages": core["page_count"],
                "outcome_pages": outcome["page_count"],
                "outcome_metrics_unavailable": outcome_unavailable,
                "date_from": date_from,
                "date_to": date_to,
                "sales_funnel_dwd": dwd_result,
            }
            logger.info(
                "[Ozon同步服务] 经营分析同步完成 - 店铺: %s, 结果: %s",
                shop_id,
                result,
            )
            return result
        except Exception as exc:
            await self.db.rollback()
            logger.error(
                "[Ozon同步服务] 经营分析同步失败 - 店铺: %s, 错误: %s",
                shop_id,
                exc,
                exc_info=True,
            )
            return {"status": "error", "message": f"同步失败: {exc}"}

    async def sync_all(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sync_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """同步所有数据"""
        logger.info(
            f"[Ozon同步服务] 开始全量同步 - 店铺: {self.shop.id}, 类型: {sync_types}"
        )

        if not sync_types:
            sync_types = [
                "accrual_types",
                "postings",
                "fbo_postings",
                "returns",
                "products",
                "reviews",
                "adverts",
                "finance_accruals",
                "realization_report",
            ]

        results: Dict[str, Any] = {
            "status": "success",
            "results": {},
        }

        sync_functions = {
            "accrual_types": self.sync_accrual_types,
            "postings": self.sync_postings,
            "fbo_postings": self.sync_fbo_postings,
            "order_dwd": self.sync_order_dwd,
            "customer_voice_dwd": self.sync_customer_voice_dwd,
            "advert_efficiency_dwd": self.sync_advert_efficiency_dwd,
            "sales_funnel_dwd": self.sync_sales_funnel_dwd,
            "product_name_translation": self.sync_product_name_translations,
            "postings_report": self.sync_posting_reports,
            "returns": self.sync_returns,
            "reviews": self.sync_reviews,
            "products": self.sync_products,
            "adverts": self.sync_adverts,
            "advert_products": self.sync_advert_products,
            "analytics_data": self.sync_analytics_data,
            "finance_accruals": self.sync_finance_accruals,
            "realization_report": self.sync_realization_report,
        }

        for sync_type in sync_types:
            if sync_type in sync_functions:
                logger.info(f"[Ozon同步服务] 执行同步类型: {sync_type}")
                if sync_type in ["realization_report", "accrual_types", "products"]:
                    result = await sync_functions[sync_type]()
                else:
                    result = await sync_functions[sync_type](date_from, date_to)
                results["results"][sync_type] = result

        await self.db.commit()

        logger.info(f"[Ozon同步服务] 全量同步完成: {results}")
        return results
