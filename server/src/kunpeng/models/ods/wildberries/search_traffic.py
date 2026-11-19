"""ODS 层 - Wildberries 商品搜索流量报告模型。"""

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


class ODSWBSearchTraffic(BaseModel):
    """Wildberries 商品搜索流量滚动窗口快照。"""

    __tablename__ = "ods_wb_traffic_search_traffic"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")
    date_from = Column(Date, nullable=False, comment="报告开始日期")
    date_to = Column(Date, nullable=False, comment="报告结束日期")
    nm_id = Column(BigInteger, nullable=False, comment="Wildberries商品ID")
    position_cluster = Column(
        String(32), nullable=False, default="all", comment="搜索位置分组"
    )

    product_name = Column(String(500), nullable=True, comment="商品名称")
    vendor_code = Column(String(255), nullable=True, comment="卖家货号")
    subject_name = Column(String(255), nullable=True, comment="商品分类")
    brand_name = Column(String(255), nullable=True, comment="品牌")
    main_photo = Column(String(1000), nullable=True, comment="商品主图")
    is_advertised = Column(Boolean, nullable=True, comment="是否广告商品")
    is_substituted_sku = Column(Boolean, nullable=True, comment="是否替换商品")
    is_card_rated = Column(Boolean, nullable=True, comment="商品卡是否有评分")
    rating = Column(Numeric(10, 4), nullable=True, comment="商品卡评分")
    feedback_rating = Column(Numeric(10, 4), nullable=True, comment="用户反馈评分")
    min_price = Column(Numeric(18, 2), nullable=True, comment="最低价格")
    max_price = Column(Numeric(18, 2), nullable=True, comment="最高价格")

    avg_position_current = Column(
        Numeric(18, 6), nullable=True, comment="当前平均搜索位置"
    )
    avg_position_dynamics = Column(
        Numeric(18, 6), nullable=True, comment="平均搜索位置变化"
    )
    open_card_current = Column(BigInteger, nullable=True, comment="打开商品卡次数")
    open_card_dynamics = Column(Numeric(18, 6), nullable=True, comment="打开商品卡变化")
    add_to_cart_current = Column(BigInteger, nullable=True, comment="加购次数")
    add_to_cart_dynamics = Column(Numeric(18, 6), nullable=True, comment="加购变化")
    open_to_cart_current = Column(
        Numeric(18, 6), nullable=True, comment="打开到加购转化率"
    )
    open_to_cart_dynamics = Column(
        Numeric(18, 6), nullable=True, comment="打开到加购转化率变化"
    )
    orders_current = Column(BigInteger, nullable=True, comment="订单数")
    orders_dynamics = Column(Numeric(18, 6), nullable=True, comment="订单数变化")
    cart_to_order_current = Column(
        Numeric(18, 6), nullable=True, comment="加购到下单转化率"
    )
    cart_to_order_dynamics = Column(
        Numeric(18, 6), nullable=True, comment="加购到下单转化率变化"
    )
    visibility_current = Column(Numeric(18, 6), nullable=True, comment="当前搜索可见度")
    visibility_dynamics = Column(
        Numeric(18, 6), nullable=True, comment="搜索可见度变化"
    )

    currency = Column(String(16), nullable=True, comment="币种")
    row_data = Column(JSON, nullable=False, comment="API原始JSON数据")
    synced_at = Column(DateTime(timezone=True), nullable=False, comment="同步时间")

    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "date_from",
            "date_to",
            "nm_id",
            "position_cluster",
            name="uq_wb_search_traffic_window_product",
        ),
        Index("idx_wb_search_traffic_shop_id", "shop_id"),
        Index("idx_wb_search_traffic_date_range", "date_from", "date_to"),
        Index("idx_wb_search_traffic_nm_id", "nm_id"),
        {"comment": "Wildberries商品搜索流量滚动窗口表"},
    )
