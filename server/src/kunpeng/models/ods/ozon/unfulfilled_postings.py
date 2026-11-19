"""
Ozon ODS 层 - 待处理（未发货）FBS 订单表（"新订单"数据源）

对应官方API: POST /v4/posting/fbs/unfulfilled/list
文档: https://docs.ozon.ru/api/seller/zh/#operation/PostingAPI_GetFbsPostingUnfulfilledList

说明:
    该表独立于 ods_ozon_fbs_postings，专门存放"待卖家处理的新订单"快照。
    unfulfilled 接口返回的都是仍需人工组装/发货的订单。表中不物理删除历史
    记录，并通过 first_seen_at、last_seen_at、is_active 和 resolved_at
    区分首次出现、仍待处理、已离开列表和重新出现。
"""

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import VARCHAR
from sqlalchemy.sql import func

from kunpeng.models.base import BaseModel


class ODSOzonUnfulfilledPosting(BaseModel):
    """
    Ozon ODS 层 - 待处理（未发货）FBS 订单主表

    存储 API: /v4/posting/fbs/unfulfilled/list 返回的待处理订单数据。
    """

    __tablename__ = "ods_ozon_order_unfulfilled_postings"
    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "posting_number",
            name="uq_ods_ozon_unfulfilled_postings_shop_posting",
        ),
        Index("idx_ods_ozon_unfulfilled_postings_shop_id", "shop_id"),
        Index("idx_ods_ozon_unfulfilled_postings_in_process", "in_process_at"),
        Index("idx_ods_ozon_unfulfilled_postings_first_seen", "first_seen_at"),
        Index(
            "idx_ods_ozon_unfulfilled_postings_shop_active",
            "shop_id",
            "is_active",
        ),
        Index(
            "idx_ods_ozon_unfulfilled_postings_shop_cutoff",
            "shop_id",
            "cutoff_at",
        ),
        {"comment": "Ozon 待处理（未发货）FBS 订单表（新订单）"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    # ========== 核心订单字段 ==========
    posting_number = Column(
        VARCHAR(100), nullable=False, comment="订单号 (API: posting_number)"
    )
    order_id = Column(BigInteger, nullable=True, comment="订单ID (API: order_id)")
    order_number = Column(
        VARCHAR(100), nullable=True, comment="订单编号 (API: order_number)"
    )
    status = Column(VARCHAR(50), nullable=True, comment="订单状态 (API: status)")
    substatus = Column(
        VARCHAR(50), nullable=True, comment="订单子状态 (API: substatus)"
    )
    delivery_method_name = Column(
        VARCHAR(255), nullable=True, comment="配送方式名称 (API: delivery_method.name)"
    )

    # ========== 时间字段 ==========
    in_process_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="进入处理状态时间 (API: in_process_at)",
    )
    shipment_date = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="计划发货时间 (API: shipment_date)",
    )
    delivering_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="计划送达时间 (API: delivering_date)",
    )
    shipment_without_delay_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="无延迟情况下的计划发货时间 (API: shipment_date_without_delay)",
    )
    cutoff_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="组装截止时间 (API: cutoff_at / posting.cutoff)",
    )

    # ========== JSON 明细字段 ==========
    products = Column(JSON, nullable=True, comment="商品明细 (API: products)")
    analytics_data = Column(
        JSON, nullable=True, comment="分析数据 (API: analytics_data)"
    )
    financial_data = Column(
        JSON, nullable=True, comment="财务数据 (API: financial_data)"
    )
    delivery_method = Column(
        JSON, nullable=True, comment="配送方式 (API: delivery_method)"
    )
    barcodes = Column(JSON, nullable=True, comment="条码 (API: barcodes)")
    cancellation = Column(JSON, nullable=True, comment="取消信息 (API: cancellation)")
    customer = Column(JSON, nullable=True, comment="客户信息 (API: customer)")
    available_actions = Column(
        JSON,
        nullable=True,
        comment="当前允许的订单操作 (API: available_actions)",
    )
    requirements = Column(
        JSON,
        nullable=True,
        comment="履约要求 (API: requirements)",
    )
    sorting_center = Column(
        JSON,
        nullable=True,
        comment="分拣中心信息 (API: sorting_center)",
    )

    # ========== 履约运营字段 ==========
    tracking_number = Column(
        VARCHAR(255),
        nullable=True,
        comment="物流跟踪号 (API: tracking_number)",
    )
    integration_type_flow = Column(
        VARCHAR(100),
        nullable=True,
        comment="履约集成流程类型 (API: integration_type_flow)",
    )
    parent_posting_number = Column(
        VARCHAR(100),
        nullable=True,
        comment="父发送号 (API: parent_posting_number)",
    )
    destination_place_id = Column(
        BigInteger,
        nullable=True,
        comment="目的地点ID (API: destination_place_id)",
    )
    destination_place_name = Column(
        VARCHAR(255),
        nullable=True,
        comment="目的地点名称 (API: destination_place_name)",
    )
    is_express = Column(
        Boolean,
        nullable=True,
        comment="是否为加急配送 (API: is_express)",
    )
    is_multibox = Column(
        Boolean,
        nullable=True,
        comment="是否为多箱订单 (API: is_multibox)",
    )
    multi_box_qty = Column(
        Integer,
        nullable=True,
        comment="多箱数量 (API: multi_box_qty)",
    )

    # ========== 增量提醒辅助字段 ==========
    first_seen_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="首次入库时间（用于识别增量新订单）",
    )
    last_seen_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="最近一次在未履约接口完整结果中看到该订单的时间",
    )
    is_active = Column(
        Boolean,
        server_default="1",
        nullable=False,
        comment="当前是否仍在对应截止时间窗口的未履约列表中",
    )
    resolved_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="订单从完整未履约结果中消失的时间",
    )
