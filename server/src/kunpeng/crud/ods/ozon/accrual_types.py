"""
Ozon ODS 层 - 财务应计类型字典表 CRUD
"""
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.models.ods.ozon.accrual_types import ODSOzonFinanceAccrualType
from kunpeng.crud.ods.ozon.utils import safe_int, safe_str

from kunpeng.crud.ods.ozon.accrual_type_names import ACCRUAL_TYPE_NAME_ZH

logger = logging.getLogger(__name__)


class CRUDOzonFinanceAccrualType(CRUDBase[ODSOzonFinanceAccrualType, Dict[str, Any], Dict[str, Any]]):
    """ODS 财务应计类型字典表 CRUD"""

    async def _get_existing_item(
        self,
        db: AsyncSession,
        type_id: int,
    ) -> Optional[ODSOzonFinanceAccrualType]:
        """根据唯一约束获取现有记录"""
        query = select(ODSOzonFinanceAccrualType).where(
            ODSOzonFinanceAccrualType.type_id == type_id
        )

        result = await db.execute(query)
        return result.scalar_one_or_none()

    def _extract_item_data(
        self,
        item: Dict[str, Any],
    ) -> Dict[str, Any]:
        """从API响应中提取数据到模型字段"""
        type_id = safe_int(item.get('id'))
        return {
            'row_data': item,
            'type_id': type_id,
            'name': safe_str(item.get('name')),
            'description': safe_str(item.get('description')),
            'name_zh': ACCRUAL_TYPE_NAME_ZH.get(type_id),
            'category': safe_str(item.get('category')),
            'is_active': item.get('isActive', True),
        }

    async def create_many(
        self,
        db: AsyncSession,
        *,
        items: List[Dict[str, Any]],
    ) -> List[ODSOzonFinanceAccrualType]:
        """批量创建/更新财务应计类型"""
        logger.debug(
            f"[ODS Ozon Accrual Types] 开始同步 - 数据量: {len(items)}"
        )

        result_list = []
        updated_count = 0
        created_count = 0

        for item in items:
            item_data = self._extract_item_data(item)
            type_id = item_data.get('type_id')

            existing = None
            if type_id is not None:
                existing = await self._get_existing_item(db, type_id)

            if existing:
                for field, value in item_data.items():
                    if field != 'id' and hasattr(existing, field):
                        setattr(existing, field, value)
                result_list.append(existing)
                updated_count += 1
            else:
                new_item = ODSOzonFinanceAccrualType(**item_data)
                db.add(new_item)
                result_list.append(new_item)
                created_count += 1

        await db.flush()

        logger.debug(
            f"[ODS Ozon Accrual Types] 同步完成 - 新增: {created_count}, 更新: {updated_count}, 总计: {len(result_list)}"
        )
        return result_list


# CRUD 实例
crud_ods_ozon_accrual_types = CRUDOzonFinanceAccrualType(ODSOzonFinanceAccrualType)
