"""
Ozon ODS 层 - 退货相关表
"""
from sqlalchemy import (JSON, BigInteger, Boolean, Column, Date, DateTime,
                        Index, Integer, Numeric, String, UniqueConstraint)
from sqlalchemy.dialects.mysql import DECIMAL, TEXT, VARCHAR
from sqlalchemy.sql import func

from kunpeng.models.base import BaseModel


class ODSOzonReturn(BaseModel):
    """
    Ozon ODS 层 - 退货主表

    描述: 存储Ozon退货主数据，包含退货基本信息、状态、原因、物流信息、地点信息等完整退货数据。
    """

    __tablename__ = "ods_ozon_returns"
    __table_args__ = (
        UniqueConstraint(
            "shop_id", "return_id",
            name="uq_ods_ozon_returns_shop_return_id"
        ),
        Index("idx_ods_ozon_returns_shop_id", "shop_id"),
        Index("idx_ods_ozon_returns_posting_number", "posting_number"),
        Index("idx_ods_ozon_returns_return_date", "return_date"),
        {
            "comment": "Ozon退货主表"
        }
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")
    return_id = Column(BigInteger, nullable=True, comment="退货ID (API返回的id)")
    company_id = Column(BigInteger, nullable=True, comment="公司ID")
    posting_number = Column(VARCHAR(100), nullable=True, comment="订单号")
    order_id = Column(BigInteger, nullable=True, comment="订单ID")
    order_number = Column(VARCHAR(100), nullable=True, comment="订单编号")
    schema = Column(VARCHAR(20), nullable=True, comment="发货模式 (FBO/FBS)")
    type = Column(VARCHAR(50), nullable=True, comment="退货类型")
    return_reason_name = Column(TEXT, nullable=True, comment="退货原因")
    clearing_id = Column(BigInteger, nullable=True, comment="清算ID")
    return_clearing_id = Column(BigInteger, nullable=True, comment="退货清算ID")
    source_id = Column(BigInteger, nullable=True, comment="来源ID")
    compensation_status = Column(
        VARCHAR(100), nullable=True, comment="赔偿状态编码（兼容旧字段）"
    )
    compensation_status_id = Column(Integer, nullable=True, comment="赔偿状态ID")
    compensation_status_display_name = Column(
        VARCHAR(255), nullable=True, comment="赔偿状态显示名称"
    )
    compensation_status_sys_name = Column(
        VARCHAR(255), nullable=True, comment="赔偿状态系统名称"
    )
    compensation_status_change_moment = Column(
        DateTime(timezone=True), nullable=True, comment="赔偿状态变更时间"
    )
    buyer_comment = Column(TEXT, nullable=True, comment="买家评论（接口返回时记录）")
    status_id = Column(Integer, nullable=True, comment="状态ID")
    status_display_name = Column(VARCHAR(255), nullable=True, comment="状态显示名称")
    status_sys_name = Column(VARCHAR(255), nullable=True, comment="状态系统名称")
    status_change_moment = Column(DateTime(timezone=True), nullable=True, comment="状态变更时间")
    return_date = Column(DateTime(timezone=True), nullable=True, comment="退货日期")
    logistic_barcode = Column(VARCHAR(255), nullable=True, comment="物流条码")
    logistic_technical_return_moment = Column(DateTime(timezone=True), nullable=True, comment="技术退货时间")
    logistic_final_moment = Column(DateTime(timezone=True), nullable=True, comment="最终时间")
    logistic_cancelled_with_compensation_moment = Column(DateTime(timezone=True), nullable=True, comment="取消赔偿时间")
    place_id = Column(BigInteger, nullable=True, comment="地点ID")
    place_name = Column(VARCHAR(255), nullable=True, comment="地点名称")
    place_address = Column(TEXT, nullable=True, comment="地点地址")
    target_place_id = Column(BigInteger, nullable=True, comment="目标地点ID")
    target_place_name = Column(VARCHAR(255), nullable=True, comment="目标地点名称")
    target_place_address = Column(TEXT, nullable=True, comment="目标地点地址")
    is_opened = Column(Boolean, nullable=True, comment="是否已打开")
    is_super_econom = Column(Boolean, nullable=True, comment="是否超级经济")
    exemplars = Column(JSON, nullable=True, comment="样品列表")


class ODSOzonReturnProduct(BaseModel):
    """
    Ozon ODS 层 - 退货商品表

    描述: 存储Ozon退货商品明细数据，包含退货商品的SKU、名称、数量、价格、佣金、样品ID等商品信息。
    """

    __tablename__ = "ods_ozon_return_products"
    __table_args__ = (
        UniqueConstraint(
            "shop_id", "return_id", "sku",
            name="uq_ods_ozon_return_products_shop_return_sku"
        ),
        Index("idx_ods_ozon_return_products_return_id", "return_id"),
        {
            "comment": "Ozon退货商品表"
        }
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")
    return_id = Column(BigInteger, nullable=True, comment="关联退货ID")
    sku = Column(BigInteger, nullable=True, comment="商品SKU")
    offer_id = Column(VARCHAR(255), nullable=True, comment="商家SKU")
    product_name = Column(TEXT, nullable=True, comment="商品名称")
    quantity = Column(Integer, nullable=True, comment="数量")
    price_amount = Column(DECIMAL(18, 4), nullable=True, comment="商品价格金额")
    price_currency = Column(VARCHAR(10), nullable=True, comment="商品价格币种")
    price_without_commission_amount = Column(DECIMAL(18, 4), nullable=True, comment="不含佣金价格金额")
    price_without_commission_currency = Column(VARCHAR(10), nullable=True, comment="不含佣金价格币种")
    commission_percent = Column(DECIMAL(8, 2), nullable=True, comment="佣金比例")
    commission_amount = Column(DECIMAL(18, 4), nullable=True, comment="佣金金额")
    commission_currency = Column(VARCHAR(10), nullable=True, comment="佣金币种")
    exemplar_id = Column(BigInteger, nullable=True, comment="样品ID")


class ODSOzonReturnStorage(BaseModel):
    """
    Ozon ODS 层 - 退货仓储费表

    描述: 存储Ozon退货仓储费用数据，包含仓储天数、费用金额、到达时间、预计销毁时间等仓储相关信息。
    """

    __tablename__ = "ods_ozon_return_storage"
    __table_args__ = (
        UniqueConstraint(
            "shop_id", "return_id",
            name="uq_ods_ozon_return_storage_shop_return"
        ),
        Index("idx_ods_ozon_return_storage_return_id", "return_id"),
        {
            "comment": "Ozon退货仓储费表"
        }
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")
    return_id = Column(BigInteger, nullable=True, comment="关联退货ID")
    storage_days = Column(Integer, nullable=True, comment="仓储天数")
    tariffication_first_date = Column(DateTime(timezone=True), nullable=True, comment="免费存储到期日")
    tariffication_start_date = Column(DateTime(timezone=True), nullable=True, comment="计费开始日期")
    arrived_moment = Column(DateTime(timezone=True), nullable=True, comment="到达时间")
    storage_fee_amount = Column(DECIMAL(18, 4), nullable=True, comment="仓储费金额")
    storage_fee_currency = Column(VARCHAR(10), nullable=True, comment="仓储费币种")
    utilization_fee_amount = Column(DECIMAL(18, 4), nullable=True, comment="销毁费金额")
    utilization_fee_currency = Column(VARCHAR(10), nullable=True, comment="销毁费币种")
    utilization_forecast_date = Column(DateTime(timezone=True), nullable=True, comment="销毁预计日期")
