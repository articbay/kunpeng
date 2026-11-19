
"""
Unified Platform Sync API
==========================

Single API endpoint for syncing data from any registered platform.
"""

from typing import Dict, Optional, Any
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from kunpeng.core.database import get_db
from kunpeng.services.platform_sync import PlatformRegistry
from kunpeng.utils.timezone import today_platform

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/platforms", tags=["platforms"])


def get_date_range(
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
) -> tuple[str, str]:
    """
    Get date range from query parameters, default to last 7 days.
    """
    today = today_platform()
    if not date_to:
        date_to = today.isoformat()
    if not date_from:
        date_from = (today - timedelta(days=7)).isoformat()
    return date_from, date_to


@router.get("")
async def list_platforms() -> Any:
    """
    List all registered platforms.
    """
    platforms = PlatformRegistry.get_platforms()
    return {"platforms": platforms}


@router.get("/{platform}/data-types")
async def list_data_types(platform: str) -> Any:
    """
    List supported data types for a platform.
    """
    service = PlatformRegistry.get_service(platform)
    if not service:
        raise HTTPException(status_code=404, detail=f"Platform '{platform}' not found")

    data_types = service.get_data_types()
    return {"platform": platform, "data_types": data_types}


@router.post("/{platform}/sync")
async def sync_platform_all(
    platform: str,
    shop_id: int = Query(..., description="Shop ID to sync"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    Sync all data types for a platform.
    """
    service = PlatformRegistry.get_service(platform)
    if not service:
        raise HTTPException(status_code=404, detail=f"Platform '{platform}' not found")

    date_from, date_to = get_date_range(date_from, date_to)

    logger.info(
        "Starting full platform sync",
        platform=platform,
        shop_id=shop_id,
        date_from=date_from,
        date_to=date_to,
    )

    try:
        results = await service.sync_all(db, shop_id, date_from, date_to)

        logger.info(
            "Completed full platform sync",
            platform=platform,
            shop_id=shop_id,
            results=results,
        )

        return {
            "status": "success",
            "platform": platform,
            "shop_id": shop_id,
            "date_from": date_from,
            "date_to": date_to,
            "results": results,
        }
    except Exception as e:
        logger.error(
            "Platform sync failed",
            platform=platform,
            shop_id=shop_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")


@router.post("/{platform}/sync/{data_type}")
async def sync_platform_type(
    platform: str,
    data_type: str,
    shop_id: int = Query(..., description="Shop ID to sync"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    Sync a specific data type for a platform.
    """
    service = PlatformRegistry.get_service(platform)
    if not service:
        raise HTTPException(status_code=404, detail=f"Platform '{platform}' not found")

    date_from, date_to = get_date_range(date_from, date_to)

    logger.info(
        "Starting data type sync",
        platform=platform,
        data_type=data_type,
        shop_id=shop_id,
        date_from=date_from,
        date_to=date_to,
    )

    try:
        count = await service.sync_type(data_type, db, shop_id, date_from, date_to)

        logger.info(
            "Completed data type sync",
            platform=platform,
            data_type=data_type,
            shop_id=shop_id,
            count=count,
        )

        return {
            "status": "success",
            "platform": platform,
            "data_type": data_type,
            "shop_id": shop_id,
            "date_from": date_from,
            "date_to": date_to,
            "count": count,
        }
    except Exception as e:
        logger.error(
            "Data type sync failed",
            platform=platform,
            data_type=data_type,
            shop_id=shop_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

