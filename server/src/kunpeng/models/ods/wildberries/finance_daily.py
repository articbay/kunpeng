"""
ODS 层 - Wildberries 销售报告数据模型 (新API版本)
"""

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from kunpeng.models.base import BaseModel


class ODSWBSalesReportDaily(BaseModel):
    """
    ODS 层 - Wildberries 按日销售报告明细数据
    对应新 API: POST /api/finance/v1/sales-reports/detailed
    """

    __tablename__ = "ods_wb_sales_reports_daily"
    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "date_from",
            "date_to",
            "rrd_id",
            name="uq_ods_sales_report_daily_shop_date_rrd",
        ),
        Index("idx_ods_sales_report_daily_shop_id", "shop_id"),
        Index("idx_ods_sales_report_daily_date_range", "date_from", "date_to"),
        Index("idx_ods_sales_report_daily_nm_id", "nm_id"),
        Index(
            "idx_ods_sales_report_daily_shop_order",
            "shop_id",
            "order_id",
        ),
        {"comment": "Wildberries 销售报告明细表（按天维度）"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")

    # 关联店铺
    shop_id = Column(Integer, nullable=False, comment="店铺ID")

    # 原始 JSON 数据
    row_data = Column(JSON, nullable=False, comment="原始响应JSON数据")

    # ========== 报告基本信息 ==========
    report_id = Column(BigInteger, nullable=True, comment="报告ID")
    date_from = Column(Date, nullable=False, comment="开始日期")
    date_to = Column(Date, nullable=False, comment="结束日期")
    create_date = Column(Date, nullable=True, comment="报告创建日期")
    currency = Column(String(10), nullable=True, comment="币种")
    report_type = Column(Integer, nullable=True, comment="报告类型")

    # ========== 记录ID ==========
    rrd_id = Column(BigInteger, nullable=False, comment="编号（唯一值）")
    gi_id = Column(BigInteger, nullable=True, comment="GI ID")

    # ========== 商品信息 ==========
    nm_id = Column(BigInteger, nullable=True, comment="WB商品编号")
    brand_name = Column(String(255), nullable=True, comment="品牌名称")
    vendor_code = Column(String(255), nullable=True, comment="卖家商品编号")
    title = Column(Text, nullable=True, comment="商品标题")
    tech_size = Column(String(100), nullable=True, comment="技术尺寸")
    sku = Column(String(255), nullable=True, comment="条码 (API: sku)")
    subject_name = Column(String(255), nullable=True, comment="商品品类")

    # ========== 文档和操作类型 ==========
    doc_type_name = Column(String(255), nullable=True, comment="文档类型")
    seller_oper_name = Column(String(255), nullable=True, comment="付款依据")
    bonus_type_name = Column(String(255), nullable=True, comment="奖金类型名称")

    # ========== 数量 ==========
    quantity = Column(Integer, nullable=True, comment="数量")
    delivery_amount = Column(Integer, nullable=True, comment="配送数量")
    return_amount = Column(Integer, nullable=True, comment="退货数量")
    dlv_prc = Column(Integer, nullable=True, comment="配送百分比")

    # ========== 价格和金额 (字符串格式，需转换) ==========
    retail_price = Column(Numeric(18, 2), nullable=True, comment="零售价")
    retail_amount = Column(
        Numeric(18, 2), nullable=True, comment="零售总额(WB销售商品)"
    )
    retail_price_with_disc = Column(
        Numeric(18, 2), nullable=True, comment="折扣后零售价"
    )
    sale_percent = Column(Numeric(8, 2), nullable=True, comment="销售百分比")

    # ========== 佣金 ==========
    commission_percent = Column(Numeric(8, 2), nullable=True, comment="佣金百分比")
    spp = Column(Numeric(8, 2), nullable=True, comment="SPP")
    kvw_base = Column(Numeric(8, 2), nullable=True, comment="KVW基础")
    kvw = Column(Numeric(8, 2), nullable=True, comment="KVW")
    ppvz_sales_commission = Column(Numeric(18, 2), nullable=True, comment="销售佣金")
    vw = Column(Numeric(18, 2), nullable=True, comment="VW")
    vw_nds = Column(Numeric(18, 2), nullable=True, comment="含增值税VW")

    # ========== 支付和结算 ==========
    for_pay = Column(Numeric(18, 2), nullable=True, comment="应支付金额")
    ppvz_reward = Column(Numeric(18, 2), nullable=True, comment="奖励")
    acquiring_fee = Column(Numeric(18, 2), nullable=True, comment="收单手续费")
    acquiring_percent = Column(Numeric(8, 2), nullable=True, comment="收单百分比")
    payment_schedule = Column(String(50), nullable=True, comment="付款计划")

    # ========== 物流和仓库 ==========
    delivery_service = Column(Numeric(18, 2), nullable=True, comment="配送服务费")
    paid_storage = Column(Numeric(18, 2), nullable=True, comment="仓储费")
    paid_acceptance = Column(Numeric(18, 2), nullable=True, comment="验收费")
    rebill_logistic_cost = Column(Numeric(18, 2), nullable=True, comment="重新物流成本")
    rebill_logistic_org = Column(String(100), nullable=True, comment="重新物流机构")
    gi_box_type_name = Column(String(100), nullable=True, comment="GI包装类型名称")
    office_name = Column(String(255), nullable=True, comment="仓库名称")
    ppvz_office_name = Column(Text, nullable=True, comment="办公室名称")
    ppvz_office_id = Column(BigInteger, nullable=True, comment="办公室ID")

    # ========== 折扣和促销 ==========
    product_discount_for_report = Column(
        Numeric(18, 2), nullable=True, comment="产品折扣"
    )
    seller_promo = Column(Numeric(18, 2), nullable=True, comment="卖家促销")
    seller_promo_id = Column(BigInteger, nullable=True, comment="卖家促销ID")
    seller_promo_discount = Column(Numeric(8, 2), nullable=True, comment="卖家促销折扣")
    wibes_discount_percent = Column(
        Numeric(8, 2), nullable=True, comment="WIBES折扣百分比"
    )
    cashback_amount = Column(Numeric(18, 2), nullable=True, comment="返现金额")
    cashback_discount = Column(Numeric(18, 2), nullable=True, comment="返现折扣")
    cashback_commission_change = Column(
        Numeric(18, 2), nullable=True, comment="返现佣金变化"
    )
    loyalty_id = Column(BigInteger, nullable=True, comment="忠诚度ID")
    loyalty_discount = Column(Numeric(8, 2), nullable=True, comment="忠诚度折扣")
    uuid_promocode = Column(String(255), nullable=True, comment="促销码UUID")
    sale_price_promocode_discount_prc = Column(
        Numeric(8, 2), nullable=True, comment="促销码折扣百分比"
    )
    sale_price_affiliated_discount_prc = Column(
        Numeric(8, 2), nullable=True, comment="关联折扣百分比"
    )
    sale_price_wholesale_discount_prc = Column(
        Numeric(8, 2), nullable=True, comment="批发折扣百分比"
    )
    article_substitution = Column(String(255), nullable=True, comment="商品替换")

    # ========== 日期和时间 ==========
    order_dt = Column(DateTime(timezone=True), nullable=True, comment="订单日期时间")
    sale_dt = Column(DateTime(timezone=True), nullable=True, comment="销售日期时间")
    rr_date = Column(DateTime(timezone=True), nullable=True, comment="RR日期")
    fix_tariff_date_from = Column(String(50), nullable=True, comment="固定费率开始日期")
    fix_tariff_date_to = Column(String(50), nullable=True, comment="固定费率结束日期")

    # ========== 标识和条码 ==========
    shk_id = Column(BigInteger, nullable=True, comment="SHK ID")
    sticker_id = Column(String(255), nullable=True, comment="贴纸ID")
    order_id = Column(BigInteger, nullable=True, comment="订单ID")
    order_uid = Column(String(255), nullable=True, comment="订单唯一标识")
    srid = Column(String(255), nullable=True, comment="SRID")
    trbx_id = Column(String(100), nullable=True, comment="TRBX ID")

    # ========== 供应商和支付信息 ==========
    ppvz_supplier_name = Column(String(255), nullable=True, comment="供应商名称")
    ppvz_supplier_inn = Column(String(50), nullable=True, comment="供应商INN")
    declaration_number = Column(String(255), nullable=True, comment="报关单号")
    acquiring_bank = Column(String(255), nullable=True, comment="收单银行")
    payment_processing = Column(String(100), nullable=True, comment="支付处理")

    # ========== 国家和类型 ==========
    country = Column(String(50), nullable=True, comment="国家")
    is_b2b = Column(Boolean, nullable=True, comment="是否B2B")
    srv_dbs = Column(Boolean, nullable=True, comment="SRV DBS")
    is_kgvp_v2 = Column(Integer, nullable=True, comment="是否KGVP V2")
    sup_rating_up = Column(Integer, nullable=True, comment="供应商评级提升")

    # ========== 费用和惩罚 ==========
    penalty = Column(Numeric(18, 2), nullable=True, comment="罚款")
    additional_payment = Column(Numeric(18, 2), nullable=True, comment="额外支付")
    deduction = Column(Numeric(18, 2), nullable=True, comment="扣款")
    installment_cofinancing_amount = Column(
        Numeric(18, 2), nullable=True, comment="分期共同融资金额"
    )

    # ========== 物流配送 ==========
    delivery_method = Column(String(255), nullable=True, comment="配送方式")
