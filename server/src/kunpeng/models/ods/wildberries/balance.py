
"""
ODS 层 - 余额和广告预算相关模型
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Numeric,
    Index,
    UniqueConstraint,
    Date,
    JSON,
    BigInteger,
)

from kunpeng.models.base import BaseModel


class ODSWBBalance(BaseModel):
    """ODS 层 - Wildberries账户余额"""

    __tablename__ = "ods_wb_balance"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")

    # 关联店铺
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")

    # 原始 JSON 数据（用于追溯）
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    # 余额字段 (根据官方文档)
    balance = Column(Numeric(18, 2), nullable=True, comment="账户余额 (Счёт)")
    net = Column(Numeric(18, 2), nullable=True, comment="余额 (Баланс)")
    bonus = Column(Numeric(18, 2), nullable=True, comment="奖金 (Бонусы)")

    # 同步时间字段
    sync_date = Column(Date, nullable=False, comment="同步日期")
    sync_at = Column(DateTime(timezone=True), nullable=False, comment="同步时间")

    __table_args__ = (
        UniqueConstraint("shop_id", "sync_date", name="uq_ods_balance_shop_syncdate"),
        Index("idx_ods_balance_shop_id", "shop_id"),
        Index("idx_ods_balance_sync_date", "sync_date"),
        {"comment": "Wildberries账户余额表"},
    )


class ODSWBCashback(BaseModel):
    """ODS 层 - Wildberries Cashback返利信息"""

    __tablename__ = "ods_wb_cashback"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")

    # 关联店铺
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")

    # 原始 JSON 数据（用于追溯）
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    # Cashback核心字段
    sum = Column(Numeric(18, 2), nullable=True, comment="Cashback金额")
    percent = Column(Numeric(8, 4), nullable=True, comment="返利比例")
    expiration_date = Column(Date, nullable=False, comment="过期日期")

    # 同步时间
    sync_at = Column(DateTime(timezone=True), nullable=False, comment="同步时间")

    __table_args__ = (
        UniqueConstraint("shop_id", "expiration_date", name="uq_ods_cashback_shop_expiration"),
        Index("idx_ods_cashback_shop_id", "shop_id"),
        Index("idx_ods_cashback_expiration_date", "expiration_date"),
        {"comment": "Wildberries Cashback返利表"},
    )


class ODSWBAdvertProduct(BaseModel):
    """ODS 层 - Wildberries广告商品（原nm_settings拆分）"""

    __tablename__ = "ods_wb_advert_product"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")

    # 关联店铺
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")

    # 原始 JSON 数据（用于追溯）
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    # 关联字段
    advert_id = Column(BigInteger, nullable=False, comment="广告活动ID")
    nm_id = Column(BigInteger, nullable=False, comment="商品ID")

    # 竞价字段 (bids_kopecks)
    bid_search = Column(BigInteger, nullable=True, comment="搜索位置竞价(戈比)")
    bid_recommendations = Column(BigInteger, nullable=True, comment="推荐位置竞价(戈比)")

    # 子类目字段 (subject)
    subject_id = Column(BigInteger, nullable=True, comment="子类目ID")
    subject_name = Column(String(500), nullable=True, comment="子类目名称")

    __table_args__ = (
        UniqueConstraint("shop_id", "advert_id", "nm_id", name="uq_ods_adprod_shop_advert_nm"),
        Index("idx_ods_adprod_shop_id", "shop_id"),
        Index("idx_ods_adprod_advert_id", "advert_id"),
        Index("idx_ods_adprod_nm_id", "nm_id"),
        {"comment": "Wildberries广告商品表"},
    )


class ODSWBAdvertBudget(BaseModel):
    """ODS 层 - Wildberries广告预算"""

    __tablename__ = "ods_wb_advert_budget"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")

    # 关联店铺
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")

    # 原始 JSON 数据（用于追溯）
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    # 关联字段
    advert_id = Column(BigInteger, nullable=False, comment="广告活动ID")

    # 预算字段（根据API文档）
    cash = Column(Numeric(18, 2), nullable=True, comment="现金（未使用，始终为0）")
    netting = Column(Numeric(18, 2), nullable=True, comment="净额（未使用，始终为0）")
    total = Column(Numeric(18, 2), nullable=True, comment="活动预算，单位：卢布")

    # 同步时间
    sync_date = Column(Date, nullable=False, comment="同步日期")
    sync_at = Column(DateTime(timezone=True), nullable=False, comment="同步时间")

    __table_args__ = (
        UniqueConstraint("shop_id", "advert_id", "sync_date", name="uq_ods_advbudget_shop_advert_syncdate"),
        Index("idx_ods_advbudget_shop_id", "shop_id"),
        Index("idx_ods_advbudget_advert_id", "advert_id"),
        Index("idx_ods_advbudget_sync_date", "sync_date"),
        {"comment": "Wildberries广告预算表"},
    )


class ODSWBSearchClusterStat(BaseModel):
    """ODS 层 - Wildberries搜索关键字维度广告统计"""

    __tablename__ = "ods_wb_search_cluster_stat"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")

    # 关联店铺
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")

    # 原始 JSON 数据（用于追溯）
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    # 关键字维度字段
    stat_date = Column(Date, nullable=False, comment="统计日期")
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
        UniqueConstraint("shop_id", "stat_date", "advert_id", "nm_id", "norm_query", name="uq_ods_searchstat_shop_date_advert_nm_normquery"),
        Index("idx_ods_searchstat_shop_id", "shop_id"),
        Index("idx_ods_searchstat_stat_date", "stat_date"),
        Index("idx_ods_searchstat_nm_id", "nm_id"),
        Index("idx_ods_searchstat_advert_id", "advert_id"),
        {"comment": "Wildberries搜索关键字维度广告统计表"},
    )
