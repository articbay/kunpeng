"""ODS model for Wildberries FBS supplies."""

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
from sqlalchemy.sql import func

from kunpeng.models.base import BaseModel


class ODSWBFbsSupply(BaseModel):
    """Supply returned by ``GET /api/v3/supplies``."""

    __tablename__ = "ods_wb_order_fbs_supplies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")
    supply_id = Column(String(64), nullable=False, comment="Wildberries供货单ID")

    name = Column(String(500), nullable=True, comment="供货单名称")
    is_b2b = Column(Boolean, nullable=True, comment="是否为B2B供货单")
    is_done = Column(Boolean, nullable=True, comment="供货单是否完成")
    created_at = Column(
        DateTime(timezone=True), nullable=True, comment="供货单创建时间"
    )
    closed_at = Column(DateTime(timezone=True), nullable=True, comment="供货单关闭时间")
    scan_at = Column(
        DateTime(timezone=True), nullable=True, comment="供货单扫描时间(API: scanDt)"
    )
    rejected_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="供货单拒绝时间(API: rejectDt)",
    )
    cargo_type = Column(Integer, nullable=True, comment="货物尺寸类型")
    cross_border_type = Column(Integer, nullable=True, comment="跨境类型")
    destination_office_id = Column(
        BigInteger, nullable=True, comment="目的仓库或分拣中心ID"
    )
    recommended_warehouse_id = Column(
        BigInteger,
        nullable=True,
        comment="推荐仓库ID(API: recommendedWhId)",
    )
    is_pickup_point_shipment_allowed = Column(
        Boolean,
        nullable=True,
        comment="是否允许发往取货点(API: isPickupPointShipmentAllowed)",
    )

    row_data = Column(JSON, nullable=False, comment="Wildberries原始JSON数据")
    first_seen_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="首次同步到该供货单的时间",
    )
    last_seen_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="最近一次从API获取到该供货单的时间",
    )

    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "supply_id",
            name="uq_ods_wb_fbs_supply_shop_supply",
        ),
        Index(
            "idx_ods_wb_fbs_supply_shop_created",
            "shop_id",
            "created_at",
        ),
        Index(
            "idx_ods_wb_fbs_supply_shop_done",
            "shop_id",
            "is_done",
        ),
        Index(
            "idx_ods_wb_fbs_supply_shop_seen",
            "shop_id",
            "last_seen_at",
        ),
        {"comment": "Wildberries FBS供货单表"},
    )
