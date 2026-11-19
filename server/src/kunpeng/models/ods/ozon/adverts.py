"""
Ozon ODS 层 - 广告（Performance API）相关表
"""
from sqlalchemy import (
    Column, BigInteger, Integer, JSON, Index, UniqueConstraint, Date
)
from sqlalchemy.dialects.mysql import VARCHAR, DECIMAL, TEXT

from kunpeng.models.base import BaseModel


class ODSOzonAdvCampaign(BaseModel):
    """
    Ozon ODS 层 - 广告活动表

    描述: 存储 Ozon Performance API 的广告活动（campaign）主数据，
    来源接口 GET /api/client/campaign，用于活动维度分析与统计表关联。
    """

    __tablename__ = "ods_ozon_adv_campaigns"
    __table_args__ = (
        UniqueConstraint(
            "shop_id", "campaign_id",
            name="uq_ods_ozon_adv_campaigns_shop_campaign"
        ),
        Index("idx_ods_ozon_adv_campaigns_shop_id", "shop_id"),
        {"comment": "Ozon广告活动表"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")
    campaign_id = Column(VARCHAR(64), nullable=False, comment="广告活动ID")
    title = Column(VARCHAR(500), nullable=True, comment="广告活动名称")
    state = Column(VARCHAR(64), nullable=True, comment="活动状态(CAMPAIGN_STATE_*)")
    adv_object_type = Column(VARCHAR(64), nullable=True, comment="广告对象类型(如SKU)")
    placement = Column(VARCHAR(255), nullable=True, comment="投放位置(placement数组拼接)")
    payment_type = Column(VARCHAR(64), nullable=True, comment="付费类型(如CPC)")
    # 注意: Performance API 预算字段单位为「微卢布(micro)」整数，即 卢布 × 10^6。
    # 例如 6000000000 表示 6000₽。ODS 层忠实存原始值，换算为卢布请在分析层 /1e6。
    daily_budget = Column(DECIMAL(18, 4), nullable=True, comment="日预算(单位:微卢布/micro，=卢布×10^6)")
    weekly_budget = Column(DECIMAL(18, 4), nullable=True, comment="周预算(单位:微卢布/micro，=卢布×10^6)")
    budget = Column(DECIMAL(18, 4), nullable=True, comment="总预算(单位:微卢布/micro，=卢布×10^6)")
    from_date = Column(Date, nullable=True, comment="活动开始日期")
    to_date = Column(Date, nullable=True, comment="活动结束日期")


class ODSOzonAdvStatDaily(BaseModel):
    """
    Ozon ODS 层 - 广告日统计表（活动 x 日期维度）

    描述: 存储 Performance API 按天统计数据，
    来源接口 GET /api/client/statistics/daily/json。
    对齐 Excel《推广分析》中的展现量/点击/费用/订单/销售额等指标。
    CTR、单笔费用、每次点击成本、广告费用份额(DRR)等派生指标在分析层计算。
    """

    __tablename__ = "ods_ozon_adv_stats_daily"
    __table_args__ = (
        UniqueConstraint(
            "shop_id", "campaign_id", "stat_date",
            name="uq_ods_ozon_adv_stats_daily_shop_campaign_date"
        ),
        Index("idx_ods_ozon_adv_stats_daily_shop_id", "shop_id"),
        Index("idx_ods_ozon_adv_stats_daily_date", "stat_date"),
        {"comment": "Ozon广告日统计表"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")
    campaign_id = Column(VARCHAR(64), nullable=False, comment="广告活动ID")
    title = Column(VARCHAR(500), nullable=True, comment="广告活动名称")
    stat_date = Column(Date, nullable=False, comment="统计日期")
    views = Column(BigInteger, nullable=True, comment="展现量")
    clicks = Column(BigInteger, nullable=True, comment="点击次数")
    money_spent = Column(DECIMAL(18, 4), nullable=True, comment="费用(₽)")
    orders = Column(BigInteger, nullable=True, comment="订单数")
    orders_money = Column(DECIMAL(18, 4), nullable=True, comment="销售额(₽)")


class ODSOzonAdvStatProductDaily(BaseModel):
    """
    Ozon ODS 层 - 广告SKU日统计表（活动 x SKU x 日期维度）

    描述: 存储 Performance API 异步报表的 SKU 级明细，
    来源接口 POST /api/client/statistics/json + 轮询下载。
    对齐 Excel《推广分析》的 SKU、商品名称、CTR、加购(toCart)、DRR 等指标。
    金额为俄式小数，日期为 DD.MM.YYYY，入库前转换。
    """

    __tablename__ = "ods_ozon_adv_stats_product_daily"
    __table_args__ = (
        UniqueConstraint(
            "shop_id", "campaign_id", "sku", "stat_date",
            name="uq_ods_ozon_adv_stats_product_daily_key"
        ),
        Index("idx_ods_ozon_adv_stats_product_daily_shop_id", "shop_id"),
        Index("idx_ods_ozon_adv_stats_product_daily_date", "stat_date"),
        Index("idx_ods_ozon_adv_stats_product_daily_sku", "sku"),
        {"comment": "Ozon广告SKU日统计表"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")
    campaign_id = Column(VARCHAR(64), nullable=False, comment="广告活动ID")
    sku = Column(BigInteger, nullable=False, comment="商品SKU")
    stat_date = Column(Date, nullable=False, comment="统计日期")
    title = Column(TEXT, nullable=True, comment="商品名称")
    search_query = Column(VARCHAR(500), nullable=True, comment="搜索词")
    price = Column(DECIMAL(18, 4), nullable=True, comment="商品价格")
    views = Column(BigInteger, nullable=True, comment="展现量")
    clicks = Column(BigInteger, nullable=True, comment="点击次数")
    ctr = Column(DECIMAL(10, 4), nullable=True, comment="点击率(%)")
    to_cart = Column(BigInteger, nullable=True, comment="加购次数")
    avg_bid = Column(DECIMAL(18, 4), nullable=True, comment="平均出价")
    money_spent = Column(DECIMAL(18, 4), nullable=True, comment="广告费用(₽)")
    orders = Column(BigInteger, nullable=True, comment="订单数")
    orders_money = Column(DECIMAL(18, 4), nullable=True, comment="订单销售额(₽)")
    models = Column(BigInteger, nullable=True, comment="含组合卡的订单数")
    models_money = Column(DECIMAL(18, 4), nullable=True, comment="含组合卡的销售额(₽)")
    drr = Column(DECIMAL(10, 4), nullable=True, comment="广告费用份额DRR(%)")
    general_drr = Column(DECIMAL(10, 4), nullable=True, comment="总DRR(%)")
    product_gmv = Column(DECIMAL(18, 4), nullable=True, comment="商品GMV(₽)")
