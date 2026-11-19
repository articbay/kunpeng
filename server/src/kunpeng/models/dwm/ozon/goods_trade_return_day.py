"""Ozon order-cohort trade and return daily aggregate model."""

from sqlalchemy import (  # isort: skip
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Index,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.sql import func

from kunpeng.core.database import Base


class DWMOzonGoodsTradeReturnDay(Base):
    """One row per Ozon shop, platform day and SKU."""

    __tablename__ = "dwm_ozon_goods_trade_return_day"

    stat_date = Column(Date, primary_key=True, nullable=False, comment="平台统计日期")
    shop_id = Column(BigInteger, primary_key=True, nullable=False, comment="店铺ID")
    sku = Column(BigInteger, primary_key=True, nullable=False, comment="Ozon SKU")

    offer_id = Column(String(255), nullable=True, comment="商家货号")
    product_name = Column(Text, nullable=True, comment="商品名称")
    product_name_cn = Column(Text, nullable=True, comment="商品名称（中文）")
    category_name = Column(String(255), nullable=True, comment="商品品类")
    category_name_cn = Column(String(255), nullable=True, comment="商品品类（中文）")

    order_cnt = Column(
        BigInteger,
        nullable=False,
        server_default=text("0"),
        comment="去重货件数",
    )
    order_line_cnt = Column(
        BigInteger,
        nullable=False,
        server_default=text("0"),
        comment="订单商品明细行数",
    )
    order_qty = Column(
        BigInteger, nullable=False, server_default=text("0"), comment="下单件数"
    )
    delivered_qty = Column(
        BigInteger, nullable=False, server_default=text("0"), comment="已送达件数"
    )
    cancelled_qty = Column(
        BigInteger, nullable=False, server_default=text("0"), comment="已取消件数"
    )
    sales_amount_sum = Column(
        Numeric(18, 4),
        nullable=True,
        server_default=text("0"),
        comment="销售金额合计（seller_price×quantity）",
    )
    sales_currency = Column(String(10), nullable=True, comment="销售金额币种")

    return_cnt = Column(
        BigInteger, nullable=False, server_default=text("0"), comment="退货单数"
    )
    return_qty = Column(
        BigInteger, nullable=False, server_default=text("0"), comment="退货件数"
    )
    return_amount_sum = Column(
        Numeric(18, 4),
        nullable=True,
        server_default=text("0"),
        comment="退货商品金额合计",
    )
    return_amount_currency = Column(
        String(10), nullable=True, comment="退货商品金额币种"
    )
    storage_fee_sum = Column(
        Numeric(18, 4),
        nullable=True,
        server_default=text("0"),
        comment="退货仓储费合计",
    )
    storage_fee_currency = Column(String(10), nullable=True, comment="退货仓储费币种")
    utilization_fee_sum = Column(
        Numeric(18, 4),
        nullable=True,
        server_default=text("0"),
        comment="退货销毁费合计",
    )
    utilization_fee_currency = Column(
        String(10), nullable=True, comment="退货销毁费币种"
    )
    commission_amount_sum = Column(
        Numeric(18, 4),
        nullable=True,
        server_default=text("0"),
        comment="退货佣金合计",
    )
    commission_currency = Column(String(10), nullable=True, comment="退货佣金币种")

    return_rate_ordered = Column(
        Numeric(12, 6),
        nullable=False,
        server_default=text("0"),
        comment="按下单件数计算的退货率（0-1）",
    )
    return_rate_delivered = Column(
        Numeric(12, 6),
        nullable=False,
        server_default=text("0"),
        comment="按送达件数计算的退货率（0-1）",
    )
    has_currency_conflict = Column(
        Boolean,
        nullable=False,
        server_default=text("0"),
        comment="金额存在混币或缺少币种",
    )

    has_funnel_data = Column(
        Boolean,
        nullable=False,
        server_default=text("0"),
        comment="销售漏斗DWD是否存在该商品日",
    )
    has_traffic_metrics = Column(
        Boolean,
        nullable=False,
        server_default=text("0"),
        comment="销售漏斗是否实际返回流量指标",
    )
    funnel_ordered_units = Column(
        BigInteger, nullable=True, comment="Ozon销售漏斗下单商品件数"
    )
    funnel_revenue = Column(
        Numeric(18, 4), nullable=True, comment="Ozon销售漏斗下单金额"
    )
    traffic_views_search = Column(
        BigInteger, nullable=True, comment="搜索和类目展示次数"
    )
    traffic_views_pdp = Column(BigInteger, nullable=True, comment="商品详情页浏览次数")
    traffic_views = Column(BigInteger, nullable=True, comment="总展示/浏览次数")
    traffic_visitors_search = Column(
        BigInteger, nullable=True, comment="搜索和类目访问用户数"
    )
    traffic_visitors_pdp = Column(
        BigInteger, nullable=True, comment="商品详情页访问用户数"
    )
    traffic_visitors = Column(BigInteger, nullable=True, comment="总访问用户数")
    traffic_to_cart_search = Column(
        BigInteger, nullable=True, comment="搜索和类目加购次数"
    )
    traffic_to_cart_pdp = Column(
        BigInteger, nullable=True, comment="商品详情页加购次数"
    )
    traffic_to_cart = Column(BigInteger, nullable=True, comment="总加购次数")
    traffic_cart_rate = Column(
        Numeric(12, 6), nullable=True, comment="全站加购率（总加购/总访问用户，0-1）"
    )

    has_ad_data = Column(
        Boolean,
        nullable=False,
        server_default=text("0"),
        comment="广告效率DWD是否存在该商品日",
    )
    ad_campaign_cnt = Column(BigInteger, nullable=True, comment="广告活动数")
    ad_views = Column(BigInteger, nullable=True, comment="广告展现量")
    ad_clicks = Column(BigInteger, nullable=True, comment="广告点击次数")
    ad_to_cart = Column(BigInteger, nullable=True, comment="广告加购次数")
    ad_spend_amount = Column(Numeric(18, 4), nullable=True, comment="广告花费")
    ad_spend_currency = Column(String(10), nullable=True, comment="广告花费币种")
    ad_attributed_order_cnt = Column(
        BigInteger, nullable=True, comment="广告归因订单数"
    )
    ad_attributed_sales_amount = Column(
        Numeric(18, 4), nullable=True, comment="广告归因销售额"
    )
    ad_ctr = Column(
        Numeric(12, 6), nullable=True, comment="广告点击率（点击/展现，0-1）"
    )
    ad_cart_rate = Column(
        Numeric(12, 6), nullable=True, comment="广告加购率（加购/点击，0-1）"
    )
    ad_cpc = Column(Numeric(18, 4), nullable=True, comment="广告单次点击成本")
    ad_cpo = Column(Numeric(18, 4), nullable=True, comment="广告单笔订单成本")
    ad_roas = Column(
        Numeric(18, 6), nullable=True, comment="广告投入产出比（归因销售额/花费）"
    )
    ad_drr = Column(
        Numeric(12, 6), nullable=True, comment="广告费用率（花费/归因销售额，0-1）"
    )

    create_time = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="创建时间",
    )
    update_time = Column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
        comment="更新时间",
    )

    __table_args__ = (
        Index("idx_dwm_ozon_trade_return_shop_date", "shop_id", "stat_date"),
        Index("idx_dwm_ozon_trade_return_sku_date", "sku", "stat_date"),
        {
            "comment": "DWM-Ozon商品交易、退货、流量与广告日宽表",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )
