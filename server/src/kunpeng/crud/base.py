from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.base import BaseModel as DBBaseModel

ModelType = TypeVar("ModelType", bound=DBBaseModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """CRUD基类"""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: int) -> Optional[ModelType]:
        """根据ID获取单条记录"""
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100, **filters
    ) -> List[ModelType]:
        """获取多条记录"""
        query = select(self.model)
        for key, value in filters.items():
            if value is not None:
                query = query.where(getattr(self.model, key) == value)
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def count(self, db: AsyncSession, **filters) -> int:
        """统计记录数量"""
        from sqlalchemy import func

        query = select(func.count(self.model.id))
        for key, value in filters.items():
            if value is not None:
                query = query.where(getattr(self.model, key) == value)
        result = await db.execute(query)
        return result.scalar_one()

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType | Dict[str, Any]) -> ModelType:
        """创建记录"""
        if isinstance(obj_in, dict):
            obj_in_data = obj_in
        else:
            obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, *, db_obj: ModelType, obj_in: UpdateSchemaType | Dict[str, Any]
    ) -> ModelType:
        """更新记录"""
        obj_data = db_obj.__dict__
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, *, id: int) -> Optional[ModelType]:
        """删除记录"""
        obj = await self.get(db, id=id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj
