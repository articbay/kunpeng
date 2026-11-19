"""Ozon FBS/FBO 订单与退货状态历史 ODS 表。"""

from sqlalchemy import BigInteger, Column, DateTime, Index, Integer, JSON, String
from sqlalchemy import UniqueConstraint

from kunpeng.models.base import BaseModel


class ODSOzonPostingStatusHistory(BaseModel):
    __tablename__ = "ods_ozon_posting_status_history"
    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "mode",
            "posting_number",
            "state_key",
            name="uq_ods_ozon_posting_status_history_state",
        ),
        Index(
            "idx_ods_ozon_posting_status_history_posting",
            "shop_id",
            "mode",
            "posting_number",
        ),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    shop_id = Column(Integer, nullable=False, index=True)
    mode = Column(String(10), nullable=False)
    posting_number = Column(String(100), nullable=False)
    order_id = Column(BigInteger, nullable=True)
    status = Column(String(100), nullable=True)
    substatus = Column(String(100), nullable=True)
    state_key = Column(String(64), nullable=False)
    source_changed_at = Column(DateTime(timezone=True), nullable=True)
    first_observed_at = Column(DateTime(timezone=True), nullable=False)
    row_data = Column(JSON, nullable=False)


class ODSOzonReturnStatusHistory(BaseModel):
    __tablename__ = "ods_ozon_return_status_history"
    __table_args__ = (
        UniqueConstraint(
            "shop_id",
            "return_id",
            "state_key",
            name="uq_ods_ozon_return_status_history_state",
        ),
        Index(
            "idx_ods_ozon_return_status_history_return", "shop_id", "return_id"
        ),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    shop_id = Column(Integer, nullable=False, index=True)
    return_id = Column(BigInteger, nullable=False)
    posting_number = Column(String(100), nullable=True)
    status_id = Column(BigInteger, nullable=True)
    status_sys_name = Column(String(100), nullable=True)
    status_display_name = Column(String(255), nullable=True)
    state_key = Column(String(64), nullable=False)
    source_changed_at = Column(DateTime(timezone=True), nullable=True)
    first_observed_at = Column(DateTime(timezone=True), nullable=False)
    row_data = Column(JSON, nullable=False)
