"""DWD 层 - Wildberries 广告配置与效果模型。"""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)

from kunpeng.models.base import BaseModel


class DWDWBAdvertActivityDetail(BaseModel):
    """广告活动与商品的当前配置快照。"""

    __tablename__ = "dwd_wb_advert_activity_detail"
    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "advert_id",
            "nm_id",
            name="uq_dwd_wb_advert_activity_shop_advert_nm",
        ),
        Index("idx_dwd_wb_advert_activity_shop_status", "shop_id", "status"),
        Index("idx_dwd_wb_advert_activity_nm", "nm_id"),
        {"comment": "Wildberries广告活动商品当前配置快照"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")
    snapshot_date = Column(Date, nullable=False, comment="快照日期（平台业务日期）")
    advert_id = Column(BigInteger, nullable=False, comment="广告活动ID")
    nm_id = Column(BigInteger, nullable=False, comment="WB商品编号")
    advert_name = Column(String(500), nullable=True, comment="广告活动名称")
    status = Column(Integer, nullable=True, comment="广告活动状态编码")
    status_name = Column(String(64), nullable=True, comment="广告活动状态名称")
    bid_type = Column(String(50), nullable=True, comment="出价类型")
    payment_type = Column(String(20), nullable=True, comment="计费类型")
    currency = Column(String(10), nullable=True, comment="原始金额币种")
    placement_search = Column(Boolean, nullable=True, comment="是否投放搜索")
    placement_recommendations = Column(
        Boolean,
        nullable=True,
        comment="是否投放推荐",
    )
    subject_id = Column(BigInteger, nullable=True, comment="商品类目ID")
    subject_name = Column(String(500), nullable=True, comment="商品类目名称")
    bid_search = Column(
        BigInteger,
        nullable=True,
        comment="搜索出价（接口原始最小货币单位）",
    )
    bid_recommendations = Column(
        BigInteger,
        nullable=True,
        comment="推荐出价（接口原始最小货币单位）",
    )
    total_budget = Column(
        Numeric(18, 4),
        nullable=True,
        comment="活动预算（接口原始币种金额）",
    )
    budget_sync_date = Column(Date, nullable=True, comment="预算来源同步日期")


class DWDWBAdvertBidConfig(BaseModel):
    """Norm关键词当前启停、实际出价与推荐档位。"""

    __tablename__ = "dwd_wb_advert_bid_config"
    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "advert_id",
            "nm_id",
            "norm_query",
            name="uq_dwd_wb_advert_bid_shop_advert_nm_query",
        ),
        Index("idx_dwd_wb_advert_bid_shop_advert", "shop_id", "advert_id"),
        Index("idx_dwd_wb_advert_bid_nm", "nm_id"),
        {"comment": "Wildberries Norm关键词当前出价配置快照"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")
    snapshot_date = Column(Date, nullable=False, comment="快照日期（平台业务日期）")
    advert_id = Column(BigInteger, nullable=False, comment="广告活动ID")
    nm_id = Column(BigInteger, nullable=False, comment="WB商品编号")
    norm_query = Column(String(500), nullable=False, comment="标准查询词/搜索集群")
    is_active = Column(Boolean, nullable=True, comment="关键词是否启用")
    currency = Column(String(10), nullable=True, comment="出价原始币种")

    reach_max_bid_kopecks = Column(
        BigInteger,
        nullable=True,
        comment="最大触达原始戈比值",
    )
    reach_max_bid = Column(Numeric(12, 4), nullable=True, comment="最大触达接口金额")
    reach_medium_bid_kopecks = Column(
        BigInteger,
        nullable=True,
        comment="中等触达原始戈比值",
    )
    reach_medium_bid = Column(
        Numeric(12, 4),
        nullable=True,
        comment="中等触达接口金额",
    )
    reach_min_bid_kopecks = Column(
        BigInteger,
        nullable=True,
        comment="最小触达原始戈比值",
    )
    reach_min_bid = Column(Numeric(12, 4), nullable=True, comment="最小触达接口金额")
    base_competitive_bid_kopecks = Column(
        BigInteger,
        nullable=True,
        comment="竞争档位原始戈比值",
    )
    base_competitive_bid = Column(
        Numeric(12, 4),
        nullable=True,
        comment="竞争档位接口金额",
    )
    base_leaders_bid_kopecks = Column(
        BigInteger,
        nullable=True,
        comment="领先档位原始戈比值",
    )
    base_leaders_bid = Column(
        Numeric(12, 4),
        nullable=True,
        comment="领先档位接口金额",
    )
    base_top2_bid_kopecks = Column(
        BigInteger,
        nullable=True,
        comment="Top2档位原始戈比值",
    )
    base_top2_bid = Column(Numeric(12, 4), nullable=True, comment="Top2档位接口金额")
    query_bid = Column(
        Numeric(12, 4),
        nullable=True,
        comment="关键词实际出价（接口原始值，不做汇率换算）",
    )


class DWDWBAdvertStatsHourlyIncr(BaseModel):
    """广告商品小时增量效果事实。"""

    __tablename__ = "dwd_wb_advert_stats_hourly_incr"
    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "stat_date",
            "stat_hour",
            "advert_id",
            "nm_id",
            "currency",
            name="uq_dwd_wb_advert_hourly_dim",
        ),
        Index("idx_dwd_wb_advert_hourly_shop_date", "shop_id", "stat_date"),
        Index("idx_dwd_wb_advert_hourly_advert_nm", "advert_id", "nm_id"),
        {"comment": "Wildberries广告商品小时增量效果事实表"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")
    advert_id = Column(BigInteger, nullable=False, comment="广告活动ID")
    status = Column(Integer, nullable=True, comment="构建时广告活动状态编码")
    status_name = Column(String(64), nullable=True, comment="构建时广告活动状态名称")
    payment_type = Column(String(20), nullable=True, comment="构建时计费类型")
    bid_type = Column(String(50), nullable=True, comment="构建时出价类型")
    nm_id = Column(BigInteger, nullable=False, comment="WB商品编号")
    nm_name = Column(String(500), nullable=True, comment="商品名称")
    stat_date = Column(Date, nullable=False, comment="统计日期")
    stat_hour = Column(Integer, nullable=False, comment="统计小时（0-23）")
    currency = Column(String(10), nullable=False, comment="原始金额币种")
    views = Column(BigInteger, nullable=False, default=0, comment="浏览次数")
    clicks = Column(BigInteger, nullable=False, default=0, comment="点击次数")
    atbs = Column(BigInteger, nullable=False, default=0, comment="加购次数")
    orders = Column(BigInteger, nullable=False, default=0, comment="订单次数")
    canceled = Column(BigInteger, nullable=False, default=0, comment="取消次数")
    shks = Column(BigInteger, nullable=False, default=0, comment="SKU数量")
    sum_cost = Column(Numeric(18, 4), nullable=False, default=0, comment="原币花费")
    sum_price = Column(Numeric(18, 4), nullable=False, default=0, comment="原币销售额")
    cpc = Column(
        Numeric(18, 6),
        nullable=False,
        default=0,
        comment="原币单次点击成本",
    )
    ctr = Column(Numeric(18, 6), nullable=False, default=0, comment="点击率（0-1）")
    cr = Column(Numeric(18, 6), nullable=False, default=0, comment="转化率（0-1）")
    roi = Column(Numeric(18, 6), nullable=False, default=0, comment="投入产出比")
    source_platform = Column(
        String(16),
        nullable=False,
        default="WB",
        comment="来源平台",
    )


class DWDWBAdvertStatsDailyIncr(BaseModel):
    """由小时事实重新汇总的广告商品日效果事实。"""

    __tablename__ = "dwd_wb_advert_stats_daily_incr"
    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "stat_date",
            "advert_id",
            "nm_id",
            "currency",
            name="uq_dwd_wb_advert_daily_dim",
        ),
        Index("idx_dwd_wb_advert_daily_shop_date", "shop_id", "stat_date"),
        Index("idx_dwd_wb_advert_daily_advert_nm", "advert_id", "nm_id"),
        {"comment": "Wildberries广告商品日增量效果事实表"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")
    advert_id = Column(BigInteger, nullable=False, comment="广告活动ID")
    status = Column(Integer, nullable=True, comment="构建时广告活动状态编码")
    status_name = Column(String(64), nullable=True, comment="构建时广告活动状态名称")
    payment_type = Column(String(20), nullable=True, comment="构建时计费类型")
    bid_type = Column(String(50), nullable=True, comment="构建时出价类型")
    nm_id = Column(BigInteger, nullable=False, comment="WB商品编号")
    nm_name = Column(String(500), nullable=True, comment="商品名称")
    stat_date = Column(Date, nullable=False, comment="统计日期")
    currency = Column(String(10), nullable=False, comment="原始金额币种")
    views = Column(BigInteger, nullable=False, default=0, comment="浏览次数")
    clicks = Column(BigInteger, nullable=False, default=0, comment="点击次数")
    atbs = Column(BigInteger, nullable=False, default=0, comment="加购次数")
    orders = Column(BigInteger, nullable=False, default=0, comment="订单次数")
    canceled = Column(BigInteger, nullable=False, default=0, comment="取消次数")
    shks = Column(BigInteger, nullable=False, default=0, comment="SKU数量")
    sum_cost = Column(Numeric(18, 4), nullable=False, default=0, comment="原币花费")
    sum_price = Column(Numeric(18, 4), nullable=False, default=0, comment="原币销售额")
    cpc = Column(
        Numeric(18, 6),
        nullable=False,
        default=0,
        comment="原币单次点击成本",
    )
    ctr = Column(Numeric(18, 6), nullable=False, default=0, comment="点击率（0-1）")
    cr = Column(Numeric(18, 6), nullable=False, default=0, comment="转化率（0-1）")
    roi = Column(Numeric(18, 6), nullable=False, default=0, comment="投入产出比")
    source_platform = Column(
        String(16),
        nullable=False,
        default="WB",
        comment="来源平台",
    )
