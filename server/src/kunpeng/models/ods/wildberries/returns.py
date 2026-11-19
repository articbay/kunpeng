"""
ODS 层 - 退货数据模型
"""

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)

from kunpeng.models.base import BaseModel


class ODSWBGoodsReturn(BaseModel):
    """
    ODS 层 - Wildberries 退货数据
    存储 API 返回的原始退货数据
    """

    id = Column(
        BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID"
    )

    __tablename__ = "ods_wb_goods_returns"

    # 关联店铺
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")

    # 原始 JSON 数据（用于追溯）
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")

    # 展开字段（用于快速查询）
    barcode = Column(String(255), nullable=True, comment="条码 (API: barcode)")
    brand = Column(String(255), nullable=True, comment="品牌")
    completed_dt = Column(DateTime(timezone=True), nullable=True, comment="完成日期")
    dst_office_address = Column(String(500), nullable=True, comment="目的地地址")
    dst_office_id = Column(BigInteger, nullable=True, comment="目的地ID")
    expired_dt = Column(DateTime(timezone=True), nullable=True, comment="过期日期")
    is_status_active = Column(Integer, nullable=True, comment="是否活跃状态")
    nm_id = Column(BigInteger, nullable=True, comment="商品ID")
    order_dt = Column(Date, nullable=True, comment="订单日期")
    order_id = Column(BigInteger, nullable=True, comment="订单ID")
    ready_to_return_dt = Column(
        DateTime(timezone=True), nullable=True, comment="准备退货日期"
    )
    reason = Column(String(500), nullable=True, comment="原因")
    return_type = Column(String(255), nullable=True, comment="退货类型")
    shk_id = Column(BigInteger, nullable=True, comment="SHK ID")
    srid = Column(String(255), nullable=True, comment="SRID")
    status = Column(String(255), nullable=True, comment="退货状态")
    sticker_id = Column(String(255), nullable=True, comment="贴纸ID")
    subject_name = Column(String(255), nullable=True, comment="主题名称")
    tech_size = Column(String(100), nullable=True, comment="技术尺寸")

    __table_args__ = (
        UniqueConstraint("shop_id", "srid", name="uq_ods_return_shop_srid"),
        Index("idx_ods_return_shop_id", "shop_id"),
        Index("idx_ods_return_nm_id", "nm_id"),
        Index("idx_ods_return_status", "status"),
        {"comment": "Wildberries 退货数据表"},
    )
