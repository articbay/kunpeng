"""Build the Wildberries customer-voice workbook from a native PivotTable template."""

from __future__ import annotations

import json
import re
import zipfile
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Any, Mapping, Sequence
from xml.sax.saxutils import escape

DATA_COLUMNS: tuple[tuple[str, str], ...] = (
    ("日期", "business_date"),
    ("发生时间（莫斯科）", "event_date"),
    ("下单日期", "order_date"),
    ("记录类型", "record_type"),
    ("店铺ID", "shop_id"),
    ("业务ID", "record_id"),
    ("卖家货号", "supplier_article"),
    ("WB货号", "nm_id"),
    ("星级数量", "rating"),
    ("品牌", "brand_name"),
    ("评价文本", "feedback_text"),
    ("评价文本（中文）", "feedback_text_cn"),
    ("优点", "pros"),
    ("优点（中文）", "pros_cn"),
    ("缺点", "cons"),
    ("缺点（中文）", "cons_cn"),
    ("用户姓名", "user_name"),
    ("颜色", "color"),
    ("颜色（中文）", "color_cn"),
    ("尺码", "size"),
    ("尺码（中文）", "size_cn"),
    ("问题文本", "question_text"),
    ("问题文本（中文）", "question_text_cn"),
    ("回复状态", "answer_status"),
    ("商家回复", "answer"),
    ("商家回复（中文）", "answer_cn"),
    ("退货原因", "reason"),
    ("退货原因（中文）", "reason_cn"),
    ("原因V1", "reason_category"),
    ("状态", "status"),
    ("状态（中文）", "status_cn"),
    ("退货类型", "return_type"),
    ("退货类型（中文）", "return_type_cn"),
    ("配货单号", "order_id"),
    ("系统订单号", "srid"),
    ("初始评价ID", "parent_feedback_id"),
    ("追加评价ID", "child_feedback_id"),
    ("数量", "quantity"),
)

TEMPLATE_TABLE_NAME = "CustomerVoiceData"
_LAST_COLUMN = "AL"
_DATA_SHEET_PART = "xl/worksheets/sheet1.xml"
_TABLE_PART = "xl/tables/table1.xml"
_PIVOT_CACHE_DEFINITION_PART = "xl/pivotCache/pivotCacheDefinition1.xml"
_TEMPLATE_PATH = (
    Path(__file__).resolve().parent.parent
    / "templates"
    / "wb_customer_voice_native_pivot.xlsx"
)


def build_customer_voice_workbook(rows: Sequence[Mapping[str, Any]]) -> bytes:
    """Fill the template's data table while preserving its native PivotTables."""
    if not _TEMPLATE_PATH.is_file():
        raise RuntimeError(f"客户声音原生透视表模板不存在: {_TEMPLATE_PATH}")

    last_row = len(rows) + 1
    table_ref = f"A1:{_LAST_COLUMN}{last_row}"
    output = BytesIO()

    with zipfile.ZipFile(_TEMPLATE_PATH, "r") as template, zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED
    ) as workbook:
        for entry in template.infolist():
            payload = template.read(entry.filename)
            if entry.filename == _DATA_SHEET_PART:
                payload = _rewrite_data_sheet(payload, rows, table_ref)
            elif entry.filename == _TABLE_PART:
                payload = _rewrite_table(payload, table_ref)
            elif entry.filename == _PIVOT_CACHE_DEFINITION_PART:
                payload = _enable_refresh_on_load(payload)
            workbook.writestr(entry, payload)

    return output.getvalue()


def _rewrite_data_sheet(
    payload: bytes, rows: Sequence[Mapping[str, Any]], table_ref: str
) -> bytes:
    xml = payload.decode("utf-8")
    headers = [label for label, _ in DATA_COLUMNS]
    sheet_rows = [_row_xml(1, headers, style_id=2)]
    sheet_rows.extend(
        _row_xml(
            row_number,
            [row.get(field) for _, field in DATA_COLUMNS],
            style_id=3,
        )
        for row_number, row in enumerate(rows, start=2)
    )
    replacement = f"<sheetData>{''.join(sheet_rows)}</sheetData>"

    xml, dimension_count = re.subn(
        r'<dimension\s+ref="[^"]+"\s*/>',
        f'<dimension ref="{table_ref}"/>',
        xml,
        count=1,
    )
    xml, sheet_data_count = re.subn(
        r"<sheetData>.*?</sheetData>", replacement, xml, count=1, flags=re.DOTALL
    )
    if dimension_count != 1 or sheet_data_count != 1:
        raise RuntimeError("客户声音模板的数据工作表结构不符合预期")
    return xml.encode("utf-8")


def _rewrite_table(payload: bytes, table_ref: str) -> bytes:
    xml = payload.decode("utf-8")
    xml, table_count = re.subn(
        r'(<table\b[^>]*\bref=")[^"]+("[^>]*>)',
        rf"\g<1>{table_ref}\g<2>",
        xml,
        count=1,
    )
    xml, filter_count = re.subn(
        r'(<autoFilter\b[^>]*\bref=")[^"]+("[^>]*>)',
        rf"\g<1>{table_ref}\g<2>",
        xml,
        count=1,
    )
    if table_count != 1 or filter_count != 1:
        raise RuntimeError("客户声音模板的数据表结构不符合预期")
    return xml.encode("utf-8")


def _enable_refresh_on_load(payload: bytes) -> bytes:
    xml = payload.decode("utf-8")
    if re.search(r"\brefreshOnLoad=", xml):
        xml = re.sub(r'refreshOnLoad="[^"]*"', 'refreshOnLoad="1"', xml, count=1)
    else:
        xml = xml.replace(
            "<pivotCacheDefinition ",
            '<pivotCacheDefinition refreshOnLoad="1" ',
            1,
        )
    return xml.encode("utf-8")


def _row_xml(row_index: int, values: Sequence[Any], *, style_id: int) -> str:
    cells = [
        _cell_xml(_cell_ref(column_index, row_index), value, style_id)
        for column_index, value in enumerate(values, start=1)
    ]
    return f'<row r="{row_index}" spans="1:{len(DATA_COLUMNS)}">{"".join(cells)}</row>'


def _cell_xml(cell_ref: str, value: Any, style_id: int) -> str:
    style_attr = f' s="{style_id}"'
    if value is None:
        return f'<c r="{cell_ref}"{style_attr}/>'
    if _is_number(value):
        return f'<c r="{cell_ref}"{style_attr}><v>{_number_text(value)}</v></c>'
    text = _escape_text(_string_text(value))
    return (
        f'<c r="{cell_ref}" t="inlineStr"{style_attr}>'
        f'<is><t xml:space="preserve">{text}</t></is></c>'
    )


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)


def _number_text(value: int | float | Decimal) -> str:
    return format(value, "f") if isinstance(value, Decimal) else str(value)


def _string_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    if isinstance(value, bool):
        return "是" if value else "否"
    return str(value)


def _escape_text(value: str) -> str:
    cleaned = "".join(char for char in value if char in "\t\n\r" or ord(char) >= 32)
    return escape(cleaned[:32767])


def _cell_ref(column_index: int, row_index: int) -> str:
    return f"{_column_name(column_index)}{row_index}"


def _column_name(column_index: int) -> str:
    name = ""
    while column_index:
        column_index, remainder = divmod(column_index - 1, 26)
        name = chr(65 + remainder) + name
    return name
