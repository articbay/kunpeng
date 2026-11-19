"""DWD 层 - Wildberries 销售漏斗商品明细 CRUD。"""

from collections.abc import Sequence
from datetime import date
from typing import Any

from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.models.dwd.wildberries.funnel import DWDWBSalesFunnelDetail
from kunpeng.models.ods.wildberries.funnel import ODSWBSalesFunnel

FUNNEL_BUSINESS_FIELDS = (
    "vendor_code",
    "nm_id",
    "title",
    "subject_name",
    "brand_name",
    "tags",
    "product_rating",
    "feedback_rating",
    "date_from",
    "open_count",
    "cart_count",
    "add_to_wishlist",
    "order_count",
    "buyout_count",
    "cancel_count",
    "add_to_cart_percent",
    "cart_to_order_percent",
    "buyout_percent",
    "order_sum",
    "buyout_sum",
    "cancel_sum",
)


class CRUDDWDWBSalesFunnelDetail:
    """从销售漏斗 ODS 构建 DWD 商品明细。"""

    @staticmethod
    async def get_source_batch(
        db: AsyncSession,
        *,
        after_id: int,
        batch_size: int,
        shop_id: int | None = None,
    ) -> list[ODSWBSalesFunnel]:
        statement = select(ODSWBSalesFunnel).where(ODSWBSalesFunnel.id > after_id)
        if shop_id is not None:
            statement = statement.where(ODSWBSalesFunnel.shop_id == shop_id)
        statement = statement.order_by(ODSWBSalesFunnel.id).limit(batch_size)
        result = await db.execute(statement)
        return list(result.scalars().all())

    @staticmethod
    def build_dwd_data(source: ODSWBSalesFunnel) -> dict[str, Any]:
        """严格按第二个 Sheet 的有效映射字段提取 DWD 行。"""
        data = {field: getattr(source, field) for field in FUNNEL_BUSINESS_FIELDS}
        data["source_ods_id"] = source.id
        data["shop_id"] = source.shop_id
        data["date_to"] = source.date_to
        return data

    @staticmethod
    async def upsert_source_batch(
        db: AsyncSession,
        *,
        sources: Sequence[ODSWBSalesFunnel],
    ) -> dict[str, int]:
        latest_sources = {
            (
                source.shop_id,
                source.date_from,
                source.date_to,
                source.nm_id,
            ): source
            for source in sources
        }
        if not latest_sources:
            return {"created": 0, "updated": 0}

        statement = select(DWDWBSalesFunnelDetail).where(
            tuple_(
                DWDWBSalesFunnelDetail.shop_id,
                DWDWBSalesFunnelDetail.date_from,
                DWDWBSalesFunnelDetail.date_to,
                DWDWBSalesFunnelDetail.nm_id,
            ).in_(list(latest_sources))
        )
        result = await db.execute(statement)
        existing_by_key = {
            (item.shop_id, item.date_from, item.date_to, item.nm_id): item
            for item in result.scalars().all()
        }

        created = 0
        updated = 0
        for key, source in latest_sources.items():
            item_data = CRUDDWDWBSalesFunnelDetail.build_dwd_data(source)
            existing = existing_by_key.get(key)
            if existing is None:
                db.add(DWDWBSalesFunnelDetail(**item_data))
                created += 1
                continue

            for field, value in item_data.items():
                setattr(existing, field, value)
            updated += 1

        await db.flush()
        return {"created": created, "updated": updated}

    @staticmethod
    def _apply_detail_filters(
        statement: Any,
        *,
        shop_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
        nm_id: int | None = None,
        vendor_code: str | None = None,
        title: str | None = None,
        subject_name: str | None = None,
        brand_name: str | None = None,
    ) -> Any:
        """为列表和导出复用同一套 DWD 销售漏斗筛选条件。"""
        statement = statement.where(DWDWBSalesFunnelDetail.shop_id == shop_id)
        if date_from is not None:
            statement = statement.where(DWDWBSalesFunnelDetail.date_from >= date_from)
        if date_to is not None:
            statement = statement.where(DWDWBSalesFunnelDetail.date_to <= date_to)
        if nm_id is not None:
            statement = statement.where(DWDWBSalesFunnelDetail.nm_id == nm_id)
        if vendor_code:
            statement = statement.where(
                DWDWBSalesFunnelDetail.vendor_code.contains(
                    vendor_code,
                    autoescape=True,
                )
            )
        if title:
            statement = statement.where(
                DWDWBSalesFunnelDetail.title.contains(title, autoescape=True)
            )
        if subject_name:
            statement = statement.where(
                DWDWBSalesFunnelDetail.subject_name.contains(
                    subject_name,
                    autoescape=True,
                )
            )
        if brand_name:
            statement = statement.where(
                DWDWBSalesFunnelDetail.brand_name.contains(
                    brand_name,
                    autoescape=True,
                )
            )
        return statement

    async def list_details(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        page: int,
        page_size: int,
        date_from: date | None = None,
        date_to: date | None = None,
        nm_id: int | None = None,
        vendor_code: str | None = None,
        title: str | None = None,
        subject_name: str | None = None,
        brand_name: str | None = None,
    ) -> tuple[list[DWDWBSalesFunnelDetail], int]:
        """返回一页 DWD 销售漏斗明细及总记录数。"""
        filters = {
            "shop_id": shop_id,
            "date_from": date_from,
            "date_to": date_to,
            "nm_id": nm_id,
            "vendor_code": vendor_code,
            "title": title,
            "subject_name": subject_name,
            "brand_name": brand_name,
        }
        count_statement = self._apply_detail_filters(
            select(func.count()).select_from(DWDWBSalesFunnelDetail),
            **filters,
        )
        total = int((await db.execute(count_statement)).scalar_one())

        statement = self._apply_detail_filters(
            select(DWDWBSalesFunnelDetail),
            **filters,
        )
        statement = (
            statement.order_by(
                DWDWBSalesFunnelDetail.date_from.desc(),
                DWDWBSalesFunnelDetail.date_to.desc(),
                DWDWBSalesFunnelDetail.nm_id.asc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(statement)
        return list(result.scalars().all()), total

    async def list_details_for_export(
        self,
        db: AsyncSession,
        *,
        shop_id: int,
        date_from: date | None = None,
        date_to: date | None = None,
        nm_id: int | None = None,
        vendor_code: str | None = None,
        title: str | None = None,
        subject_name: str | None = None,
        brand_name: str | None = None,
    ) -> list[DWDWBSalesFunnelDetail]:
        """导出符合筛选条件的全部 DWD 销售漏斗明细。"""
        statement = self._apply_detail_filters(
            select(DWDWBSalesFunnelDetail),
            shop_id=shop_id,
            date_from=date_from,
            date_to=date_to,
            nm_id=nm_id,
            vendor_code=vendor_code,
            title=title,
            subject_name=subject_name,
            brand_name=brand_name,
        ).order_by(
            DWDWBSalesFunnelDetail.date_from.desc(),
            DWDWBSalesFunnelDetail.date_to.desc(),
            DWDWBSalesFunnelDetail.nm_id.asc(),
        )
        result = await db.execute(statement)
        return list(result.scalars().all())


crud_dwd_wb_sales_funnel_detail = CRUDDWDWBSalesFunnelDetail()
