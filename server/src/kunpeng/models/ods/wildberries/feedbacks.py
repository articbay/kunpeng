"""
ODS 层 - 评价和问答数据模型
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Numeric,
    Boolean,
    Text,
    Index,
    UniqueConstraint,
    Date,
    JSON,
    BigInteger,
)

from kunpeng.models.base import BaseModel


class ODSWBFeedback(BaseModel):
    """
    ODS 层 - Wildberries 评价数据
    存储 API 返回的原始评价数据
    """

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="主键ID")

    __tablename__ = "ods_wb_feedbacks"

    # 关联店铺
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")

    # 原始 JSON 数据（用于追溯）
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    # 展开字段（用于快速查询）
    feedback_id = Column(String(255), nullable=False, comment="评价ID")
    created_date = Column(DateTime(timezone=True), nullable=True, comment="创建时间")
    updated_date = Column(DateTime(timezone=True), nullable=True, comment="更新时间")

    # 商品信息
    nm_id = Column(BigInteger, nullable=True, comment="商品ID")
    imt_id = Column(BigInteger, nullable=True, comment="IMT ID")
    product_name = Column(String(500), nullable=True, comment="商品名称")
    product_details = Column(JSON, nullable=True, comment="商品详情")
    supplier_article = Column(String(255), nullable=True, comment="供应商货号")
    supplier_name = Column(String(255), nullable=True, comment="供应商名称")
    brand_name = Column(String(255), nullable=True, comment="品牌名称")
    color = Column(String(100), nullable=True, comment="颜色")
    size = Column(String(100), nullable=True, comment="尺码")
    subject_name = Column(String(255), nullable=True, comment="主题名称")
    subject_id = Column(BigInteger, nullable=True, comment="主题ID")

    # 评价内容
    product_valuation = Column(Integer, nullable=True, comment="商品评分")
    text = Column(Text, nullable=True, comment="评价内容")
    pros = Column(Text, nullable=True, comment="优点")
    cons = Column(Text, nullable=True, comment="缺点")
    video = Column(JSON, nullable=True, comment="视频信息")
    photo_links = Column(JSON, nullable=True, comment="照片链接")

    # 用户信息
    user_name = Column(String(255), nullable=True, comment="用户名称")

    # 订单信息
    order_status = Column(String(50), nullable=True, comment="订单状态")
    matching_size = Column(String(50), nullable=True, comment="尺码匹配情况")
    last_order_shk_id = Column(BigInteger, nullable=True, comment="最后订单SHK ID")
    last_order_created_at = Column(DateTime(timezone=True), nullable=True, comment="最后订单创建时间")

    # 互动状态
    state = Column(String(50), nullable=True, comment="状态")
    was_viewed = Column(Boolean, nullable=True, comment="是否已查看")
    is_answered = Column(Boolean, nullable=True, comment="是否已回复")
    answer = Column(JSON, nullable=True, comment="回复内容")
    bables = Column(JSON, nullable=True, comment="标签")
    supplier_feedback_valuation = Column(Integer, nullable=True, comment="供应商对评价的评分")
    supplier_product_valuation = Column(Integer, nullable=True, comment="供应商对商品的评分")
    is_able_supplier_feedback_valuation = Column(Boolean, nullable=True, comment="是否可以对评价评分")
    is_able_supplier_product_valuation = Column(Boolean, nullable=True, comment="是否可以对商品评分")
    is_able_return_product_orders = Column(Boolean, nullable=True, comment="是否可以退单")
    return_product_orders_date = Column(DateTime(timezone=True), nullable=True, comment="退单日期")

    # 关联
    parent_feedback_id = Column(String(255), nullable=True, comment="父评价ID")
    child_feedback_id = Column(String(255), nullable=True, comment="子评价ID")

    __table_args__ = (
        UniqueConstraint("shop_id", "feedback_id", name="uq_ods_feedback_shop_feedback"),
        Index("idx_ods_feedback_shop_id", "shop_id"),
        Index("idx_ods_feedback_nm_id", "nm_id"),
        Index("idx_ods_feedback_is_answered", "is_answered"),
        Index("idx_ods_feedback_created_date", "created_date"),
        Index("idx_ods_feedback_state", "state"),
        {"comment": "Wildberries 评价表"},
    )


class ODSWBQuestion(BaseModel):
    """
    ODS 层 - Wildberries 问答数据
    存储 API 返回的原始问答数据
    """

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, comment="主键ID")

    __tablename__ = "ods_wb_questions"

    # 关联店铺
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")

    # 原始 JSON 数据（用于追溯）
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    # 展开字段（用于快速查询）
    question_id = Column(String(255), nullable=False, comment="问题ID")
    created_date = Column(DateTime(timezone=True), nullable=True, comment="创建时间")
    updated_date = Column(DateTime(timezone=True), nullable=True, comment="更新时间")

    # 商品信息
    nm_id = Column(BigInteger, nullable=True, comment="商品ID")
    imt_id = Column(BigInteger, nullable=True, comment="IMT ID")
    product_name = Column(String(500), nullable=True, comment="商品名称")
    product_details = Column(JSON, nullable=True, comment="商品详情")
    supplier_article = Column(String(255), nullable=True, comment="供应商货号")
    supplier_name = Column(String(255), nullable=True, comment="供应商名称")
    brand_name = Column(String(255), nullable=True, comment="品牌名称")
    subject_name = Column(String(255), nullable=True, comment="主题名称")

    # 问答内容
    text = Column(Text, nullable=True, comment="问题内容")

    # 状态
    state = Column(String(50), nullable=True, comment="状态")
    was_viewed = Column(Boolean, nullable=True, comment="是否已查看")
    is_warned = Column(Boolean, nullable=True, comment="是否警告")
    is_answered = Column(Boolean, nullable=True, comment="是否已回复")
    answer = Column(JSON, nullable=True, comment="回复内容")

    __table_args__ = (
        UniqueConstraint("shop_id", "question_id", name="uq_ods_question_shop_question"),
        Index("idx_ods_question_shop_id", "shop_id"),
        Index("idx_ods_question_nm_id", "nm_id"),
        Index("idx_ods_question_is_answered", "is_answered"),
        Index("idx_ods_question_created_date", "created_date"),
        Index("idx_ods_question_state", "state"),
        {"comment": "Wildberries 问答表"},
    )
