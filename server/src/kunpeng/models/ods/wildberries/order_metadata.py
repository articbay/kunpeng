"""ODS model for Wildberries FBS assembly order metadata."""

from sqlalchemy import (JSON, BigInteger, Column, DateTime, Index, Integer,
                        UniqueConstraint)

from kunpeng.models.base import BaseModel


class ODSWBOrderMetadata(BaseModel):
    """Metadata returned by ``POST /api/marketplace/v3/orders/meta``."""

    __tablename__ = "ods_wb_order_metadata"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")
    order_id = Column(BigInteger, nullable=False, comment="组装订单ID")

    row_data = Column(JSON, nullable=False, comment="Wildberries 原始JSON数据")
    meta_details = Column(
        JSON,
        nullable=True,
        comment="订单元数据明细及校验结果 (API: metaDetails)",
    )
    legacy_meta = Column(
        JSON,
        nullable=True,
        comment="兼容旧版订单元数据结构 (API: meta)",
    )
    last_synced_at = Column(
        DateTime(timezone=True),
        nullable=False,
        comment="最近同步时间",
    )

    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "order_id",
            name="uq_ods_wb_order_metadata_shop_order",
        ),
        Index(
            "idx_ods_wb_order_metadata_shop_synced",
            "shop_id",
            "last_synced_at",
        ),
        {"comment": "Wildberries FBS组装订单元数据表"},
    )
