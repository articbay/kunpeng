"""
ODS 层 - 广告商品 CRUD 操作
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.models.ods.wildberries.balance import ODSWBAdvertProduct

logger = logging.getLogger(__name__)


class CRUDODSWBAdvertProduct(
    CRUDBase[ODSWBAdvertProduct, Dict[str, Any], Dict[str, Any]]
):
    """ODS 广告商品数据 CRUD"""

    async def _get_existing(
        self, db: AsyncSession, shop_id: int, advert_id: int, nm_id: int
    ) -> Optional[ODSWBAdvertProduct]:
        """根据唯一索引获取现有记录"""
        result = await db.execute(
            select(ODSWBAdvertProduct).where(
                (ODSWBAdvertProduct.shop_id == shop_id)
                & (ODSWBAdvertProduct.advert_id == advert_id)
                & (ODSWBAdvertProduct.nm_id == nm_id)
            )
        )
        return result.scalar_one_or_none()

    async def create_many(
        self,
        db: AsyncSession,
        *,
        adverts_data: List[Dict[str, Any]],
        shop_id: int,
    ) -> List[ODSWBAdvertProduct]:
        """批量创建/更新 ODS 广告商品数据（从广告列表的nm_settings拆分）"""
        logger.debug(f"[ODS CRUD] 开始同步广告商品数据 - 店铺: {shop_id}")

        result_list = []
        incoming_keys: set[tuple[int, int]] = set()

        for advert_data in adverts_data:
            advert_id = advert_data.get("id") or advert_data.get("advertId")
            if not advert_id:
                continue

            # 获取 nm_settings 列表
            nm_settings = advert_data.get("nm_settings", [])
            if not nm_settings:
                continue

            # 处理每个商品设置
            for nm_setting in nm_settings:
                nm_id = nm_setting.get("nm_id") or nm_setting.get("nmId")
                if not nm_id:
                    continue
                incoming_keys.add((int(advert_id), int(nm_id)))

                # 解析 bids_kopecks
                bids_kopecks = nm_setting.get("bids_kopecks", {})

                # 解析 subject
                subject = nm_setting.get("subject", {})

                # 构建 ODS 记录数据
                ods_data = {
                    "shop_id": shop_id,
                    "row_data": nm_setting,
                    "advert_id": advert_id,
                    "nm_id": nm_id,
                    "bid_search": bids_kopecks.get("search"),
                    "bid_recommendations": bids_kopecks.get("recommendations"),
                    "subject_id": subject.get("id"),
                    "subject_name": subject.get("name"),
                }

                # 检查是否已存在
                existing = await self._get_existing(db, shop_id, advert_id, nm_id)

                if existing:
                    # 更新现有记录
                    for field, value in ods_data.items():
                        if hasattr(existing, field):
                            setattr(existing, field, value)
                    result_list.append(existing)
                else:
                    # 创建新记录
                    ods_record = ODSWBAdvertProduct(**ods_data)
                    db.add(ods_record)
                    result_list.append(ods_record)

        deleted_count = 0
        # adverts/v2 返回完整活动列表；仅在非空响应时清理已失效的商品映射。
        # API 异常返回空列表时保留现状，避免误清空当前快照来源。
        if adverts_data:
            existing_result = await db.execute(
                select(ODSWBAdvertProduct).where(ODSWBAdvertProduct.shop_id == shop_id)
            )
            for existing in existing_result.scalars().all():
                if (existing.advert_id, existing.nm_id) not in incoming_keys:
                    await db.delete(existing)
                    deleted_count += 1

        logger.debug(
            "[ODS CRUD] 准备提交数据库 - 更新: %s, 清理失效映射: %s",
            len(result_list),
            deleted_count,
        )
        await db.commit()
        logger.debug(f"[ODS CRUD] 数据库提交成功")
        for record in result_list:
            await db.refresh(record)
        logger.debug(f"[ODS CRUD] 广告商品同步完成 - 总计: {len(result_list)}")
        return result_list

    async def get_nm_ids_by_adverts(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        advert_ids: List[int],
    ) -> List[int]:
        """获取指定广告活动的商品ID列表"""
        if not advert_ids:
            return []

        result = await db.execute(
            select(ODSWBAdvertProduct.nm_id)
            .where(
                (ODSWBAdvertProduct.shop_id == shop_id)
                & (ODSWBAdvertProduct.advert_id.in_(advert_ids))
            )
            .distinct()
        )
        nm_ids = list(result.scalars().all())
        logger.debug(f"[ODS CRUD] 获取到 {len(nm_ids)} 个商品ID")
        return nm_ids

    async def get_advert_nm_map(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        advert_ids: List[int],
    ) -> Dict[int, List[int]]:
        """获取广告活动到商品ID列表的映射 {advert_id: [nm_id1, nm_id2, ...]}"""
        if not advert_ids:
            return {}

        result = await db.execute(
            select(ODSWBAdvertProduct.advert_id, ODSWBAdvertProduct.nm_id)
            .where(
                (ODSWBAdvertProduct.shop_id == shop_id)
                & (ODSWBAdvertProduct.advert_id.in_(advert_ids))
            )
            .distinct()
        )

        advert_nm_map: Dict[int, List[int]] = {}
        for row in result.all():
            advert_id, nm_id = row
            if advert_id not in advert_nm_map:
                advert_nm_map[advert_id] = []
            advert_nm_map[advert_id].append(nm_id)

        logger.debug(f"[ODS CRUD] 广告商品映射: {len(advert_nm_map)} 个广告")
        return advert_nm_map


# CRUD 实例
crud_ods_wb_advert_product = CRUDODSWBAdvertProduct(ODSWBAdvertProduct)
