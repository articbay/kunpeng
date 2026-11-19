"""Ozon native sales-funnel daily detail model."""

from sqlalchemy import (BigInteger, Boolean, Column, Date, DateTime, Index,
                        Integer, Numeric, String, Text, UniqueConstraint)

from kunpeng.models.base import BaseModel


class DWDOzonSalesFunnelDetail(BaseModel):
    """One Ozon Seller Analytics row per shop, SKU and platform day."""

    __tablename__ = "dwd_ozon_sales_funnel_detail"
    __table_args__ = (
        UniqueConstraint("source_ods_id", name="uq_dwd_ozon_sales_funnel_source_ods"),
        UniqueConstraint(
            "shop_id",
            "stat_date",
            "sku",
            name="uq_dwd_ozon_sales_funnel_shop_date_sku",
        ),
        Index("idx_dwd_ozon_sales_funnel_shop_date", "shop_id", "stat_date"),
        Index("idx_dwd_ozon_sales_funnel_sku", "sku"),
        Index("idx_dwd_ozon_sales_funnel_offer", "offer_id"),
        {
            "comment": "Ozon销售漏斗SKU日明细表",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    source_ods_id = Column(
        BigInteger,
        nullable=False,
        comment="来源 ods_ozon_analytics_data_daily.id",
    )

    # 维度字段；中文翻译紧跟原字段。
    shop_id = Column(Integer, nullable=False, comment="店铺ID")
    offer_id = Column(String(255), nullable=True, comment="卖家商品编号")
    sku = Column(BigInteger, nullable=False, comment="Ozon SKU")
    product_name = Column(Text, nullable=True, comment="商品名称")
    product_name_cn = Column(Text, nullable=True, comment="商品名称（中文）")
    category_name = Column(String(255), nullable=True, comment="商品品类")
    category_name_cn = Column(String(255), nullable=True, comment="商品品类（中文）")
    stat_date = Column(Date, nullable=False, comment="统计日期")

    # Ozon /v1/analytics/data 原生指标。
    hits_view_search = Column(BigInteger, nullable=True, comment="搜索和类目展示次数")
    hits_view_pdp = Column(BigInteger, nullable=True, comment="商品详情页浏览次数")
    hits_view = Column(BigInteger, nullable=True, comment="总展示/浏览次数")
    session_view_search = Column(
        BigInteger, nullable=True, comment="搜索和类目访问用户数"
    )
    session_view_pdp = Column(BigInteger, nullable=True, comment="商品详情页访问用户数")
    session_view = Column(BigInteger, nullable=True, comment="总访问用户数")
    hits_tocart_search = Column(BigInteger, nullable=True, comment="搜索和类目加购次数")
    hits_tocart_pdp = Column(BigInteger, nullable=True, comment="商品详情页加购次数")
    hits_tocart = Column(BigInteger, nullable=True, comment="总加购次数")
    conv_tocart_search = Column(
        Numeric(18, 6), nullable=True, comment="搜索和类目加购转化率（API原值）"
    )
    conv_tocart_pdp = Column(
        Numeric(18, 6), nullable=True, comment="商品详情页加购转化率（API原值）"
    )
    conv_tocart = Column(
        Numeric(18, 6), nullable=True, comment="总加购转化率（API原值）"
    )
    ordered_units = Column(BigInteger, nullable=True, comment="下单商品件数")
    revenue = Column(Numeric(18, 4), nullable=True, comment="下单金额")
    delivered_units = Column(BigInteger, nullable=True, comment="送达商品件数")
    cancellations = Column(BigInteger, nullable=True, comment="取消商品件数")
    returns = Column(BigInteger, nullable=True, comment="退货商品件数")
    position_category = Column(
        Numeric(18, 6), nullable=True, comment="搜索和类目平均位置"
    )

    # 已确认的项目计算指标，不冒充 Ozon API 原值。
    cart_to_order_rate = Column(
        Numeric(18, 6), nullable=True, comment="加购至下单转化率（项目计算，%）"
    )

    # 来源质量与追踪技术字段。
    has_core_metrics = Column(
        Boolean, nullable=False, default=False, comment="基础指标组是否返回该行"
    )
    has_outcome_metrics = Column(
        Boolean, nullable=False, default=False, comment="结果指标组是否返回该行"
    )
    source_synced_at = Column(
        DateTime(timezone=True), nullable=True, comment="来源ODS最近同步时间"
    )
