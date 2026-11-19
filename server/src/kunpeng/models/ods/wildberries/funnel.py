"""
ODS 层 - 销售漏斗数据模型
"""

from sqlalchemy import (JSON, BigInteger, Boolean, Column, Date, DateTime,
                        Index, Integer, Numeric, String, UniqueConstraint)

from kunpeng.models.base import BaseModel


class ODSWBSalesFunnel(BaseModel):
    """
    ODS 层 - Wildberries 销售漏斗数据
    存储 API 返回的原始销售漏斗数据
    """

    id = Column(
        BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID"
    )

    __tablename__ = "ods_wb_sales_funnels"

    # 关联店铺
    shop_id = Column(Integer, nullable=False, comment="店铺ID")

    # 日期范围
    date_from = Column(Date, nullable=False, comment="开始日期")
    date_to = Column(Date, nullable=False, comment="结束日期")

    # ==========================================
    # product 字段
    # ==========================================
    nm_id = Column(BigInteger, nullable=True, index=True, comment="商品ID")
    vendor_code = Column(String(255), nullable=True, comment="供应商编码")
    subject_name = Column(String(255), nullable=True, comment="主题名称")
    brand_name = Column(String(255), nullable=True, comment="品牌名称")
    title = Column(String(1000), nullable=True, comment="商品标题")
    subject_id = Column(BigInteger, nullable=True, comment="主题ID")
    product_rating = Column(Integer, nullable=True, comment="商品评分")
    feedback_rating = Column(Numeric(5, 2), nullable=True, comment="评价评分")
    tags = Column(JSON, nullable=True, comment="标签列表")

    # statistic.selected.timeToReady 字段
    time_to_ready_days = Column(Integer, nullable=True, comment="准备天数")
    time_to_ready_hours = Column(Integer, nullable=True, comment="准备小时数")
    time_to_ready_mins = Column(Integer, nullable=True, comment="准备分钟数")

    # product.stocks 字段
    stocks_wb = Column(Integer, nullable=True, comment="WB库存")
    stocks_mp = Column(Integer, nullable=True, comment="MP库存")
    stocks_balance_sum = Column(Numeric(18, 2), nullable=True, comment="库存总金额")

    # ==========================================
    # statistic.selected 字段
    # ==========================================
    # 基础统计
    open_count = Column(Integer, nullable=True, comment="浏览次数")
    cart_count = Column(Integer, nullable=True, comment="加购次数")
    order_count = Column(Integer, nullable=True, comment="下单次数")
    order_sum = Column(Numeric(18, 2), nullable=True, comment="下单金额")
    buyout_count = Column(Integer, nullable=True, comment="购买次数")
    buyout_sum = Column(Numeric(18, 2), nullable=True, comment="购买金额")
    cancel_count = Column(Integer, nullable=True, comment="取消次数")
    cancel_sum = Column(Numeric(18, 2), nullable=True, comment="取消金额")

    # 均价和转化率
    avg_price = Column(Numeric(18, 2), nullable=True, comment="平均价格")
    avg_orders_count_per_day = Column(
        Numeric(8, 2), nullable=True, comment="日均订单数"
    )
    share_order_percent = Column(Numeric(8, 2), nullable=True, comment="订单占比")

    # 其他指标
    add_to_wishlist = Column(Integer, nullable=True, comment="收藏次数")
    localization_percent = Column(Integer, nullable=True, comment="本地化百分比")

    # statistic.selected.conversions 字段
    add_to_cart_percent = Column(Numeric(8, 2), nullable=True, comment="加购转化率")
    cart_to_order_percent = Column(
        Numeric(8, 2), nullable=True, comment="加购转下单转化率"
    )
    buyout_percent = Column(Numeric(8, 2), nullable=True, comment="购买转化率")

    # statistic.selected.wbClub 字段
    wb_club_order_count = Column(Integer, nullable=True, comment="WB Club下单次数")
    wb_club_order_sum = Column(Numeric(18, 2), nullable=True, comment="WB Club下单金额")
    wb_club_buyout_count = Column(Integer, nullable=True, comment="WB Club购买次数")
    wb_club_buyout_sum = Column(
        Numeric(18, 2), nullable=True, comment="WB Club购买金额"
    )
    wb_club_cancel_count = Column(Integer, nullable=True, comment="WB Club取消次数")
    wb_club_cancel_sum = Column(
        Numeric(18, 2), nullable=True, comment="WB Club取消金额"
    )
    wb_club_avg_price = Column(Numeric(18, 2), nullable=True, comment="WB Club平均价格")
    wb_club_buyout_percent = Column(
        Numeric(8, 2), nullable=True, comment="WB Club购买转化率"
    )
    wb_club_avg_order_count_per_day = Column(
        Numeric(8, 2), nullable=True, comment="WB Club日均订单数"
    )

    # 原始 JSON 数据（用于追溯）
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "date_from",
            "date_to",
            "nm_id",
            name="uq_ods_funnel_shop_date_nm",
        ),
        Index("idx_ods_funnel_shop_id", "shop_id"),
        Index("idx_ods_funnel_date_range", "date_from", "date_to"),
        Index("idx_ods_funnel_nm_id", "nm_id"),
        Index(
            "idx_ods_funnel_shop_nm_date",
            "shop_id",
            "nm_id",
            "date_to",
            "date_from",
        ),
        {"comment": "Wildberries 销售漏斗数据表"},
    )
