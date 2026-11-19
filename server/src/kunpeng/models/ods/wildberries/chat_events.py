"""ODS layer model for Wildberries buyers chat events."""

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from kunpeng.models.base import BaseModel


class ODSWBChatEvent(BaseModel):
    """Wildberries buyers chat event returned by ``/api/v1/seller/events``."""

    __tablename__ = "ods_wb_voc_chat_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")

    row_data = Column(JSON, nullable=False, comment="Wildberries 原始JSON数据")
    event_id = Column(String(64), nullable=False, comment="聊天事件ID")
    chat_id = Column(String(255), nullable=False, comment="聊天会话ID")
    event_type = Column(String(50), nullable=True, comment="事件类型")
    sender = Column(String(50), nullable=True, comment="消息发送方")
    source = Column(String(100), nullable=True, comment="消息来源")
    is_new_chat = Column(Boolean, nullable=True, comment="是否为新会话")
    client_name = Column(String(255), nullable=True, comment="买家显示名称")

    message_text = Column(Text, nullable=True, comment="消息正文")
    attachments = Column(JSON, nullable=True, comment="消息附件元数据")
    nm_id = Column(BigInteger, nullable=True, comment="关联的Wildberries商品ID")
    order_rid = Column(String(255), nullable=True, comment="关联订单RID")

    event_timestamp_ms = Column(
        BigInteger, nullable=False, comment="事件Unix毫秒时间戳"
    )
    event_at = Column(DateTime(timezone=True), nullable=False, comment="事件发生时间")
    last_synced_at = Column(
        DateTime(timezone=True), nullable=False, comment="最近同步时间"
    )

    __table_args__ = (
        UniqueConstraint("shop_id", "event_id", name="uq_ods_wb_chat_event_shop_event"),
        Index("idx_ods_wb_chat_event_shop_time", "shop_id", "event_at"),
        Index(
            "idx_ods_wb_chat_event_shop_chat_time",
            "shop_id",
            "chat_id",
            "event_at",
        ),
        Index("idx_ods_wb_chat_event_nm_id", "nm_id"),
        {"comment": "Wildberries 买家聊天事件表"},
    )
