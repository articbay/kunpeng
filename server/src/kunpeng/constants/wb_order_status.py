"""Canonical Chinese terminology for Wildberries order statuses."""

WB_ORDER_STATUS_CN: dict[str, str] = {
    "waiting": "待WB接收",
    "sorted": "WB已接收并分拣",
    "sold": "买家已收货",
    "ready_for_pickup": "已到取货点",
    "postponed_delivery": "配送延期",
    "accepted_by_carrier": "承运商已接收",
    "sent_to_carrier": "已发往承运商仓库",
    "canceled": "订单已取消",
    "canceled_by_client": "买家收货时取消",
    "declined_by_client": "买家早期取消",
    "defect": "因商品缺陷取消",
    "canceled_by_missed_call": "未联系到买家而取消",
}

WB_SUPPLIER_STATUS_CN: dict[str, str] = {
    "new": "新订单",
    "confirm": "组装中",
    "complete": "配送中",
    "deliver": "配送中",
    "receive": "买家已收货",
    "reject": "买家拒收",
    "cancel": "卖家取消",
    "cancel_missed_call": "未联系到买家而取消",
}
