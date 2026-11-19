"""Business translations for Ozon return statuses."""

from typing import Optional

OZON_RETURN_STATUS_CN_BY_SYS_NAME: dict[str, str] = {
    "MovingToOzon": "运输中，发往Ozon仓库",
    "MovingToWarehouse": "运输中，发往仓库",
    "MovingToSeller": "运输中，发往卖家",
    "ReturnedToOzon": "已在Ozon仓库",
    "WaitingShipment": "待发运",
}

OZON_RETURN_STATUS_CN_BY_DISPLAY_NAME: dict[str, str] = {
    "В пункте выдачи": "已到取货点",
    "Деньги возвращены": "已退款",
    "Едет к вам": "运输中，发往卖家",
    "Едет на склад Ozon": "运输中，发往Ozon仓库",
    "Ищем товар": "正在查找商品",
    "На складе": "已在仓库",
    "На складе Ozon": "已在Ozon仓库",
    "На утилизации": "处置中",
    "Ожидает отправки": "待发运",
    "Отменена покупателем": "买家已取消",
    "Получен": "已收货",
    "Списали товар": "商品已核销",
    "Утилизирован": "已处置",
}


def resolve_ozon_return_status_cn(
    *,
    status_sys_name: Optional[str],
    status_display_name: Optional[str],
    stored_translation: Optional[str],
) -> Optional[str]:
    """Return the reviewed business translation, preserving unknown translations."""
    normalized_sys_name = (status_sys_name or "").strip()
    if normalized_sys_name in OZON_RETURN_STATUS_CN_BY_SYS_NAME:
        return OZON_RETURN_STATUS_CN_BY_SYS_NAME[normalized_sys_name]

    normalized_display_name = (status_display_name or "").strip()
    if normalized_display_name in OZON_RETURN_STATUS_CN_BY_DISPLAY_NAME:
        return OZON_RETURN_STATUS_CN_BY_DISPLAY_NAME[normalized_display_name]

    return stored_translation
