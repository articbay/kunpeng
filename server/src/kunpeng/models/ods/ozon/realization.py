"""
Ozon ODS 层 - 销售实现报告相关表
"""
from sqlalchemy import (
    Column, BigInteger, Integer, String, Boolean, DateTime, Date,
    Numeric, JSON, Index, UniqueConstraint
)
from sqlalchemy.dialects.mysql import VARCHAR, TEXT, DECIMAL
from sqlalchemy.sql import func

from kunpeng.models.base import BaseModel


class ODSOzonFinanceRealizationHeader(BaseModel):
    """
    Ozon ODS 层 - 销售实现报告头表

    描述: 存储Ozon销售实现报告的头部信息，包含报告编号、日期范围、合同信息、收付款方信息等报告基础信息。
    """

    __tablename__ = "ods_ozon_finance_realization_header"
    __table_args__ = (
        UniqueConstraint(
            "shop_id", "report_number",
            name="uq_ods_ozon_realization_header_shop_report"
        ),
        Index("idx_ods_ozon_realization_header_shop_id", "shop_id"),
        Index("idx_ods_ozon_realization_header_doc_date", "doc_date"),
        {
            "comment": "Ozon销售实现报告头表"
        }
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")
    report_number = Column(VARCHAR(100), nullable=True, comment="报告编号")
    doc_date = Column(Date, nullable=True, comment="报告日期")
    start_date = Column(Date, nullable=True, comment="开始日期")
    stop_date = Column(Date, nullable=True, comment="结束日期")
    contract_date = Column(Date, nullable=True, comment="合同日期")
    contract_number = Column(VARCHAR(100), nullable=True, comment="合同编号")
    currency = Column(VARCHAR(10), nullable=True, comment="币种")
    payer_name = Column(TEXT, nullable=True, comment="付款方名称")
    payer_inn = Column(VARCHAR(50), nullable=True, comment="付款方INN")
    payer_kpp = Column(VARCHAR(50), nullable=True, comment="付款方KPP")
    receiver_name = Column(TEXT, nullable=True, comment="收款方名称")
    receiver_inn = Column(VARCHAR(50), nullable=True, comment="收款方INN")
    receiver_kpp = Column(VARCHAR(50), nullable=True, comment="收款方KPP")


class ODSOzonFinanceRealizationRow(BaseModel):
    """
    Ozon ODS 层 - 销售实现报告行表

    描述: 存储Ozon销售实现报告的行数据，包含商品销售和退货的明细数据，如价格、数量、佣金、奖励等财务信息。
    """

    __tablename__ = "ods_ozon_finance_realization_rows"
    __table_args__ = (
        UniqueConstraint(
            "shop_id", "header_id", "row_number",
            name="uq_ods_ozon_realization_rows_shop_header_row"
        ),
        Index("idx_ods_ozon_realization_rows_header_id", "header_id"),
        Index("idx_ods_ozon_realization_rows_sku", "sku"),
        {
            "comment": "Ozon销售实现报告行表"
        }
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")
    header_id = Column(BigInteger, nullable=True, comment="关联报告头ID")
    row_number = Column(Integer, nullable=True, comment="行号")
    product_name = Column(TEXT, nullable=True, comment="商品名称")
    offer_id = Column(VARCHAR(255), nullable=True, comment="商家SKU")
    sku = Column(BigInteger, nullable=True, comment="Ozon SKU")
    barcode = Column(VARCHAR(255), nullable=True, comment="条形码")
    seller_price_per_instance = Column(DECIMAL(18, 4), nullable=True, comment="折扣前价格")
    is_return = Column(Boolean, nullable=True, comment="是否退货")
    sold_price_per_instance = Column(DECIMAL(18, 4), nullable=True, comment="销售单价")
    sold_quantity = Column(Integer, nullable=True, comment="销售数量")
    sold_amount = Column(DECIMAL(18, 4), nullable=True, comment="销售金额")
    sold_standard_fee = Column(DECIMAL(18, 4), nullable=True, comment="标准佣金")
    sold_bonus = Column(DECIMAL(18, 4), nullable=True, comment="奖金/积分")
    sold_bank_coinvestment = Column(DECIMAL(18, 4), nullable=True, comment="合作伙伴奖励")
    sold_total = Column(DECIMAL(18, 4), nullable=True, comment="总应计金额")
    return_price_per_instance = Column(DECIMAL(18, 4), nullable=True, comment="退货单价")
    return_quantity = Column(Integer, nullable=True, comment="退货数量")
    return_amount = Column(DECIMAL(18, 4), nullable=True, comment="退货金额")
    return_standard_fee = Column(DECIMAL(18, 4), nullable=True, comment="退货-标准佣金")
    return_bonus = Column(DECIMAL(18, 4), nullable=True, comment="退货-奖金/积分")
    return_bank_coinvestment = Column(DECIMAL(18, 4), nullable=True, comment="退货-合作伙伴奖励")
    return_total = Column(DECIMAL(18, 4), nullable=True, comment="退货-总应计金额")
    commission_ratio = Column(DECIMAL(10, 6), nullable=True, comment="佣金比例")
