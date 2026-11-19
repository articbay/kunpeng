"""Ozon advertising efficiency business detail model."""

from sqlalchemy import BigInteger, Column, Date, Index, Integer, Numeric, String, Text

from kunpeng.core.database import Base


class DWDOzonAdvertEfficiencyDetail(Base):
    """One Ozon advertising performance row per shop, campaign, SKU and day."""

    __tablename__ = "dwd_ozon_advert_efficiency_detail"

    # 复合主键也是固定统计粒度，禁止跨日期直接覆盖或合并。
    shop_id = Column(Integer, primary_key=True, nullable=False, comment="店铺ID")
    stat_date = Column(Date, primary_key=True, nullable=False, comment="统计日期")
    sku = Column(BigInteger, primary_key=True, nullable=False, comment="Ozon SKU")

    # 业务字段按广告效率 Excel 顺序排列，中文翻译紧跟原字段。
    product_name = Column(Text, nullable=True, comment="商品名称")
    product_name_cn = Column(Text, nullable=True, comment="商品名称（中文）")
    category_name = Column(String(255), nullable=True, comment="品类名称")
    category_name_cn = Column(String(255), nullable=True, comment="品类名称（中文）")
    payment_type = Column(String(64), nullable=True, comment="广告工具/付费类型")
    placement = Column(String(255), nullable=True, comment="投放位置")
    campaign_id = Column(
        String(64), primary_key=True, nullable=False, comment="广告活动ID"
    )
    campaign_name = Column(String(500), nullable=True, comment="广告活动名称")
    money_spent = Column(Numeric(18, 4), nullable=True, comment="费用（卢布）")
    drr = Column(Numeric(12, 4), nullable=True, comment="广告费用份额（%）")
    orders_money = Column(Numeric(18, 4), nullable=True, comment="销售额（卢布）")
    orders = Column(BigInteger, nullable=True, comment="订单数")
    ctr = Column(Numeric(12, 4), nullable=True, comment="点击率（%）")
    views = Column(BigInteger, nullable=True, comment="展现量")
    clicks = Column(BigInteger, nullable=True, comment="点击次数")
    to_cart = Column(BigInteger, nullable=True, comment="加购次数")
    to_cart_conversion_rate = Column(
        Numeric(12, 4), nullable=True, comment="加购转化率（%）"
    )
    cost_per_order = Column(Numeric(18, 4), nullable=True, comment="单笔费用（卢布）")
    cost_per_click = Column(
        Numeric(18, 4), nullable=True, comment="每次点击成本（卢布）"
    )

    __table_args__ = (
        Index("idx_dwd_ozon_advert_efficiency_date", "stat_date"),
        Index("idx_dwd_ozon_advert_efficiency_sku", "sku"),
        Index("idx_dwd_ozon_advert_efficiency_campaign", "campaign_id"),
        {
            "comment": "Ozon广告效率SKU日明细表",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )
