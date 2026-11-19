"""Ozon Seller Analytics API ODS models."""

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import DECIMAL, TEXT
from sqlalchemy.sql import func

from kunpeng.models.base import BaseModel


class OzonAnalyticsMetricsMixin:
    """The 18 source metrics exposed by ``POST /v1/analytics/data``."""

    revenue = Column(DECIMAL(18, 4), nullable=True, comment="下单金额")
    ordered_units = Column(BigInteger, nullable=True, comment="下单商品件数")
    hits_view_search = Column(BigInteger, nullable=True, comment="搜索/类目展示次数")
    hits_view_pdp = Column(BigInteger, nullable=True, comment="商品详情页展示次数")
    hits_view = Column(BigInteger, nullable=True, comment="总展示次数")
    hits_tocart_search = Column(BigInteger, nullable=True, comment="搜索/类目加购次数")
    hits_tocart_pdp = Column(BigInteger, nullable=True, comment="商品详情页加购次数")
    hits_tocart = Column(BigInteger, nullable=True, comment="总加购次数")
    session_view_search = Column(
        BigInteger, nullable=True, comment="搜索/类目访问用户数"
    )
    session_view_pdp = Column(BigInteger, nullable=True, comment="商品详情页访问用户数")
    session_view = Column(BigInteger, nullable=True, comment="总访问用户数")
    conv_tocart_search = Column(
        DECIMAL(18, 6), nullable=True, comment="搜索/类目加购转化率(API原值)"
    )
    conv_tocart_pdp = Column(
        DECIMAL(18, 6), nullable=True, comment="商品详情页加购转化率(API原值)"
    )
    conv_tocart = Column(DECIMAL(18, 6), nullable=True, comment="总加购转化率(API原值)")
    returns = Column(BigInteger, nullable=True, comment="退货商品件数")
    cancellations = Column(BigInteger, nullable=True, comment="取消商品件数")
    delivered_units = Column(BigInteger, nullable=True, comment="送达商品件数")
    position_category = Column(
        DECIMAL(18, 6), nullable=True, comment="搜索及类目平均位置"
    )


class ODSOzonAnalyticsDataDaily(OzonAnalyticsMetricsMixin, BaseModel):
    """Ozon analytics facts at shop x SKU x platform-day grain."""

    __tablename__ = "ods_ozon_analytics_data_daily"
    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "sku",
            "stat_date",
            name="uq_ods_ozon_analytics_daily_shop_sku_date",
        ),
        Index("idx_ods_ozon_analytics_daily_shop_date", "shop_id", "stat_date"),
        Index("idx_ods_ozon_analytics_daily_sku_date", "sku", "stat_date"),
        {"comment": "Ozon经营分析SKU日明细表"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, comment="店铺ID")
    sku = Column(BigInteger, nullable=False, comment="Ozon SKU")
    sku_name = Column(TEXT, nullable=True, comment="API返回的商品名称")
    stat_date = Column(Date, nullable=False, comment="平台统计日期")

    source_date_from = Column(Date, nullable=False, comment="API请求开始日期")
    source_date_to = Column(Date, nullable=False, comment="API请求结束日期")
    requested_metrics_core = Column(JSON, nullable=False, comment="核心指标请求顺序")
    requested_metrics_outcome = Column(JSON, nullable=False, comment="履约指标请求顺序")
    row_data_core = Column(JSON, nullable=True, comment="核心指标API原始行")
    row_data_outcome = Column(JSON, nullable=True, comment="履约指标API原始行")
    has_core_metrics = Column(
        Boolean, nullable=False, default=False, comment="核心指标组是否返回该行"
    )
    has_outcome_metrics = Column(
        Boolean, nullable=False, default=False, comment="履约指标组是否返回该行"
    )
    api_timestamp_core = Column(
        DateTime(timezone=True), nullable=True, comment="核心指标报告生成时间"
    )
    api_timestamp_outcome = Column(
        DateTime(timezone=True), nullable=True, comment="履约指标报告生成时间"
    )
    synced_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="最近成功同步时间",
    )


class ODSOzonAnalyticsTotalsWindow(OzonAnalyticsMetricsMixin, BaseModel):
    """Source totals for one shop and one API request window."""

    __tablename__ = "ods_ozon_analytics_totals_window"
    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "date_from",
            "date_to",
            name="uq_ods_ozon_analytics_totals_shop_window",
        ),
        Index(
            "idx_ods_ozon_analytics_totals_shop_window",
            "shop_id",
            "date_from",
            "date_to",
        ),
        {"comment": "Ozon经营分析请求窗口汇总表"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(Integer, nullable=False, comment="店铺ID")
    date_from = Column(Date, nullable=False, comment="API请求开始日期")
    date_to = Column(Date, nullable=False, comment="API请求结束日期")
    requested_metrics_core = Column(JSON, nullable=False, comment="核心指标请求顺序")
    requested_metrics_outcome = Column(JSON, nullable=False, comment="履约指标请求顺序")
    raw_totals_core = Column(JSON, nullable=False, comment="核心指标原始totals数组")
    raw_totals_outcome = Column(JSON, nullable=False, comment="履约指标原始totals数组")
    api_timestamp_core = Column(
        DateTime(timezone=True), nullable=True, comment="核心指标报告生成时间"
    )
    api_timestamp_outcome = Column(
        DateTime(timezone=True), nullable=True, comment="履约指标报告生成时间"
    )
    synced_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="最近成功同步时间",
    )
