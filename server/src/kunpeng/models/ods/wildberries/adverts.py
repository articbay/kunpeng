"""
ODS 层 - 广告数据模型
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


class ODSWBAdvert(BaseModel):
    """
    ODS 层 - Wildberries 广告活动列表
    存储 API 返回的原始广告活动数据
    """

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")

    __tablename__ = "ods_wb_adverts"

    # 关联店铺
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")

    # 原始 JSON 数据（用于追溯）
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    # 展开字段（用于快速查询）
    advert_id = Column(BigInteger, nullable=False, comment="广告活动ID")
    name = Column(String(500), nullable=True, comment="广告活动名称")
    status = Column(Integer, nullable=True, comment="状态")
    bid_type = Column(String(50), nullable=True, comment="竞价类型")
    currency = Column(String(10), nullable=True, comment="币种")
    payment_type = Column(String(20), nullable=True, comment="支付类型")

    # 投放位置
    placement_search = Column(Boolean, nullable=True, comment="搜索位置")
    placement_recommendations = Column(Boolean, nullable=True, comment="推荐位置")

    # 时间戳（timestamps字段）
    started_at = Column(DateTime(timezone=True), nullable=True, comment="开始时间")
    deleted_at = Column(DateTime(timezone=True), nullable=True, comment="删除时间")


    __table_args__ = (
        UniqueConstraint("shop_id", "advert_id", name="uq_ods_advert_shop_advert"),
        Index("idx_ods_advert_shop_id", "shop_id"),
        Index("idx_ods_advert_status", "status"),
        {"comment": "Wildberries 广告活动表"},
    )


class ODSWBAdvertStat(BaseModel):
    """
    ODS 层 - Wildberries 广告统计数据
    存储 API 返回的原始广告统计数据（商品维度）
    """

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")

    __tablename__ = "ods_wb_advert_stats"

    # 关联店铺
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")

    # 原始 JSON 数据（用于追溯）
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    # 展开字段（用于快速查询）
    advert_id = Column(BigInteger, nullable=True, comment="广告活动ID")
    stat_date = Column(Date, nullable=True, comment="统计日期")

    # 商品维度字段（新增）
    nm_id = Column(BigInteger, nullable=True, comment="商品ID")
    nm_name = Column(String(500), nullable=True, comment="商品名称")

    # 终端类型字段
    app_type = Column(String(50), nullable=True, comment="终端类型")

    # 核心统计字段（来自响应）
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
        UniqueConstraint("shop_id", "advert_id", "stat_date", "nm_id", "app_type", name="uq_ods_adstat_shop_advert_statdate_nmid_apptype"),
        Index("idx_ods_adstat_shop_id", "shop_id"),
        Index("idx_ods_adstat_advert_id", "advert_id"),
        Index("idx_ods_adstat_stat_date", "stat_date"),
        Index("idx_ods_adstat_nm_id", "nm_id"),
        Index("idx_ods_adstat_app_type", "app_type"),
        {"comment": "Wildberries 广告统计商品维度表"},
    )
