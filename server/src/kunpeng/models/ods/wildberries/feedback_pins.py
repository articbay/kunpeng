"""ODS model for Wildberries pinned feedback operations."""

from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
)

from kunpeng.models.base import BaseModel


class ODSWBFeedbackPin(BaseModel):
    """Pinned and automatically unpinned feedback operation history."""

    __tablename__ = "ods_wb_voc_feedback_pins"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")
    pin_id = Column(BigInteger, nullable=False, comment="评价置顶操作ID(API: pinId)")
    feedback_id = Column(
        String(255),
        nullable=False,
        comment="评价ID(API: feedbackId)",
    )
    nm_id = Column(BigInteger, nullable=True, comment="Wildberries商品ID(API: nmId)")
    imt_id = Column(
        BigInteger,
        nullable=True,
        comment="合并商品卡片组ID(API: imtId)",
    )
    state = Column(
        String(16),
        nullable=False,
        comment="置顶状态: pinned/unpinned",
    )
    pin_on = Column(
        String(16),
        nullable=True,
        comment="置顶位置: nm/imt(API: pinOn)",
    )
    pin_method = Column(
        String(32),
        nullable=True,
        comment="置顶方式: subscription/tariff(API: pinMethod)",
    )
    change_state_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="置顶状态变化时间(API: changeStateAt)",
    )
    unpinned_cause = Column(
        String(255),
        nullable=True,
        comment="自动取消置顶原因(API: unpinnedCause)",
    )
    row_data = Column(JSON, nullable=False, comment="Wildberries原始JSON数据")
    first_seen_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="首次同步时间",
    )
    last_seen_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="最近同步时间",
    )

    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "pin_id",
            name="uq_ods_wb_feedback_pin_shop_pin",
        ),
        Index(
            "idx_ods_wb_feedback_pin_shop_state_changed",
            "shop_id",
            "state",
            "change_state_at",
        ),
        Index(
            "idx_ods_wb_feedback_pin_shop_feedback",
            "shop_id",
            "feedback_id",
        ),
        Index("idx_ods_wb_feedback_pin_nm", "nm_id"),
        Index("idx_ods_wb_feedback_pin_imt", "imt_id"),
        {"comment": "Wildberries评价置顶及自动取消置顶记录表"},
    )
