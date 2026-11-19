"""统一WB订单状态中文词典

Revision ID: 4b7f2d91a6c3
Revises: 86a5e58bca0a
Create Date: 2026-09-02 18:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "4b7f2d91a6c3"
down_revision = "86a5e58bca0a"
branch_labels = None
depends_on = None

TABLES = (
    "dwd_wb_order_detail",
    "dwm_wb_order_lifecycle_detail",
)

WB_STATUS_CN = {
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

SUPPLIER_STATUS_CN = {
    "new": "新订单",
    "confirm": "组装中",
    "complete": "配送中",
    "deliver": "配送中",
    "receive": "买家已收货",
    "reject": "买家拒收",
    "cancel": "卖家取消",
    "cancel_missed_call": "未联系到买家而取消",
}


def _normalized_status_update_sql(
    table: str,
    source_column: str,
    target_column: str,
    translations: dict[str, str],
) -> sa.TextClause:
    cases = "\n".join(
        f"WHEN '{status}' THEN '{translation}'"
        for status, translation in translations.items()
    )
    statuses = ", ".join(f"'{status}'" for status in translations)
    return sa.text(
        f"""
        UPDATE {table}
        SET {target_column} = CASE LOWER(TRIM({source_column}))
            {cases}
            ELSE {target_column}
        END
        WHERE LOWER(TRIM({source_column})) IN ({statuses})
        """
    )


def upgrade() -> None:
    for table in TABLES:
        op.execute(
            _normalized_status_update_sql(
                table,
                "wb_status",
                "wb_status_cn",
                WB_STATUS_CN,
            )
        )
        op.execute(
            _normalized_status_update_sql(
                table,
                "supplier_status",
                "supplier_status_cn",
                SUPPLIER_STATUS_CN,
            )
        )


def downgrade() -> None:
    # Historical translations cannot be reconstructed after normalization.
    pass
