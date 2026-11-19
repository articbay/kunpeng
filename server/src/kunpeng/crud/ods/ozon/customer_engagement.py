"""Ozon 客户声音 ODS 原子 upsert。"""

from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.ods.ozon.utils import parse_iso_datetime, safe_int, safe_str
from kunpeng.models.ods.ozon.customer_engagement import (
    ODSOzonChat,
    ODSOzonChatMessage,
    ODSOzonQuestion,
    ODSOzonQuestionAnswer,
    ODSOzonReviewComment,
)


async def _upsert_rows(
    db: AsyncSession,
    model: Any,
    rows: Iterable[Dict[str, Any]],
    immutable_columns: set[str],
) -> int:
    values = list(rows)
    if not values:
        return 0
    statement = insert(model).values(values)
    update_columns = {
        column.name: getattr(statement.inserted, column.name)
        for column in model.__table__.columns
        if column.name not in immutable_columns | {"id", "create_time"}
        and column.name in values[0]
    }
    update_columns["update_time"] = func.now()
    await db.execute(statement.on_duplicate_key_update(**update_columns))
    return len(values)


class CRUDOzonReviewComment:
    async def upsert_many(
        self,
        db: AsyncSession,
        *,
        items: List[Dict[str, Any]],
        shop_id: int,
        review_id: str,
    ) -> int:
        rows = []
        for item in items:
            comment_id = safe_str(item.get("id") or item.get("comment_id"))
            if not comment_id:
                continue
            rows.append(
                {
                    "shop_id": shop_id,
                    "comment_id": comment_id,
                    "review_id": review_id,
                    "parent_comment_id": safe_str(
                        item.get("parent_comment_id") or item.get("parent_id")
                    ),
                    "text": safe_str(item.get("text")),
                    "published_at": parse_iso_datetime(
                        item.get("published_at") or item.get("created_at")
                    ),
                    "is_owner": item.get("is_owner"),
                    "is_official": item.get("is_official"),
                    "row_data": item,
                }
            )
        return await _upsert_rows(db, ODSOzonReviewComment, rows, {"shop_id", "comment_id"})


class CRUDOzonQuestion:
    async def upsert_many(
        self, db: AsyncSession, *, items: List[Dict[str, Any]], shop_id: int
    ) -> int:
        rows = []
        for item in items:
            question_id = safe_str(item.get("id") or item.get("question_id"))
            if not question_id:
                continue
            product = item.get("product") or {}
            rows.append(
                {
                    "shop_id": shop_id,
                    "question_id": question_id,
                    "sku": safe_int(item.get("sku") or product.get("sku")),
                    "offer_id": safe_str(
                        item.get("offer_id") or product.get("offer_id")
                    ),
                    "status": safe_str(item.get("status")),
                    "text": safe_str(item.get("text") or item.get("question")),
                    "published_at": parse_iso_datetime(
                        item.get("published_at") or item.get("created_at")
                    ),
                    "answers_count": safe_int(
                        item.get("answers_count") or item.get("answers_amount")
                    ),
                    "row_data": item,
                }
            )
        return await _upsert_rows(db, ODSOzonQuestion, rows, {"shop_id", "question_id"})


class CRUDOzonQuestionAnswer:
    async def upsert_many(
        self,
        db: AsyncSession,
        *,
        items: List[Dict[str, Any]],
        shop_id: int,
        question_id: str,
    ) -> int:
        rows = []
        for item in items:
            answer_id = safe_str(item.get("id") or item.get("answer_id"))
            if not answer_id:
                continue
            rows.append(
                {
                    "shop_id": shop_id,
                    "answer_id": answer_id,
                    "question_id": question_id,
                    "text": safe_str(item.get("text") or item.get("answer")),
                    "published_at": parse_iso_datetime(
                        item.get("published_at") or item.get("created_at")
                    ),
                    "is_owner": item.get("is_owner"),
                    "is_official": item.get("is_official"),
                    "row_data": item,
                }
            )
        return await _upsert_rows(
            db, ODSOzonQuestionAnswer, rows, {"shop_id", "answer_id"}
        )


def _chat_payload(item: Dict[str, Any]) -> Dict[str, Any]:
    nested = item.get("chat")
    return nested if isinstance(nested, dict) else item


class CRUDOzonChat:
    async def upsert_many(
        self, db: AsyncSession, *, items: List[Dict[str, Any]], shop_id: int
    ) -> int:
        rows = []
        for item in items:
            chat = _chat_payload(item)
            chat_id = safe_str(chat.get("chat_id") or chat.get("id"))
            posting_number = safe_str(
                chat.get("posting_number") or item.get("posting_number")
            )
            if not chat_id or not posting_number:
                continue
            rows.append(
                {
                    "shop_id": shop_id,
                    "chat_id": chat_id,
                    "chat_type": safe_str(chat.get("chat_type") or chat.get("type")),
                    "status": safe_str(chat.get("status") or item.get("status")),
                    "posting_number": posting_number,
                    "unread_count": safe_int(
                        item.get("unread_count") or chat.get("unread_count")
                    ),
                    "last_message_id": safe_str(
                        item.get("last_message_id") or chat.get("last_message_id")
                    ),
                    "row_data": item,
                }
            )
        return await _upsert_rows(db, ODSOzonChat, rows, {"shop_id", "chat_id"})

    async def get_latest_message_id(
        self, db: AsyncSession, *, shop_id: int, chat_id: str
    ) -> Optional[str]:
        result = await db.execute(
            select(ODSOzonChatMessage.message_id)
            .where(
                ODSOzonChatMessage.shop_id == shop_id,
                ODSOzonChatMessage.chat_id == chat_id,
            )
            .order_by(
                ODSOzonChatMessage.created_at.desc(),
                ODSOzonChatMessage.id.desc(),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()


class CRUDOzonChatMessage:
    async def upsert_many(
        self,
        db: AsyncSession,
        *,
        items: List[Dict[str, Any]],
        shop_id: int,
        chat_id: str,
        posting_number: str,
    ) -> int:
        rows = []
        for item in items:
            message_id = safe_str(item.get("message_id") or item.get("id"))
            if not message_id:
                continue
            user = item.get("user") or {}
            data = item.get("data")
            text = data.get("text") if isinstance(data, dict) else item.get("text")
            rows.append(
                {
                    "shop_id": shop_id,
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "posting_number": posting_number,
                    "user_type": safe_str(user.get("type") or item.get("user_type")),
                    "text": safe_str(text),
                    "created_at": parse_iso_datetime(item.get("created_at")),
                    "is_read": item.get("is_read"),
                    "is_image": item.get("is_image"),
                    "row_data": item,
                }
            )
        return await _upsert_rows(
            db,
            ODSOzonChatMessage,
            rows,
            {"shop_id", "chat_id", "message_id"},
        )


crud_ods_ozon_review_comment = CRUDOzonReviewComment()
crud_ods_ozon_question = CRUDOzonQuestion()
crud_ods_ozon_question_answer = CRUDOzonQuestionAnswer()
crud_ods_ozon_chat = CRUDOzonChat()
crud_ods_ozon_chat_message = CRUDOzonChatMessage()
