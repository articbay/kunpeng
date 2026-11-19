from kunpeng.crud.dwm.ozon.refresh_scope import CRUDDWMOzonRefreshScope


def test_recent_return_scope_uses_ods_update_time_and_dwd_order_date() -> None:
    sql = CRUDDWMOzonRefreshScope._recent_return_order_dates_statement.text.upper()

    assert "INNER JOIN ODS_OZON_RETURNS" in sql
    assert "ODS.UPDATE_TIME >= :UPDATED_SINCE" in sql
    assert "DATE(RET.ORDER_DATE)" in sql
    assert "SELECT DISTINCT" in sql
