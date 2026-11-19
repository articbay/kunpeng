from __future__ import annotations

import json
import zipfile
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from typing import Any, Iterable, Optional, Sequence
from xml.sax.saxutils import escape

from sqlalchemy.ext.asyncio import AsyncSession

from kunpeng.crud import crud_ods_wb_sales_funnel
from kunpeng.schemas.wildberries import WBSalesFunnelListItem

SALES_FUNNEL_COLUMNS: tuple[tuple[str, str], ...] = (
    ("卖家商品编号", "vendor_code"),
    ("WB 商品编号", "nm_id"),
    ("名称", "subject_name"),
    ("品牌", "brand_name"),
    ("商品标签", "tags"),
    ("商品详情页评分", "product_rating"),
    ("评论评分", "feedback_rating"),
    ("商品点击", "open_count"),
    ("商品加购", "cart_count"),
    ("加入“收藏夹”", "add_to_wishlist"),
)


class WBSalesFunnelService:
    async def list_sales_funnels(
        self,
        db: AsyncSession,
        *,
        shop_id: Optional[int] = None,
        allowed_shop_ids: Optional[Sequence[int]] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        nm_id: Optional[int] = None,
        vendor_code: Optional[str] = None,
        brand_name: Optional[str] = None,
        subject_name: Optional[str] = None,
    ) -> list[WBSalesFunnelListItem]:
        records = await crud_ods_wb_sales_funnel.list_sales_funnels(
            db,
            shop_id=shop_id,
            allowed_shop_ids=allowed_shop_ids,
            date_from=date_from,
            date_to=date_to,
            nm_id=nm_id,
            vendor_code=vendor_code,
            brand_name=brand_name,
            subject_name=subject_name,
        )
        return [WBSalesFunnelListItem.model_validate(record) for record in records]

    async def export_sales_funnels(
        self,
        db: AsyncSession,
        *,
        shop_id: Optional[int] = None,
        allowed_shop_ids: Optional[Sequence[int]] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        nm_id: Optional[int] = None,
        vendor_code: Optional[str] = None,
        brand_name: Optional[str] = None,
        subject_name: Optional[str] = None,
    ) -> bytes:
        items = await self.list_sales_funnels(
            db,
            shop_id=shop_id,
            allowed_shop_ids=allowed_shop_ids,
            date_from=date_from,
            date_to=date_to,
            nm_id=nm_id,
            vendor_code=vendor_code,
            brand_name=brand_name,
            subject_name=subject_name,
        )
        rows = [item.model_dump(mode="python") for item in items]
        return build_xlsx(SALES_FUNNEL_COLUMNS, rows)


def build_xlsx(
    columns: Sequence[tuple[str, str]],
    rows: Sequence[dict[str, Any]],
    *,
    sheet_name: str = "sales_funnels",
) -> bytes:
    output = BytesIO()
    sheet_xml = _build_sheet_xml(columns, rows)

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml())
        archive.writestr("_rels/.rels", _root_relationships_xml())
        archive.writestr("xl/workbook.xml", _workbook_xml(sheet_name))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_relationships_xml())
        archive.writestr("xl/styles.xml", _styles_xml())
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)

    return output.getvalue()


def _build_sheet_xml(
    columns: Sequence[tuple[str, str]], rows: Sequence[dict[str, Any]]
) -> str:
    header_values = [label for label, _ in columns]
    body_values = [[row.get(field) for _, field in columns] for row in rows]
    row_count = max(len(body_values) + 1, 1)
    col_count = max(len(columns), 1)
    dimension = f"A1:{_column_name(col_count)}{row_count}"

    sheet_rows = [_row_xml(1, header_values, style_id=1)]
    sheet_rows.extend(
        _row_xml(row_index, values)
        for row_index, values in enumerate(body_values, start=2)
    )

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="{dimension}"/>'
        '<sheetViews><sheetView workbookViewId="0">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        '<selection pane="bottomLeft" activeCell="A2" sqref="A2"/>'
        "</sheetView></sheetViews>"
        f"{_cols_xml(columns, rows)}"
        f"<sheetData>{''.join(sheet_rows)}</sheetData>"
        "</worksheet>"
    )


def _row_xml(
    row_index: int, values: Iterable[Any], style_id: Optional[int] = None
) -> str:
    cells = [
        _cell_xml(_cell_ref(column_index, row_index), value, style_id)
        for column_index, value in enumerate(values, start=1)
    ]
    return f'<row r="{row_index}">{"".join(cells)}</row>'


def _cell_xml(cell_ref: str, value: Any, style_id: Optional[int]) -> str:
    style_attr = f' s="{style_id}"' if style_id is not None else ""
    if value is None:
        return f'<c r="{cell_ref}"{style_attr}/>'

    if _is_number(value):
        return f'<c r="{cell_ref}"{style_attr}><v>{_number_text(value)}</v></c>'

    text = _string_text(value)
    return (
        f'<c r="{cell_ref}" t="inlineStr"{style_attr}>'
        f"<is><t>{_escape_text(text)}</t></is>"
        "</c>"
    )


def _cols_xml(
    columns: Sequence[tuple[str, str]], rows: Sequence[dict[str, Any]]
) -> str:
    col_xml = []
    for column_index, (label, field) in enumerate(columns, start=1):
        width = min(
            max(_display_len(label), _max_column_display_len(rows, field)) + 2,
            40,
        )
        col_xml.append(
            f'<col min="{column_index}" max="{column_index}" '
            f'width="{width}" customWidth="1"/>'
        )
    return f"<cols>{''.join(col_xml)}</cols>"


def _max_column_display_len(rows: Sequence[dict[str, Any]], field: str) -> int:
    if not rows:
        return 0
    return max(_display_len(_string_text(row.get(field))) for row in rows)


def _display_len(value: str) -> int:
    return sum(2 if ord(char) > 127 else 1 for char in value)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)


def _number_text(value: int | float | Decimal) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def _string_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _escape_text(value: str) -> str:
    cleaned = "".join(char for char in value if char in "\t\n\r" or ord(char) >= 32)
    return escape(cleaned)


def _cell_ref(column_index: int, row_index: int) -> str:
    return f"{_column_name(column_index)}{row_index}"


def _column_name(column_index: int) -> str:
    name = ""
    while column_index:
        column_index, remainder = divmod(column_index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _content_types_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.'
        'spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.'
        'spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.'
        'spreadsheetml.styles+xml"/>'
        "</Types>"
    )


def _root_relationships_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
        'relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )


def _workbook_xml(sheet_name: str) -> str:
    safe_sheet_name = escape(sheet_name[:31] or "Sheet1", {'"': "&quot;"})
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{safe_sheet_name}" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )


def _workbook_relationships_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
        'relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/styles" '
        'Target="styles.xml"/>'
        "</Relationships>"
    )


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2">'
        '<font><sz val="11"/><color theme="1"/><name val="Calibri"/>'
        '<family val="2"/></font>'
        '<font><b/><sz val="11"/><color theme="1"/><name val="Calibri"/>'
        '<family val="2"/></font>'
        "</fonts>"
        '<fills count="2"><fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/>'
        "</border></borders>"
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" '
        'borderId="0"/></cellStyleXfs>'
        '<cellXfs count="2">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
        "</cellXfs>"
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" '
        'builtinId="0"/></cellStyles>'
        "</styleSheet>"
    )
