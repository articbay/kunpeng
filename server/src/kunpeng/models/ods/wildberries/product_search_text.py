"""ODS 层 - Wildberries 商品搜索词报告模型。"""

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)

from kunpeng.models.base import BaseModel


class ODSWBProductSearchText(BaseModel):
    """Wildberries 商品自然搜索词表现快照。"""

    __tablename__ = "ods_wb_traffic_product_search_texts"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")
    date_from = Column(Date, nullable=False, comment="报告开始日期")
    date_to = Column(Date, nullable=False, comment="报告结束日期")
    nm_id = Column(BigInteger, nullable=False, comment="Wildberries商品ID")
    search_text = Column(String(1000), nullable=False, comment="搜索词")
    search_text_hash = Column(String(64), nullable=False, comment="标准化搜索词哈希")
    top_order_by = Column(String(32), nullable=False, comment="取榜排序指标")

    subject_name = Column(String(255), nullable=True, comment="商品分类")
    brand_name = Column(String(255), nullable=True, comment="品牌")
    vendor_code = Column(String(255), nullable=True, comment="卖家货号")
    product_name = Column(String(500), nullable=True, comment="商品名称")
    is_card_rated = Column(Boolean, nullable=True, comment="商品卡是否有评分")
    rating = Column(Numeric(10, 4), nullable=True, comment="商品评分")
    feedback_rating = Column(Numeric(10, 4), nullable=True, comment="反馈评分")
    min_price = Column(Numeric(18, 2), nullable=True, comment="最低价格")
    max_price = Column(Numeric(18, 2), nullable=True, comment="最高价格")

    frequency_current = Column(BigInteger, nullable=True, comment="当前搜索频次")
    frequency_dynamics = Column(Numeric(18, 6), nullable=True, comment="搜索频次变化")
    week_frequency = Column(BigInteger, nullable=True, comment="周搜索频次")
    median_position_current = Column(
        Numeric(18, 6), nullable=True, comment="当前中位排名"
    )
    median_position_dynamics = Column(
        Numeric(18, 6), nullable=True, comment="中位排名变化"
    )
    avg_position_current = Column(Numeric(18, 6), nullable=True, comment="当前平均排名")
    avg_position_dynamics = Column(
        Numeric(18, 6), nullable=True, comment="平均排名变化"
    )

    open_card_current = Column(BigInteger, nullable=True, comment="打开商品卡次数")
    open_card_dynamics = Column(Numeric(18, 6), nullable=True, comment="打开商品卡变化")
    open_card_percentile = Column(
        Numeric(18, 6), nullable=True, comment="打开商品卡百分位"
    )
    add_to_cart_current = Column(BigInteger, nullable=True, comment="加购次数")
    add_to_cart_dynamics = Column(Numeric(18, 6), nullable=True, comment="加购变化")
    add_to_cart_percentile = Column(Numeric(18, 6), nullable=True, comment="加购百分位")
    open_to_cart_current = Column(
        Numeric(18, 6), nullable=True, comment="打开到加购转化率"
    )
    open_to_cart_dynamics = Column(
        Numeric(18, 6), nullable=True, comment="打开到加购转化率变化"
    )
    open_to_cart_percentile = Column(
        Numeric(18, 6), nullable=True, comment="打开到加购转化率百分位"
    )
    orders_current = Column(BigInteger, nullable=True, comment="订单数")
    orders_dynamics = Column(Numeric(18, 6), nullable=True, comment="订单数变化")
    orders_percentile = Column(Numeric(18, 6), nullable=True, comment="订单数百分位")
    cart_to_order_current = Column(
        Numeric(18, 6), nullable=True, comment="加购到下单转化率"
    )
    cart_to_order_dynamics = Column(
        Numeric(18, 6), nullable=True, comment="加购到下单转化率变化"
    )
    cart_to_order_percentile = Column(
        Numeric(18, 6), nullable=True, comment="加购到下单转化率百分位"
    )
    visibility_current = Column(Numeric(18, 6), nullable=True, comment="当前可见度")
    visibility_dynamics = Column(Numeric(18, 6), nullable=True, comment="可见度变化")

    currency = Column(String(16), nullable=True, comment="币种")
    row_data = Column(JSON, nullable=False, comment="API原始JSON数据")
    synced_at = Column(DateTime(timezone=True), nullable=False, comment="同步时间")

    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "date_from",
            "date_to",
            "nm_id",
            "search_text_hash",
            "top_order_by",
            name="uq_wb_product_search_text_window_term",
        ),
        Index("idx_wb_product_search_text_shop_id", "shop_id"),
        Index("idx_wb_product_search_text_date_range", "date_from", "date_to"),
        Index("idx_wb_product_search_text_nm_id", "nm_id"),
        Index("idx_wb_product_search_text_hash", "search_text_hash"),
        {"comment": "Wildberries商品自然搜索词报告表"},
    )
