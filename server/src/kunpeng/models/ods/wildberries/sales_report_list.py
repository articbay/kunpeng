"""ODS 层 - Wildberries 财务报表列表模型。"""

from sqlalchemy import (JSON, BigInteger, Column, Date, DateTime, Index,
                        Integer, Numeric, String, UniqueConstraint)

from kunpeng.models.base import BaseModel


class ODSWBSalesReportList(BaseModel):
    """Wildberries 周度财务报表汇总。"""

    __tablename__ = "ods_wb_sales_report_list"

    id = Column(
        BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID"
    )
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")
    report_id = Column(BigInteger, nullable=False, comment="Wildberries报表ID")
    seller_finance_name = Column(String(255), nullable=True, comment="卖家财务主体名称")
    date_from = Column(Date, nullable=False, comment="报表开始日期")
    date_to = Column(Date, nullable=False, comment="报表结束日期")
    create_date = Column(Date, nullable=True, comment="报表生成日期")
    currency = Column(String(10), nullable=True, comment="币种")
    report_type = Column(Integer, nullable=True, comment="报表类型")
    retail_amount_sum = Column(Numeric(20, 2), nullable=True, comment="零售金额合计")
    for_pay_sum = Column(Numeric(20, 2), nullable=True, comment="应付金额合计")
    avg_sale_percent = Column(
        Numeric(10, 4), nullable=True, comment="平均销售折扣百分比"
    )
    delivery_service_sum = Column(
        Numeric(20, 2), nullable=True, comment="配送服务费合计"
    )
    paid_storage_sum = Column(Numeric(20, 2), nullable=True, comment="付费仓储费合计")
    paid_acceptance_sum = Column(
        Numeric(20, 2), nullable=True, comment="付费验收费合计"
    )
    deduction_sum = Column(Numeric(20, 2), nullable=True, comment="扣款合计")
    penalty_sum = Column(Numeric(20, 2), nullable=True, comment="罚款合计")
    additional_payment_sum = Column(
        Numeric(20, 2), nullable=True, comment="额外付款合计"
    )
    cashback_amount_sum = Column(Numeric(20, 2), nullable=True, comment="返现金额合计")
    cashback_discount_sum = Column(
        Numeric(20, 2), nullable=True, comment="返现折扣合计"
    )
    cashback_commission_change_sum = Column(
        Numeric(20, 2), nullable=True, comment="返现佣金调整合计"
    )
    payment_schedule = Column(String(50), nullable=True, comment="付款计划")
    bank_payment_sum = Column(Numeric(20, 2), nullable=True, comment="银行付款合计")
    row_data = Column(JSON, nullable=False, comment="API原始JSON数据")
    synced_at = Column(DateTime(timezone=True), nullable=False, comment="同步时间")

    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "report_id",
            name="uq_ods_wb_sales_report_list_shop_report",
        ),
        Index("idx_ods_wb_sales_report_list_shop_id", "shop_id"),
        Index(
            "idx_ods_wb_sales_report_list_date_range",
            "date_from",
            "date_to",
        ),
        Index("idx_ods_wb_sales_report_list_create_date", "create_date"),
        {"comment": "Wildberries财务报表列表汇总表"},
    )
