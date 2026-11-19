"""Wildberries customer feedback business detail model."""

from sqlalchemy import BigInteger, Column, DateTime, Index, String, Text
from sqlalchemy.dialects.mysql import TINYINT

from kunpeng.core.database import Base


class DWDWBVOCFeedbackDetail(Base):
    """Cleaned Wildberries customer feedback detail."""

    __tablename__ = "dwd_wb_voc_feedback_detail"

    shop_id = Column(BigInteger, primary_key=True, nullable=False, comment="店铺ID")
    feedback_id = Column(
        String(255), primary_key=True, nullable=False, comment="评价ID"
    )
    created_date = Column(
        DateTime(timezone=True), nullable=True, comment="评价创建时间"
    )
    supplier_article = Column(String(255), nullable=True, comment="卖家货号")
    nm_id = Column(BigInteger, nullable=True, comment="WB货号")
    product_name = Column(String(500), nullable=True, comment="商品名称")
    product_name_cn = Column(String(500), nullable=True, comment="商品名称（中文）")
    product_valuation = Column(
        TINYINT(unsigned=True), nullable=True, comment="星级数量"
    )
    brand_name = Column(String(255), nullable=True, comment="品牌名称")
    text = Column(Text, nullable=True, comment="评价文本")
    text_cn = Column(Text, nullable=True, comment="评价文本（中文）")
    pros = Column(Text, nullable=True, comment="优点")
    pros_cn = Column(Text, nullable=True, comment="优点（中文）")
    cons = Column(Text, nullable=True, comment="缺点")
    cons_cn = Column(Text, nullable=True, comment="缺点（中文）")
    user_name = Column(String(255), nullable=True, comment="用户姓名")
    color = Column(String(100), nullable=True, comment="颜色")
    color_cn = Column(String(100), nullable=True, comment="颜色（中文）")
    size = Column(String(100), nullable=True, comment="尺码")
    size_cn = Column(String(100), nullable=True, comment="尺码（中文）")
    answer = Column(Text, nullable=True, comment="回复正文")
    answer_cn = Column(Text, nullable=True, comment="回复正文（中文）")
    parent_feedback_id = Column(String(255), nullable=True, comment="初始评价ID")
    child_feedback_id = Column(String(255), nullable=True, comment="追加评价ID")

    __table_args__ = (
        Index("idx_dwd_wb_voc_feedback_created_date", "created_date"),
        Index("idx_dwd_wb_voc_feedback_nm_id", "nm_id"),
        Index("idx_dwd_wb_voc_feedback_supplier_article", "supplier_article"),
        {
            "comment": "Wildberries客户评价业务明细表",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )
