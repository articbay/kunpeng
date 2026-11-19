from kunpeng.crud.dwd.ozon.customer_voice import (
    CRUDDWDOzonCustomerVoiceDetail,
)
from kunpeng.services.ozon_customer_voice_service import (
    OZON_CUSTOMER_VOICE_EXPORT_COLUMNS,
)


def test_customer_voice_export_places_shop_name_after_shop_id():
    assert OZON_CUSTOMER_VOICE_EXPORT_COLUMNS[:2] == (
        ("店铺ID", "shop_id"),
        ("店铺名称", "shop_name"),
    )


def test_customer_voice_upsert_qualifies_target_translation_sources():
    sql = str(CRUDDWDOzonCustomerVoiceDetail._upsert_statement)

    for field in (
        "product_name",
        "product_name_cn",
        "order_status",
        "order_status_cn",
        "review_text",
        "review_text_cn",
        "review_status",
        "review_status_cn",
    ):
        assert f"dwd_ozon_customer_voice_detail.{field}" in sql
