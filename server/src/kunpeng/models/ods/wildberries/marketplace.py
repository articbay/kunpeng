"""
ODS 层 - Wildberries Marketplace 订单数据模型
对应官方API: https://dev.wildberries.ru/en/docs/openapi/orders-fbs#tag/FBS-Assembly-Orders/paths/~1api~1v3~1orders/get
"""

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from kunpeng.models.base import BaseModel


class ODSWBMarketplaceOrder(BaseModel):
    """
    ODS 层 - Wildberries Marketplace FBS 订单列表
    存储 API: /api/v3/orders 返回的原始订单数据
    """

    __tablename__ = "ods_wb_marketplace_orders"

    id = Column(
        Integer, primary_key=True, index=True, autoincrement=True, comment="主键ID"
    )

    # 关联店铺
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")

    # 原始 JSON 数据（用于追溯）
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    # ========== 核心订单字段 ==========

    # 订单基本标识
    order_id = Column(BigInteger, nullable=False, comment="订单ID (API: id)")
    order_uid = Column(
        String(255), nullable=True, comment="订单唯一标识 (API: orderUid)"
    )
    rid = Column(String(255), nullable=True, comment="记录ID (API: rid)")

    # 供货与配送
    supply_id = Column(
        String(255), nullable=True, index=True, comment="供货ID (API: supplyId)"
    )
    delivery_type = Column(
        String(50), nullable=True, comment="配送类型 (API: deliveryType)"
    )

    # 时间
    created_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="订单创建时间 (API: createdAt)",
    )

    # ========== 商品字段 ==========

    article = Column(
        String(255), nullable=True, index=True, comment="卖家货号 (API: article)"
    )
    nm_id = Column(BigInteger, nullable=True, index=True, comment="商品ID (API: nmId)")
    chrt_id = Column(BigInteger, nullable=True, comment="商品图表ID (API: chrtId)")
    color_code = Column(String(100), nullable=True, comment="颜色代码 (API: colorCode)")

    # ========== 价格字段 ==========

    price = Column(Numeric(18, 2), nullable=True, comment="价格 (API: price)")
    converted_price = Column(
        Numeric(18, 2), nullable=True, comment="折算价格 (API: convertedPrice)"
    )
    currency_code = Column(
        Integer, nullable=True, comment="币种代码 (API: currencyCode)"
    )
    converted_currency_code = Column(
        Integer, nullable=True, comment="折算币种代码 (API: convertedCurrencyCode)"
    )
    scan_price = Column(
        Numeric(18, 2), nullable=True, comment="扫描价格 (API: scanPrice)"
    )

    # ========== 仓库与地点字段 ==========

    warehouse_id = Column(
        BigInteger, nullable=True, index=True, comment="仓库ID (API: warehouseId)"
    )
    office_id = Column(BigInteger, nullable=True, comment="办公室ID (API: officeId)")

    # ========== 分类字段 ==========

    cargo_type = Column(Integer, nullable=True, comment="货物类型 (API: cargoType)")
    cross_border_type = Column(
        Integer, nullable=True, comment="跨境类型 (API: crossBorderType)"
    )

    # ========== 标志字段 ==========

    is_zero_order = Column(
        Boolean, nullable=True, comment="是否零订单 (API: isZeroOrder)"
    )

    # ========== 订单状态字段 (从 /api/v3/orders/status 获取) ==========

    is_cancellable = Column(
        Boolean, nullable=True, comment="是否可取消 (API: isCancellable)"
    )
    supplier_status = Column(
        String(100),
        nullable=True,
        index=True,
        comment="供应商状态 (API: supplierStatus)",
    )
    wb_status = Column(
        String(100), nullable=True, index=True, comment="WB状态 (API: wbStatus)"
    )

    # ========== 文本字段 ==========

    comment = Column(Text, nullable=True, comment="备注 (API: comment)")

    # ========== JSON字段 ==========

    address = Column(JSON, nullable=True, comment="地址 (API: address)")
    offices = Column(JSON, nullable=True, comment="办公室列表 (API: offices)")
    skus = Column(JSON, nullable=True, comment="SKU列表 (API: skus)")
    options = Column(JSON, nullable=True, comment="选项 (API: options)")

    __table_args__ = (
        UniqueConstraint("shop_id", "order_id", name="uq_ods_mp_order_shop_order"),
        {"comment": "Wildberries Marketplace订单表"},
    )


class ODSWBMarketplaceOrderStatusHistory(BaseModel):
    """
    ODS 层 - Wildberries Marketplace FBS 订单状态历史
    存储 API: /api/v3/orders/status/history 返回的状态变更记录
    """

    __tablename__ = "ods_wb_marketplace_order_status_histories"

    id = Column(
        Integer, primary_key=True, index=True, autoincrement=True, comment="主键ID"
    )

    # 关联店铺
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")

    # 关联订单
    order_id = Column(BigInteger, nullable=False, index=True, comment="订单ID")

    # 原始 JSON 数据（用于追溯）
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    # ========== 状态历史字段 ==========

    # 状态信息 - 先使用原始JSON存储，待确认实际字段结构
    # 暂时只存储原始数据，等有实际API响应后再解析字段

    __table_args__ = (
        UniqueConstraint(
            "shop_id", "order_id", name="uq_ods_mp_order_status_shop_order"
        ),
        {"comment": "Wildberries Marketplace订单状态历史表"},
    )
