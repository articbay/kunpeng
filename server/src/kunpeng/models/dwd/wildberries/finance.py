"""DWD 层 - Wildberries 财务结算明细模型。"""

from sqlalchemy import (
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


class DWDWBSalesReportDetail(BaseModel):
    """按最终表头映射表清洗后的 WB 财务结算明细。"""

    __tablename__ = "dwd_wb_sales_report_detail"
    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "rrd_id",
            name="uq_dwd_wb_sales_report_shop_rrd",
        ),
        UniqueConstraint(
            "source_ods_id",
            name="uq_dwd_wb_sales_report_source_ods",
        ),
        Index("idx_dwd_wb_sales_report_date_from", "date_from"),
        Index("idx_dwd_wb_sales_report_nm_id", "nm_id"),
        {"comment": "Wildberries 财务结算明细 DWD 表"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    source_ods_id = Column(
        BigInteger,
        nullable=False,
        comment="来源 ods_wb_sales_reports.id",
    )
    shop_id = Column(Integer, nullable=False, comment="店铺ID")

    date_from = Column(Date, nullable=False, comment="财务报告周开始日期")
    rrd_id = Column(BigInteger, nullable=False, comment="财务结算明细唯一编号")
    gi_id = Column(BigInteger, nullable=True, comment="供货编号")
    subject_name = Column(String(255), nullable=True, comment="商品品类")
    nm_id = Column(BigInteger, nullable=True, comment="WB商品编号")
    brand_name = Column(String(255), nullable=True, comment="品牌")
    vendor_code = Column(String(255), nullable=True, comment="卖家商品编号")
    title = Column(Text, nullable=True, comment="商品名称")
    tech_size = Column(String(100), nullable=True, comment="尺码")
    sku = Column(String(255), nullable=True, comment="条形码")
    doc_type_name = Column(String(255), nullable=True, comment="文档类型")
    seller_oper_name = Column(String(255), nullable=True, comment="付款依据")
    order_dt = Column(DateTime(timezone=True), nullable=True, comment="买家下单日期")
    sale_dt = Column(DateTime(timezone=True), nullable=True, comment="销售日期")
    quantity = Column(Integer, nullable=True, comment="数量")
    retail_price = Column(Numeric(18, 2), nullable=True, comment="零售价")
    retail_amount = Column(Numeric(18, 2), nullable=True, comment="WB销售商品金额")
    sale_percent = Column(Numeric(8, 2), nullable=True, comment="协商商品折扣比例")
    seller_promo = Column(Numeric(18, 2), nullable=True, comment="促销码比例")
    product_discount_for_report = Column(
        Numeric(18, 2),
        nullable=True,
        comment="最终折扣比例",
    )
    retail_price_with_disc = Column(
        Numeric(18, 2),
        nullable=True,
        comment="包含最终折扣的零售价格",
    )
    sup_rating_up = Column(
        Integer,
        nullable=True,
        comment="卖家评级佣金减免比例",
    )
    is_kgvp_v2 = Column(
        Integer,
        nullable=True,
        comment="促销活动佣金减免标识",
    )
    spp = Column(Numeric(8, 2), nullable=True, comment="常客折扣比例")
    commission_percent = Column(
        Numeric(8, 2),
        nullable=True,
        comment="WB佣金比例",
    )
    kvw_base = Column(
        Numeric(8, 2),
        nullable=True,
        comment="WB基础佣金比例（不含增值税）",
    )
    kvw = Column(
        Numeric(8, 2),
        nullable=True,
        comment="WB最终佣金比例（不含增值税）",
    )
    ppvz_sales_commission = Column(
        Numeric(18, 2),
        nullable=True,
        comment="未扣代理服务费和增值税的销售佣金",
    )
    ppvz_reward = Column(
        Numeric(18, 2),
        nullable=True,
        comment="取件和退货服务费用赔偿",
    )
    acquiring_fee = Column(
        Numeric(18, 2),
        nullable=True,
        comment="收单或支付结算服务费",
    )
    acquiring_percent = Column(
        Numeric(8, 2),
        nullable=True,
        comment="收单或支付结算服务费率",
    )
    payment_processing = Column(
        String(100),
        nullable=True,
        comment="收单或支付结算付款类型",
    )
    vw = Column(Numeric(18, 2), nullable=True, comment="WB佣金（不含增值税）")
    vw_nds = Column(Numeric(18, 2), nullable=True, comment="WB佣金增值税")
    for_pay = Column(
        Numeric(18, 2),
        nullable=True,
        comment="支付给卖家的已售商品金额",
    )
    delivery_amount = Column(Integer, nullable=True, comment="交付数量")
    return_amount = Column(Integer, nullable=True, comment="退货数量")
    delivery_service = Column(
        Numeric(18, 2),
        nullable=True,
        comment="向买家交付货物的服务费",
    )
    dlv_prc = Column(Integer, nullable=True, comment="仓库供应固定系数")
    fix_tariff_date_from = Column(
        String(50),
        nullable=True,
        comment="固定费率开始日期",
    )
    fix_tariff_date_to = Column(
        String(50),
        nullable=True,
        comment="固定费率结束日期",
    )
    srv_dbs = Column(Boolean, nullable=True, comment="付费配送服务标识")
    penalty = Column(Numeric(18, 2), nullable=True, comment="罚款总额")
    additional_payment = Column(
        Numeric(18, 2),
        nullable=True,
        comment="WB佣金调整",
    )
    bonus_type_name = Column(
        String(255),
        nullable=True,
        comment="物流、罚款及WB佣金调整类型",
    )
    shk_id = Column(BigInteger, nullable=True, comment="FBS标签")
    acquiring_bank = Column(String(255), nullable=True, comment="收单银行名称")
    ppvz_office_id = Column(BigInteger, nullable=True, comment="办公室编号")
    ppvz_office_name = Column(Text, nullable=True, comment="送货点名称")
    ppvz_supplier_inn = Column(String(50), nullable=True, comment="合作站点税号")
    ppvz_supplier_name = Column(String(255), nullable=True, comment="合作伙伴")
    office_name = Column(String(255), nullable=True, comment="仓库")
    country = Column(String(50), nullable=True, comment="国家")
    gi_box_type_name = Column(String(100), nullable=True, comment="箱型")
    declaration_number = Column(String(255), nullable=True, comment="报关单号")
    order_id = Column(BigInteger, nullable=True, comment="配货任务编号")
    kiz = Column(String(255), nullable=True, comment="标记编码，来源 row_data.kiz")
    sticker_id = Column(String(255), nullable=True, comment="仓库标签")
    srid = Column(String(255), nullable=True, comment="SRID")
    rebill_logistic_cost = Column(
        Numeric(18, 2),
        nullable=True,
        comment="运输或仓储费用补偿",
    )
    rebill_logistic_org = Column(String(100), nullable=True, comment="承运人")
    paid_storage = Column(Numeric(18, 2), nullable=True, comment="仓储费")
    deduction = Column(Numeric(18, 2), nullable=True, comment="扣款")
    paid_acceptance = Column(
        Numeric(18, 2),
        nullable=True,
        comment="入库验收操作费",
    )
    is_b2b = Column(Boolean, nullable=True, comment="向法人实体销售标识")
    trbx_id = Column(String(100), nullable=True, comment="商品处理箱号")
    installment_cofinancing_amount = Column(
        Numeric(18, 2),
        nullable=True,
        comment="联合融资计划折扣",
    )
    wibes_discount_percent = Column(
        Numeric(8, 2),
        nullable=True,
        comment="Wibes折扣比例",
    )
    cashback_discount = Column(
        Numeric(18, 2),
        nullable=True,
        comment="忠诚度计划折扣补偿",
    )
    cashback_commission_change = Column(
        Numeric(18, 2),
        nullable=True,
        comment="忠诚度计划参与费用",
    )
    cashback_amount = Column(
        Numeric(18, 2),
        nullable=True,
        comment="已扣除的忠诚度积分金额",
    )
    order_uid = Column(String(255), nullable=True, comment="订单购物车ID")
    payment_schedule = Column(
        String(50),
        nullable=True,
        comment="一次性结算周期变更",
    )
    delivery_method = Column(String(255), nullable=True, comment="商品配送方式")
