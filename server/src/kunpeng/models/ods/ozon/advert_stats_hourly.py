"""
Ozon ODS 层 - 广告SKU小时统计模型
"""
from sqlalchemy import (
    Column, BigInteger, Integer, JSON, Index, UniqueConstraint, Date
)
from sqlalchemy.dialects.mysql import VARCHAR, DECIMAL, TEXT

from kunpeng.models.base import BaseModel


class ODSOzonAdvStatProductHourly(BaseModel):
    """
    Ozon ODS 层 - 广告SKU小时统计表（活动 x SKU x 日期 x 小时维度）

    描述: 存储按小时拆解的 SKU 级广告统计数据，维度对齐 ods_ozon_adv_stats_product_daily，
    额外增加 stat_hour。

    口径参照 Wildberries 广告小时统计（ods_wb_advert_stats_hourly）:
    Ozon Performance API 仅提供「按天累计」数据（异步报表 group_by=DATE），无原生小时接口。
    故小时数据通过「当天累计值 - 当天已写入小时累计」计算当前小时增量得到，
    由定时任务每小时执行一次幂等落库。

    字段区分:
    - 累加型指标（views/clicks/toCart/moneySpent/orders/ordersMoney/models/modelsMoney/productGmv）
      存储「当前小时增量」；
    - 派生/快照型指标（price/ctr/avgBid/drr/generalDrr 等）存储「当天累计快照值」，
      不做增量计算。
    """

    __tablename__ = "ods_ozon_adv_stats_product_hourly"
    __table_args__ = (
        UniqueConstraint(
            "shop_id", "campaign_id", "sku", "stat_date", "stat_hour",
            name="uq_ods_ozon_adv_stats_product_hourly_key"
        ),
        Index("idx_ods_ozon_adv_stats_product_hourly_shop_id", "shop_id"),
        Index("idx_ods_ozon_adv_stats_product_hourly_campaign_id", "campaign_id"),
        Index("idx_ods_ozon_adv_stats_product_hourly_date", "stat_date"),
        Index("idx_ods_ozon_adv_stats_product_hourly_hour", "stat_hour"),
        Index("idx_ods_ozon_adv_stats_product_hourly_sku", "sku"),
        {"comment": "Ozon广告SKU小时统计表"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, index=True, comment="店铺ID")
    row_data = Column(JSON, nullable=False, comment="原始JSON数据（当天累计快照）")
    campaign_id = Column(VARCHAR(64), nullable=False, comment="广告活动ID")
    sku = Column(BigInteger, nullable=False, comment="商品SKU")
    stat_date = Column(Date, nullable=False, comment="统计日期")
    stat_hour = Column(Integer, nullable=False, comment="统计小时（0-23）")
    title = Column(TEXT, nullable=True, comment="商品名称")
    search_query = Column(VARCHAR(500), nullable=True, comment="搜索词")
    price = Column(DECIMAL(18, 4), nullable=True, comment="商品价格（当天累计快照）")
    views = Column(BigInteger, nullable=True, comment="展现量（当前小时增量）")
    clicks = Column(BigInteger, nullable=True, comment="点击次数（当前小时增量）")
    ctr = Column(DECIMAL(10, 4), nullable=True, comment="点击率(%)（当天累计快照）")
    to_cart = Column(BigInteger, nullable=True, comment="加购次数（当前小时增量）")
    avg_bid = Column(DECIMAL(18, 4), nullable=True, comment="平均出价（当天累计快照）")
    money_spent = Column(DECIMAL(18, 4), nullable=True, comment="广告费用(₽)（当前小时增量）")
    orders = Column(BigInteger, nullable=True, comment="订单数（当前小时增量）")
    orders_money = Column(DECIMAL(18, 4), nullable=True, comment="订单销售额(₽)（当前小时增量）")
    models = Column(BigInteger, nullable=True, comment="含组合卡的订单数（当前小时增量）")
    models_money = Column(DECIMAL(18, 4), nullable=True, comment="含组合卡的销售额(₽)（当前小时增量）")
    drr = Column(DECIMAL(10, 4), nullable=True, comment="广告费用份额DRR(%)（当天累计快照）")
    general_drr = Column(DECIMAL(10, 4), nullable=True, comment="总DRR(%)（当天累计快照）")
    product_gmv = Column(DECIMAL(18, 4), nullable=True, comment="商品GMV(₽)（当前小时增量）")
