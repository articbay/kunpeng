"""ODS 层 - Wildberries 卖家余额快照模型。"""

from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    Date,
    DateTime,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)

from kunpeng.models.base import BaseModel


class ODSWBSellerBalance(BaseModel):
    """Wildberries 财务域卖家余额每日快照。"""

    __tablename__ = "ods_wb_finance_seller_balance"

    id = Column(
        BigInteger, primary_key=True, index=True, autoincrement=True, comment="主键ID"
    )
    shop_id = Column(BigInteger, nullable=False, comment="店铺ID")
    row_data = Column(JSON, nullable=False, comment="API原始JSON数据")
    currency = Column(String(10), nullable=True, comment="币种")
    current = Column(Numeric(18, 2), nullable=True, comment="当前余额")
    for_withdraw = Column(Numeric(18, 2), nullable=True, comment="可提现金额")
    snapshot_date = Column(Date, nullable=False, comment="平台时区快照日期")
    synced_at = Column(DateTime(timezone=True), nullable=False, comment="同步时间")

    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "snapshot_date",
            name="uq_ods_wb_seller_balance_shop_date",
        ),
        Index("idx_ods_wb_seller_balance_shop_id", "shop_id"),
        Index("idx_ods_wb_seller_balance_snapshot_date", "snapshot_date"),
        {"comment": "Wildberries卖家余额每日快照表"},
    )
