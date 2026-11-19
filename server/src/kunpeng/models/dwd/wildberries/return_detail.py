"""Wildberries return business detail model."""

from sqlalchemy import BigInteger, Column, Date, DateTime, Index, String

from kunpeng.core.database import Base


class DWDWBReturnDetail(Base):
    """Cleaned Wildberries return detail."""

    __tablename__ = "dwd_wb_return_detail"

    shop_id = Column(BigInteger, primary_key=True, nullable=False, comment="店铺ID")
    brand = Column(String(255), nullable=True, comment="品牌")
    subject_name = Column(String(255), nullable=True, comment="商品品类")
    subject_name_cn = Column(String(255), nullable=True, comment="商品品类（中文）")
    barcode_ori = Column(String(255), nullable=True, comment="原生条形码")
    barcode_hand = Column(String(255), nullable=True, comment="手调条形码")
    nm_id = Column(BigInteger, nullable=True, comment="WB货号")
    sticker_id = Column(String(255), nullable=True, comment="标签ID")
    status = Column(String(255), nullable=True, comment="状态")
    status_cn = Column(String(255), nullable=True, comment="状态（中文）")
    ready_to_return_dt = Column(
        DateTime(timezone=True), nullable=True, comment="准备好取货时间"
    )
    completed_dt = Column(
        DateTime(timezone=True), nullable=True, comment="已被领取时间"
    )
    expired_dt = Column(DateTime(timezone=True), nullable=True, comment="过期时间")
    return_type = Column(String(255), nullable=True, comment="退货类型")
    return_type_cn = Column(String(255), nullable=True, comment="退货类型（中文）")
    order_dt = Column(Date, nullable=True, comment="下单日期")
    reason = Column(String(500), nullable=True, comment="退货原因")
    reason_cn = Column(String(500), nullable=True, comment="退货原因（中文）")
    order_id = Column(BigInteger, nullable=True, comment="配货单号")
    srid = Column(String(255), primary_key=True, nullable=False, comment="系统订单号")
    dst_office_address = Column(String(500), nullable=True, comment="地址")
    dst_office_address_cn = Column(String(500), nullable=True, comment="地址（中文）")
    dst_office_id = Column(BigInteger, nullable=True, comment="地址ID")

    __table_args__ = (
        Index("idx_dwd_wb_return_nm_id", "nm_id"),
        Index("idx_dwd_wb_return_status", "status"),
        Index("idx_dwd_wb_return_order_dt", "order_dt"),
        {
            "comment": "Wildberries退货业务明细表",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
        },
    )
