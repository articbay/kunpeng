"""
Ozon ODS 层 - 财务应计类型字典表
"""
from sqlalchemy import Column, BigInteger, Integer, String, Boolean, JSON, Index, UniqueConstraint
from sqlalchemy.dialects.mysql import VARCHAR, TEXT

from kunpeng.models.base import BaseModel


class ODSOzonFinanceAccrualType(BaseModel):
    """
    Ozon ODS 层 - 财务应计类型字典表

    描述: 存储Ozon财务应计类型字典数据，包含所有可能的费用类型定义，用于财务数据分类和分析。
    注意: 这是全局维度表，不按店铺区分。
    """

    __tablename__ = "ods_ozon_finance_accrual_types"
    __table_args__ = (
        UniqueConstraint(
            "type_id",
            name="uq_ods_ozon_accrual_types_type_id"
        ),
        {
            "comment": "Ozon财务应计类型字典表"
        }
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    row_data = Column(JSON, nullable=False, comment="原始JSON数据")
    type_id = Column(BigInteger, nullable=True, comment="应计类型ID (API返回的id)")
    name = Column(VARCHAR(255), nullable=True, comment="英文名称")
    description = Column(VARCHAR(500), nullable=True, comment="俄文描述")
    name_zh = Column(VARCHAR(255), nullable=True, comment="中文名称")
    category = Column(VARCHAR(100), nullable=True, comment="分类 (预留字段)")
    is_active = Column(Boolean, nullable=True, default=True, comment="是否启用 (预留字段)")
