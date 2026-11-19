"""Ozon 客户声音只读 ODS 表。"""

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Index, Integer, JSON
from sqlalchemy import String, Text, UniqueConstraint

from kunpeng.models.base import BaseModel


class ODSOzonReviewComment(BaseModel):
    __tablename__ = "ods_ozon_review_comments"
    __table_args__ = (
        UniqueConstraint(
            "shop_id", "comment_id", name="uq_ods_ozon_review_comments_shop_comment"
        ),
        Index("idx_ods_ozon_review_comments_review", "shop_id", "review_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    shop_id = Column(Integer, nullable=False, index=True)
    comment_id = Column(String(100), nullable=False)
    review_id = Column(String(100), nullable=False)
    parent_comment_id = Column(String(100), nullable=True)
    text = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    is_owner = Column(Boolean, nullable=True)
    is_official = Column(Boolean, nullable=True)
    row_data = Column(JSON, nullable=False)


class ODSOzonQuestion(BaseModel):
    __tablename__ = "ods_ozon_questions"
    __table_args__ = (
        UniqueConstraint(
            "shop_id", "question_id", name="uq_ods_ozon_questions_shop_question"
        ),
        Index("idx_ods_ozon_questions_shop_status", "shop_id", "status"),
        Index("idx_ods_ozon_questions_shop_sku", "shop_id", "sku"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    shop_id = Column(Integer, nullable=False, index=True)
    question_id = Column(String(100), nullable=False)
    sku = Column(BigInteger, nullable=True)
    offer_id = Column(String(255), nullable=True)
    status = Column(String(50), nullable=True)
    text = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    answers_count = Column(Integer, nullable=True)
    row_data = Column(JSON, nullable=False)


class ODSOzonQuestionAnswer(BaseModel):
    __tablename__ = "ods_ozon_question_answers"
    __table_args__ = (
        UniqueConstraint(
            "shop_id", "answer_id", name="uq_ods_ozon_question_answers_shop_answer"
        ),
        Index("idx_ods_ozon_question_answers_question", "shop_id", "question_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    shop_id = Column(Integer, nullable=False, index=True)
    answer_id = Column(String(100), nullable=False)
    question_id = Column(String(100), nullable=False)
    text = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    is_owner = Column(Boolean, nullable=True)
    is_official = Column(Boolean, nullable=True)
    row_data = Column(JSON, nullable=False)


class ODSOzonChat(BaseModel):
    __tablename__ = "ods_ozon_chats"
    __table_args__ = (
        UniqueConstraint("shop_id", "chat_id", name="uq_ods_ozon_chats_shop_chat"),
        Index("idx_ods_ozon_chats_shop_posting", "shop_id", "posting_number"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    shop_id = Column(Integer, nullable=False, index=True)
    chat_id = Column(String(100), nullable=False)
    chat_type = Column(String(100), nullable=True)
    status = Column(String(50), nullable=True)
    posting_number = Column(String(100), nullable=False)
    unread_count = Column(Integer, nullable=True)
    last_message_id = Column(String(100), nullable=True)
    row_data = Column(JSON, nullable=False)


class ODSOzonChatMessage(BaseModel):
    __tablename__ = "ods_ozon_chat_messages"
    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "chat_id",
            "message_id",
            name="uq_ods_ozon_chat_messages_shop_chat_message",
        ),
        Index("idx_ods_ozon_chat_messages_chat", "shop_id", "chat_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    shop_id = Column(Integer, nullable=False, index=True)
    chat_id = Column(String(100), nullable=False)
    message_id = Column(String(100), nullable=False)
    posting_number = Column(String(100), nullable=False)
    user_type = Column(String(50), nullable=True)
    text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)
    is_read = Column(Boolean, nullable=True)
    is_image = Column(Boolean, nullable=True)
    row_data = Column(JSON, nullable=False)
