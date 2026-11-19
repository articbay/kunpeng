"""ODS model for Wildberries FBS assembly orders requiring reshipment."""

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
)

from kunpeng.models.base import BaseModel


class ODSWBReshipmentOrder(BaseModel):
    """Current and historical state from the WB reshipment snapshot."""

    __tablename__ = "ods_wb_order_reshipment_orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")
    order_id = Column(BigInteger, nullable=False, comment="组装订单ID(API: orderID)")
    supply_id = Column(
        String(64),
        nullable=False,
        comment="原供货单ID(API: supplyID)",
    )
    row_data = Column(JSON, nullable=False, comment="Wildberries原始JSON数据")

    is_active = Column(
        Boolean,
        nullable=False,
        comment="当前是否仍要求重新发货",
    )
    first_seen_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="首次检测到需要重新发货的时间",
    )
    last_seen_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="最近一次仍出现在API快照中的时间",
    )
    status_changed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="最近一次进入或退出重新发货清单的检测时间",
    )
    resolved_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="检测到不再需要重新发货的时间",
    )

    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "order_id",
            "supply_id",
            name="uq_ods_wb_reshipment_shop_order_supply",
        ),
        Index(
            "idx_ods_wb_reshipment_shop_active",
            "shop_id",
            "is_active",
        ),
        Index(
            "idx_ods_wb_reshipment_shop_changed",
            "shop_id",
            "status_changed_at",
        ),
        Index("idx_ods_wb_reshipment_order", "order_id"),
        Index("idx_ods_wb_reshipment_supply", "supply_id"),
        {"comment": "Wildberries FBS重新发货订单状态表"},
    )
