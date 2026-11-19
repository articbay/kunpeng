from datetime import datetime
from decimal import Decimal

from kunpeng.crud.ods.ozon.posting_reports import CRUDOzonPostingReportRow
from kunpeng.models.ods.ozon.posting_reports import (
    ODSOzonPostingReportRow,
    ODSOzonPostingReportTask,
)


def test_posting_report_models_keep_task_and_product_keys():
    task_columns = ODSOzonPostingReportTask.__table__.columns
    row_columns = ODSOzonPostingReportRow.__table__.columns

    assert "report_code" in task_columns
    assert "response_data" in task_columns
    assert "delivery_fee" in row_columns
    assert "cancellation_at" in row_columns
    assert "product_size" in row_columns
    assert "actual_tariffication" in row_columns


def test_parse_fbs_posting_report_csv_maps_report_only_fields():
    content = (
        "\ufeffНомер заказа;Номер отправления;Принят в обработку;Дата отмены;"
        "Название товара;Цвет товара;Размер товара;SKU;Артикул;"
        "Стоимость доставки;Выкуп товара;Скидка %;Фактическая тарификация\n"
        "order-1;posting-1;24.08.2026 10:30:00;24.08.2026 12:00:00;"
        "Товар;Красный;XL;123456;offer-1;1 234,56;Да;10,5%;Тариф A\n"
    ).encode("utf-8")

    rows = CRUDOzonPostingReportRow().parse_csv(content)

    assert len(rows) == 1
    row = rows[0]
    assert row["posting_number"] == "posting-1"
    assert row["sku"] == 123456
    assert row["in_process_at"] == datetime(2026, 8, 24, 10, 30)
    assert row["cancellation_at"] == datetime(2026, 8, 24, 12, 0)
    assert row["product_size"] == "XL"
    assert row["delivery_fee"] == Decimal("1234.56")
    assert row["discount_percent"] == Decimal("10.5")
    assert row["is_marketplace_buyout"] is True
    assert row["actual_tariffication"] == "Тариф A"


def test_parse_fbo_posting_report_csv_maps_volume_weight():
    content = (
        "Номер отправления;SKU;Доупаковка;Пломбирование;"
        "Объемный вес товаров, кг\n"
        "posting-2;987654;12,50;нет;0,7500\n"
    ).encode("utf-8")

    row = CRUDOzonPostingReportRow().parse_csv(content)[0]

    assert row["additional_packaging"] == Decimal("12.50")
    assert row["sealing"] is None
    assert row["product_volume_weight"] == Decimal("0.7500")


def test_parse_posting_report_treats_epoch_placeholder_as_missing():
    content = (
        "Номер отправления;SKU;Фактическая дата передачи в доставку\n"
        "posting-3;123456;01.01.1970 00:00:00\n"
    ).encode("utf-8")

    row = CRUDOzonPostingReportRow().parse_csv(content)[0]

    assert row["transferred_to_delivery_at"] is None
