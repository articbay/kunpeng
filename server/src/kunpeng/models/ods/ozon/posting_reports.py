"""Ozon shipment-report task and row ODS models."""

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


class ODSOzonPostingReportTask(BaseModel):
    """Metadata for one asynchronous Ozon shipment report."""

    __tablename__ = "ods_ozon_posting_report_tasks"
    __table_args__ = (
        UniqueConstraint(
            "shop_id", "report_code", name="uq_ods_ozon_posting_report_task_code"
        ),
        Index("idx_ods_ozon_posting_report_task_period", "shop_id", "period_from"),
        {"comment": "Ozon发货报表异步任务"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")
    report_code = Column(String(255), nullable=False, comment="Ozon报表任务编码")
    fulfillment_type = Column(String(3), nullable=False, comment="履约方式（FBS/FBO）")
    period_from = Column(
        DateTime(timezone=True), nullable=False, comment="报表开始时间"
    )
    period_to = Column(DateTime(timezone=True), nullable=False, comment="报表结束时间")
    status = Column(String(30), nullable=False, comment="报表任务状态")
    report_type = Column(String(100), nullable=True, comment="Ozon报表类型")
    file_name = Column(String(500), nullable=True, comment="报表文件名或下载地址摘要")
    error_message = Column(Text, nullable=True, comment="报表错误信息")
    report_params = Column(JSON, nullable=True, comment="报表请求参数")
    response_data = Column(JSON, nullable=True, comment="报表状态原始响应")
    row_count = Column(Integer, nullable=True, comment="解析明细行数")
    completed_at = Column(
        DateTime(timezone=True), nullable=True, comment="报表完成时间"
    )


class ODSOzonPostingReportRow(BaseModel):
    """One product row parsed from an Ozon shipment report CSV."""

    __tablename__ = "ods_ozon_posting_report_rows"
    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "fulfillment_type",
            "posting_number",
            "sku",
            name="uq_ods_ozon_posting_report_row_key",
        ),
        Index("idx_ods_ozon_posting_report_row_task", "task_id"),
        Index("idx_ods_ozon_posting_report_row_order", "shop_id", "order_number"),
        {"comment": "Ozon发货报表商品明细ODS"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")
    task_id = Column(BigInteger, nullable=False, comment="报表任务ID")
    report_code = Column(String(255), nullable=False, comment="Ozon报表任务编码")
    fulfillment_type = Column(String(3), nullable=False, comment="履约方式（FBS/FBO）")
    row_data = Column(JSON, nullable=False, comment="CSV原始行数据")

    order_number = Column(String(100), nullable=True, comment="订单号")
    posting_number = Column(String(100), nullable=False, comment="发货号码")
    in_process_at = Column(DateTime(timezone=True), nullable=True, comment="正在处理中")
    shipment_date = Column(DateTime(timezone=True), nullable=True, comment="发运日期")
    shipment_date_without_delay = Column(
        DateTime(timezone=True), nullable=True, comment="不逾期的发运日期"
    )
    report_status = Column(String(255), nullable=True, comment="报表展示状态")
    delivery_date = Column(DateTime(timezone=True), nullable=True, comment="配送日期")
    transferred_to_delivery_at = Column(
        DateTime(timezone=True), nullable=True, comment="实际转移配送日期"
    )
    cancellation_at = Column(DateTime(timezone=True), nullable=True, comment="取消日期")

    shipment_amount = Column(Numeric(18, 4), nullable=True, comment="发货金额")
    shipment_currency = Column(String(10), nullable=True, comment="发货金额币种")
    product_name = Column(Text, nullable=True, comment="商品名称")
    product_color = Column(String(255), nullable=True, comment="商品颜色")
    product_size = Column(String(255), nullable=True, comment="商品尺寸")
    sku = Column(BigInteger, nullable=False, comment="Ozon SKU")
    offer_id = Column(String(255), nullable=True, comment="商家货号")
    additional_packaging = Column(Numeric(18, 4), nullable=True, comment="FBO加包装费")
    sealing = Column(Numeric(18, 4), nullable=True, comment="FBO封装费")
    seller_price = Column(Numeric(18, 4), nullable=True, comment="卖家价格")
    product_currency = Column(String(10), nullable=True, comment="商品币种")
    buyer_paid_amount = Column(Numeric(18, 4), nullable=True, comment="买家支付金额")
    buyer_currency = Column(String(10), nullable=True, comment="买家支付币种")
    quantity = Column(Integer, nullable=True, comment="数量")
    delivery_fee = Column(Numeric(18, 4), nullable=True, comment="配送费用")
    related_posting_number = Column(Text, nullable=True, comment="关联货件")
    is_marketplace_buyout = Column(Boolean, nullable=True, comment="是否商品认购")
    old_price = Column(Numeric(18, 4), nullable=True, comment="折扣前价格")
    discount_percent = Column(Numeric(10, 4), nullable=True, comment="折扣百分比")
    discount_amount = Column(Numeric(18, 4), nullable=True, comment="折扣金额")
    promotion_actions = Column(Text, nullable=True, comment="促销活动")
    actual_tariffication = Column(Text, nullable=True, comment="FBS实际计费")
    floor_lift_fee = Column(Numeric(18, 4), nullable=True, comment="FBS上楼费")
    product_volume_weight = Column(
        Numeric(12, 4), nullable=True, comment="FBO商品体积重量（公斤）"
    )
