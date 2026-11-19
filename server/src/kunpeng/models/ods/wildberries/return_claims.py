"""ODS layer model for Wildberries buyers' return claims."""

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)

from kunpeng.models.base import BaseModel


class ODSWBReturnClaim(BaseModel):
    """Wildberries buyers' return application returned by ``/api/v1/claims``."""

    __tablename__ = "ods_wb_return_claims"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")

    row_data = Column(JSON, nullable=False, comment="Wildberries 原始JSON数据")
    claim_id = Column(String(36), nullable=False, comment="退货申请ID")
    claim_type = Column(Integer, nullable=True, comment="申请类型")
    status = Column(Integer, nullable=True, comment="申请状态")
    status_ex = Column(Integer, nullable=True, comment="申请扩展状态")
    is_archive = Column(Boolean, nullable=False, default=False, comment="是否已归档")

    nm_id = Column(BigInteger, nullable=True, comment="Wildberries 商品ID")
    srid = Column(String(255), nullable=True, comment="订单唯一ID")
    product_name = Column(String(500), nullable=True, comment="商品名称")

    user_comment = Column(Text, nullable=True, comment="买家说明")
    wb_comment = Column(Text, nullable=True, comment="Wildberries 处理说明")
    origin_id_info = Column(Text, nullable=True, comment="商品标识校验信息")

    claim_created_at = Column(
        DateTime(timezone=True), nullable=True, comment="申请时间"
    )
    claim_updated_at = Column(
        DateTime(timezone=True), nullable=True, comment="申请更新时间"
    )
    order_at = Column(DateTime(timezone=True), nullable=True, comment="下单时间")
    delivery_at = Column(DateTime(timezone=True), nullable=True, comment="送达时间")
    last_synced_at = Column(
        DateTime(timezone=True), nullable=False, comment="最近同步时间"
    )

    photos = Column(JSON, nullable=True, comment="图片地址")
    video_paths = Column(JSON, nullable=True, comment="视频地址")
    actions = Column(JSON, nullable=True, comment="当前允许的处理动作")
    price = Column(Numeric(18, 2), nullable=True, comment="商品价格")
    currency_code = Column(String(10), nullable=True, comment="币种代码")

    __table_args__ = (
        UniqueConstraint(
            "shop_id", "claim_id", name="uq_ods_wb_return_claim_shop_claim"
        ),
        Index("idx_ods_wb_return_claim_shop_id", "shop_id"),
        Index(
            "idx_ods_wb_return_claim_shop_updated",
            "shop_id",
            "claim_updated_at",
        ),
        Index(
            "idx_ods_wb_return_claim_shop_archive_status",
            "shop_id",
            "is_archive",
            "status",
        ),
        Index("idx_ods_wb_return_claim_nm_id", "nm_id"),
        Index("idx_ods_wb_return_claim_srid", "srid"),
        {"comment": "Wildberries 买家退货申请表"},
    )
