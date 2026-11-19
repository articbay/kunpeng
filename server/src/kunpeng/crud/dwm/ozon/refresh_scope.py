"""Read refresh scopes shared by the Ozon DWM builders."""

from datetime import date, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class CRUDDWMOzonRefreshScope:
    """Resolve historical order dates affected by recently synchronized returns."""

    _recent_return_order_dates_statement = text(
        """
        SELECT DISTINCT DATE(ret.order_date) AS order_date
        FROM dwd_ozon_return_detail AS ret
        INNER JOIN ods_ozon_returns AS ods
          ON ods.shop_id = ret.shop_id
         AND ods.return_id = ret.return_id
        WHERE ret.order_date IS NOT NULL
          AND ods.update_time >= :updated_since
        ORDER BY order_date
        """
    )

    async def get_recent_return_order_dates(
        self,
        db: AsyncSession,
        *,
        updated_since: datetime,
    ) -> list[date]:
        """Return distinct order dates touched by recent Ozon return upserts."""
        rows = await db.execute(
            self._recent_return_order_dates_statement,
            {"updated_since": updated_since},
        )
        return [row[0] for row in rows if row[0] is not None]


crud_dwm_ozon_refresh_scope = CRUDDWMOzonRefreshScope()
