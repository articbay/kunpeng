"""Ozon return business detail model."""

from sqlalchemy import (BigInteger, Boolean, Column, DateTime, Index, Integer,
                        Numeric, String, Text)

from kunpeng.core.database import Base


class DWDOzonReturnDetail(Base):
    """Cleaned Ozon return-product detail."""

    __tablename__ = "dwd_ozon_return_detail"

    shop_id = Column(BigInteger, primary_key=True, nullable=False, comment="店铺ID")
    return_id = Column(BigInteger, primary_key=True, nullable=False, comment="退货ID")
    nm_id = Column(
        BigInteger,
        primary_key=True,
        nullable=False,
        comment="Ozon SKU（沿用nm_id命名）",
    )

    # 业务字段按《FBO和FBS退货2026》表头顺序声明；主键固定置于最前。
    schema = Column(String(20), nullable=True, comment="发货模式（FBO/FBS）")
    product_name = Column(Text, nullable=True, comment="商品名称")
    product_name_cn = Column(Text, nullable=True, comment="商品名称（中文）")
    posting_number = Column(String(100), nullable=True, comment="货件编号")
    offer_id = Column(String(255), nullable=True, comment="商家货号")
    order_date = Column(DateTime(timezone=True), nullable=True, comment="下订单日期")
    return_date = Column(DateTime(timezone=True), nullable=True, comment="退货日期")
    status_id = Column(Integer, nullable=True, comment="状态ID")
    status_display_name = Column(String(255), nullable=True, comment="退货状态")
    status_display_name_cn = Column(
        String(255), nullable=True, comment="退货状态（中文）"
    )
    status_sys_name = Column(String(255), nullable=True, comment="状态编码")
    status_change_at = Column(
        DateTime(timezone=True), nullable=True, comment="状态变更时间"
    )
    compensation_status_id = Column(Integer, nullable=True, comment="赔偿状态ID")
    compensation_status_display_name = Column(
        String(255), nullable=True, comment="赔偿状态"
    )
    compensation_status_display_name_cn = Column(
        String(255), nullable=True, comment="赔偿状态（中文）"
    )
    compensation_status_sys_name = Column(
        String(255), nullable=True, comment="赔偿状态编码"
    )
    compensation_status_change_at = Column(
        DateTime(timezone=True), nullable=True, comment="赔偿状态变更时间"
    )
    return_reason_name = Column(Text, nullable=True, comment="退货原因")
    return_reason_name_cn = Column(Text, nullable=True, comment="退货原因（中文）")
    buyer_comment = Column(Text, nullable=True, comment="买家评论")
    buyer_comment_cn = Column(Text, nullable=True, comment="买家评论（中文）")
    quantity = Column(Integer, nullable=True, comment="退货数量")
    is_opened = Column(Boolean, nullable=True, comment="货件是否已打开")
    target_place_name = Column(String(255), nullable=True, comment="目的地")
    target_place_name_cn = Column(String(255), nullable=True, comment="目的地（中文）")
    target_place_address = Column(Text, nullable=True, comment="存储地址")
    target_place_address_cn = Column(Text, nullable=True, comment="存储地址（中文）")
    ready_to_pickup_at = Column(
        DateTime(timezone=True), nullable=True, comment="到达取货点时间"
    )
    place_name = Column(String(255), nullable=True, comment="位置")
    place_name_cn = Column(String(255), nullable=True, comment="位置（中文）")
    picked_up_at = Column(
        DateTime(timezone=True), nullable=True, comment="向卖家退货日期"
    )
    storage_days = Column(Integer, nullable=True, comment="存储天数")
    storage_expire_at = Column(
        DateTime(timezone=True), nullable=True, comment="免费存储的最后一天"
    )
    logistic_barcode = Column(String(255), nullable=True, comment="退货条形码")
    storage_fee_amount = Column(Numeric(18, 4), nullable=True, comment="仓储费用")
    storage_fee_currency = Column(String(10), nullable=True, comment="仓储费用币种")
    utilization_fee_amount = Column(Numeric(18, 4), nullable=True, comment="销毁费用")
    utilization_fee_currency = Column(String(10), nullable=True, comment="销毁费用币种")
    price_amount = Column(Numeric(18, 4), nullable=True, comment="商品价格")
    price_currency = Column(String(10), nullable=True, comment="商品价格币种")
    commission_percent = Column(Numeric(8, 2), nullable=True, comment="佣金百分比")
    commission_amount = Column(Numeric(18, 4), nullable=True, comment="佣金")
    commission_currency = Column(String(10), nullable=True, comment="佣金币种")
    price_without_commission_amount = Column(
        Numeric(18, 4), nullable=True, comment="不含佣金的价格"
    )
    price_without_commission_currency = Column(
        String(10), nullable=True, comment="不含佣金价格币种"
    )

    # 以下为诊断、筛选与兼容用途的补充字段，不属于目标 Excel 主表头。
    brand_name = Column(String(255), nullable=True, comment="品牌名称")
    category_name = Column(String(255), nullable=True, comment="商品品类")
    category_name_cn = Column(String(255), nullable=True, comment="商品品类（中文）")
    product_barcode = Column(String(255), nullable=True, comment="商品条形码")
    exemplar_id = Column(BigInteger, nullable=True, comment="商品实例ID")
    utilization_forecast_at = Column(
        DateTime(timezone=True), nullable=True, comment="预计销毁时间"
    )
    pickup_duration_hours = Column(
        Numeric(12, 2), nullable=True, comment="提货用时（小时）"
    )
    order_id = Column(BigInteger, nullable=True, comment="订单ID")
    order_number = Column(String(100), nullable=True, comment="订单编号")
    srid = Column(
        String(255),
        nullable=True,
        comment="系统订单号（兼容字段，取Ozon order_number）",
    )

    place_id = Column(BigInteger, nullable=True, comment="当前地点ID")
    place_address = Column(Text, nullable=True, comment="当前地点地址")
    place_address_cn = Column(Text, nullable=True, comment="当前地点地址（中文）")
    target_place_id = Column(BigInteger, nullable=True, comment="目标提货点ID")
    return_type = Column(String(50), nullable=True, comment="退货类型")
    is_super_econom = Column(Boolean, nullable=True, comment="是否超级经济")

    __table_args__ = (
        Index("idx_dwd_ozon_return_posting", "posting_number"),
        Index("idx_dwd_ozon_return_order_date", "order_date"),
        Index("idx_dwd_ozon_return_status", "status_sys_name"),
        Index("idx_dwd_ozon_return_offer", "offer_id"),
        {
            "comment": "Ozon退货业务明细表",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )
