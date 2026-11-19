"""
ODS 层 - Wildberries 搜索关键字统计小时数据模型
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Index,
    UniqueConstraint,
    Date,
    JSON,
    BigInteger,
)

from kunpeng.models.base import BaseModel


class ODSWBSearchClusterStatHourly(BaseModel):
    """
    ODS 层 - Wildberries 搜索关键字维度广告统计小时数据
    """

    __tablename__ = "ods_wb_search_cluster_stat_hourly"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")

    # 关联店铺
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")

    # 原始 JSON 数据（用于追溯）
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    # 关键字维度字段
    stat_date = Column(Date, nullable=False, comment="统计日期")
    stat_hour = Column(Integer, nullable=True, comment="统计小时（0-23）")
    advert_id = Column(BigInteger, nullable=True, comment="广告活动ID")
    nm_id = Column(BigInteger, nullable=False, comment="商品ID")
    norm_query = Column(String(500), nullable=True, comment="标准化搜索关键字")

    # 统计字段
    views = Column(Integer, nullable=True, comment="浏览次数")
    clicks = Column(Integer, nullable=True, comment="点击次数")
    sum_cost = Column(Numeric(18, 2), nullable=True, comment="总花费")
    atbs = Column(Integer, nullable=True, comment="加购次数")
    orders = Column(Integer, nullable=True, comment="订单次数")

    # 计算指标
    cpc = Column(Numeric(12, 4), nullable=True, comment="单次点击成本")
    ctr = Column(Numeric(8, 4), nullable=True, comment="点击率")
    cr = Column(Numeric(8, 4), nullable=True, comment="转化率")

    __table_args__ = (
        UniqueConstraint(
            "shop_id", "stat_date", "stat_hour", "advert_id", "nm_id", "norm_query",
            name="uq_ods_searchstat_hourly_shop_date_hour_advert_nm_normquery",
        ),
        Index("idx_ods_searchstat_hourly_shop_id", "shop_id"),
        Index("idx_ods_searchstat_hourly_stat_date", "stat_date"),
        Index("idx_ods_searchstat_hourly_stat_hour", "stat_hour"),
        Index("idx_ods_searchstat_hourly_nm_id", "nm_id"),
        Index("idx_ods_searchstat_hourly_advert_id", "advert_id"),
        {"comment": "Wildberries 搜索关键字维度广告统计小时数据表"},
    )
