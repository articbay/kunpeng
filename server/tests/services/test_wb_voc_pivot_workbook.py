from datetime import date, datetime
from io import BytesIO
from xml.etree import ElementTree
from zipfile import ZipFile

from kunpeng.services.wb_voc_pivot_workbook import \
    build_customer_voice_workbook

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS = {"m": MAIN_NS}


def _sample_rows():
    return [
        {
            "record_type": "feedback",
            "record_id": "feedback-1",
            "business_date": date(2026, 7, 21),
            "event_date": datetime(2026, 7, 21, 11, 0),
            "shop_id": 8,
            "supplier_article": "article-1",
            "nm_id": 419767432,
            "rating": 5,
            "feedback_text": "Очень хорошо",
            "feedback_text_cn": "非常好",
            "quantity": 1,
        },
        {
            "record_type": "question",
            "record_id": "question-1",
            "business_date": date(2026, 7, 21),
            "shop_id": 8,
            "nm_id": 419767432,
            "question_text": "Размер?",
            "question_text_cn": "尺码？",
            "answer_status": "未回复",
            "quantity": 1,
        },
        {
            "record_type": "return",
            "record_id": "return-1",
            "business_date": date(2026, 7, 21),
            "order_date": date(2026, 7, 20),
            "shop_id": 8,
            "nm_id": 419767432,
            "reason": "Клиент отказался от товара",
            "reason_cn": "买家拒收",
            "reason_category": "买家拒收",
            "status": "Выдано",
            "status_cn": "已领取",
            "quantity": 1,
        },
    ]


def _cell_values(sheet_xml: bytes) -> dict[str, str]:
    root = ElementTree.fromstring(sheet_xml)
    values: dict[str, str] = {}
    for cell in root.findall(".//m:sheetData/m:row/m:c", NS):
        ref = cell.attrib["r"]
        if cell.attrib.get("t") == "inlineStr":
            text = cell.find("m:is/m:t", NS)
            values[ref] = "" if text is None or text.text is None else text.text
        else:
            value = cell.find("m:v", NS)
            values[ref] = "" if value is None or value.text is None else value.text
    return values


def test_customer_voice_workbook_preserves_native_pivots_and_updates_data_table():
    content = build_customer_voice_workbook(_sample_rows())

    assert content.startswith(b"PK")
    with ZipFile(BytesIO(content)) as workbook:
        names = workbook.namelist()
        workbook_xml = workbook.read("xl/workbook.xml")
        data_xml = workbook.read("xl/worksheets/sheet1.xml")
        table_xml = ElementTree.fromstring(workbook.read("xl/tables/table1.xml"))
        cache_xml = ElementTree.fromstring(
            workbook.read("xl/pivotCache/pivotCacheDefinition1.xml")
        )
        for name in names:
            if name.endswith(".xml"):
                ElementTree.fromstring(workbook.read(name))

    assert workbook_xml.count(b"<sheet ") == 2
    assert "客户声音-data".encode() in workbook_xml
    assert "客户声音-PIVOT".encode() in workbook_xml
    assert sum(name.startswith("xl/pivotTables/pivotTable") for name in names) == 4
    assert table_xml.attrib["name"] == "CustomerVoiceData"
    assert table_xml.attrib["ref"] == "A1:AL4"
    assert table_xml.find("m:autoFilter", NS).attrib["ref"] == "A1:AL4"
    assert cache_xml.attrib["refreshOnLoad"] == "1"
    worksheet_source = cache_xml.find("m:cacheSource/m:worksheetSource", NS)
    assert worksheet_source is not None
    assert worksheet_source.attrib["name"] == "CustomerVoiceData"

    values = _cell_values(data_xml)
    assert values["A1"] == "日期"
    assert values["D1"] == "记录类型"
    assert values["AL1"] == "数量"
    assert values["A2"] == "2026-07-21"
    assert values["B2"] == "2026-07-21 11:00:00"
    assert values["D2"] == "feedback"
    assert values["F3"] == "question-1"
    assert values["AA4"] == "Клиент отказался от товара"
    assert values["AE4"] == "已领取"


def test_customer_voice_workbook_supports_an_empty_data_table():
    content = build_customer_voice_workbook([])

    with ZipFile(BytesIO(content)) as workbook:
        table_xml = ElementTree.fromstring(workbook.read("xl/tables/table1.xml"))
        data_xml = workbook.read("xl/worksheets/sheet1.xml")

    assert table_xml.attrib["ref"] == "A1:AL1"
    values = _cell_values(data_xml)
    assert values["A1"] == "日期"
    assert values["AL1"] == "数量"
    assert "A2" not in values
