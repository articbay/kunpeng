"""
ODS 层 - Wildberries 新订单（待处理组装订单）数据模型
对应官方API: GET /api/v3/orders/new
文档: https://dev.wildberries.ru/en/docs/openapi/orders-fbs

说明:
    该表独立于 ods_wb_marketplace_orders，专门存放"新的组装订单"快照。
    /api/v3/orders/new 每次返回当前所有待卖家处理的订单，采用只 upsert 不删除
    的策略，并记录 first_seen_at（首次入库时间），方便下游（如 Hermes 智能体）
    通过"新出现的行"识别增量新订单并做提醒。
"""

from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from kunpeng.models.base import BaseModel


class ODSWBNewOrder(BaseModel):
    """
    ODS 层 - Wildberries 新订单（待处理组装订单）
    存储 API: /api/v3/orders/new 返回的原始订单数据
    """

    __tablename__ = "ods_wb_new_orders"

    id = Column(
        Integer, primary_key=True, index=True, autoincrement=True, comment="主键ID"
    )

    # 关联店铺
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")

    # 原始 JSON 数据（用于追溯）
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    # ========== 核心订单字段 ==========

    order_id = Column(BigInteger, nullable=False, comment="组装订单ID (API: id)")
    order_uid = Column(
        String(255), nullable=True, comment="订单唯一标识 (API: orderUid)"
    )
    rid = Column(String(255), nullable=True, comment="唯一订单ID (API: rid, 对应 srid)")

    # 配送
    delivery_type = Column(
        String(50), nullable=True, comment="配送类型 (API: deliveryType)"
    )

    # 时间
    created_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="组装订单创建时间 (API: createdAt)",
    )

    # ========== 商品字段 ==========

    article = Column(
        String(255), nullable=True, index=True, comment="卖家货号 (API: article)"
    )
    nm_id = Column(BigInteger, nullable=True, index=True, comment="商品ID (API: nmId)")
    chrt_id = Column(BigInteger, nullable=True, comment="商品尺寸ID (API: chrtId)")
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
    sale_price = Column(
        Numeric(18, 2), nullable=True, comment="销售价格 (API: salePrice, 单位分)"
    )
    scan_price = Column(
        Numeric(18, 2), nullable=True, comment="扫描价格 (API: scanPrice)"
    )

    # ========== 仓库与地点字段 ==========

    warehouse_id = Column(
        BigInteger, nullable=True, index=True, comment="仓库ID (API: warehouseId)"
    )
    office_id = Column(BigInteger, nullable=True, comment="WB仓库ID (API: officeId)")

    # ========== 分类字段 ==========

    cargo_type = Column(Integer, nullable=True, comment="货物类型 (API: cargoType)")

    # ========== 交付日期 ==========

    ddate = Column(
        String(50), nullable=True, comment="计划送达日期 (API: ddate, 大件订单)"
    )
    seller_date = Column(
        String(50), nullable=True, comment="建议送达日期 (API: sellerDate, 大件订单)"
    )

    # ========== 文本字段 ==========

    comment = Column(Text, nullable=True, comment="买家备注 (API: comment)")

    # ========== JSON字段 ==========

    address = Column(JSON, nullable=True, comment="买家地址 (API: address)")
    offices = Column(JSON, nullable=True, comment="办公室列表 (API: offices)")
    skus = Column(JSON, nullable=True, comment="SKU列表 (API: skus)")
    required_meta = Column(
        JSON, nullable=True, comment="必填元数据 (API: requiredMeta)"
    )
    optional_meta = Column(
        JSON, nullable=True, comment="可选元数据 (API: optionalMeta)"
    )
    options = Column(JSON, nullable=True, comment="选项 (API: options)")

    # ========== 增量提醒辅助字段 ==========

    first_seen_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
        comment="首次入库时间（用于识别增量新订单）",
    )

    __table_args__ = (
        UniqueConstraint("shop_id", "order_id", name="uq_ods_wb_new_order_shop_order"),
        Index("idx_ods_wb_new_order_shop_id", "shop_id"),
        Index("idx_ods_wb_new_order_first_seen", "first_seen_at"),
        {"comment": "Wildberries 新订单（待处理组装订单）表"},
    )
