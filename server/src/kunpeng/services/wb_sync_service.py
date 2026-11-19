"""
Wildberries 数据同步服务（简化版 - ODS 层）
"""

import asyncio
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.clients.wildberries import WildberriesClient
from kunpeng.config import settings
from kunpeng.crud.dwd import (
    crud_dwd_wb_order_detail,
    crud_dwd_wb_order_statistics_detail,
    crud_dwd_wb_return_detail,
    crud_dwd_wb_voc_feedback_detail,
    crud_dwd_wb_voc_question_detail,
)
from kunpeng.crud.ods.wildberries.chat_events import parse_chat_event_datetime
from kunpeng.crud.ods.wildberries.feedback_pins import parse_feedback_pin_datetime
from kunpeng.crud.ods.wildberries.return_claims import parse_claim_datetime
from kunpeng.crud.ods.wildberries.supplies import parse_supply_datetime
from kunpeng.utils.timezone import now_platform, platform_tz

logger = logging.getLogger(__name__)
from kunpeng.crud.ods import (
    crud_ods_wb_advert,
    crud_ods_wb_advert_budget,
    crud_ods_wb_advert_full_stat,
    crud_ods_wb_advert_product,
    crud_ods_wb_advert_stat,
    crud_ods_wb_advert_stat_hourly,
    crud_ods_wb_advert_v2,
    crud_ods_wb_balance,
    crud_ods_wb_bid_recommendation,
    crud_ods_wb_cashback,
    crud_ods_wb_chat_event,
    crud_ods_wb_fbs_supply,
    crud_ods_wb_feedback,
    crud_ods_wb_feedback_pin,
    crud_ods_wb_goods_return,
    crud_ods_wb_marketplace_order,
    crud_ods_wb_marketplace_order_status_history,
    crud_ods_wb_new_order,
    crud_ods_wb_norm_query_bid,
    crud_ods_wb_norm_query_list,
    crud_ods_wb_norm_query_minus,
    crud_ods_wb_norm_query_stat,
    crud_ods_wb_order_metadata,
    crud_ods_wb_product_search_text,
    crud_ods_wb_promotion_count,
    crud_ods_wb_question,
    crud_ods_wb_region_sale,
    crud_ods_wb_reshipment_order,
    crud_ods_wb_return_claim,
    crud_ods_wb_sales_funnel,
    crud_ods_wb_sales_report,
    crud_ods_wb_sales_report_daily,
    crud_ods_wb_sales_report_list,
    crud_ods_wb_search_cluster_stat,
    crud_ods_wb_search_cluster_stat_hourly,
    crud_ods_wb_search_traffic,
    crud_ods_wb_seller_balance,
    crud_ods_wb_supplier_order,
    crud_ods_wb_supplier_sale,
)
from kunpeng.models.shop import Shop
from kunpeng.services.wb_dwd_service import wb_dwd_service


def _get_val(data: dict, *keys):
    """从 dict 中按优先级获取第一个非 None 值"""
    for k in keys:
        if k in data and data[k] is not None:
            return data[k]
    return None


class WBSyncService:
    """Wildberries 数据同步服务"""

    def __init__(self, db: AsyncSession, shop: Shop):
        self.db = db
        self.shop = shop
        self.client = self._init_client()

    def _init_client(self) -> WildberriesClient:
        """初始化 API 客户端"""
        # TODO: 从 Shop 模型中获取不同类型的 API Key
        # 目前假设 shop.api_key 包含所有需要的 key
        api_key = str(self.shop.api_key or "")
        logger.debug(f"[同步服务] 初始化客户端 - Shop ID: {self.shop.id}")
        logger.debug(f"[同步服务] API Key 前50字符: {api_key[:50]}...")
        logger.debug(f"[同步服务] API Key 总长度: {len(api_key)}")
        return WildberriesClient(
            statistics_api_key=api_key,
            analytics_api_key=api_key,
            advert_api_key=api_key,
            feedbacks_api_key=api_key,
            buyer_chat_api_key=api_key,
            returns_api_key=api_key,
            marketplace_api_key=api_key,
            finance_api_key=api_key,
        )

    async def _safe_rollback(self) -> None:
        """安全回滚事务，忽略任何错误"""
        try:
            await self.db.rollback()
            logger.debug(f"[同步服务] 事务已回滚")
        except Exception as e:
            logger.warning(f"[同步服务] 回滚事务时出错: {e}")

    async def _get_date_range(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> tuple[str, str]:
        """获取日期范围"""
        if not date_to:
            date_to = now_platform().strftime("%Y-%m-%d")
        if not date_from:
            # 默认同步过去 7 天
            date_from = (now_platform() - timedelta(days=7)).strftime("%Y-%m-%d")
        return date_from, date_to

    async def _refresh_order_dwd(
        self,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Refresh the order DWD after any contributing ODS source changes."""
        try:
            dwd_result = await crud_dwd_wb_order_detail.upsert_from_ods(
                self.db,
                shop_id=self.shop.id,
            )
        except Exception as error:
            await self.db.rollback()
            logger.exception(
                "[同步服务] 订单ODS已更新，但订单DWD刷新失败 - 店铺: %s",
                self.shop.id,
            )
            result["status"] = "partial_success"
            result["message"] = f"{result['message']}，订单DWD更新失败: {error}"
            result["dwd_status"] = "error"
            result["dwd_count"] = 0
            return result

        result["dwd_status"] = "success"
        result["dwd_count"] = dwd_result["source_count"]
        return result

    async def _refresh_order_statistics_dwd(
        self,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Refresh the statistics-order DWD after Supplier Orders changes."""
        try:
            dwd_result = await crud_dwd_wb_order_statistics_detail.upsert_from_ods(
                self.db,
                shop_id=self.shop.id,
            )
        except Exception as error:
            await self.db.rollback()
            logger.exception(
                "[同步服务] Supplier Orders已更新，但统计订单DWD刷新失败 - 店铺: %s",
                self.shop.id,
            )
            result["status"] = "partial_success"
            result["message"] = f"{result['message']}，统计订单DWD更新失败: {error}"
            result["statistics_dwd_status"] = "error"
            result["statistics_dwd_count"] = 0
            return result

        result["statistics_dwd_status"] = "success"
        result["statistics_dwd_count"] = dwd_result["source_count"]
        return result

    async def sync_sales(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """同步销售数据"""
        logger.debug(
            f"[同步服务] 开始同步销售数据 - 店铺: {self.shop.id}, 日期: {date_from}~{date_to}"
        )
        if not self.client.statistics:
            return {
                "status": "error",
                "message": "Statistics API client not configured",
            }

        date_from, date_to = await self._get_date_range(date_from, date_to)

        try:
            async with self.client:
                # 获取销售数据
                logger.debug(f"[同步服务] 调用 Wildberries API 获取销售数据")
                sales_data = await self.client.statistics.get_supplier_sales(date_from)
                logger.debug(f"[同步服务] 从 API 获取到 {len(sales_data)} 条销售数据")

                # 保存到 ODS 层
                logger.debug(f"[同步服务] 开始保存销售数据到 ODS 层")
                ods_sales = await crud_ods_wb_supplier_sale.create_many(
                    self.db,
                    sales_data=sales_data,
                    shop_id=self.shop.id,
                )
                logger.debug(f"[同步服务] ODS 层销售数据保存完成: {len(ods_sales)} 条")

                result = {
                    "status": "success",
                    "message": f"同步了 {len(ods_sales)} 条销售数据 (ODS)",
                    "count": len(ods_sales),
                }
                logger.debug(f"[同步服务] 销售数据同步完成: {result}")
                return result
        except Exception as e:
            logger.error(f"[同步服务] 同步销售数据失败: {str(e)}")
            return {"status": "error", "message": f"同步销售数据失败: {str(e)}"}

    async def sync_orders(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """同步订单数据"""
        logger.debug(
            f"[同步服务] 开始同步订单数据 - 店铺: {self.shop.id}, 日期: {date_from}~{date_to}"
        )
        if not self.client.statistics:
            return {
                "status": "error",
                "message": "Statistics API client not configured",
            }

        date_from, date_to = await self._get_date_range(date_from, date_to)

        try:
            async with self.client:
                # 获取订单数据
                logger.debug(f"[同步服务] 调用 Wildberries API 获取订单数据")
                orders_data = await self.client.statistics.get_supplier_orders(
                    date_from
                )
                logger.debug(f"[同步服务] 从 API 获取到 {len(orders_data)} 条订单数据")

                # 保存到 ODS 层
                logger.debug(f"[同步服务] 开始保存订单数据到 ODS 层")
                ods_orders = await crud_ods_wb_supplier_order.create_many(
                    self.db,
                    orders_data=orders_data,
                    shop_id=self.shop.id,
                )
                logger.debug(f"[同步服务] ODS 层订单数据保存完成: {len(ods_orders)} 条")

                result = {
                    "status": "success",
                    "message": f"同步了 {len(ods_orders)} 条订单数据 (ODS)",
                    "count": len(ods_orders),
                }
                result = await self._refresh_order_dwd(result)
                result = await self._refresh_order_statistics_dwd(result)
                logger.debug(f"[同步服务] 订单数据同步完成: {result}")
                return result
        except Exception as e:
            logger.error(f"[同步服务] 同步订单数据失败: {str(e)}")
            return {"status": "error", "message": f"同步订单数据失败: {str(e)}"}

    async def sync_adverts(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """同步广告数据（扩展版）"""
        logger.debug(
            f"[同步服务] 开始同步广告数据 - 店铺: {self.shop.id}, 日期: {date_from}~{date_to}"
        )
        if not self.client.advert:
            return {"status": "error", "message": "Advert API client not configured"}

        # 获取日期范围
        date_from_str, date_to_str = await self._get_date_range(date_from, date_to)
        ods_date_from = date.fromisoformat(date_from_str) if date_from_str else None
        ods_date_to = date.fromisoformat(date_to_str) if date_to_str else None

        try:
            async with self.client:
                # ---------- 1. 获取广告活动列表 ----------
                adverts_result = await self.client.advert.get_adverts_list()
                adverts_data = adverts_result.get("adverts", [])
                logger.debug(
                    f"[同步服务] 从 API 获取到 {len(adverts_data)} 条广告活动数据"
                )

                ods_adverts_count = 0
                advert_ids = []
                if adverts_data:
                    ods_adverts = await crud_ods_wb_advert.create_many(
                        self.db,
                        adverts_data=adverts_data,
                        shop_id=self.shop.id,
                    )
                    ods_adverts_count = len(ods_adverts)
                    advert_ids = [
                        adv.get("id") for adv in adverts_data if adv.get("id")
                    ]
                    logger.debug(
                        f"[同步服务] ODS 层广告活动保存完成: {ods_adverts_count} 条"
                    )

                # ---------- 2. 同步广告商品数据 ----------
                ods_advert_product_count = 0
                if adverts_data:
                    ods_advert_products = await crud_ods_wb_advert_product.create_many(
                        self.db,
                        adverts_data=adverts_data,
                        shop_id=self.shop.id,
                    )
                    ods_advert_product_count = len(ods_advert_products)
                    logger.debug(
                        f"[同步服务] ODS 层广告商品保存完成: {ods_advert_product_count} 条"
                    )

                # ---------- 3. 同步广告预算 ----------
                ods_budget_count = 0
                if advert_ids:
                    for advert_id in advert_ids:
                        try:
                            logger.debug(
                                f"[同步服务] 获取广告 {advert_id} 的预算数据..."
                            )
                            budget_result = await self.client.advert.get_advert_budget(
                                advert_id
                            )
                            logger.debug(
                                f"[同步服务] 广告 {advert_id} 预算响应: {budget_result}"
                            )
                            if budget_result:
                                ods_budget = (
                                    await crud_ods_wb_advert_budget.create_or_update(
                                        self.db,
                                        budget_data=budget_result,
                                        advert_id=advert_id,
                                        shop_id=self.shop.id,
                                    )
                                )
                                ods_budget_count += 1
                        except Exception as e:
                            logger.warning(
                                f"[同步服务] 获取广告 {advert_id} 预算失败: {str(e)}",
                                exc_info=True,
                            )
                            continue
                    logger.debug(
                        f"[同步服务] ODS 层广告预算保存完成: {ods_budget_count} 条"
                    )

                # ---------- 4. 同步广告统计（原有逻辑） ----------
                ods_stats_count = 0
                if advert_ids:
                    stats_data = await self.client.advert.get_advert_stats(
                        advert_ids=advert_ids,
                        begin_date=date_from_str,
                        end_date=date_to_str,
                    )
                    if stats_data:
                        ods_stats = await crud_ods_wb_advert_stat.create_many(
                            self.db,
                            stats_data=stats_data,
                            shop_id=self.shop.id,
                            date_from=ods_date_from,
                            date_to=ods_date_to,
                        )
                        ods_stats_count = len(ods_stats)

                # ---------- 5. 同步搜索关键字统计 ----------
                ods_search_stat_count = 0
                if advert_ids and ods_advert_product_count > 0:
                    # 获取广告活动到商品ID的映射
                    advert_nm_map = await crud_ods_wb_advert_product.get_advert_nm_map(
                        self.db,
                        shop_id=self.shop.id,
                        advert_ids=advert_ids,
                    )
                    logger.debug(f"[同步服务] 广告商品映射: {advert_nm_map}")
                    if advert_nm_map:
                        try:
                            logger.debug(f"[同步服务] 获取搜索关键字统计...")
                            search_stats = await self.client.advert.get_normquery_stats(
                                advert_nm_map=advert_nm_map,
                                begin_date=date_from_str,
                                end_date=date_to_str,
                            )
                            logger.debug(
                                f"[同步服务] 搜索关键字统计响应: {len(search_stats) if search_stats else 0} 条"
                            )
                            if search_stats:
                                ods_search_stats = (
                                    await crud_ods_wb_search_cluster_stat.create_many(
                                        self.db,
                                        stats_data=search_stats,
                                        shop_id=self.shop.id,
                                    )
                                )
                                ods_search_stat_count = len(ods_search_stats)
                                logger.debug(
                                    f"[同步服务] ODS 层搜索关键字统计保存完成: {ods_search_stat_count} 条"
                                )
                        except Exception as e:
                            logger.warning(
                                f"[同步服务] 获取搜索关键字统计失败: {str(e)}",
                                exc_info=True,
                            )

                result = {
                    "status": "success",
                    "message": f"广告同步完成（活动: {ods_adverts_count}条，商品: {ods_advert_product_count}条，预算: {ods_budget_count}条，统计: {ods_stats_count}条，关键字统计: {ods_search_stat_count}条）",
                    "adverts_count": ods_adverts_count,
                    "advert_product_count": ods_advert_product_count,
                    "budget_count": ods_budget_count,
                    "stats_count": ods_stats_count,
                    "search_stat_count": ods_search_stat_count,
                }
                logger.debug(f"[同步服务] 广告数据同步完成: {result}")
                return result
        except Exception as e:
            logger.error(f"[同步服务] 同步广告数据失败: {str(e)}")
            import traceback

            logger.error(f"[同步服务] 错误堆栈: {traceback.format_exc()}")
            return {"status": "error", "message": f"同步广告数据失败: {str(e)}"}

    async def sync_feedbacks(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """同步评价数据"""
        if not self.client.feedbacks:
            return {"status": "error", "message": "Feedbacks API client not configured"}

        date_from, date_to = await self._get_date_range(date_from, date_to)

        try:
            async with self.client:
                all_feedbacks = []

                # Fetch both answered and unanswered feedbacks
                for is_answered in [True, False]:
                    skip = 0
                    take = 5000

                    while True:
                        logger.debug(
                            f"[同步服务] 获取评价数据 - isAnswered={is_answered}, skip={skip}"
                        )
                        feedbacks_result = await self.client.feedbacks.get_feedbacks(
                            is_answered=is_answered,
                            date_from=date_from,
                            date_to=date_to,
                            take=take,
                            skip=skip,
                        )

                        # Extract feedbacks from response
                        feedbacks = []
                        if isinstance(feedbacks_result, dict):
                            if "data" in feedbacks_result:
                                feedbacks = feedbacks_result["data"].get(
                                    "feedbacks", []
                                )
                            elif "feedbacks" in feedbacks_result:
                                feedbacks = feedbacks_result["feedbacks"]

                        if not feedbacks:
                            break

                        all_feedbacks.extend(feedbacks)
                        logger.debug(f"[同步服务] 本页获取到 {len(feedbacks)} 条评价")

                        # Check if there are more pages
                        if len(feedbacks) < take:
                            break

                        skip += take

                logger.debug(f"[同步服务] 总共获取到 {len(all_feedbacks)} 条评价")

                # 保存到 ODS 层
                ods_count = 0
                if all_feedbacks:
                    logger.debug(f"[同步服务] 开始保存评价数据到 ODS 层")
                    ods_feedbacks = await crud_ods_wb_feedback.create_many(
                        self.db,
                        feedbacks_data=all_feedbacks,
                        shop_id=self.shop.id,
                    )
                    ods_count = len(ods_feedbacks)
                    logger.debug(f"[同步服务] ODS 层评价数据保存完成: {ods_count} 条")

                try:
                    dwd_result = await crud_dwd_wb_voc_feedback_detail.upsert_from_ods(
                        self.db,
                        shop_id=self.shop.id,
                    )
                except Exception as dwd_error:
                    await self.db.rollback()
                    logger.exception(
                        "[同步服务] ODS评价已保存，但DWD客户评价更新失败 - 店铺: %s",
                        self.shop.id,
                    )
                    return {
                        "status": "partial_success",
                        "message": (
                            f"获取到 {len(all_feedbacks)} 条评价数据 "
                            f"(ODS: {ods_count})，DWD更新失败: {dwd_error}"
                        ),
                        "count": len(all_feedbacks),
                        "ods_count": ods_count,
                        "dwd_status": "error",
                        "dwd_count": 0,
                    }

                return {
                    "status": "success",
                    "message": (
                        f"获取到 {len(all_feedbacks)} 条评价数据 "
                        f"(ODS: {ods_count}, DWD: {dwd_result['source_count']})"
                    ),
                    "count": len(all_feedbacks),
                    "ods_count": ods_count,
                    "dwd_status": "success",
                    "dwd_count": dwd_result["source_count"],
                }
        except Exception as e:
            logger.error(f"[同步服务] 同步评价数据失败: {str(e)}")
            import traceback

            logger.error(f"[同步服务] 错误堆栈: {traceback.format_exc()}")
            return {"status": "error", "message": f"同步评价数据失败: {str(e)}"}

    async def sync_feedback_pins(
        self,
        *,
        window_start: datetime,
        window_end: datetime,
    ) -> Dict[str, Any]:
        """Sync pinned and automatically unpinned feedback operations."""
        logger.info(
            "[同步服务] 开始同步评价置顶记录 - 店铺: %s, 窗口: %s ~ %s",
            self.shop.id,
            window_start,
            window_end,
        )
        if not self.client.feedbacks:
            return {
                "status": "error",
                "message": "Feedbacks API client not configured",
            }
        if window_start >= window_end:
            return {
                "status": "error",
                "message": "评价置顶记录同步窗口起点必须早于终点",
            }

        limit = 500
        page_count = 0
        pins_by_id: Dict[int, Dict[str, Any]] = {}

        try:
            async with self.client:
                for state in ("pinned", "unpinned"):
                    cursor: Optional[int] = None
                    seen_cursors = set()
                    state_page_count = 0
                    while True:
                        if state_page_count >= 1000:
                            raise ValueError("评价置顶记录分页超过1000页安全上限")
                        response = await self.client.feedbacks.get_feedback_pins(
                            state=state,
                            next_id=cursor,
                            limit=limit,
                        )
                        if not isinstance(response, dict) or "data" not in response:
                            raise ValueError("评价置顶记录接口响应缺少data字段")
                        pins_data = response["data"]
                        if not isinstance(pins_data, list):
                            raise ValueError("评价置顶记录接口返回的data不是列表")

                        page_count += 1
                        state_page_count += 1
                        for item in pins_data:
                            if not isinstance(item, dict):
                                logger.warning(
                                    "[同步服务] 跳过非对象评价置顶记录: %s",
                                    item,
                                )
                                continue
                            changed_at = parse_feedback_pin_datetime(
                                item.get("changeStateAt")
                            )
                            if (
                                changed_at is None
                                or changed_at < window_start
                                or changed_at >= window_end
                            ):
                                continue
                            try:
                                pin_id = int(item.get("pinId"))
                            except (TypeError, ValueError):
                                logger.warning(
                                    "[同步服务] 跳过缺少有效pinId的评价置顶记录: %s",
                                    item,
                                )
                                continue
                            pins_by_id[pin_id] = item

                        next_cursor = response.get("next")
                        if not pins_data or next_cursor in (None, 0, ""):
                            break
                        try:
                            next_cursor = int(next_cursor)
                        except (TypeError, ValueError) as exc:
                            raise ValueError(
                                "评价置顶记录接口返回无效next游标"
                            ) from exc
                        if next_cursor in seen_cursors or next_cursor == cursor:
                            raise ValueError("评价置顶记录接口返回重复next游标")
                        seen_cursors.add(next_cursor)
                        cursor = next_cursor

            pins = list(pins_by_id.values())
            ods_count = await crud_ods_wb_feedback_pin.upsert_many(
                self.db,
                pins_data=pins,
                shop_id=self.shop.id,
                seen_at=window_end,
            )
            return {
                "status": "success",
                "message": (
                    f"同步评价置顶及自动取消置顶记录{len(pins)}条，"
                    f"写入{ods_count}条"
                ),
                "count": len(pins),
                "ods_count": ods_count,
                "page_count": page_count,
            }
        except Exception as e:
            await self.db.rollback()
            logger.exception(
                "[同步服务] 同步评价置顶记录失败 - 店铺: %s",
                self.shop.id,
            )
            return {
                "status": "error",
                "message": f"同步评价置顶记录失败: {str(e)}",
            }

    async def sync_chat_events(
        self,
        window_start: Optional[datetime] = None,
        window_end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """同步从昨天零点到本次运行时刻的买家聊天事件。"""
        if not self.client.buyer_chat:
            return {
                "status": "error",
                "message": "Buyer Chat API client not configured",
            }

        window_end = window_end or now_platform()
        if window_end.tzinfo is None:
            window_end = window_end.replace(tzinfo=platform_tz())
        window_start = window_start or (
            window_end - timedelta(days=settings.sync.wb_chat_events_lookback_days)
        ).replace(hour=0, minute=0, second=0, microsecond=0)
        if window_start.tzinfo is None:
            window_start = window_start.replace(tzinfo=platform_tz())
        if window_start >= window_end:
            return {"status": "error", "message": "聊天事件同步时间窗口无效"}

        try:
            cursor = int(window_start.timestamp() * 1000)
            seen_cursors = {cursor}
            selected: Dict[str, Dict[str, Any]] = {}
            scanned_count = 0

            async with self.client:
                while True:
                    response = await self.client.buyer_chat.get_events(next_=cursor)
                    result = (
                        response.get("result") if isinstance(response, dict) else None
                    )
                    if not isinstance(result, dict):
                        raise ValueError(
                            "Wildberries chat events response has no result object"
                        )

                    events = result.get("events", [])
                    if not isinstance(events, list):
                        raise ValueError(
                            "Wildberries chat events response is not a list"
                        )

                    scanned_count += len(events)
                    for event in events:
                        if not isinstance(event, dict) or not event.get("eventID"):
                            logger.warning(
                                "[同步服务] 跳过格式无效的 Wildberries 聊天事件"
                            )
                            continue

                        event_at = parse_chat_event_datetime(
                            event.get("addTime") or event.get("addTimestamp")
                        )
                        if event_at is None or not (
                            window_start <= event_at < window_end
                        ):
                            continue
                        selected[str(event["eventID"])] = event

                    total_events = result.get("totalEvents", 0)
                    if total_events == 0:
                        break

                    next_cursor = result.get("next")
                    if (
                        not isinstance(next_cursor, int)
                        or next_cursor < 0
                        or next_cursor in seen_cursors
                    ):
                        raise ValueError(
                            "Wildberries chat events cursor did not advance"
                        )
                    cursor = next_cursor
                    seen_cursors.add(cursor)

            events_to_save = list(selected.values())
            saved_count = await crud_ods_wb_chat_event.upsert_many(
                self.db,
                events_data=events_to_save,
                shop_id=self.shop.id,
                synced_at=window_end,
            )
            return {
                "status": "success",
                "message": (
                    f"扫描 {scanned_count} 条聊天事件，"
                    f"幂等写入指定时间窗口内的 {saved_count} 条"
                ),
                "count": saved_count,
                "scanned_count": scanned_count,
                "window_start": window_start.isoformat(),
                "window_end": window_end.isoformat(),
            }
        except Exception as e:
            logger.exception("[同步服务] 同步买家聊天事件失败")
            return {"status": "error", "message": f"同步买家聊天事件失败: {e}"}

    async def sync_return_claims(
        self,
        window_start: Optional[datetime] = None,
        window_end: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """同步最近一小时新增或发生变化的买家退货申请。"""
        if not self.client.returns:
            return {"status": "error", "message": "Returns API client not configured"}

        window_end = window_end or now_platform()
        if window_end.tzinfo is None:
            window_end = window_end.replace(tzinfo=platform_tz())
        window_start = window_start or (
            window_end - timedelta(hours=settings.sync.wb_return_claims_lookback_hours)
        )
        if window_start.tzinfo is None:
            window_start = window_start.replace(tzinfo=platform_tz())
        if window_start >= window_end:
            return {"status": "error", "message": "退货申请同步时间窗口无效"}

        try:
            selected: Dict[str, tuple[datetime, bool, Dict[str, Any]]] = {}
            scanned_count = 0
            page_size = 200

            async with self.client:
                # 接口要求分开查询处理中与归档数据。API 只支持最近 14 天，
                # 不支持时间过滤，因此完整分页后再按 dt_update/dt 筛选。
                for is_archive in (False, True):
                    offset = 0
                    while True:
                        response = await self.client.returns.get_claims(
                            is_archive=is_archive,
                            limit=page_size,
                            offset=offset,
                        )
                        claims = (
                            response.get("claims", [])
                            if isinstance(response, dict)
                            else []
                        )
                        if not isinstance(claims, list):
                            raise ValueError(
                                "Wildberries claims response is not a list"
                            )

                        scanned_count += len(claims)
                        for claim in claims:
                            if not isinstance(claim, dict) or not claim.get("id"):
                                logger.warning(
                                    "[同步服务] 跳过格式无效的 Wildberries 退货申请"
                                )
                                continue

                            event_time = parse_claim_datetime(
                                claim.get("dt_update")
                            ) or parse_claim_datetime(claim.get("dt"))
                            if event_time is None or not (
                                window_start <= event_time < window_end
                            ):
                                continue

                            claim_id = str(claim["id"])
                            current = selected.get(claim_id)
                            # 若同一申请短暂同时出现在两个集合，优先更新时间更晚
                            # 的版本；时间相同则优先归档版本。
                            if current and (
                                event_time < current[0]
                                or (
                                    event_time == current[0]
                                    and current[1]
                                    and not is_archive
                                )
                            ):
                                continue
                            selected[claim_id] = (
                                event_time,
                                is_archive,
                                {**claim, "_is_archive": is_archive},
                            )

                        offset += len(claims)
                        total = (
                            response.get("total")
                            if isinstance(response, dict)
                            else None
                        )
                        if (
                            not claims
                            or len(claims) < page_size
                            or (isinstance(total, int) and offset >= total)
                        ):
                            break

            claims_to_save = [item[2] for item in selected.values()]
            saved_count = await crud_ods_wb_return_claim.upsert_many(
                self.db,
                claims_data=claims_to_save,
                shop_id=self.shop.id,
                synced_at=window_end,
            )
            return {
                "status": "success",
                "message": (
                    f"扫描 {scanned_count} 条退货申请，"
                    f"同步最近一小时内新增或变化的 {saved_count} 条"
                ),
                "count": saved_count,
                "scanned_count": scanned_count,
                "window_start": window_start.isoformat(),
                "window_end": window_end.isoformat(),
            }
        except Exception as e:
            logger.exception("[同步服务] 同步买家退货申请失败")
            return {"status": "error", "message": f"同步买家退货申请失败: {e}"}

    async def sync_questions(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """同步问答数据"""
        if not self.client.feedbacks:
            return {"status": "error", "message": "Feedbacks API client not configured"}

        date_from, date_to = await self._get_date_range(date_from, date_to)

        try:
            async with self.client:
                all_questions = []

                # Fetch both answered and unanswered questions
                for is_answered in [True, False]:
                    skip = 0
                    take = 5000

                    while True:
                        logger.debug(
                            f"[同步服务] 获取提问数据 - isAnswered={is_answered}, skip={skip}"
                        )
                        questions_result = await self.client.feedbacks.get_questions(
                            is_answered=is_answered,
                            date_from=date_from,
                            date_to=date_to,
                            take=take,
                            skip=skip,
                        )

                        # Extract questions from response
                        questions = []
                        if isinstance(questions_result, dict):
                            if "data" in questions_result:
                                questions = questions_result["data"].get(
                                    "questions", []
                                )
                            elif "questions" in questions_result:
                                questions = questions_result["questions"]

                        if not questions:
                            break

                        all_questions.extend(questions)
                        logger.debug(f"[同步服务] 本页获取到 {len(questions)} 条提问")

                        # Check if there are more pages
                        if len(questions) < take:
                            break

                        skip += take

                logger.debug(f"[同步服务] 总共获取到 {len(all_questions)} 条提问")

                # 保存到 ODS 层
                ods_count = 0
                if all_questions:
                    logger.debug(f"[同步服务] 开始保存提问数据到 ODS 层")
                    ods_questions = await crud_ods_wb_question.create_many(
                        self.db,
                        questions_data=all_questions,
                        shop_id=self.shop.id,
                    )
                    ods_count = len(ods_questions)
                    logger.debug(f"[同步服务] ODS 层提问数据保存完成: {ods_count} 条")

                try:
                    dwd_result = await crud_dwd_wb_voc_question_detail.upsert_from_ods(
                        self.db,
                        shop_id=self.shop.id,
                    )
                except Exception as dwd_error:
                    await self.db.rollback()
                    logger.exception(
                        "[同步服务] ODS提问已保存，但DWD客户提问更新失败 - 店铺: %s",
                        self.shop.id,
                    )
                    return {
                        "status": "partial_success",
                        "message": (
                            f"获取到 {len(all_questions)} 条提问数据"
                            f"(ODS: {ods_count})，DWD更新失败: {dwd_error}"
                        ),
                        "count": len(all_questions),
                        "ods_count": ods_count,
                        "dwd_status": "error",
                        "dwd_count": 0,
                    }

                return {
                    "status": "success",
                    "message": (
                        f"获取到 {len(all_questions)} 条提问数据"
                        f"(ODS: {ods_count}, DWD: {dwd_result['source_count']})"
                    ),
                    "count": len(all_questions),
                    "ods_count": ods_count,
                    "dwd_status": "success",
                    "dwd_count": dwd_result["source_count"],
                }
        except Exception as e:
            logger.error(f"[同步服务] 同步提问数据失败: {str(e)}")
            import traceback

            logger.error(f"[同步服务] 错误堆栈: {traceback.format_exc()}")
            return {"status": "error", "message": f"同步提问数据失败: {str(e)}"}

    async def sync_funnel(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        *,
        sync_dwd: bool = True,
    ) -> Dict[str, Any]:
        """同步一个日期区间的销售漏斗数据，并完整拉取所有分页。"""
        logger.debug(
            f"[同步服务] 开始同步销售漏斗数据 - 店铺: {self.shop.id}, 日期: {date_from}~{date_to}"
        )
        if not self.client.analytics:
            return {"status": "error", "message": "Analytics API client not configured"}

        if not date_from and not date_to:
            yesterday = (now_platform() - timedelta(days=1)).date().isoformat()
            date_from = yesterday
            date_to = yesterday
        elif not date_from:
            date_from = date_to
        elif not date_to:
            date_to = date_from

        try:
            ods_date_from = date.fromisoformat(date_from)
            ods_date_to = date.fromisoformat(date_to)
        except (TypeError, ValueError):
            return {"status": "error", "message": "销售漏斗日期格式必须为 YYYY-MM-DD"}
        if ods_date_from > ods_date_to:
            return {"status": "error", "message": "销售漏斗开始日期不能晚于结束日期"}

        try:
            async with self.client:
                offset = 0
                page_limit = 1000
                request_count = 0
                total_count = 0
                ods_count = 0

                while True:
                    funnel_result = await self.client.analytics.get_sales_funnel(
                        date_from,
                        date_to,
                        limit=page_limit,
                        offset=offset,
                    )
                    request_count += 1
                    funnel_data = self._extract_funnel_products(funnel_result)
                    logger.debug(
                        "[同步服务] 销售漏斗分页完成 - 日期: %s~%s, offset: %s, 条数: %s",
                        date_from,
                        date_to,
                        offset,
                        len(funnel_data),
                    )

                    if funnel_data:
                        ods_funnel = await crud_ods_wb_sales_funnel.create_many(
                            self.db,
                            funnel_data=funnel_data,
                            shop_id=self.shop.id,
                            date_from=ods_date_from,
                            date_to=ods_date_to,
                        )
                        total_count += len(funnel_data)
                        ods_count += len(ods_funnel)

                    if len(funnel_data) < page_limit:
                        break
                    offset += page_limit

                dwd_stats = None
                if sync_dwd:
                    try:
                        dwd_stats = await wb_dwd_service.sync_sales_funnel_detail(
                            self.db,
                            shop_id=self.shop.id,
                        )
                    except Exception as dwd_error:
                        logger.error(
                            "[同步服务] ODS 销售漏斗已保存，但 DWD 同步失败: "
                            f"{dwd_error}"
                        )
                        return {
                            "status": "error",
                            "message": (
                                f"ODS 已保存 {ods_count} 条，但销售漏斗 DWD "
                                f"同步失败: {dwd_error}"
                            ),
                            "count": total_count,
                            "ods_count": ods_count,
                            "request_count": request_count,
                            "date_from": date_from,
                            "date_to": date_to,
                            "dwd_status": "error",
                        }

                result = {
                    "status": "success",
                    "message": (
                        f"销售漏斗 {date_from} 同步完成: "
                        f"获取 {total_count} 条，写入/更新 {ods_count} 条"
                    ),
                    "count": total_count,
                    "ods_count": ods_count,
                    "request_count": request_count,
                    "date_from": date_from,
                    "date_to": date_to,
                }
                if dwd_stats is not None:
                    result.update(
                        {
                            "dwd_scanned": dwd_stats["scanned"],
                            "dwd_created": dwd_stats["created"],
                            "dwd_updated": dwd_stats["updated"],
                        }
                    )
                logger.debug(f"[同步服务] 销售漏斗数据同步完成: {result}")
                return result
        except Exception as e:
            logger.error(f"[同步服务] 同步销售漏斗数据失败: {str(e)}")
            import traceback

            logger.error(f"[同步服务] 错误堆栈: {traceback.format_exc()}")
            return {"status": "error", "message": f"同步销售漏斗数据失败: {str(e)}"}

    @staticmethod
    def _extract_funnel_products(funnel_result: Any) -> List[Dict[str, Any]]:
        """兼容销售漏斗接口的历史响应包装格式。"""
        if isinstance(funnel_result, list):
            return funnel_result
        if not isinstance(funnel_result, dict):
            return []

        data = funnel_result.get("data")
        if isinstance(data, dict):
            products = data.get("products", [])
        elif isinstance(data, list):
            products = data
        else:
            products = funnel_result.get("products", [])
        return products if isinstance(products, list) else []

    async def sync_funnel_lookback(
        self, lookback_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """按单日粒度同步最近 N 个已结束的平台日。"""
        days = (
            settings.sync.wb_funnel_lookback_days
            if lookback_days is None
            else lookback_days
        )
        if days < 1 or days > 31:
            return {"status": "error", "message": "销售漏斗回看天数必须为 1 至 31"}

        platform_today = now_platform().date()
        daily_results: Dict[str, Dict[str, Any]] = {}
        total_count = 0
        ods_count = 0
        request_count = 0

        for days_ago in range(days, 0, -1):
            target_date = (platform_today - timedelta(days=days_ago)).isoformat()
            day_result = await self.sync_funnel(
                target_date,
                target_date,
                sync_dwd=False,
            )
            daily_results[target_date] = day_result
            total_count += day_result.get("count", 0)
            ods_count += day_result.get("ods_count", 0)
            request_count += day_result.get("request_count", 0)

        failed_dates = [
            target_date
            for target_date, result in daily_results.items()
            if result.get("status") != "success"
        ]

        try:
            dwd_stats = await wb_dwd_service.sync_sales_funnel_detail(
                self.db,
                shop_id=self.shop.id,
            )
        except Exception as dwd_error:
            logger.error(
                "[同步服务] 销售漏斗回补 ODS 已保存，但 DWD 同步失败: " f"{dwd_error}"
            )
            return {
                "status": "error",
                "message": (f"销售漏斗 ODS 回补后，DWD 同步失败: {dwd_error}"),
                "count": total_count,
                "ods_count": ods_count,
                "request_count": request_count,
                "daily_results": daily_results,
                "dwd_status": "error",
            }

        if failed_dates:
            return {
                "status": "error",
                "message": (
                    f"销售漏斗近 {days} 日回补未全部完成，"
                    f"失败日期: {', '.join(failed_dates)}"
                ),
                "count": total_count,
                "ods_count": ods_count,
                "request_count": request_count,
                "daily_results": daily_results,
                "dwd_scanned": dwd_stats["scanned"],
                "dwd_created": dwd_stats["created"],
                "dwd_updated": dwd_stats["updated"],
            }

        return {
            "status": "success",
            "message": (
                f"销售漏斗 T-{days} 至 T-1 回补完成: "
                f"获取 {total_count} 条，写入/更新 {ods_count} 条"
            ),
            "count": total_count,
            "ods_count": ods_count,
            "request_count": request_count,
            "daily_results": daily_results,
            "dwd_scanned": dwd_stats["scanned"],
            "dwd_created": dwd_stats["created"],
            "dwd_updated": dwd_stats["updated"],
        }

    async def sync_returns(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """同步退货数据"""
        logger.debug(
            f"[同步服务] 开始同步退货数据 - 店铺: {self.shop.id}, 日期: {date_from}~{date_to}"
        )
        if not self.client.analytics:
            return {"status": "error", "message": "Analytics API client not configured"}

        date_from, date_to = await self._get_date_range(date_from, date_to)

        try:
            async with self.client:
                # 获取退货数据
                logger.debug(f"[同步服务] 调用 Wildberries API 获取退货数据")
                returns_result = await self.client.analytics.get_goods_return(
                    date_from, date_to
                )

                # 调试：打印完整的 API 响应
                logger.debug(f"[同步服务] API 原始响应: {returns_result}")

                # 尝试正确提取数据
                returns_data = []
                if isinstance(returns_result, dict):
                    if "report" in returns_result:
                        returns_data = returns_result["report"]
                    elif "data" in returns_result:
                        returns_data = returns_result["data"]
                    elif "returns" in returns_result:
                        returns_data = returns_result["returns"]
                elif isinstance(returns_result, list):
                    returns_data = returns_result

                # 如果 returns_data 不是列表，尝试转换
                if not isinstance(returns_data, list):
                    logger.warning(
                        f"[同步服务] returns_data 不是列表: {type(returns_data)}"
                    )
                    returns_data = []

                logger.debug(f"[同步服务] 从 API 获取到 {len(returns_data)} 条退货数据")

                # 保存到 ODS 层
                ods_count = 0
                if returns_data:
                    logger.debug(f"[同步服务] 开始保存退货数据到 ODS 层")
                    ods_returns = await crud_ods_wb_goods_return.create_many(
                        self.db,
                        returns_data=returns_data,
                        shop_id=self.shop.id,
                    )
                    ods_count = len(ods_returns)
                    logger.debug(f"[同步服务] ODS 层退货数据保存完成: {ods_count} 条")

                try:
                    dwd_result = await crud_dwd_wb_return_detail.upsert_from_ods(
                        self.db,
                        shop_id=self.shop.id,
                    )
                except Exception as dwd_error:
                    await self.db.rollback()
                    logger.exception(
                        "[同步服务] ODS退货已保存，但DWD退货明细更新失败 - 店铺: %s",
                        self.shop.id,
                    )
                    return {
                        "status": "partial_success",
                        "message": (
                            f"获取了 {len(returns_data)} 条退货数据"
                            f"(ODS: {ods_count})，DWD更新失败: {dwd_error}"
                        ),
                        "count": len(returns_data),
                        "ods_count": ods_count,
                        "dwd_status": "error",
                        "dwd_count": 0,
                    }

                result = {
                    "status": "success",
                    "message": (
                        f"获取了 {len(returns_data)} 条退货数据"
                        f"(ODS: {ods_count}, DWD: {dwd_result['source_count']})"
                    ),
                    "count": len(returns_data),
                    "ods_count": ods_count,
                    "dwd_status": "success",
                    "dwd_count": dwd_result["source_count"],
                }
                logger.debug(f"[同步服务] 退货数据同步完成: {result}")
                return result
        except Exception as e:
            logger.error(f"[同步服务] 同步退货数据失败: {str(e)}")
            import traceback

            logger.error(f"[同步服务] 错误堆栈: {traceback.format_exc()}")
            return {"status": "error", "message": f"同步退货数据失败: {str(e)}"}

    async def sync_finance(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """同步财务数据（使用新的销售报告API - 单表版本）"""
        logger.debug(
            f"[同步服务] 开始同步销售报告数据 - 店铺: {self.shop.id}, 日期: {date_from}~{date_to}"
        )
        if not self.client.finance:
            return {"status": "error", "message": "Finance API client not configured"}

        date_from, date_to = await self._get_date_range(date_from, date_to)
        ods_date_from = date.fromisoformat(date_from) if date_from else None
        ods_date_to = date.fromisoformat(date_to) if date_to else None

        try:
            async with self.client:
                all_items: List[Dict[str, Any]] = []
                next_id: Optional[int] = None
                limit = 100000
                max_pages = 10  # 防止无限循环
                page_count = 0

                # 分页获取数据
                while page_count < max_pages:
                    logger.debug(
                        f"[同步服务] 调用新财务 API 获取销售报告明细，第 {page_count + 1} 页, next_id={next_id}"
                    )
                    result = await self.client.finance.get_sales_reports_detailed(
                        date_from, date_to, limit=limit, next_id=next_id
                    )

                    logger.debug(f"[同步服务] API 原始响应: {result}")

                    # 提取明细数据 - 尝试多种可能的响应结构
                    items_data = []
                    if isinstance(result, dict):
                        # 尝试不同的可能字段名
                        if "data" in result:
                            data = result["data"]
                            if isinstance(data, dict):
                                if "items" in data:
                                    items_data = data["items"]
                                elif "list" in data:
                                    items_data = data["list"]
                                elif "sales" in data:
                                    items_data = data["sales"]
                            elif isinstance(data, list):
                                items_data = data
                        elif "items" in result:
                            items_data = result["items"]
                        elif "list" in result:
                            items_data = result["list"]
                        elif "sales" in result:
                            items_data = result["sales"]
                        elif "result" in result:
                            items_data = result["result"]
                    elif isinstance(result, list):
                        items_data = result

                    if not items_data:
                        logger.debug(f"[同步服务] 没有更多销售报告数据")
                        break

                    all_items.extend(items_data)
                    logger.debug(
                        f"[同步服务] 本页获取到 {len(items_data)} 条销售报告明细，累计 {len(all_items)} 条"
                    )

                    # 获取下一页游标
                    new_next_id = None
                    if isinstance(result, dict):
                        if "next" in result:
                            new_next_id = result.get("next")
                        elif "nextId" in result:
                            new_next_id = result.get("nextId")
                        elif "data" in result and isinstance(result["data"], dict):
                            if "next" in result["data"]:
                                new_next_id = result["data"].get("next")
                            elif "nextId" in result["data"]:
                                new_next_id = result["data"].get("nextId")

                    next_id = new_next_id if new_next_id else None

                    # 如果没有下一页了，退出
                    if not next_id:
                        logger.debug(f"[同步服务] 没有下一页游标，退出")
                        break

                    page_count += 1

                logger.debug(
                    f"[同步服务] 从新财务 API 总共获取到 {len(all_items)} 条销售报告明细"
                )

                # 保存明细数据（直接保存到单表）
                ods_count = 0
                if all_items and ods_date_from and ods_date_to:
                    ods_items = await crud_ods_wb_sales_report.create_many(
                        self.db,
                        items=all_items,
                        shop_id=self.shop.id,
                    )
                    ods_count = len(ods_items)
                    await self.db.commit()
                    logger.debug(f"[同步服务] ODS 层销售报告保存完成: {ods_count} 条")

                try:
                    dwd_stats = await wb_dwd_service.sync_sales_report_detail(
                        self.db,
                        shop_id=self.shop.id,
                    )
                    logger.debug("[同步服务] DWD 财务结算明细同步完成: " f"{dwd_stats}")
                except Exception as dwd_error:
                    logger.error(
                        "[同步服务] ODS 财务数据已保存，但 DWD 同步失败: "
                        f"{dwd_error}"
                    )
                    return {
                        "status": "error",
                        "message": (
                            f"ODS 已保存 {ods_count} 条，但 DWD 同步失败: "
                            f"{dwd_error}"
                        ),
                        "count": len(all_items),
                        "ods_count": ods_count,
                        "dwd_status": "error",
                    }

                result = {
                    "status": "success",
                    "message": (
                        f"获取了 {len(all_items)} 条销售报告明细 "
                        f"(ODS: {ods_count}, DWD扫描: {dwd_stats['scanned']})"
                    ),
                    "count": len(all_items),
                    "ods_count": ods_count,
                    "dwd_scanned": dwd_stats["scanned"],
                    "dwd_created": dwd_stats["created"],
                    "dwd_updated": dwd_stats["updated"],
                }
                result = await self._refresh_order_dwd(result)
                logger.debug(f"[同步服务] 销售报告数据同步完成: {result}")
                return result
        except Exception as e:
            logger.error(f"[同步服务] 同步销售报告数据失败: {str(e)}")
            import traceback

            logger.error(f"[同步服务] 错误堆栈: {traceback.format_exc()}")
            return {"status": "error", "message": f"同步销售报告数据失败: {str(e)}"}

    @staticmethod
    def _extract_report_items(result: Any) -> List[Dict[str, Any]]:
        """从财务 API 响应中提取明细列表。"""
        items_data: Any = []
        if isinstance(result, dict):
            if "data" in result:
                data = result["data"]
                if isinstance(data, dict):
                    items_data = (
                        data.get("items") or data.get("list") or data.get("sales") or []
                    )
                elif isinstance(data, list):
                    items_data = data
            else:
                items_data = (
                    result.get("items")
                    or result.get("list")
                    or result.get("sales")
                    or result.get("result")
                    or []
                )
        elif isinstance(result, list):
            items_data = result
        return items_data if isinstance(items_data, list) else []

    @staticmethod
    def _extract_report_next_id(result: Any) -> Optional[int]:
        """从财务 API 响应中提取下一页游标。"""
        if not isinstance(result, dict):
            return None
        next_id = result.get("next") or result.get("nextId")
        data = result.get("data")
        if not next_id and isinstance(data, dict):
            next_id = data.get("next") or data.get("nextId")
        return next_id or None

    async def _fetch_sales_reports(
        self,
        date_from: str,
        date_to: str,
        period: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """分页拉取财务销售报告明细。"""
        all_items: List[Dict[str, Any]] = []
        next_id: Optional[int] = None

        for page_number in range(1, 11):
            logger.debug(
                "[同步服务] 调用财务 API %s~%s，period=%s，第 %s 页，next_id=%s",
                date_from,
                date_to,
                period,
                page_number,
                next_id,
            )
            result = await self.client.finance.get_sales_reports_detailed(
                date_from,
                date_to,
                limit=100000,
                next_id=next_id,
                period=period,
            )
            items_data = self._extract_report_items(result)
            if not items_data:
                break
            all_items.extend(items_data)
            next_id = self._extract_report_next_id(result)
            if not next_id:
                break

        return all_items

    async def sync_finance_daily(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """同步 WB 按日财务明细到独立 ODS 表。"""
        if not self.client.finance:
            return {"status": "error", "message": "Finance API client not configured"}

        if not date_to:
            date_to = (now_platform() - timedelta(days=1)).strftime("%Y-%m-%d")
        if not date_from:
            date_from = (
                now_platform()
                - timedelta(days=settings.sync.wb_finance_daily_backfill_days)
            ).strftime("%Y-%m-%d")

        try:
            start_date = date.fromisoformat(date_from)
            end_date = date.fromisoformat(date_to)
        except (TypeError, ValueError):
            return {
                "status": "error",
                "message": f"日期格式错误: {date_from}~{date_to}",
            }

        if start_date > end_date:
            return {
                "status": "error",
                "message": f"date_from 不能晚于 date_to: {date_from}~{date_to}",
            }

        try:
            async with self.client:
                all_items = await self._fetch_sales_reports(
                    date_from, date_to, period="daily"
                )
                ods_count = 0
                if all_items:
                    ods_items = await crud_ods_wb_sales_report_daily.create_many(
                        self.db,
                        items=all_items,
                        shop_id=self.shop.id,
                    )
                    ods_count = len(ods_items)
                    await self.db.commit()

            return {
                "status": "success",
                "message": (
                    f"按天同步销售报告完成 {date_from}~{date_to}，"
                    f"共 {len(all_items)} 条 (ODS: {ods_count})"
                ),
                "count": len(all_items),
                "ods_count": ods_count,
            }
        except Exception as exc:
            await self._safe_rollback()
            logger.exception("[同步服务] 同步销售报告数据(按天)失败")
            return {
                "status": "error",
                "message": f"同步销售报告数据(按天)失败: {exc}",
            }

    async def sync_marketplace_orders(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """同步 Marketplace 订单数据"""
        logger.debug(
            f"[同步服务] 开始同步 Marketplace 订单数据 - 店铺: {self.shop.id}, 日期: {date_from}~{date_to}"
        )
        if not self.client.marketplace:
            return {
                "status": "error",
                "message": "Marketplace API client not configured",
            }

        date_from, date_to = await self._get_date_range(date_from, date_to)

        try:
            async with self.client:
                all_orders_data: List[Dict[str, Any]] = []
                next_cursor = 0
                limit = 1000
                max_pages = 100  # 防止无限循环
                page_count = 0

                # 分页获取数据
                while page_count < max_pages:
                    logger.debug(
                        f"[同步服务] 调用 Marketplace API，第 {page_count + 1} 页, cursor={next_cursor}"
                    )
                    result = await self.client.marketplace.get_orders(
                        date_from, date_to, limit=limit, next_=next_cursor
                    )

                    # 提取订单数据
                    orders_data = []
                    if isinstance(result, dict):
                        orders_data = result.get("orders", [])
                        next_cursor = result.get("next", 0)
                    elif isinstance(result, list):
                        orders_data = result
                        next_cursor = 0

                    if not orders_data:
                        logger.debug(f"[同步服务] 没有更多订单数据")
                        break

                    all_orders_data.extend(orders_data)
                    logger.debug(
                        f"[同步服务] 本页获取到 {len(orders_data)} 条订单数据，累计 {len(all_orders_data)} 条"
                    )

                    # 如果没有下一页了，退出
                    if not next_cursor:
                        logger.debug(f"[同步服务] 没有下一页游标，退出")
                        break

                    page_count += 1

                logger.debug(
                    f"[同步服务] 从 API 总共获取到 {len(all_orders_data)} 条 Marketplace 订单数据"
                )

                # 保存到 ODS 层
                ods_orders = []
                ods_status_histories_count = 0
                if all_orders_data:
                    logger.debug(f"[同步服务] 开始保存 Marketplace 订单数据到 ODS 层")
                    ods_orders = await crud_ods_wb_marketplace_order.create_many(
                        self.db,
                        orders_data=all_orders_data,
                        shop_id=self.shop.id,
                    )
                    logger.debug(
                        f"[同步服务] ODS 层 Marketplace 订单数据保存完成: {len(ods_orders)} 条"
                    )

                    # 获取订单ID列表
                    order_ids = [
                        order.get("id") for order in all_orders_data if order.get("id")
                    ]

                    if order_ids:
                        # 分批获取订单状态（每次最多1000个订单）
                        batch_size = 1000
                        for i in range(0, len(order_ids), batch_size):
                            batch_order_ids = order_ids[i : i + batch_size]

                            # 1. 获取订单状态并更新订单表
                            logger.debug(
                                f"[同步服务] 获取订单状态: {len(batch_order_ids)} 个订单"
                            )
                            try:
                                status_result = (
                                    await self.client.marketplace.get_orders_status(
                                        batch_order_ids
                                    )
                                )
                                if (
                                    isinstance(status_result, dict)
                                    and "orders" in status_result
                                ):
                                    orders_status = status_result["orders"]
                                    # 更新每个订单的状态字段
                                    for order_status in orders_status:
                                        order_id = order_status.get("id")
                                        if order_id:
                                            # 获取已保存的订单记录
                                            db_order = await crud_ods_wb_marketplace_order.get_by_order_id(
                                                self.db, self.shop.id, order_id
                                            )
                                            if db_order:
                                                # 更新实际存在的字段
                                                db_order.is_cancellable = (
                                                    order_status.get("isCancellable")
                                                )
                                                db_order.supplier_status = (
                                                    order_status.get("supplierStatus")
                                                )
                                                db_order.wb_status = order_status.get(
                                                    "wbStatus"
                                                )

                                                self.db.add(db_order)
                                    await self.db.commit()
                                    logger.debug(
                                        f"[同步服务] 订单状态更新完成: {len(orders_status)} 个订单"
                                    )
                            except Exception as e:
                                logger.error(f"[同步服务] 获取订单状态失败: {str(e)}")

                            # 2. 获取订单状态历史 - 保存原始JSON
                            logger.debug(
                                f"[同步服务] 获取订单状态历史: {len(batch_order_ids)} 个订单"
                            )
                            try:
                                status_history_result = await self.client.marketplace.get_orders_status_history(
                                    batch_order_ids
                                )
                                if (
                                    isinstance(status_history_result, dict)
                                    and "orders" in status_history_result
                                ):
                                    orders_status_history = status_history_result[
                                        "orders"
                                    ]
                                    # 构建订单ID到状态历史的映射 - 保存完整原始数据
                                    status_history_map = {}
                                    for order_history in orders_status_history:
                                        order_id = order_history.get(
                                            "orderID"
                                        )  # API返回的是orderID
                                        if order_id:
                                            status_history_map[order_id] = order_history
                                    # 保存状态历史
                                    if status_history_map:
                                        ods_histories = await crud_ods_wb_marketplace_order_status_history.create_many(
                                            self.db,
                                            orders_status_histories=status_history_map,
                                            shop_id=self.shop.id,
                                        )
                                        ods_status_histories_count += len(ods_histories)
                                        logger.debug(
                                            f"[同步服务] 订单状态历史保存完成: {len(ods_histories)} 条"
                                        )
                            except Exception as e:
                                logger.error(
                                    f"[同步服务] 获取订单状态历史失败: {str(e)}"
                                )

                result = {
                    "status": "success",
                    "message": f"获取了 {len(all_orders_data)} 条 Marketplace 订单数据 (ODS: {len(ods_orders)}, 状态历史: {ods_status_histories_count})",
                    "count": len(all_orders_data),
                    "ods_count": len(ods_orders),
                    "ods_status_histories_count": ods_status_histories_count,
                }
                result = await self._refresh_order_dwd(result)
                logger.debug(f"[同步服务] Marketplace 订单数据同步完成: {result}")
                return result
        except Exception as e:
            logger.error(f"[同步服务] 同步 Marketplace 订单数据失败: {str(e)}")
            import traceback

            logger.error(f"[同步服务] 错误堆栈: {traceback.format_exc()}")
            return {
                "status": "error",
                "message": f"同步 Marketplace 订单数据失败: {str(e)}",
            }

    async def sync_new_orders(self) -> Dict[str, Any]:
        """同步新订单（待处理组装订单）数据

        数据源: GET /api/v3/orders/new
        该接口返回"当前所有待卖家处理的新组装订单"，无日期参数、不分页。
        采用只 upsert 不删除策略，配合 first_seen_at 供下游识别增量新订单。
        """
        logger.debug(f"[同步服务] 开始同步新订单数据 - 店铺: {self.shop.id}")
        if not self.client.marketplace:
            return {
                "status": "error",
                "message": "Marketplace API client not configured",
            }

        try:
            async with self.client:
                result = await self.client.marketplace.get_new_orders()

                orders_data: List[Dict[str, Any]] = []
                if isinstance(result, dict):
                    orders_data = result.get("orders", []) or []
                elif isinstance(result, list):
                    orders_data = result

                logger.debug(
                    f"[同步服务] 从 API 获取到 {len(orders_data)} 条新订单数据"
                )

                ods_orders = []
                if orders_data:
                    ods_orders = await crud_ods_wb_new_order.create_many(
                        self.db,
                        orders_data=orders_data,
                        shop_id=self.shop.id,
                    )

                result = {
                    "status": "success",
                    "message": f"获取了 {len(orders_data)} 条新订单数据 (ODS: {len(ods_orders)})",
                    "count": len(orders_data),
                    "ods_count": len(ods_orders),
                }
                logger.debug(f"[同步服务] 新订单数据同步完成: {result}")
                return result
        except Exception as e:
            logger.error(f"[同步服务] 同步新订单数据失败: {str(e)}")
            return {"status": "error", "message": f"同步新订单数据失败: {str(e)}"}

    async def sync_fbs_supplies(
        self,
        *,
        window_start: datetime,
        window_end: datetime,
    ) -> Dict[str, Any]:
        """Synchronize the complete paginated FBS supply list.

        The WB endpoint has no date filter. All returned supplies are upserted so
        lifecycle changes on older supplies are not lost. ``window_count`` is a
        reporting metric for supplies whose create/close/scan timestamp is in the
        requested business window.
        """
        logger.info(
            "[同步服务] 开始同步FBS供货单 - 店铺: %s, 业务窗口: %s ~ %s",
            self.shop.id,
            window_start,
            window_end,
        )
        if not self.client.marketplace:
            return {
                "status": "error",
                "message": "Marketplace API client not configured",
            }
        if window_start >= window_end:
            return {
                "status": "error",
                "message": "FBS供货单同步窗口起点必须早于终点",
            }

        cursor = 0
        page_count = 0
        source_count = 0
        ods_count = 0
        window_count = 0
        seen_cursors = set()
        seen_supply_ids = set()

        def is_in_business_window(data: Dict[str, Any]) -> bool:
            for field in ("createdAt", "closedAt", "scanDt"):
                timestamp = parse_supply_datetime(data.get(field))
                if timestamp is None:
                    continue
                if timestamp.tzinfo is not None and window_start.tzinfo is not None:
                    timestamp = timestamp.astimezone(window_start.tzinfo)
                if window_start <= timestamp < window_end:
                    return True
            return False

        try:
            async with self.client:
                while cursor not in seen_cursors:
                    seen_cursors.add(cursor)
                    response = await self.client.marketplace.get_supplies(
                        limit=1000,
                        next_=cursor,
                    )
                    page_count += 1
                    page = (
                        response.get("supplies", [])
                        if isinstance(response, dict)
                        else []
                    )
                    if not isinstance(page, list):
                        raise ValueError("FBS供货单接口返回的supplies不是列表")

                    unique_page = []
                    for item in page:
                        if not isinstance(item, dict) or not item.get("id"):
                            logger.warning(
                                "[同步服务] 跳过缺少有效id的FBS供货单响应: %s",
                                item,
                            )
                            continue
                        supply_id = str(item["id"])
                        if supply_id in seen_supply_ids:
                            continue
                        seen_supply_ids.add(supply_id)
                        unique_page.append(item)
                        if is_in_business_window(item):
                            window_count += 1

                    source_count += len(unique_page)
                    ods_count += await crud_ods_wb_fbs_supply.upsert_many(
                        self.db,
                        supplies_data=unique_page,
                        shop_id=self.shop.id,
                        seen_at=window_end,
                    )

                    if not page:
                        break
                    next_cursor = response.get("next")
                    try:
                        next_cursor = int(next_cursor)
                    except (TypeError, ValueError):
                        raise ValueError("FBS供货单接口返回了无效的next游标")
                    if next_cursor in seen_cursors:
                        break
                    cursor = next_cursor

            return {
                "status": "success",
                "message": (
                    f"分页获取{source_count}张FBS供货单，写入{ods_count}条，"
                    f"业务窗口内{window_count}条"
                ),
                "count": source_count,
                "ods_count": ods_count,
                "window_count": window_count,
                "page_count": page_count,
            }
        except Exception as e:
            logger.exception(
                "[同步服务] 同步FBS供货单失败 - 店铺: %s",
                self.shop.id,
            )
            return {
                "status": "error",
                "message": f"同步FBS供货单失败: {str(e)}",
            }

    async def sync_reshipment_orders(
        self,
        *,
        window_start: datetime,
        window_end: datetime,
    ) -> Dict[str, Any]:
        """Reconcile all FBS assembly orders currently requiring reshipment."""
        logger.info(
            "[同步服务] 开始同步重新发货订单 - 店铺: %s, 业务窗口: %s ~ %s",
            self.shop.id,
            window_start,
            window_end,
        )
        if not self.client.marketplace:
            return {
                "status": "error",
                "message": "Marketplace API client not configured",
            }
        if window_start >= window_end:
            return {
                "status": "error",
                "message": "重新发货订单同步窗口起点必须早于终点",
            }

        try:
            async with self.client:
                response = await self.client.marketplace.get_reshipment_orders()
            if not isinstance(response, dict) or "orders" not in response:
                raise ValueError("重新发货订单接口响应缺少orders字段")
            orders_data = response["orders"]
            if not isinstance(orders_data, list):
                raise ValueError("重新发货订单接口返回的orders不是列表")

            reconciliation = await crud_ods_wb_reshipment_order.reconcile_snapshot(
                self.db,
                orders_data=orders_data,
                shop_id=self.shop.id,
                observed_at=window_end,
            )
            window_count = await crud_ods_wb_reshipment_order.count_changed_in_window(
                self.db,
                shop_id=self.shop.id,
                window_start=window_start,
                window_end=window_end,
            )
            return {
                "status": "success",
                "message": (
                    f"当前{reconciliation['count']}个订单需要重新发货，"
                    f"新增{reconciliation['new_count']}个，"
                    f"重新进入{reconciliation['reactivated_count']}个，"
                    f"已解决{reconciliation['resolved_count']}个"
                ),
                **reconciliation,
                "window_count": window_count,
            }
        except Exception as e:
            await self.db.rollback()
            logger.exception(
                "[同步服务] 同步重新发货订单失败 - 店铺: %s",
                self.shop.id,
            )
            return {
                "status": "error",
                "message": f"同步重新发货订单失败: {str(e)}",
            }

    async def sync_order_metadata(
        self,
        *,
        window_start: datetime,
        window_end: datetime,
    ) -> Dict[str, Any]:
        """Enrich existing Marketplace orders with FBS assembly metadata."""
        logger.info(
            "[同步服务] 开始同步订单元数据 - 店铺: %s, 窗口: %s ~ %s",
            self.shop.id,
            window_start,
            window_end,
        )
        if not self.client.marketplace:
            return {
                "status": "error",
                "message": "Marketplace API client not configured",
            }
        if window_start >= window_end:
            return {
                "status": "error",
                "message": "订单元数据同步窗口起点必须早于终点",
            }

        try:
            order_ids = await crud_ods_wb_order_metadata.get_source_order_ids(
                self.db,
                shop_id=self.shop.id,
                window_start=window_start,
                window_end=window_end,
            )
            if not order_ids:
                return {
                    "status": "success",
                    "message": "时间窗口内没有可补全元数据的现有订单",
                    "source_count": 0,
                    "count": 0,
                    "ods_count": 0,
                    "batch_count": 0,
                }

            metadata_by_order_id: Dict[int, Dict[str, Any]] = {}
            batch_count = 0
            async with self.client:
                for start in range(0, len(order_ids), 100):
                    batch = order_ids[start : start + 100]
                    response = await self.client.marketplace.get_orders_metadata(batch)
                    batch_count += 1
                    response_orders = (
                        response.get("orders", []) if isinstance(response, dict) else []
                    )
                    for item in response_orders:
                        if not isinstance(item, dict):
                            continue
                        try:
                            metadata_by_order_id[int(item.get("id"))] = item
                        except (TypeError, ValueError):
                            logger.warning(
                                "[同步服务] 跳过缺少有效 id 的订单元数据响应: %s",
                                item,
                            )

            metadata = list(metadata_by_order_id.values())
            ods_count = await crud_ods_wb_order_metadata.upsert_many(
                self.db,
                metadata=metadata,
                shop_id=self.shop.id,
                synced_at=window_end,
            )
            return {
                "status": "success",
                "message": (
                    f"查询了 {len(order_ids)} 个现有订单，"
                    f"获取 {len(metadata)} 条元数据，写入 {ods_count} 条"
                ),
                "source_count": len(order_ids),
                "count": len(metadata),
                "ods_count": ods_count,
                "batch_count": batch_count,
            }
        except Exception as e:
            logger.exception(
                "[同步服务] 同步订单元数据失败 - 店铺: %s",
                self.shop.id,
            )
            return {
                "status": "error",
                "message": f"同步订单元数据失败: {str(e)}",
            }

    async def sync_balance(
        self, date_from: Optional[str] = None, date_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """同步余额和cashback数据

        余额为实时快照，无需日期区间；保留可选参数是为了与 sync_all 中
        统一的 (date_from, date_to) 调用签名兼容。
        """
        logger.debug(f"[同步服务] 开始同步余额和cashback - 店铺: {self.shop.id}")
        if not self.client.advert:
            return {"status": "error", "message": "Advert API client not configured"}

        try:
            async with self.client:
                # 获取余额数据
                balance_result = await self.client.advert.get_balance()
                logger.debug(f"[同步服务] 获取余额数据: {balance_result}")

                ods_balance_count = 0
                ods_cashback_count = 0

                if balance_result:
                    # 保存余额
                    ods_balance = await crud_ods_wb_balance.create_or_update(
                        self.db,
                        balance_data=balance_result,
                        shop_id=self.shop.id,
                    )
                    ods_balance_count = 1

                    # 保存cashback（官方文档字段名为 cashbacks 数组）
                    cashbacks = balance_result.get("cashbacks", [])
                    if cashbacks:
                        for cashback_item in cashbacks:
                            ods_cashback = await crud_ods_wb_cashback.create_or_update(
                                self.db,
                                cashback_data=cashback_item,
                                shop_id=self.shop.id,
                            )
                            if ods_cashback:
                                ods_cashback_count += 1

                result = {
                    "status": "success",
                    "message": f"余额同步完成（余额: {ods_balance_count}条，cashback: {ods_cashback_count}条）",
                    "balance_count": ods_balance_count,
                    "cashback_count": ods_cashback_count,
                }
                logger.debug(f"[同步服务] 余额同步完成: {result}")
                return result
        except Exception as e:
            logger.error(f"[同步服务] 同步余额失败: {str(e)}")
            import traceback

            logger.error(f"[同步服务] 错误堆栈: {traceback.format_exc()}")
            return {"status": "error", "message": f"同步余额失败: {str(e)}"}

    async def sync_seller_balance(self) -> Dict[str, Any]:
        """同步财务域卖家当前余额并保存每日快照。"""
        logger.info("[同步服务] 开始同步卖家余额 - 店铺: %s", self.shop.id)
        if not self.client.finance:
            return {"status": "error", "message": "Finance API client not configured"}

        try:
            async with self.client:
                balance_result = await self.client.finance.get_balance()
                if not balance_result:
                    return {
                        "status": "success",
                        "message": "卖家余额接口未返回数据",
                        "count": 0,
                    }

                await crud_ods_wb_seller_balance.upsert_snapshot(
                    self.db,
                    shop_id=self.shop.id,
                    balance_data=balance_result,
                )
                return {
                    "status": "success",
                    "message": "卖家余额同步完成",
                    "count": 1,
                }
        except Exception as e:
            logger.exception("[同步服务] 同步卖家余额失败: %s", e)
            return {"status": "error", "message": f"同步卖家余额失败: {str(e)}"}

    async def sync_sales_report_list(
        self,
        date_from: str,
        date_to: str,
    ) -> Dict[str, Any]:
        """同步指定自然周的财务报表列表。"""
        if not self.client.finance:
            return {"status": "error", "message": "Finance API client not configured"}

        try:
            start_date = date.fromisoformat(date_from)
            end_date = date.fromisoformat(date_to)
        except ValueError:
            return {
                "status": "error",
                "message": "财务报表列表日期格式必须为 YYYY-MM-DD",
            }
        if start_date > end_date:
            return {
                "status": "error",
                "message": "财务报表列表开始日期不能晚于结束日期",
            }

        try:
            async with self.client:
                reports: List[Dict[str, Any]] = []
                limit = 1000
                offset = 0
                max_pages = 10

                for page_number in range(max_pages):
                    response = await self.client.finance.get_sales_reports_list(
                        date_from,
                        date_to,
                        limit=limit,
                        offset=offset,
                        period="weekly",
                    )
                    if isinstance(response, list):
                        page = response
                    elif isinstance(response, dict):
                        data = response.get("data", response.get("items", []))
                        page = data if isinstance(data, list) else []
                    else:
                        page = []

                    reports.extend(item for item in page if isinstance(item, dict))
                    if len(page) < limit:
                        break

                    offset += limit
                    if page_number < max_pages - 1:
                        # 官方限制为每个卖家账户每分钟 1 次。
                        await asyncio.sleep(60)

                records = await crud_ods_wb_sales_report_list.upsert_many(
                    self.db,
                    shop_id=self.shop.id,
                    reports=reports,
                )
                try:
                    dwd_stats = await wb_dwd_service.sync_sales_report_summary(
                        self.db,
                        shop_id=self.shop.id,
                    )
                except Exception as dwd_error:
                    logger.error(
                        "财务报表列表 ODS 已保存，但周汇总 DWD 同步失败: %s",
                        dwd_error,
                    )
                    return {
                        "status": "error",
                        "message": (
                            f"ODS 已保存 {len(records)} 条，但周汇总 DWD 同步失败: "
                            f"{dwd_error}"
                        ),
                        "count": len(reports),
                        "ods_count": len(records),
                        "dwd_status": "error",
                        "date_from": date_from,
                        "date_to": date_to,
                    }
                return {
                    "status": "success",
                    "message": f"财务报表列表同步完成，共保存 {len(records)} 条",
                    "count": len(reports),
                    "ods_count": len(records),
                    "dwd_scanned": dwd_stats["scanned"],
                    "dwd_created": dwd_stats["created"],
                    "dwd_updated": dwd_stats["updated"],
                    "date_from": date_from,
                    "date_to": date_to,
                }
        except Exception as e:
            logger.exception("[同步服务] 同步财务报表列表失败: %s", e)
            return {
                "status": "error",
                "message": f"同步财务报表列表失败: {str(e)}",
            }

    async def sync_region_sales(
        self,
        date_from: str,
        date_to: str,
    ) -> Dict[str, Any]:
        """同步指定完整日期窗口的区域销售聚合报告。"""
        if not self.client.analytics:
            return {"status": "error", "message": "Analytics API client not configured"}

        try:
            start_date = date.fromisoformat(date_from)
            end_date = date.fromisoformat(date_to)
        except ValueError:
            return {
                "status": "error",
                "message": "区域销售报告日期格式必须为 YYYY-MM-DD",
            }

        period_days = (end_date - start_date).days + 1
        if period_days < 1 or period_days > 31:
            return {
                "status": "error",
                "message": "区域销售报告日期范围必须为 1 至 31 天",
            }

        logger.info(
            "[同步服务] 开始同步区域销售报告 - 店铺: %s, 日期: %s~%s",
            self.shop.id,
            date_from,
            date_to,
        )
        try:
            async with self.client:
                response = await self.client.analytics.get_region_sales(
                    date_from,
                    date_to,
                )
                report_data = response.get("report", []) if response else []
                if not isinstance(report_data, list):
                    return {
                        "status": "error",
                        "message": "区域销售报告返回格式异常",
                    }

                records = await crud_ods_wb_region_sale.upsert_many(
                    self.db,
                    shop_id=self.shop.id,
                    date_from=start_date,
                    date_to=end_date,
                    report_data=report_data,
                )
                return {
                    "status": "success",
                    "message": f"区域销售报告同步完成: {len(records)} 条",
                    "count": len(records),
                    "date_from": date_from,
                    "date_to": date_to,
                }
        except Exception as e:
            logger.exception("[同步服务] 同步区域销售报告失败: %s", e)
            return {
                "status": "error",
                "message": f"同步区域销售报告失败: {str(e)}",
            }

    async def sync_product_search_texts(
        self,
        date_from: str,
        date_to: str,
        *,
        top_order_by: str = "openCard",
    ) -> Dict[str, Any]:
        """同步指定完整日期窗口内全部商品的自然搜索词表现。"""
        if not self.client.analytics:
            return {"status": "error", "message": "Analytics API client not configured"}

        try:
            start_date = date.fromisoformat(date_from)
            end_date = date.fromisoformat(date_to)
        except ValueError:
            return {"status": "error", "message": "商品搜索词日期格式必须为 YYYY-MM-DD"}
        period_days = (end_date - start_date).days + 1
        if period_days < 1 or period_days > 31:
            return {"status": "error", "message": "商品搜索词日期范围必须为 1 至 31 天"}

        logger.info(
            "[同步服务] 开始同步商品搜索词 - 店铺: %s, 日期: %s~%s",
            self.shop.id,
            date_from,
            date_to,
        )
        try:
            async with self.client:
                nm_ids: List[int] = []
                offset = 0
                page_limit = 1000
                while True:
                    response = await self.client.analytics.get_search_report_products(
                        date_from,
                        date_to,
                        limit=page_limit,
                        offset=offset,
                    )
                    data = response.get("data", response) if response else {}
                    products = data.get("products") or data.get("items") or []
                    if not isinstance(products, list):
                        return {
                            "status": "error",
                            "message": "商品搜索报告商品列表格式异常",
                        }

                    for product in products:
                        details = product.get("product") or product
                        nm_id = (
                            details.get("nmId") if isinstance(details, dict) else None
                        )
                        if nm_id is not None:
                            nm_ids.append(int(nm_id))

                    if not products or data.get("isNextPage") is False:
                        break
                    if len(products) < page_limit:
                        break
                    offset += page_limit

                unique_nm_ids = list(dict.fromkeys(nm_ids))
                all_items: List[Dict[str, Any]] = []
                currency = None
                request_count = 0
                for start in range(0, len(unique_nm_ids), 50):
                    response = await self.client.analytics.get_product_search_texts(
                        date_from,
                        date_to,
                        unique_nm_ids[start : start + 50],
                        top_order_by=top_order_by,
                        limit=30,
                    )
                    request_count += 1
                    data = response.get("data", response) if response else {}
                    items = data.get("items") or []
                    if not isinstance(items, list):
                        return {"status": "error", "message": "商品搜索词返回格式异常"}
                    all_items.extend(items)
                    currency = data.get("currency") or currency

                records = await crud_ods_wb_product_search_text.upsert_many(
                    self.db,
                    shop_id=self.shop.id,
                    date_from=start_date,
                    date_to=end_date,
                    items=all_items,
                    currency=currency,
                    top_order_by=top_order_by,
                )
                return {
                    "status": "success",
                    "message": f"商品搜索词同步完成: {len(records)} 条",
                    "count": len(records),
                    "product_count": len(unique_nm_ids),
                    "request_count": request_count,
                    "date_from": date_from,
                    "date_to": date_to,
                }
        except Exception as e:
            logger.exception("[同步服务] 同步商品搜索词失败: %s", e)
            return {"status": "error", "message": f"同步商品搜索词失败: {str(e)}"}

    async def sync_search_traffic(
        self,
        date_from: str,
        date_to: str,
        *,
        position_cluster: str = "all",
    ) -> Dict[str, Any]:
        """同步指定滚动窗口内的商品搜索流量。"""
        if not self.client.analytics:
            return {"status": "error", "message": "Analytics API client not configured"}

        try:
            start_date = date.fromisoformat(date_from)
            end_date = date.fromisoformat(date_to)
        except ValueError:
            return {"status": "error", "message": "搜索流量日期格式必须为 YYYY-MM-DD"}
        period_days = (end_date - start_date).days + 1
        if period_days < 1 or period_days > 31:
            return {"status": "error", "message": "搜索流量日期范围必须为 1 至 31 天"}
        past_end_date = start_date - timedelta(days=1)
        past_start_date = past_end_date - timedelta(days=period_days - 1)
        past_date_from = past_start_date.isoformat()
        past_date_to = past_end_date.isoformat()

        logger.info(
            "[同步服务] 开始同步搜索流量 - 店铺: %s, 日期: %s~%s",
            self.shop.id,
            date_from,
            date_to,
        )
        try:
            async with self.client:
                products: List[Dict[str, Any]] = []
                currency = None
                offset = 0
                page_limit = 1000
                request_count = 0
                while True:
                    response = await self.client.analytics.get_search_report_products(
                        date_from,
                        date_to,
                        limit=page_limit,
                        offset=offset,
                        position_cluster=position_cluster,
                        past_date_from=past_date_from,
                        past_date_to=past_date_to,
                    )
                    request_count += 1
                    data = response.get("data", response) if response else {}
                    page_products = data.get("products") or data.get("items") or []
                    if not isinstance(page_products, list):
                        return {"status": "error", "message": "搜索流量返回格式异常"}
                    products.extend(page_products)
                    currency = data.get("currency") or currency

                    if not page_products or data.get("isNextPage") is False:
                        break
                    if len(page_products) < page_limit:
                        break
                    offset += page_limit

                records = await crud_ods_wb_search_traffic.upsert_many(
                    self.db,
                    shop_id=self.shop.id,
                    date_from=start_date,
                    date_to=end_date,
                    products=products,
                    currency=currency,
                    position_cluster=position_cluster,
                )
                return {
                    "status": "success",
                    "message": f"搜索流量同步完成: {len(records)} 条",
                    "count": len(records),
                    "request_count": request_count,
                    "date_from": date_from,
                    "date_to": date_to,
                    "past_date_from": past_date_from,
                    "past_date_to": past_date_to,
                }
        except Exception as e:
            logger.exception("[同步服务] 同步搜索流量失败: %s", e)
            return {"status": "error", "message": f"同步搜索流量失败: {str(e)}"}

    @staticmethod
    def _flatten_advert_stats(stats_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        将 API 返回的广告统计展平为商品维度列表

        API 结构: advert_stat -> days[] -> apps[] -> nms[]
        输出: [{advert_id, nm_id, app_type, views, clicks, ...}, ...]
        """
        flat_list = []
        for advert_stat in stats_data:
            advert_id = advert_stat.get("advertId") or advert_stat.get("advert_id")
            currency = advert_stat.get("currency")
            days = advert_stat.get("days", [])

            for day_data in days:
                apps = day_data.get("apps", [])
                if apps:
                    for app in apps:
                        app_type = app.get("appType") or app.get("app_type")
                        nms = app.get("nms", [])
                        for nm_data in nms:
                            nm_id = nm_data.get("nmId")
                            if not nm_id:
                                continue
                            flat_list.append(
                                {
                                    "advert_id": advert_id,
                                    "nm_id": nm_id,
                                    "nm_name": nm_data.get("name"),
                                    "app_type": app_type,
                                    "views": nm_data.get("views"),
                                    "clicks": nm_data.get("clicks"),
                                    "atbs": nm_data.get("atbs"),
                                    "orders": nm_data.get("orders"),
                                    "canceled": nm_data.get("canceled"),
                                    "shks": nm_data.get("shks"),
                                    "sum_cost": nm_data.get("sum"),
                                    "sum_price": nm_data.get("sum_price"),
                                    "cpc": nm_data.get("cpc"),
                                    "ctr": nm_data.get("ctr"),
                                    "cr": nm_data.get("cr"),
                                    "currency": currency,
                                    "row_data": nm_data,
                                }
                            )
        return flat_list

    async def sync_advert_stats_hourly(self) -> Dict[str, Any]:
        """
        同步广告统计数据（小时维度）

        1. 从数据库查询该店铺所有广告ID
        2. 调用 API 获取今天的整天累计数据
        3. 查询今天已写入的小时累计（排除当前小时）
        4. 计算当前小时增量
        5. 幂等写入小时表
        """
        logger.debug(f"[同步服务] 开始同步广告小时统计 - 店铺: {self.shop.id}")
        if not self.client.advert:
            return {"status": "error", "message": "Advert API client not configured"}

        # 按平台业务时区(莫斯科)判定当前小时/日期
        now = now_platform()
        # 跨天边界处理：00:00-00:10 执行时，结算昨天的 23:00 数据
        if now.hour == 0 and now.minute < 10:
            stat_date = (now - timedelta(days=1)).date()
            stat_hour = 23
        else:
            stat_date = now.date()
            stat_hour = now.hour
        today_str = stat_date.strftime("%Y-%m-%d")

        try:
            async with self.client:
                # 1. 获取广告ID列表
                advert_result = await self.client.advert.get_adverts_list()
                adverts_data = advert_result.get("adverts", [])
                advert_ids = [adv.get("id") for adv in adverts_data if adv.get("id")]

                if not advert_ids:
                    return {"status": "success", "message": "没有广告活动", "count": 0}

                # 2. 调用 API 获取今天整天累计数据
                stats_data = await self.client.advert.get_advert_stats(
                    advert_ids=advert_ids,
                    begin_date=today_str,
                    end_date=today_str,
                )

                if not stats_data:
                    return {
                        "status": "success",
                        "message": "API 返回空数据",
                        "count": 0,
                    }

                # 展平为商品维度
                flat_stats = self._flatten_advert_stats(stats_data)

                # 3. 查询已写入的小时累计（排除当前小时）
                hourly_sums = (
                    await crud_ods_wb_advert_stat_hourly.get_hourly_sum_before_hour(
                        self.db, self.shop.id, stat_date, stat_hour
                    )
                )

                # 4. 计算当前小时增量
                hourly_records = []
                for record in flat_stats:
                    key = (record["advert_id"], record["nm_id"], record["app_type"])
                    written = hourly_sums.get(
                        key,
                        {
                            "views": 0,
                            "clicks": 0,
                            "atbs": 0,
                            "orders": 0,
                            "canceled": 0,
                            "shks": 0,
                            "sum_cost": 0,
                            "sum_price": 0,
                        },
                    )

                    # 计算增量（负数则置为0）
                    record["views"] = max(0, (record["views"] or 0) - written["views"])
                    record["clicks"] = max(
                        0, (record["clicks"] or 0) - written["clicks"]
                    )
                    record["atbs"] = max(0, (record["atbs"] or 0) - written["atbs"])
                    record["orders"] = max(
                        0, (record["orders"] or 0) - written["orders"]
                    )
                    record["canceled"] = max(
                        0, (record["canceled"] or 0) - written["canceled"]
                    )
                    record["shks"] = max(0, (record["shks"] or 0) - written["shks"])
                    record["sum_cost"] = max(
                        0, (record["sum_cost"] or 0) - written["sum_cost"]
                    )
                    record["sum_price"] = max(
                        0, (record["sum_price"] or 0) - written["sum_price"]
                    )

                    # 跳过全为0的记录
                    if any(
                        [
                            record["views"],
                            record["clicks"],
                            record["atbs"],
                            record["orders"],
                            record["canceled"],
                            record["shks"],
                            record["sum_cost"],
                            record["sum_price"],
                        ]
                    ):
                        hourly_records.append(record)

                # 5. 幂等写入
                await crud_ods_wb_advert_stat_hourly.upsert_many(
                    self.db,
                    stats_data=hourly_records,
                    shop_id=self.shop.id,
                    stat_date=stat_date,
                    stat_hour=stat_hour,
                )

                try:
                    dwd_result = await wb_dwd_service.sync_advert_stats(
                        self.db,
                        shop_id=self.shop.id,
                        date_from=stat_date,
                        date_to=stat_date,
                    )
                except Exception as dwd_error:
                    logger.exception(
                        "[同步服务] 广告小时 ODS 已保存，但 DWD 构建失败 - 店铺: %s",
                        self.shop.id,
                    )
                    return {
                        "status": "partial_success",
                        "message": (
                            f"广告小时 ODS 已同步 {len(hourly_records)} 条，"
                            f"但 DWD 构建失败: {dwd_error}"
                        ),
                        "count": len(hourly_records),
                        "stat_date": stat_date.isoformat(),
                        "stat_hour": stat_hour,
                        "dwd_status": "error",
                    }

                return {
                    "status": "success",
                    "message": f"广告小时统计同步完成: {len(hourly_records)} 条",
                    "count": len(hourly_records),
                    "stat_date": stat_date.isoformat(),
                    "stat_hour": stat_hour,
                    "dwd_status": "success",
                    "dwd": dwd_result,
                }
        except Exception as e:
            logger.error(f"[同步服务] 同步广告小时统计失败: {str(e)}")
            import traceback

            logger.error(f"[同步服务] 错误堆栈: {traceback.format_exc()}")
            return {"status": "error", "message": f"同步广告小时统计失败: {str(e)}"}

    async def sync_search_cluster_stat_hourly(self) -> Dict[str, Any]:
        """
        同步搜索关键字统计数据（小时维度）

        1. 从数据库获取 advert-nm 映射
        2. 调用 API 获取今天的整天累计数据
        3. 查询今天已写入的小时累计（排除当前小时）
        4. 计算当前小时增量
        5. 幂等写入小时表
        """
        logger.debug(f"[同步服务] 开始同步搜索关键字小时统计 - 店铺: {self.shop.id}")
        if not self.client.advert:
            return {"status": "error", "message": "Advert API client not configured"}

        # 按平台业务时区(莫斯科)判定当前小时/日期
        now = now_platform()
        # 跨天边界处理：00:00-00:10 执行时，结算昨天的 23:00 数据
        if now.hour == 0 and now.minute < 10:
            stat_date = (now - timedelta(days=1)).date()
            stat_hour = 23
        else:
            stat_date = now.date()
            stat_hour = now.hour
        today_str = stat_date.strftime("%Y-%m-%d")

        try:
            async with self.client:
                # 1. 获取 advert-nm 映射
                advert_result = await self.client.advert.get_adverts_list()
                adverts_data = advert_result.get("adverts", [])
                advert_ids = [adv.get("id") for adv in adverts_data if adv.get("id")]

                if not advert_ids:
                    return {"status": "success", "message": "没有广告活动", "count": 0}

                advert_nm_map = await crud_ods_wb_advert_product.get_advert_nm_map(
                    self.db, shop_id=self.shop.id, advert_ids=advert_ids
                )

                if not advert_nm_map:
                    return {
                        "status": "success",
                        "message": "没有广告商品映射",
                        "count": 0,
                    }

                # 2. 调用 API 获取搜索关键字统计
                search_stats = await self.client.advert.get_normquery_stats(
                    advert_nm_map=advert_nm_map,
                    begin_date=today_str,
                    end_date=today_str,
                )

                if not search_stats:
                    return {
                        "status": "success",
                        "message": "API 返回空数据",
                        "count": 0,
                    }

                # 展平数据（复用 search_cluster_stat CRUD 的逻辑）
                flat_stats = []
                for raw in search_stats:
                    if not isinstance(raw, dict):
                        continue
                    stat_dict = raw.get("stat")
                    advert_id = raw.get("advertId") or raw.get("advert_id")
                    nm_id = raw.get("nmId") or raw.get("nm_id")

                    if isinstance(stat_dict, dict) and len(stat_dict) > 0:
                        merged = dict(raw)
                        merged.pop("stat", None)
                        merged.update(stat_dict)
                        if advert_id is not None:
                            merged["advertId"] = advert_id
                        if nm_id is not None:
                            merged["nmId"] = nm_id
                        flat_stats.append(merged)
                    elif isinstance(stat_dict, list) and len(stat_dict) > 0:
                        for ds in stat_dict:
                            if isinstance(ds, dict):
                                if advert_id is not None and "advertId" not in ds:
                                    ds["advertId"] = advert_id
                                if nm_id is not None and "nmId" not in ds:
                                    ds["nmId"] = nm_id
                                flat_stats.append(ds)
                    else:
                        flat_stats.append(raw)

                # 解析为统一格式
                parsed_records = []
                for stat_data in flat_stats:
                    advert_id = stat_data.get("advertId") or stat_data.get("advert_id")
                    nm_id = stat_data.get("nmId") or stat_data.get("nm_id")
                    norm_query = stat_data.get("normQuery") or stat_data.get(
                        "norm_query"
                    )

                    if not nm_id:
                        continue

                    parsed_records.append(
                        {
                            "advert_id": advert_id,
                            "nm_id": nm_id,
                            "norm_query": norm_query,
                            "views": _get_val(stat_data, "views", "view", "shows"),
                            "clicks": _get_val(stat_data, "clicks", "click"),
                            "sum_cost": _get_val(
                                stat_data, "sum", "sumCost", "cost", "spend", "sum_cost"
                            ),
                            "atbs": _get_val(stat_data, "atbs", "atb", "addToBaskets"),
                            "orders": _get_val(stat_data, "orders", "order"),
                            "cpc": _get_val(stat_data, "cpc", "cpcValue"),
                            "ctr": _get_val(stat_data, "ctr", "ctrValue"),
                            "cr": _get_val(
                                stat_data, "cr", "crValue", "conversionRate"
                            ),
                            "row_data": stat_data,
                        }
                    )

                # 3. 查询已写入的小时累计（排除当前小时）
                hourly_sums = await crud_ods_wb_search_cluster_stat_hourly.get_hourly_sum_before_hour(
                    self.db, self.shop.id, stat_date, stat_hour
                )

                # 4. 计算当前小时增量
                hourly_records = []
                for record in parsed_records:
                    key = (record["advert_id"], record["nm_id"], record["norm_query"])
                    written = hourly_sums.get(
                        key,
                        {
                            "views": 0,
                            "clicks": 0,
                            "sum_cost": 0,
                            "atbs": 0,
                            "orders": 0,
                        },
                    )

                    record["views"] = max(0, (record["views"] or 0) - written["views"])
                    record["clicks"] = max(
                        0, (record["clicks"] or 0) - written["clicks"]
                    )
                    record["sum_cost"] = max(
                        0, (record["sum_cost"] or 0) - written["sum_cost"]
                    )
                    record["atbs"] = max(0, (record["atbs"] or 0) - written["atbs"])
                    record["orders"] = max(
                        0, (record["orders"] or 0) - written["orders"]
                    )

                    if any(
                        [
                            record["views"],
                            record["clicks"],
                            record["sum_cost"],
                            record["atbs"],
                            record["orders"],
                        ]
                    ):
                        hourly_records.append(record)

                # 5. 幂等写入
                await crud_ods_wb_search_cluster_stat_hourly.upsert_many(
                    self.db,
                    stats_data=hourly_records,
                    shop_id=self.shop.id,
                    stat_date=stat_date,
                    stat_hour=stat_hour,
                )

                return {
                    "status": "success",
                    "message": f"搜索关键字小时统计同步完成: {len(hourly_records)} 条",
                    "count": len(hourly_records),
                }
        except Exception as e:
            logger.error(f"[同步服务] 同步搜索关键字小时统计失败: {str(e)}")
            import traceback

            logger.error(f"[同步服务] 错误堆栈: {traceback.format_exc()}")
            return {
                "status": "error",
                "message": f"同步搜索关键字小时统计失败: {str(e)}",
            }

    async def sync_all(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        sync_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """同步所有数据"""
        logger.debug(
            f"[同步服务] 开始全量同步 - 店铺: {self.shop.id}, 类型: {sync_types}"
        )
        if not sync_types:
            sync_types = [
                "sales",
                "orders",
                "funnel",
                "returns",
                "adverts",
                "feedbacks",
                "questions",
                "finance",
                "marketplace_orders",
                "balance",
                "norm_query_bids",
                "norm_query_minus",
                "norm_query_list",
                "norm_query_stats",
                "promotion_count",
                "bid_recommendations",
                "advert_fullstats",
                "adverts_v2",
            ]

        results: Dict[str, Any] = {
            "status": "success",
            "results": {},
        }

        sync_functions = {
            "sales": self.sync_sales,
            "orders": self.sync_orders,
            "funnel": self.sync_funnel,
            "returns": self.sync_returns,
            "adverts": self.sync_adverts,
            "feedbacks": self.sync_feedbacks,
            "questions": self.sync_questions,
            "finance": self.sync_finance,
            "marketplace_orders": self.sync_marketplace_orders,
            "balance": self.sync_balance,
            "norm_query_bids": self.sync_norm_query_bids,
            "norm_query_minus": self.sync_norm_query_minus,
            "norm_query_list": self.sync_norm_query_list,
            "norm_query_stats": self.sync_norm_query_stats,
            "promotion_count": self.sync_promotion_count,
            "bid_recommendations": self.sync_bid_recommendations,
            "advert_fullstats": self.sync_advert_fullstats,
            "adverts_v2": self.sync_adverts_v2,
        }

        for sync_type in sync_types:
            if sync_type in sync_functions:
                logger.debug(f"[同步服务] 执行同步类型: {sync_type}")
                if sync_type == "funnel" and date_from is None and date_to is None:
                    result = await self.sync_funnel_lookback()
                else:
                    result = await sync_functions[sync_type](date_from, date_to)
                results["results"][sync_type] = result

        logger.debug(f"[同步服务] 全量同步完成: {results}")
        return results

    async def _safe_datetime_async(self, value: Any) -> Any:
        """异步安全转换为 datetime (处理ISO8601格式)"""
        from datetime import datetime

        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            # 处理 '2026-03-23T10:26:17Z' 格式
            if isinstance(value, str) and value.endswith("Z"):
                value = value.replace("Z", "+00:00")
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None

    async def sync_norm_query_bids(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """同步标准查询竞价数据"""
        logger.debug(f"[同步服务] 开始同步标准查询竞价 - 店铺: {self.shop.id}")
        if not self.client.advert:
            return {"status": "error", "message": "Advert API client not configured"}

        try:
            async with self.client:
                # 直接调用API（客户端内部会自动获取广告列表）
                bids_data = await self.client.advert.get_norm_query_bids()

                total_count = 0
                if bids_data and isinstance(bids_data, list):
                    try:
                        ods_records = await crud_ods_wb_norm_query_bid.upsert_many(
                            self.db,
                            bids_data=bids_data,
                            shop_id=self.shop.id,
                        )
                        total_count = len(ods_records)
                    except SQLAlchemyError as e:
                        logger.error(f"[同步服务] 数据库操作失败: {e}")
                        await self._safe_rollback()
                        return {"status": "error", "message": f"数据库操作失败: {e}"}

                result = {
                    "status": "success",
                    "message": f"同步了 {total_count} 条标准查询竞价数据",
                    "count": total_count,
                    "api_count": len(bids_data) if isinstance(bids_data, list) else 0,
                }
                logger.debug(f"[同步服务] 标准查询竞价同步完成: {result}")
                return result
        except Exception as e:
            logger.error(f"[同步服务] 同步标准查询竞价失败: {e}")
            import traceback

            logger.error(f"[同步服务] 错误堆栈: {traceback.format_exc()}")
            await self._safe_rollback()
            return {"status": "error", "message": f"同步标准查询竞价失败: {e}"}

    async def sync_norm_query_minus(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """同步排除关键词数据"""
        logger.debug(f"[同步服务] 开始同步排除关键词 - 店铺: {self.shop.id}")
        if not self.client.advert:
            return {"status": "error", "message": "Advert API client not configured"}

        try:
            async with self.client:
                minus_data = await self.client.advert.get_norm_query_minus()

                total_count = 0
                if minus_data and isinstance(minus_data, list):
                    try:
                        ods_records = await crud_ods_wb_norm_query_minus.upsert_many(
                            self.db,
                            minus_data=minus_data,
                            shop_id=self.shop.id,
                        )
                        total_count = len(ods_records)
                    except SQLAlchemyError as e:
                        logger.error(f"[同步服务] 数据库操作失败: {e}")
                        await self._safe_rollback()
                        return {"status": "error", "message": f"数据库操作失败: {e}"}

                result = {
                    "status": "success",
                    "message": f"同步了 {total_count} 条排除关键词数据",
                    "count": total_count,
                    "api_count": len(minus_data) if isinstance(minus_data, list) else 0,
                }
                logger.debug(f"[同步服务] 排除关键词同步完成: {result}")
                return result
        except Exception as e:
            logger.error(f"[同步服务] 同步排除关键词失败: {e}")
            await self._safe_rollback()
            return {"status": "error", "message": f"同步排除关键词失败: {e}"}

    async def sync_norm_query_list(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """同步标准查询列表数据"""
        logger.debug(f"[同步服务] 开始同步标准查询列表 - 店铺: {self.shop.id}")
        if not self.client.advert:
            return {"status": "error", "message": "Advert API client not configured"}

        try:
            async with self.client:
                list_data = await self.client.advert.get_norm_query_list()

                total_count = 0
                if list_data and isinstance(list_data, list):
                    try:
                        ods_records = await crud_ods_wb_norm_query_list.upsert_many(
                            self.db,
                            list_data=list_data,
                            shop_id=self.shop.id,
                        )
                        total_count = len(ods_records)
                    except SQLAlchemyError as e:
                        logger.error(f"[同步服务] 数据库操作失败: {e}")
                        await self._safe_rollback()
                        return {"status": "error", "message": f"数据库操作失败: {e}"}

                result = {
                    "status": "success",
                    "message": f"同步了 {total_count} 条标准查询列表数据",
                    "count": total_count,
                    "api_count": len(list_data) if isinstance(list_data, list) else 0,
                }
                logger.debug(f"[同步服务] 标准查询列表同步完成: {result}")
                return result
        except Exception as e:
            logger.error(f"[同步服务] 同步标准查询列表失败: {e}")
            await self._safe_rollback()
            return {"status": "error", "message": f"同步标准查询列表失败: {e}"}

    async def sync_norm_query_stats(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """同步标准查询统计数据"""
        logger.debug(f"[同步服务] 开始同步标准查询统计 - 店铺: {self.shop.id}")
        if not self.client.advert:
            return {"status": "error", "message": "Advert API client not configured"}

        date_from_str, date_to_str = await self._get_date_range(date_from, date_to)
        ods_date_from = date.fromisoformat(date_from_str) if date_from_str else None

        try:
            async with self.client:
                stats_data = await self.client.advert.get_norm_query_stats(
                    from_date=date_from_str,
                    to_date=date_to_str,
                )

                total_count = 0
                if stats_data and isinstance(stats_data, list):
                    try:
                        ods_stats = await crud_ods_wb_norm_query_stat.upsert_many(
                            self.db,
                            stats_data=stats_data,
                            shop_id=self.shop.id,
                            date_from=ods_date_from,
                        )
                        total_count = len(ods_stats)
                    except SQLAlchemyError as e:
                        logger.error(f"[同步服务] 数据库操作失败: {e}")
                        await self._safe_rollback()
                        return {"status": "error", "message": f"数据库操作失败: {e}"}

                result = {
                    "status": "success",
                    "message": f"同步了 {total_count} 条标准查询统计数据",
                    "count": total_count,
                    "api_count": len(stats_data) if isinstance(stats_data, list) else 0,
                }
                logger.debug(f"[同步服务] 标准查询统计同步完成: {result}")
                return result
        except Exception as e:
            logger.error(f"[同步服务] 同步标准查询统计失败: {e}")
            import traceback

            logger.error(f"[同步服务] 错误堆栈: {traceback.format_exc()}")
            await self._safe_rollback()
            return {"status": "error", "message": f"同步标准查询统计失败: {e}"}

    async def sync_promotion_count(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """同步促销计数数据"""
        logger.debug(f"[同步服务] 开始同步促销计数 - 店铺: {self.shop.id}")
        if not self.client.advert:
            return {"status": "error", "message": "Advert API client not configured"}

        try:
            async with self.client:
                promotion_data = await self.client.advert.get_promotion_count()

                total_count = 0
                if promotion_data:
                    # 提取 adverts 数组
                    adverts_list = (
                        promotion_data.get("adverts", [])
                        if isinstance(promotion_data, dict)
                        else []
                    )
                    if adverts_list and isinstance(adverts_list, list):
                        try:
                            ods_records = await crud_ods_wb_promotion_count.upsert_many(
                                self.db,
                                promotion_data=adverts_list,
                                shop_id=self.shop.id,
                            )
                            total_count = len(ods_records)
                        except SQLAlchemyError as e:
                            logger.error(f"[同步服务] 数据库操作失败: {e}")
                            await self._safe_rollback()
                            return {
                                "status": "error",
                                "message": f"数据库操作失败: {e}",
                            }

                result = {
                    "status": "success",
                    "message": f"同步了 {total_count} 条促销计数数据",
                    "count": total_count,
                }
                logger.debug(f"[同步服务] 促销计数同步完成: {result}")
                return result
        except Exception as e:
            logger.error(f"[同步服务] 同步促销计数失败: {e}")
            await self._safe_rollback()
            return {"status": "error", "message": f"同步促销计数失败: {e}"}

    async def sync_bid_recommendations(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """同步竞价推荐数据"""
        logger.debug(f"[同步服务] 开始同步竞价推荐 - 店铺: {self.shop.id}")
        if not self.client.advert:
            return {"status": "error", "message": "Advert API client not configured"}

        # 先收集所有需要的数据结构
        all_data = []

        try:
            # ========== 第一步：只调用 API，不操作数据库 ==========
            async with self.client:
                adverts_result = await self.client.advert.get_adverts_list()
                adverts_data = (
                    adverts_result.get("adverts", [])
                    if isinstance(adverts_result, dict)
                    else adverts_result
                )

                for advert in adverts_data:
                    advert_id = advert.get("id") or advert.get("advertId")
                    if not advert_id:
                        continue
                    # 获取商品ID
                    nm_list = advert.get("nm", []) or advert.get("nms", [])
                    if not nm_list:
                        # 尝试从 nm_settings 或其他字段获取
                        nm_settings = advert.get("nm_settings", []) or advert.get(
                            "nmSettings", []
                        )
                        if nm_settings:
                            nm_list = [
                                nm.get("nm_id") or nm.get("nmId")
                                for nm in nm_settings
                                if nm.get("nm_id") or nm.get("nmId")
                            ]
                    if not nm_list:
                        continue
                    for nm_id in nm_list:
                        try:
                            rec_data = await self.client.advert.get_bid_recommendations(
                                nm_id=nm_id, advert_id=advert_id
                            )
                            if rec_data:
                                # 保存完整响应（包括 base 数据）
                                all_data.append(
                                    {
                                        "advert_id": advert_id,
                                        "nm_id": nm_id,
                                        "full_response": rec_data,
                                    }
                                )
                        except Exception as e:
                            logger.warning(
                                f"[同步服务] 获取广告 {advert_id} 商品 {nm_id} 竞价推荐失败: {e}"
                            )
                            continue

            # ========== 第二步：只操作数据库，不调用 API ==========
            total_count = 0
            for data_item in all_data:
                try:
                    # 提取完整响应
                    full_response = data_item.get("full_response", {})
                    advert_id = data_item["advert_id"]
                    nm_id = data_item["nm_id"]

                    # 处理 normQueries 部分 + base 部分
                    norm_queries = (
                        full_response.get("normQueries", [])
                        if isinstance(full_response, dict)
                        else []
                    )
                    if norm_queries and isinstance(norm_queries, list):
                        ods_records = await crud_ods_wb_bid_recommendation.upsert_many(
                            self.db,
                            recommendations_data=norm_queries,
                            shop_id=self.shop.id,
                            advert_id=advert_id,
                            nm_id=nm_id,
                            full_response=full_response,  # 传递完整响应用于保存 base 数据
                        )
                        total_count += len(ods_records)
                except SQLAlchemyError as e:
                    logger.error(f"[同步服务] 数据库操作失败: {e}")
                    await self._safe_rollback()
                    # 单个失败继续
                    continue

            result = {
                "status": "success",
                "message": f"同步了 {total_count} 条竞价推荐数据",
                "count": total_count,
            }
            logger.debug(f"[同步服务] 竞价推荐同步完成: {result}")
            return result
        except Exception as e:
            logger.error(f"[同步服务] 同步竞价推荐失败: {e}")
            import traceback

            logger.error(f"[同步服务] 错误堆栈: {traceback.format_exc()}")
            await self._safe_rollback()
            return {"status": "error", "message": f"同步竞价推荐失败: {e}"}

    async def sync_advert_fullstats(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """同步广告完整统计数据"""
        logger.debug(f"[同步服务] 开始同步广告完整统计 - 店铺: {self.shop.id}")
        if not self.client.advert:
            return {"status": "error", "message": "Advert API client not configured"}

        date_from_str, date_to_str = await self._get_date_range(date_from, date_to)

        try:
            # 先获取广告列表
            adverts_result = None
            async with self.client:
                adverts_result = await self.client.advert.get_adverts_list()

            adverts_data = adverts_result.get("adverts", []) if adverts_result else []
            advert_ids = [adv.get("id") for adv in adverts_data if adv.get("id")]

            ods_count = 0
            if advert_ids:
                # 获取统计数据
                fullstats_data = None
                async with self.client:
                    fullstats_data = await self.client.advert.get_advert_fullstats(
                        advert_ids=advert_ids,
                        begin_date=date_from_str,
                        end_date=date_to_str,
                    )

                if fullstats_data:
                    try:
                        ods_stats = await crud_ods_wb_advert_full_stat.upsert_many(
                            self.db,
                            fullstats_data=fullstats_data,
                            shop_id=self.shop.id,
                        )
                        ods_count = len(ods_stats)
                    except SQLAlchemyError as e:
                        logger.error(f"[同步服务] 数据库操作失败: {e}")
                        await self._safe_rollback()
                        return {"status": "error", "message": f"数据库操作失败: {e}"}

            result = {
                "status": "success",
                "message": f"同步了 {ods_count} 条广告完整统计数据",
                "count": ods_count,
            }
            logger.debug(f"[同步服务] 广告完整统计同步完成: {result}")
            return result
        except Exception as e:
            logger.error(f"[同步服务] 同步广告完整统计失败: {e}")
            import traceback

            logger.error(f"[同步服务] 错误堆栈: {traceback.format_exc()}")
            await self._safe_rollback()
            return {"status": "error", "message": f"同步广告完整统计失败: {e}"}

    async def sync_adverts_v2(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """同步广告列表V2数据"""
        logger.debug(f"[同步服务] 开始同步广告列表V2 - 店铺: {self.shop.id}")
        if not self.client.advert:
            return {"status": "error", "message": "Advert API client not configured"}

        try:
            # 先获取API数据（独立的async context）
            adverts_v2_data = None
            async with self.client:
                adverts_v2_data = await self.client.advert.get_adverts_v2()

            ods_count = 0
            advert_product_count = 0
            if adverts_v2_data:
                try:
                    ods_adverts = await crud_ods_wb_advert_v2.upsert_many(
                        self.db,
                        adverts_data=adverts_v2_data,
                        shop_id=self.shop.id,
                    )
                    ods_count = len(ods_adverts)
                    adverts_list = (
                        adverts_v2_data.get("adverts", [])
                        if isinstance(adverts_v2_data, dict)
                        else adverts_v2_data
                    )
                    if isinstance(adverts_list, list):
                        advert_products = await crud_ods_wb_advert_product.create_many(
                            self.db,
                            adverts_data=adverts_list,
                            shop_id=self.shop.id,
                        )
                        advert_product_count = len(advert_products)
                except SQLAlchemyError as e:
                    logger.error(f"[同步服务] 数据库操作失败: {e}")
                    await self._safe_rollback()
                    return {"status": "error", "message": f"数据库操作失败: {e}"}

            result = {
                "status": "success",
                "message": (
                    f"同步了 {ods_count} 条广告列表V2数据，"
                    f"更新了 {advert_product_count} 条广告商品映射"
                ),
                "count": ods_count,
                "advert_product_count": advert_product_count,
            }
            logger.debug(f"[同步服务] 广告列表V2同步完成: {result}")
            return result
        except Exception as e:
            logger.error(f"[同步服务] 同步广告列表V2失败: {e}")
            await self._safe_rollback()
            return {"status": "error", "message": f"同步广告列表V2失败: {e}"}

    async def sync_adv_enhanced(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """同步所有增强广告数据(8个新API) - 每个同步使用独立会话"""
        logger.debug(f"[同步服务] 开始同步增强广告数据 - 店铺: {self.shop.id}")

        results: Dict[str, Any] = {
            "status": "success",
            "results": {},
        }

        # 需要独立运行的同步名称列表
        sync_names = [
            "adverts_v2",
            "norm_query_bids",
            "norm_query_minus",
            "norm_query_list",
            "norm_query_stats",
            "promotion_count",
            "bid_recommendations",
            "advert_fullstats",
        ]

        # 导入会话工厂 - 这里假设可以从 core.database 获取
        try:
            from kunpeng.core.database import AsyncSessionLocal
        except ImportError:
            # 如果导入失败，降级到原来的方式
            logger.warning("[同步服务] 无法导入独立会话，使用共享会话")
            return await self._sync_adv_enhanced_shared(date_from, date_to)

        # 每个同步使用独立的会话
        for name in sync_names:
            try:
                # 创建新的会话和服务实例
                async with AsyncSessionLocal() as db:
                    # 创建新的服务实例使用新会话
                    sync_service = WBSyncService(db, self.shop)

                    # 获取对应的同步方法
                    sync_func = getattr(sync_service, f"sync_{name}")

                    # 执行同步
                    result = await sync_func(date_from, date_to)
                    results["results"][name] = result

                    logger.debug(f"[同步服务] {name} 完成: {result}")

            except Exception as e:
                logger.error(f"[同步服务] 同步 {name} 失败: {e}", exc_info=True)
                results["results"][name] = {"status": "error", "message": str(e)}

        required_for_dwd = {
            "adverts_v2",
            "norm_query_bids",
            "norm_query_list",
            "bid_recommendations",
        }
        if all(
            results["results"].get(name, {}).get("status") == "success"
            for name in required_for_dwd
        ):
            try:
                async with AsyncSessionLocal() as db:
                    results["results"]["advert_dwd_config"] = {
                        "status": "success",
                        "data": await wb_dwd_service.sync_advert_config(
                            db,
                            shop_id=self.shop.id,
                        ),
                    }
            except Exception as exc:
                logger.exception(
                    "[同步服务] 广告 ODS 已同步，但配置 DWD 构建失败 - 店铺: %s",
                    self.shop.id,
                )
                results["results"]["advert_dwd_config"] = {
                    "status": "error",
                    "message": str(exc),
                }

        results["status"] = self._aggregate_sync_status(results["results"])
        logger.debug(f"[同步服务] 增强广告数据同步完成: {results}")
        return results

    @staticmethod
    def _aggregate_sync_status(sync_results: Dict[str, Any]) -> str:
        """Summarize child sync results without hiding partial failures."""
        if not sync_results:
            return "success"
        statuses = [
            result.get("status")
            for result in sync_results.values()
            if isinstance(result, dict)
        ]
        error_count = sum(status == "error" for status in statuses)
        if error_count == 0:
            return "success"
        if error_count == len(sync_results):
            return "error"
        return "partial_success"

    async def _sync_adv_enhanced_shared(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """降级方案：使用共享会话（原来的方式）"""
        results: Dict[str, Any] = {
            "status": "success",
            "results": {},
        }

        sync_functions = [
            ("adverts_v2", self.sync_adverts_v2),
            ("norm_query_bids", self.sync_norm_query_bids),
            ("norm_query_minus", self.sync_norm_query_minus),
            ("norm_query_list", self.sync_norm_query_list),
            ("norm_query_stats", self.sync_norm_query_stats),
            ("promotion_count", self.sync_promotion_count),
            ("bid_recommendations", self.sync_bid_recommendations),
            ("advert_fullstats", self.sync_advert_fullstats),
        ]

        for name, func in sync_functions:
            try:
                result = await func(date_from, date_to)
                results["results"][name] = result
            except Exception as e:
                logger.error(f"[同步服务] 同步 {name} 失败: {e}")
                results["results"][name] = {"status": "error", "message": str(e)}

        required_for_dwd = {
            "adverts_v2",
            "norm_query_bids",
            "norm_query_list",
            "bid_recommendations",
        }
        if all(
            results["results"].get(name, {}).get("status") == "success"
            for name in required_for_dwd
        ):
            try:
                results["results"]["advert_dwd_config"] = {
                    "status": "success",
                    "data": await wb_dwd_service.sync_advert_config(
                        self.db,
                        shop_id=self.shop.id,
                    ),
                }
            except Exception as exc:
                logger.exception(
                    "[同步服务] 广告 ODS 已同步，但配置 DWD 构建失败 - 店铺: %s",
                    self.shop.id,
                )
                results["results"]["advert_dwd_config"] = {
                    "status": "error",
                    "message": str(exc),
                }

        results["status"] = self._aggregate_sync_status(results["results"])
        return results
