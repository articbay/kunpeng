"""Wildberries customer question business detail model."""

from sqlalchemy import BigInteger, Column, DateTime, Index, String, Text

from kunpeng.core.database import Base


class DWDWBVOCQuestionDetail(Base):
    """Cleaned Wildberries customer question detail."""

    __tablename__ = "dwd_wb_voc_question_detail"

    shop_id = Column(BigInteger, primary_key=True, nullable=False, comment="店铺ID")
    question_id = Column(
        String(255), primary_key=True, nullable=False, comment="问题ID"
    )
    created_date = Column(DateTime(timezone=True), nullable=True, comment="日期")
    supplier_article = Column(String(255), nullable=True, comment="卖家货号")
    nm_id = Column(BigInteger, nullable=True, comment="WB货号")
    brand_name = Column(String(255), nullable=True, comment="品牌名称")
    text = Column(Text, nullable=True, comment="问题文本")
    text_cn = Column(Text, nullable=True, comment="问题文本（中文）")
    answer = Column(Text, nullable=True, comment="回复")
    answer_cn = Column(Text, nullable=True, comment="回复（中文）")

    __table_args__ = (
        Index("idx_dwd_wb_voc_question_created_date", "created_date"),
        Index("idx_dwd_wb_voc_question_nm_id", "nm_id"),
        Index("idx_dwd_wb_voc_question_supplier_article", "supplier_article"),
        {
            "comment": "Wildberries客户提问业务明细表",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )
