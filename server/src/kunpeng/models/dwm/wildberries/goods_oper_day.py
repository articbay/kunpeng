"""Wildberries SKU-day operating aggregate model."""

from sqlalchemy import (
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


class DWMWBGoodsOperDay(Base):
    """One row per Wildberries shop, platform day and nm_id."""

    __tablename__ = "dwm_wb_goods_oper_day"

    stat_date = Column(Date, primary_key=True, nullable=False, comment="平台统计日期")
    shop_id = Column(BigInteger, primary_key=True, nullable=False, comment="店铺ID")
    nm_id = Column(BigInteger, primary_key=True, nullable=False, comment="WB商品编号")

    vendor_code = Column(String(255), nullable=True, comment="卖家商品编号")
    product_title = Column(Text, nullable=True, comment="商品名称")
    product_title_cn = Column(Text, nullable=True, comment="商品名称（中文）")
    brand_name = Column(String(255), nullable=True, comment="品牌")
    subject_name = Column(String(255), nullable=True, comment="商品品类")
    subject_name_cn = Column(String(255), nullable=True, comment="商品品类（中文）")

    has_funnel_data = Column(Boolean, nullable=False, server_default=text("0"))
    has_order_data = Column(Boolean, nullable=False, server_default=text("0"))
    has_return_data = Column(Boolean, nullable=False, server_default=text("0"))
    has_ad_data = Column(Boolean, nullable=False, server_default=text("0"))

    product_rating = Column(Numeric(5, 2), nullable=True, comment="商品评分")
    feedback_rating = Column(Numeric(5, 2), nullable=True, comment="评论评分")
    traffic_clicks = Column(BigInteger, nullable=True, comment="商品点击数")
    traffic_cart_qty = Column(BigInteger, nullable=True, comment="商品加购数")
    traffic_wishlist_qty = Column(BigInteger, nullable=True, comment="商品收藏数")
    funnel_order_qty = Column(BigInteger, nullable=True, comment="漏斗下单商品量")
    funnel_buyout_qty = Column(BigInteger, nullable=True, comment="漏斗售出件数")
    funnel_cancel_qty = Column(BigInteger, nullable=True, comment="漏斗取消商品量")
    funnel_order_amount = Column(Numeric(18, 4), nullable=True, comment="漏斗订单金额")
    funnel_buyout_amount = Column(Numeric(18, 4), nullable=True, comment="漏斗售出金额")
    funnel_cancel_amount = Column(Numeric(18, 4), nullable=True, comment="漏斗取消金额")

    order_cnt = Column(
        BigInteger, nullable=False, server_default=text("0"), comment="去重订单数"
    )
    order_qty = Column(
        BigInteger, nullable=False, server_default=text("0"), comment="订单商品件数"
    )
    cancelled_order_cnt = Column(
        BigInteger, nullable=False, server_default=text("0"), comment="取消订单数"
    )
    cancelled_qty = Column(
        BigInteger, nullable=False, server_default=text("0"), comment="取消商品件数"
    )
    order_amount_sum = Column(Numeric(18, 4), nullable=True, comment="折后订单金额合计")
    finished_amount_sum = Column(Numeric(18, 4), nullable=True, comment="最终价格合计")

    return_cnt = Column(
        BigInteger, nullable=False, server_default=text("0"), comment="退货记录数"
    )
    return_qty = Column(
        BigInteger, nullable=False, server_default=text("0"), comment="退货件数"
    )
    return_ready_cnt = Column(
        BigInteger, nullable=False, server_default=text("0"), comment="已准备退货数"
    )
    return_completed_cnt = Column(
        BigInteger, nullable=False, server_default=text("0"), comment="已领取退货数"
    )
    return_expired_cnt = Column(
        BigInteger, nullable=False, server_default=text("0"), comment="已过期退货数"
    )

    ad_campaign_cnt = Column(BigInteger, nullable=True, comment="广告活动数")
    ad_views = Column(BigInteger, nullable=True, comment="广告曝光量")
    ad_clicks = Column(BigInteger, nullable=True, comment="广告点击数")
    ad_to_cart = Column(BigInteger, nullable=True, comment="广告加购数")
    ad_order_cnt = Column(BigInteger, nullable=True, comment="广告归因订单数")
    ad_cancelled_cnt = Column(BigInteger, nullable=True, comment="广告取消数")
    ad_sales_qty = Column(BigInteger, nullable=True, comment="广告归因销量")
    ad_spend_amount = Column(Numeric(18, 4), nullable=True, comment="广告花费")
    ad_attributed_sales_amount = Column(
        Numeric(18, 4), nullable=True, comment="广告归因销售额"
    )
    ad_currency = Column(String(10), nullable=True, comment="广告金额币种")
    has_ad_currency_conflict = Column(Boolean, nullable=False, server_default=text("0"))

    traffic_cart_rate = Column(
        Numeric(12, 6), nullable=True, comment="加购率（加购/点击）"
    )
    traffic_order_rate = Column(
        Numeric(12, 6), nullable=True, comment="下单率（漏斗下单/点击）"
    )
    traffic_buyout_rate = Column(
        Numeric(12, 6), nullable=True, comment="售出率（漏斗售出/点击）"
    )
    order_cancel_rate = Column(Numeric(12, 6), nullable=True, comment="订单取消率")
    return_rate_ordered = Column(
        Numeric(12, 6), nullable=True, comment="按下单件数计算的退货率"
    )
    return_rate_buyout = Column(
        Numeric(12, 6), nullable=True, comment="按漏斗售出件数计算的退货率"
    )
    ad_ctr = Column(Numeric(12, 6), nullable=True, comment="广告点击率")
    ad_cart_rate = Column(Numeric(12, 6), nullable=True, comment="广告加购率")
    ad_cvr = Column(Numeric(12, 6), nullable=True, comment="广告订单转化率")
    ad_cpc = Column(Numeric(18, 6), nullable=True, comment="广告单次点击成本")
    ad_cpo = Column(Numeric(18, 6), nullable=True, comment="广告单笔订单成本")
    ad_roas = Column(Numeric(18, 6), nullable=True, comment="广告投入产出比")
    ad_drr = Column(Numeric(12, 6), nullable=True, comment="广告费用率")
    ad_click_share = Column(
        Numeric(12, 6), nullable=True, comment="广告点击占商品点击比例"
    )
    estimated_organic_clicks = Column(BigInteger, nullable=True, comment="估算自然点击")
    has_click_scope_conflict = Column(Boolean, nullable=False, server_default=text("0"))

    create_time = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    update_time = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    __table_args__ = (
        Index("idx_dwm_wb_goods_oper_shop_date", "shop_id", "stat_date"),
        Index("idx_dwm_wb_goods_oper_nm_date", "nm_id", "stat_date"),
        {
            "comment": "DWM-WB商品流量、交易、退货与广告经营日宽表",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )
