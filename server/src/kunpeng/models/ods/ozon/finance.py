"""
Ozon ODS 层 - 财务应计相关表
"""
from sqlalchemy import (
    Column, BigInteger, Integer, String, Boolean, DateTime, Date,
    Numeric, JSON, Index, UniqueConstraint
)
from sqlalchemy.dialects.mysql import VARCHAR, TEXT, DECIMAL
from sqlalchemy.sql import func

from kunpeng.models.base import BaseModel


class ODSOzonFinanceAccrual(BaseModel):
    """
    Ozon ODS 层 - 财务应计主表

    描述: 存储Ozon财务应计主数据，是财务数据的核心表，包含按日期的应计记录、类型、金额、关联单号等信息，用于生成各类财务报表。
    """

    __tablename__ = "ods_ozon_finance_accruals"
    __table_args__ = (
        # by-day 接口每条应计记录以 accrual_id 唯一标识（同一订单多次应计会有不同 accrual_id）。
        # 历史约束曾用 accrual_type_id，但该接口顶层不返回类型，导致该列恒 NULL、约束失效、重复入库，
        # 现改用 (shop_id, accrual_id) 作为业务唯一键。
        UniqueConstraint(
            "shop_id", "accrual_id",
            name="uq_ods_ozon_accruals_shop_accrual_id"
        ),
        Index("idx_ods_ozon_accruals_shop_id", "shop_id"),
        Index("idx_ods_ozon_accruals_accrual_date", "accrual_date"),
        Index("idx_ods_ozon_accruals_unit_number", "unit_number"),
        {
            "comment": "Ozon财务应计主表"
        }
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")
    accrual_id = Column(BigInteger, nullable=True, comment="应计ID (by-day 接口的 accrual_id，业务唯一键)")
    accrual_type_id = Column(BigInteger, nullable=True, comment="应计类型ID (仅 NON_ITEM 类别有单一类型，取 non_item_fee.type_id；POSTING/ITEM 为多类型，见子表)")
    accrual_date = Column(Date, nullable=True, comment="应计日期")
    total_amount = Column(DECIMAL(18, 4), nullable=True, comment="总金额")
    total_currency = Column(VARCHAR(10), nullable=True, comment="币种")
    unit_number = Column(VARCHAR(100), nullable=True, comment="关联单号 (订单号/服务标识)")
    accrued_category = Column(VARCHAR(20), nullable=True, comment="应计类别 (POSTING/ITEM)")
    delivery_schema = Column(VARCHAR(20), nullable=True, comment="发货模式 (FBO/FBS) (POSTING类型时)")
    source_api = Column(VARCHAR(50), nullable=True, comment="数据来源接口 (by-day/postings)")


class ODSOzonAccrualFee(BaseModel):
    """
    Ozon ODS 层 - 应计费用明细表

    描述: 把 by-day 应计记录按"一条费用一行"拆平，统一 POSTING/ITEM/NON_ITEM 三类的费用来源，
    是财务报表的统一明细事实表。一条应计(accrual_id)按来源拆成多行，各行金额求和 == 主表 total_amount。

    费用来源(fee_source)：
    - revenue          营收(合成，type_id=-1，来自 posting.products[].commission.sale_amount)
    - sale_commission  销售佣金(type_id=69，来自 commission.sale_commission)
    - posting_service  订单物流服务费(来自 posting.products[].delivery.services[])
    - item_fee         商品费用(来自 item_fees.fees[].fees[])
    - non_item_fee     非商品费用(来自 non_item_fee，单对象)

    注：bonus(折扣积分)/coinvestment(合作伙伴计划) 不计入 total_amount，不作为费用行，
    如需分析可从主表 row_data 获取。
    """

    __tablename__ = "ods_ozon_finance_accrual_fees"
    __table_args__ = (
        UniqueConstraint(
            "shop_id", "accrual_id", "fee_source", "sku", "type_id",
            name="uq_ods_ozon_finance_accrual_fees_biz"
        ),
        Index("idx_ods_ozon_finance_accrual_fees_accrual_id", "accrual_id"),
        Index("idx_ods_ozon_finance_accrual_fees_shop_date", "shop_id", "accrual_date"),
        Index("idx_ods_ozon_finance_accrual_fees_type_id", "type_id"),
        {
            "comment": "Ozon应计费用明细表(统一拆平的费用行)"
        }
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")
    row_data = Column(JSON, nullable=True, comment="该费用行的原始JSON片段")
    accrual_id = Column(BigInteger, nullable=False, comment="关联应计ID")
    accrual_date = Column(Date, nullable=True, comment="应计日期")
    unit_number = Column(VARCHAR(100), nullable=True, comment="关联单号 (订单号/服务标识)")
    accrued_category = Column(VARCHAR(20), nullable=True, comment="应计类别 (POSTING/ITEM/NON_ITEM)")
    fee_source = Column(VARCHAR(20), nullable=False, comment="费用来源 (revenue/sale_commission/posting_service/item_fee/non_item_fee)")
    sku = Column(BigInteger, nullable=True, comment="商品SKU (非商品费用为NULL)")
    type_id = Column(BigInteger, nullable=True, comment="应计类型ID (营收合成为-1，关联accrual_types)")
    type_name = Column(VARCHAR(100), nullable=True, comment="应计类型英文名 (冗余，来自字典)")
    type_desc = Column(VARCHAR(255), nullable=True, comment="应计类型描述 (冗余，来自字典)")
    amount = Column(DECIMAL(18, 4), nullable=True, comment="金额")
    currency = Column(VARCHAR(10), nullable=True, comment="币种")
    delivery_schema = Column(VARCHAR(20), nullable=True, comment="发货模式 (FBO/FBS，POSTING类型时)")
    seller_price = Column(DECIMAL(18, 4), nullable=True, comment="卖家价格/单价 (仅 revenue 行，来自 commission.seller_price)")
    commission_ratio = Column(DECIMAL(9, 6), nullable=True, comment="销售佣金比例 (仅 revenue 行，来自 commission.commission_ratio)")
