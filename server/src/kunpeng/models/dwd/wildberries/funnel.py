"""DWD 层 - Wildberries 销售漏斗商品明细模型。"""

from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    Date,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)

from kunpeng.models.base import BaseModel


class DWDWBSalesFunnelDetail(BaseModel):
    """按表头映射表筛选后的 WB 销售漏斗商品明细。"""

    __tablename__ = "dwd_wb_sales_funnel_detail"
    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "date_from",
            "date_to",
            "nm_id",
            name="uq_dwd_wb_funnel_shop_window_nm",
        ),
        UniqueConstraint(
            "source_ods_id",
            name="uq_dwd_wb_funnel_source_ods",
        ),
        Index("idx_dwd_wb_funnel_date_range", "date_from", "date_to"),
        Index("idx_dwd_wb_funnel_nm_id", "nm_id"),
        {"comment": "Wildberries 销售漏斗商品明细 DWD 表"},
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    source_ods_id = Column(
        BigInteger,
        nullable=False,
        comment="来源 ods_wb_sales_funnels.id",
    )
    shop_id = Column(Integer, nullable=False, comment="店铺ID")
    date_from = Column(Date, nullable=False, comment="统计开始日期")
    date_to = Column(Date, nullable=False, comment="统计结束日期（技术字段）")

    vendor_code = Column(String(255), nullable=True, comment="卖家商品编号")
    nm_id = Column(BigInteger, nullable=False, comment="WB商品编号")
    title = Column(String(1000), nullable=True, comment="名称")
    subject_name = Column(String(255), nullable=True, comment="项目")
    brand_name = Column(String(255), nullable=True, comment="品牌")
    tags = Column(JSON, nullable=True, comment="商品标签")
    product_rating = Column(Integer, nullable=True, comment="商品详情页评分")
    feedback_rating = Column(Numeric(5, 2), nullable=True, comment="评论评分")
    open_count = Column(Integer, nullable=True, comment="商品点击")
    cart_count = Column(Integer, nullable=True, comment="商品加购")
    add_to_wishlist = Column(Integer, nullable=True, comment="加入收藏夹")
    order_count = Column(Integer, nullable=True, comment="下单商品量")
    buyout_count = Column(Integer, nullable=True, comment="售出件数")
    cancel_count = Column(Integer, nullable=True, comment="取消订单商品量")
    add_to_cart_percent = Column(
        Numeric(8, 2),
        nullable=True,
        comment="加购转化率",
    )
    cart_to_order_percent = Column(
        Numeric(8, 2),
        nullable=True,
        comment="下单转化率",
    )
    buyout_percent = Column(
        Numeric(8, 2),
        nullable=True,
        comment="购买转化率",
    )
    order_sum = Column(Numeric(18, 2), nullable=True, comment="订单金额")
    buyout_sum = Column(Numeric(18, 2), nullable=True, comment="售出金额")
    cancel_sum = Column(Numeric(18, 2), nullable=True, comment="取消订单金额")
