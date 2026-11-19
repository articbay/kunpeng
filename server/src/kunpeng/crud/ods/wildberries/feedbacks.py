"""
ODS 层 - 评价和问答数据 CRUD 操作
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.models.ods.wildberries.feedbacks import ODSWBFeedback, ODSWBQuestion

logger = logging.getLogger(__name__)


def parse_iso_datetime(date_str: Optional[str]) -> Optional[datetime]:
    """
    解析 ISO 8601 格式的日期时间字符串

    支持格式:
    - "2026-04-19T16:56:32Z"
    - "2026-04-19T16:56:32.123Z"
    - "2026-04-19T16:56:32+00:00"
    """
    if not date_str:
        return None

    try:
        # 处理 'Z' 后缀
        if date_str.endswith('Z'):
            date_str = date_str[:-1] + '+00:00'
        return datetime.fromisoformat(date_str)
    except (ValueError, AttributeError):
        logger.warning(f"无法解析日期时间: {date_str}")
        return None


class CRUDODSWBFeedback(CRUDBase[ODSWBFeedback, Dict[str, Any], Dict[str, Any]]):
    """ODS 评价数据 CRUD"""

    async def _get_existing(
        self, db: AsyncSession, shop_id: int, feedback_id: Optional[str]
    ) -> Optional[ODSWBFeedback]:
        """根据唯一索引获取现有记录"""
        if not feedback_id:
            return None
        result = await db.execute(
            select(ODSWBFeedback).where(
                (ODSWBFeedback.shop_id == shop_id) &
                (ODSWBFeedback.feedback_id == feedback_id)
            )
        )
        return result.scalar_one_or_none()

    async def create_many(
        self,
        db: AsyncSession,
        *,
        feedbacks_data: List[Dict[str, Any]],
        shop_id: int,
    ) -> List[ODSWBFeedback]:
        """批量创建/更新 ODS 评价数据（幂等同步）"""
        logger.debug(f"[ODS CRUD] 开始幂等同步评价数据 - 店铺: {shop_id}, 数据量: {len(feedbacks_data)}")

        result_list = []

        for data in feedbacks_data:
            feedback_id = data.get("id")

            # 提取嵌套数据
            product_details = data.get("productDetails", {})

            # 构建 ODS 记录数据
            ods_data = {
                "shop_id": shop_id,
                "row_data": data,
                "feedback_id": feedback_id,
                "created_date": parse_iso_datetime(data.get("createdDate")),
                "updated_date": parse_iso_datetime(data.get("updatedDate")),

                # productDetails 字段
                "imt_id": product_details.get("imtId"),
                "nm_id": product_details.get("nmId"),
                "product_name": product_details.get("productName"),
                "product_details": product_details,
                "supplier_article": product_details.get("supplierArticle"),
                "supplier_name": product_details.get("supplierName"),
                "brand_name": product_details.get("brandName"),
                "size": product_details.get("size"),
                "color": data.get("color"),
                "subject_id": data.get("subjectId"),
                "subject_name": data.get("subjectName"),

                # 评价内容
                "product_valuation": data.get("productValuation"),
                "text": data.get("text"),
                "pros": data.get("pros"),
                "cons": data.get("cons"),
                "video": data.get("video"),
                "photo_links": data.get("photoLinks"),

                # 用户信息
                "user_name": data.get("userName"),

                # 订单信息
                "order_status": data.get("orderStatus"),
                "matching_size": data.get("matchingSize"),
                "last_order_shk_id": data.get("lastOrderShkId"),
                "last_order_created_at": parse_iso_datetime(data.get("lastOrderCreatedAt")),

                # 互动状态
                "state": data.get("state"),
                "was_viewed": data.get("wasViewed"),
                "is_answered": data.get("answer") is not None,
                "answer": data.get("answer"),
                "bables": data.get("bables"),
                "supplier_feedback_valuation": data.get("supplierFeedbackValuation"),
                "supplier_product_valuation": data.get("supplierProductValuation"),
                "is_able_supplier_feedback_valuation": data.get("isAbleSupplierFeedbackValuation"),
                "is_able_supplier_product_valuation": data.get("isAbleSupplierProductValuation"),
                "is_able_return_product_orders": data.get("isAbleReturnProductOrders"),
                "return_product_orders_date": parse_iso_datetime(data.get("returnProductOrdersDate")),

                # 关联
                "parent_feedback_id": data.get("parentFeedbackId"),
                "child_feedback_id": data.get("childFeedbackId"),
            }

            if feedback_id:
                # 检查是否已存在
                existing = await self._get_existing(db, shop_id, feedback_id)

                if existing:
                    # 更新现有记录
                    for field, value in ods_data.items():
                        if hasattr(existing, field):
                            setattr(existing, field, value)
                    result_list.append(existing)
                    continue

            # 创建新记录
            ods_record = ODSWBFeedback(**ods_data)
            db.add(ods_record)
            result_list.append(ods_record)

        logger.debug(f"[ODS CRUD] 准备提交数据库 - 总记录: {len(result_list)}")
        await db.commit()
        logger.debug(f"[ODS CRUD] 数据库提交成功")
        for record in result_list:
            await db.refresh(record)
        logger.debug(f"[ODS CRUD] 幂等同步完成 - 总计: {len(result_list)}")
        return result_list


class CRUDODSWBQuestion(CRUDBase[ODSWBQuestion, Dict[str, Any], Dict[str, Any]]):
    """ODS 问答数据 CRUD"""

    async def _get_existing(
        self, db: AsyncSession, shop_id: int, question_id: Optional[str]
    ) -> Optional[ODSWBQuestion]:
        """根据唯一索引获取现有记录"""
        if not question_id:
            return None
        result = await db.execute(
            select(ODSWBQuestion).where(
                (ODSWBQuestion.shop_id == shop_id) &
                (ODSWBQuestion.question_id == question_id)
            )
        )
        return result.scalar_one_or_none()

    async def create_many(
        self,
        db: AsyncSession,
        *,
        questions_data: List[Dict[str, Any]],
        shop_id: int,
    ) -> List[ODSWBQuestion]:
        """批量创建/更新 ODS 问答数据（幂等同步）"""
        logger.debug(f"[ODS CRUD] 开始幂等同步问答数据 - 店铺: {shop_id}, 数据量: {len(questions_data)}")

        result_list = []

        for data in questions_data:
            question_id = data.get("id")

            # 提取嵌套数据
            product_details = data.get("productDetails", {})

            # 构建 ODS 记录数据
            ods_data = {
                "shop_id": shop_id,
                "row_data": data,
                "question_id": question_id,
                "created_date": parse_iso_datetime(data.get("createdDate")),
                "updated_date": parse_iso_datetime(data.get("updatedDate")),

                # productDetails 字段
                "imt_id": product_details.get("imtId"),
                "nm_id": product_details.get("nmId"),
                "product_name": product_details.get("productName"),
                "product_details": product_details,
                "supplier_article": product_details.get("supplierArticle"),
                "supplier_name": product_details.get("supplierName"),
                "brand_name": product_details.get("brandName"),
                "subject_name": product_details.get("subjectName"),

                # 问答内容
                "text": data.get("text"),

                # 状态
                "state": data.get("state"),
                "was_viewed": data.get("wasViewed"),
                "is_warned": data.get("isWarned"),
                "is_answered": data.get("answer") is not None,
                "answer": data.get("answer"),
            }

            if question_id:
                # 检查是否已存在
                existing = await self._get_existing(db, shop_id, question_id)

                if existing:
                    # 更新现有记录
                    for field, value in ods_data.items():
                        if hasattr(existing, field):
                            setattr(existing, field, value)
                    result_list.append(existing)
                    continue

            # 创建新记录
            ods_record = ODSWBQuestion(**ods_data)
            db.add(ods_record)
            result_list.append(ods_record)

        logger.debug(f"[ODS CRUD] 准备提交数据库 - 总记录: {len(result_list)}")
        await db.commit()
        logger.debug(f"[ODS CRUD] 数据库提交成功")
        for record in result_list:
            await db.refresh(record)
        logger.debug(f"[ODS CRUD] 幂等同步完成 - 总计: {len(result_list)}")
        return result_list


# CRUD 实例
crud_ods_wb_feedback = CRUDODSWBFeedback(ODSWBFeedback)
crud_ods_wb_question = CRUDODSWBQuestion(ODSWBQuestion)
