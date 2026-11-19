"""
ODS 层 - Wildberries 广告增强数据模型
包含8个新API端点对应的数据表
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Numeric,
    Boolean,
    Index,
    UniqueConstraint,
    Date,
    JSON,
    BigInteger,
)

from kunpeng.models.base import BaseModel


class ODSWBNormQueryBid(BaseModel):
    """
    ODS 层 - Wildberries 标准查询竞价
    API: /adv/v0/normquery/get-bids
    """

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")

    __tablename__ = "ods_wb_norm_query_bids"

    # 关联店铺
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")

    # 原始 JSON 数据
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    # 关键字段
    advert_id = Column(BigInteger, nullable=True, comment="广告活动ID")
    nm_id = Column(BigInteger, nullable=True, comment="商品ID")
    norm_query = Column(String(500), nullable=True, comment="标准查询词")

    # 竞价相关
    bid = Column(Numeric(12, 4), nullable=True, comment="竞价")
    cpm = Column(Numeric(12, 4), nullable=True, comment="千次展示成本")
    priority = Column(Integer, nullable=True, comment="优先级")

    __table_args__ = (
        UniqueConstraint("shop_id", "advert_id", "nm_id", "norm_query", name="uq_ods_normbid_shop_advert_nm_query"),
        Index("idx_ods_normbid_shop_id", "shop_id"),
        Index("idx_ods_normbid_advert_id", "advert_id"),
        Index("idx_ods_normbid_nm_id", "nm_id"),
        {"comment": "Wildberries 标准查询竞价表"},
    )


class ODSWBNormQueryMinus(BaseModel):
    """
    ODS 层 - Wildberries 排除关键词
    API: /adv/v0/normquery/get-minus
    """

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")

    __tablename__ = "ods_wb_norm_query_minus"

    # 关联店铺
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")

    # 原始 JSON 数据
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    # 关键字段
    advert_id = Column(BigInteger, nullable=True, comment="广告活动ID")
    nm_id = Column(BigInteger, nullable=True, comment="商品ID")
    minus_word = Column(String(500), nullable=True, comment="排除关键词")

    __table_args__ = (
        UniqueConstraint("shop_id", "advert_id", "nm_id", "minus_word", name="uq_ods_normminus_shop_advert_nm_word"),
        Index("idx_ods_normminus_shop_id", "shop_id"),
        Index("idx_ods_normminus_advert_id", "advert_id"),
        Index("idx_ods_normminus_nm_id", "nm_id"),
        {"comment": "Wildberries 排除关键词表"},
    )


class ODSWBNormQueryList(BaseModel):
    """
    ODS 层 - Wildberries 标准查询列表
    API: /adv/v0/normquery/list
    """

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")

    __tablename__ = "ods_wb_norm_query_list"

    # 关联店铺
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")

    # 原始 JSON 数据
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    # 关键字段
    advert_id = Column(BigInteger, nullable=True, comment="广告活动ID")
    nm_id = Column(BigInteger, nullable=True, comment="商品ID")
    norm_query = Column(String(500), nullable=True, comment="标准查询词")

    # 额外字段
    is_active = Column(Boolean, nullable=True, comment="是否启用")
    created_at = Column(DateTime(timezone=True), nullable=True, comment="创建时间")

    __table_args__ = (
        UniqueConstraint("shop_id", "advert_id", "nm_id", "norm_query", name="uq_ods_normlist_shop_advert_nm_query"),
        Index("idx_ods_normlist_shop_id", "shop_id"),
        Index("idx_ods_normlist_advert_id", "advert_id"),
        Index("idx_ods_normlist_nm_id", "nm_id"),
        {"comment": "Wildberries 标准查询列表"},
    )


class ODSWBNormQueryStat(BaseModel):
    """
    ODS 层 - Wildberries 标准查询统计
    API: /adv/v0/normquery/stats
    """

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")

    __tablename__ = "ods_wb_norm_query_stats"

    # 关联店铺
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")

    # 原始 JSON 数据
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    # 关键字段
    advert_id = Column(BigInteger, nullable=True, comment="广告活动ID")
    nm_id = Column(BigInteger, nullable=True, comment="商品ID")
    norm_query = Column(String(500), nullable=True, comment="标准查询词")
    stat_date = Column(Date, nullable=True, comment="统计日期")

    # 统计字段
    views = Column(Integer, nullable=True, comment="浏览次数")
    clicks = Column(Integer, nullable=True, comment="点击次数")
    atbs = Column(Integer, nullable=True, comment="加购次数")
    orders = Column(Integer, nullable=True, comment="订单次数")
    sum_cost = Column(Numeric(18, 2), nullable=True, comment="总花费")

    # 计算指标
    cpc = Column(Numeric(12, 4), nullable=True, comment="单次点击成本")
    ctr = Column(Numeric(8, 4), nullable=True, comment="点击率")
    cr = Column(Numeric(8, 4), nullable=True, comment="转化率")

    __table_args__ = (
        UniqueConstraint("shop_id", "advert_id", "nm_id", "norm_query", "stat_date", name="uq_ods_normstat_shop_advert_nm_query_date"),
        Index("idx_ods_normstat_shop_id", "shop_id"),
        Index("idx_ods_normstat_advert_id", "advert_id"),
        Index("idx_ods_normstat_nm_id", "nm_id"),
        Index("idx_ods_normstat_stat_date", "stat_date"),
        {"comment": "Wildberries 标准查询统计表"},
    )


class ODSWBPromotionCount(BaseModel):
    """
    ODS 层 - Wildberries 促销计数
    API: /adv/v1/promotion/count
    """

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")

    __tablename__ = "ods_wb_promotion_counts"

    # 关联店铺
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")

    # 原始 JSON 数据
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    # 关键字段
    advert_id = Column(BigInteger, nullable=True, comment="广告活动ID")
    nm_id = Column(BigInteger, nullable=True, comment="商品ID")
    promotion_type = Column(String(100), nullable=True, comment="促销类型")

    # 统计字段
    active_count = Column(Integer, nullable=True, comment="活跃数量")
    total_count = Column(Integer, nullable=True, comment="总数量")
    pending_count = Column(Integer, nullable=True, comment="待处理数量")

    __table_args__ = (
        UniqueConstraint("shop_id", "advert_id", "nm_id", "promotion_type", name="uq_ods_promocount_shop_advert_nm_type"),
        Index("idx_ods_promocount_shop_id", "shop_id"),
        Index("idx_ods_promocount_advert_id", "advert_id"),
        Index("idx_ods_promocount_nm_id", "nm_id"),
        {"comment": "Wildberries 促销计数表"},
    )


class ODSWBBidRecommendation(BaseModel):
    """
    ODS 层 - Wildberries 竞价推荐
    API: /api/advert/v0/bids/recommendations
    """

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")

    __tablename__ = "ods_wb_bid_recommendations"

    # 关联店铺
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")

    # 原始 JSON 数据
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    # 关键字段
    advert_id = Column(BigInteger, nullable=True, comment="广告活动ID")
    nm_id = Column(BigInteger, nullable=True, comment="商品ID")
    subject_id = Column(BigInteger, nullable=True, comment="主题ID")
    norm_query = Column(String(500), nullable=True, comment="标准查询词")

    # 标识记录类型: "query" (普通查询词) 或 "base" (基准数据)
    record_type = Column(String(20), nullable=True, comment="记录类型: query/base")

    # ========== Reach 数据（三列） ==========
    reach_max_bid_kopecks = Column(BigInteger, nullable=True, comment="最大触达竞价（戈比）")
    reach_max_bid = Column(Numeric(12, 4), nullable=True, comment="最大触达竞价（卢布）")
    reach_medium_bid_kopecks = Column(BigInteger, nullable=True, comment="中等触达竞价（戈比）")
    reach_medium_bid = Column(Numeric(12, 4), nullable=True, comment="中等触达竞价（卢布）")
    reach_min_bid_kopecks = Column(BigInteger, nullable=True, comment="最小触达竞价（戈比）")
    reach_min_bid = Column(Numeric(12, 4), nullable=True, comment="最小触达竞价（卢布）")

    # ========== Base 基准数据 ==========
    base_competitive_bid_kopecks = Column(BigInteger, nullable=True, comment="竞争竞价（戈比）")
    base_competitive_bid = Column(Numeric(12, 4), nullable=True, comment="竞争竞价（卢布）")
    base_leaders_bid_kopecks = Column(BigInteger, nullable=True, comment="领先者竞价（戈比）")
    base_leaders_bid = Column(Numeric(12, 4), nullable=True, comment="领先者竞价（卢布）")
    base_top2_bid_kopecks = Column(BigInteger, nullable=True, comment="Top2竞价（戈比）")
    base_top2_bid = Column(Numeric(12, 4), nullable=True, comment="Top2竞价（卢布）")

    # 保留旧字段以兼容（弃用）
    reach_type = Column(String(50), nullable=True, comment="触达类型: reachMax/reachMedium/reachMin (弃用)")
    bid_kopecks = Column(BigInteger, nullable=True, comment="竞价（戈比） (弃用)")
    recommended_bid = Column(Numeric(12, 4), nullable=True, comment="推荐竞价（卢布） (弃用)")
    min_bid = Column(Numeric(12, 4), nullable=True, comment="最小竞价 (弃用)")
    max_bid = Column(Numeric(12, 4), nullable=True, comment="最大竞价 (弃用)")
    predicted_views = Column(Integer, nullable=True, comment="预估浏览量 (弃用)")
    predicted_clicks = Column(Integer, nullable=True, comment="预估点击量 (弃用)")
    predicted_cost = Column(Numeric(18, 2), nullable=True, comment="预估花费 (弃用)")

    __table_args__ = (
        UniqueConstraint("shop_id", "advert_id", "nm_id", "subject_id", "norm_query", "record_type", name="uq_ods_bidrec_shop_advert_nm_subject_query_type"),
        Index("idx_ods_bidrec_shop_id", "shop_id"),
        Index("idx_ods_bidrec_advert_id", "advert_id"),
        Index("idx_ods_bidrec_nm_id", "nm_id"),
        Index("idx_ods_bidrec_record_type", "record_type"),
        {"comment": "Wildberries 竞价推荐表"},
    )


class ODSWBAdvertFullStat(BaseModel):
    """
    ODS 层 - Wildberries 广告完整统计
    API: /adv/v3/fullstats
    """

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")

    __tablename__ = "ods_wb_advert_full_stats"

    # 关联店铺
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")

    # 原始 JSON 数据
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    # 关键字段
    advert_id = Column(BigInteger, nullable=True, comment="广告活动ID")
    stat_date = Column(Date, nullable=True, comment="统计日期")

    # 商品维度字段
    nm_id = Column(BigInteger, nullable=True, comment="商品ID")
    nm_name = Column(String(500), nullable=True, comment="商品名称")

    # 终端类型
    app_type = Column(String(50), nullable=True, comment="终端类型")

    # 核心统计字段
    views = Column(Integer, nullable=True, comment="浏览次数")
    clicks = Column(Integer, nullable=True, comment="点击次数")
    atbs = Column(Integer, nullable=True, comment="加购次数")
    orders = Column(Integer, nullable=True, comment="订单次数")
    canceled = Column(Integer, nullable=True, comment="取消次数")
    shks = Column(Integer, nullable=True, comment="SKU数量")

    # 金额相关
    sum_cost = Column(Numeric(18, 2), nullable=True, comment="总花费")
    sum_price = Column(Numeric(18, 2), nullable=True, comment="总价格")

    # 计算指标
    cpc = Column(Numeric(12, 4), nullable=True, comment="单次点击成本")
    ctr = Column(Numeric(8, 4), nullable=True, comment="点击率")
    cr = Column(Numeric(8, 4), nullable=True, comment="转化率")

    # 货币
    currency = Column(String(10), nullable=True, comment="币种")

    __table_args__ = (
        UniqueConstraint("shop_id", "advert_id", "stat_date", "nm_id", "app_type", name="uq_ods_fullstat_shop_advert_date_nm_app"),
        Index("idx_ods_fullstat_shop_id", "shop_id"),
        Index("idx_ods_fullstat_advert_id", "advert_id"),
        Index("idx_ods_fullstat_stat_date", "stat_date"),
        Index("idx_ods_fullstat_nm_id", "nm_id"),
        {"comment": "Wildberries 广告完整统计表"},
    )


class ODSWBAdvertV2(BaseModel):
    """
    ODS 层 - Wildberries 广告列表V2
    API: /api/advert/v2/adverts
    """

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")

    __tablename__ = "ods_wb_adverts_v2"

    # 关联店铺
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")

    # 原始 JSON 数据
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    # 广告基本信息
    advert_id = Column(BigInteger, nullable=False, comment="广告活动ID")
    name = Column(String(500), nullable=True, comment="广告活动名称")
    status = Column(Integer, nullable=True, comment="状态")
    type = Column(String(50), nullable=True, comment="类型")
    bid_type = Column(String(50), nullable=True, comment="竞价类型")
    currency = Column(String(10), nullable=True, comment="币种")

    # 预算相关
    daily_budget = Column(Numeric(18, 2), nullable=True, comment="日预算")
    total_budget = Column(Numeric(18, 2), nullable=True, comment="总预算")
    spent = Column(Numeric(18, 2), nullable=True, comment="已花费")

    # 投放位置
    placement_search = Column(Boolean, nullable=True, comment="搜索位置")
    placement_recommendations = Column(Boolean, nullable=True, comment="推荐位置")
    placement_catalog = Column(Boolean, nullable=True, comment="目录位置")

    # 时间相关
    created_at = Column(DateTime(timezone=True), nullable=True, comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=True, comment="更新时间")
    started_at = Column(DateTime(timezone=True), nullable=True, comment="开始时间")
    ended_at = Column(DateTime(timezone=True), nullable=True, comment="结束时间")

    __table_args__ = (
        UniqueConstraint("shop_id", "advert_id", name="uq_ods_advertv2_shop_advert"),
        Index("idx_ods_advertv2_shop_id", "shop_id"),
        Index("idx_ods_advertv2_status", "status"),
        Index("idx_ods_advertv2_type", "type"),
        {"comment": "Wildberries 广告列表V2表"},
    )
