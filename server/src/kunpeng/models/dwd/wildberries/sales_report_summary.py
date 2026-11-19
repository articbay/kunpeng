"""DWD 层 - Wildberries 财务报告周汇总模型。"""

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)

from kunpeng.models.base import BaseModel


class DWDWBSalesReportSummary(BaseModel):
    """与店铺后台“财务报告周汇总”口径一致的报告级事实表。"""

    __tablename__ = "dwd_wb_sales_report_summary"
    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "report_id",
            name="uq_dwd_wb_sales_report_summary_shop_report",
        ),
        UniqueConstraint(
            "source_ods_id",
            name="uq_dwd_wb_sales_report_summary_source_ods",
        ),
        Index("idx_dwd_wb_sales_report_summary_shop_id", "shop_id"),
        Index(
            "idx_dwd_wb_sales_report_summary_date_range",
            "date_from",
            "date_to",
        ),
        Index(
            "idx_dwd_wb_sales_report_summary_create_date",
            "create_date",
        ),
        {"comment": "Wildberries 财务报告周汇总 DWD 表"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    source_ods_id = Column(
        BigInteger,
        nullable=False,
        comment="来源 ods_wb_sales_report_list.id",
    )
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")

    # 与“财务报告周汇总”表头顺序一致。
    report_id = Column(BigInteger, nullable=False, comment="报告编号")
    seller_finance_name = Column(String(255), nullable=True, comment="法人")
    date_from = Column(Date, nullable=False, comment="开始日期")
    date_to = Column(Date, nullable=False, comment="结束日期")
    create_date = Column(Date, nullable=True, comment="生成日期")
    report_type = Column(Integer, nullable=True, comment="报告类型")
    retail_amount_sum = Column(Numeric(20, 2), nullable=True, comment="销售")
    cashback_discount_sum = Column(
        Numeric(20, 2),
        nullable=True,
        comment="包括忠诚度计划的折扣赔偿",
    )
    for_pay_sum = Column(
        Numeric(20, 2),
        nullable=True,
        comment="应支付商品金额",
    )
    avg_sale_percent = Column(
        Numeric(10, 4),
        nullable=True,
        comment="协商折扣(%)",
    )
    delivery_service_sum = Column(
        Numeric(20, 2),
        nullable=True,
        comment="物流费用",
    )
    paid_storage_sum = Column(
        Numeric(20, 2),
        nullable=True,
        comment="仓储费用",
    )
    paid_acceptance_sum = Column(
        Numeric(20, 2),
        nullable=True,
        comment="入库验收费用",
    )
    deduction_sum = Column(
        Numeric(20, 2),
        nullable=True,
        comment="其他扣款/付款",
    )
    penalty_sum = Column(Numeric(20, 2), nullable=True, comment="罚款总额")
    additional_payment_sum = Column(
        Numeric(20, 2),
        nullable=True,
        comment="WB佣金调整",
    )
    cashback_commission_change_sum = Column(
        Numeric(20, 2),
        nullable=True,
        comment="忠诚度计划参与费用",
    )
    cashback_amount_sum = Column(
        Numeric(20, 2),
        nullable=True,
        comment="已扣除的忠诚度积分金额",
    )
    payment_schedule = Column(
        Numeric(20, 2),
        nullable=True,
        comment="一次性结算周期变更",
    )
    bank_payment_sum = Column(
        Numeric(20, 2),
        nullable=True,
        comment="应付总额",
    )
    currency = Column(String(10), nullable=True, comment="货币")
