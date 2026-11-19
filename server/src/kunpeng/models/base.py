from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.sql import func

from kunpeng.core.database import Base


class BaseModel(Base):
    """基础模型类"""

    __abstract__ = True

    create_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, comment="创建时间")
    update_time = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")
