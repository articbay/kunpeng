"""
ODS 层 - 余额和Cashback CRUD 操作
"""
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud.base import CRUDBase
from kunpeng.models.ods.wildberries.balance import ODSWBBalance, ODSWBCashback

logger = logging.getLogger(__name__)


class CRUDODSWBBalance(CRUDBase[ODSWBBalance, Dict[str, Any], Dict[str, Any]]):
    """ODS 余额数据 CRUD"""

    async def _get_existing(
        self, db: AsyncSession, shop_id: int, sync_date: date
    ) -> Optional[ODSWBBalance]:
        """根据唯一索引获取现有记录"""
        result = await db.execute(
            select(ODSWBBalance).where(
                (ODSWBBalance.shop_id == shop_id) & (ODSWBBalance.sync_date == sync_date)
            )
        )
        return result.scalar_one_or_none()

    async def create_or_update(
        self,
        db: AsyncSession,
        *,
        balance_data: Dict[str, Any],
        shop_id: int,
    ) -> ODSWBBalance:
        """创建或更新余额记录（按天分区）"""
        logger.debug(f"[ODS CRUD] 开始同步余额数据 - 店铺: {shop_id}")

        sync_date = date.today()
        sync_at = datetime.now().astimezone()

        # 构建 ODS 记录数据 (根据官方文档字段)
        ods_data = {
            "shop_id": shop_id,
            "row_data": balance_data,
            "balance": balance_data.get("balance"),
            "net": balance_data.get("net"),
            "bonus": balance_data.get("bonus"),
            "sync_date": sync_date,
            "sync_at": sync_at,
        }

        # 检查是否已存在
        existing = await self._get_existing(db, shop_id, sync_date)

        if existing:
            # 更新现有记录
            for field, value in ods_data.items():
                if hasattr(existing, field):
                    setattr(existing, field, value)
            result = existing
        else:
            # 创建新记录
            result = ODSWBBalance(**ods_data)
            db.add(result)

        await db.commit()
        await db.refresh(result)
        logger.debug(f"[ODS CRUD] 余额同步完成")
        return result


class CRUDODSWBCashback(CRUDBase[ODSWBCashback, Dict[str, Any], Dict[str, Any]]):
    """ODS Cashback数据 CRUD"""

    async def _get_existing(
        self, db: AsyncSession, shop_id: int, expiration_date: date
    ) -> Optional[ODSWBCashback]:
        """根据唯一索引获取现有记录"""
        result = await db.execute(
            select(ODSWBCashback).where(
                (ODSWBCashback.shop_id == shop_id)
                & (ODSWBCashback.expiration_date == expiration_date)
            )
        )
        return result.scalar_one_or_none()

    async def create_or_update(
        self,
        db: AsyncSession,
        *,
        cashback_data: Dict[str, Any],
        shop_id: int,
    ) -> Optional[ODSWBCashback]:
        """创建或更新Cashback记录"""
        logger.debug(f"[ODS CRUD] 开始同步Cashback数据 - 店铺: {shop_id}")

        # 解析过期日期
        expiration_date_str = cashback_data.get("expiration_date") or cashback_data.get("expirationDate")
        if not expiration_date_str:
            logger.warning(f"[ODS CRUD] Cashback缺少过期日期, 跳过")
            return None

        expiration_date = None
        try:
            if isinstance(expiration_date_str, str):
                if "T" in expiration_date_str:
                    expiration_date = date.fromisoformat(expiration_date_str[:10])
                else:
                    expiration_date = date.fromisoformat(expiration_date_str)
            elif isinstance(expiration_date_str, date):
                expiration_date = expiration_date_str
        except Exception:
            logger.warning(f"[ODS CRUD] Cashback过期日期解析失败: {expiration_date_str}")
            return None

        if not expiration_date:
            return None

        sync_at = datetime.now().astimezone()

        # 构建 ODS 记录数据
        ods_data = {
            "shop_id": shop_id,
            "row_data": cashback_data,
            "sum": cashback_data.get("sum"),
            "percent": cashback_data.get("percent"),
            "expiration_date": expiration_date,
            "sync_at": sync_at,
        }

        # 检查是否已存在
        existing = await self._get_existing(db, shop_id, expiration_date)

        if existing:
            # 更新现有记录
            for field, value in ods_data.items():
                if hasattr(existing, field):
                    setattr(existing, field, value)
            result = existing
        else:
            # 创建新记录
            result = ODSWBCashback(**ods_data)
            db.add(result)

        await db.commit()
        await db.refresh(result)
        logger.debug(f"[ODS CRUD] Cashback同步完成")
        return result


# CRUD 实例
crud_ods_wb_balance = CRUDODSWBBalance(ODSWBBalance)
crud_ods_wb_cashback = CRUDODSWBCashback(ODSWBCashback)
