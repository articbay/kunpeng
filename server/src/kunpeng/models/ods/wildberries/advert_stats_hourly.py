"""
ODS 层 - Wildberries 广告统计小时数据模型
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


class ODSWBAdvertStatHourly(BaseModel):
    """
    ODS 层 - Wildberries 广告统计小时数据
    存储按小时拆解的广告统计数据（商品维度）
    """

    __tablename__ = "ods_wb_advert_stats_hourly"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")

    # 关联店铺
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")

    # 原始 JSON 数据（用于追溯）
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    # 维度字段
    advert_id = Column(BigInteger, nullable=True, comment="广告活动ID")
    stat_date = Column(Date, nullable=True, comment="统计日期")
    stat_hour = Column(Integer, nullable=True, comment="统计小时（0-23）")

    # 商品维度字段
    nm_id = Column(BigInteger, nullable=True, comment="商品ID")
    nm_name = Column(String(500), nullable=True, comment="商品名称")

    # 终端类型字段
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
        UniqueConstraint(
            "shop_id", "advert_id", "stat_date", "stat_hour", "nm_id", "app_type",
            name="uq_ods_adstat_hourly_shop_advert_date_hour_nmid_apptype",
        ),
        Index("idx_ods_adstat_hourly_shop_id", "shop_id"),
        Index("idx_ods_adstat_hourly_advert_id", "advert_id"),
        Index("idx_ods_adstat_hourly_stat_date", "stat_date"),
        Index("idx_ods_adstat_hourly_stat_hour", "stat_hour"),
        Index("idx_ods_adstat_hourly_nm_id", "nm_id"),
        Index("idx_ods_adstat_hourly_app_type", "app_type"),
        {"comment": "Wildberries 广告统计小时数据表（商品维度）"},
    )
