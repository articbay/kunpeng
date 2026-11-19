"""
DWD 层 - Wildberries 广告报表明细模型
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Numeric,
    Index,
    UniqueConstraint,
    Date,
    BigInteger,
)

from kunpeng.models.base import BaseModel


class DWDWBAdvertsReportDetail(BaseModel):
    """
    DWD 层 - Wildberries 广告报表明细表（周度聚合）

    从 ODS 层的 ods_wb_advert_stats 和 ods_wb_adverts 聚合而来，
    按周度和广告活动维度汇总广告效果数据。
    """

    __tablename__ = "dwd_wb_adverts_report_detail"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID")

    # 关联店铺（从源表继承shop_id）
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")

    # 维度字段
    week = Column(String(20), nullable=False, comment="周度标识 (如 week202530)")
    advert_id = Column(BigInteger, nullable=False, comment="广告活动ID")
    advert_name = Column(String(500), nullable=True, comment="广告活动名称")

    # 活动状态（最新状态快照）
    advert_status = Column(Integer, nullable=True, comment="活动状态 (0-暂停, 1-进行中)")
    advert_status_label = Column(String(50), nullable=True, comment="活动状态标签")

    # 核心统计字段（周度聚合）
    paid_views = Column(Integer, nullable=False, default=0, comment="付费曝光量")
    paid_clicks = Column(Integer, nullable=False, default=0, comment="付费点击量")
    atbs = Column(Integer, nullable=False, default=0, comment="加购次数")
    orders = Column(Integer, nullable=False, default=0, comment="订单次数")

    # 计算指标
    ctr = Column(Numeric(8, 4), nullable=True, comment="点击率 (%)")
    cpc = Column(Numeric(12, 4), nullable=True, comment="单次点击成本 (₽)")
    cr = Column(Numeric(8, 4), nullable=True, comment="转化率 (%)")

    # 金额字段
    sum_cost = Column(Numeric(18, 2), nullable=True, comment="总花费 (₽)")
    sum_price = Column(Numeric(18, 2), nullable=True, comment="总销售金额 (₽)")

    __table_args__ = (
        UniqueConstraint(
            "shop_id", "week", "advert_id",
            name="uq_dwd_adreport_shop_week_advert",
        ),
        Index("idx_dwd_adreport_shop_id", "shop_id"),
        Index("idx_dwd_adreport_week", "week"),
        Index("idx_dwd_adreport_advert_id", "advert_id"),
        Index("idx_dwd_adreport_advert_status", "advert_status"),
        {"comment": "Wildberries 广告报表明细表（周度聚合）"},
    )
