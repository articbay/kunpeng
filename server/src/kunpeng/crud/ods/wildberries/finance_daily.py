"""Wildberries 按日财务明细 CRUD。"""

from kunpeng.crud.ods.wildberries.finance import CRUDODSWBSalesReport
from kunpeng.models.ods.wildberries.finance_daily import ODSWBSalesReportDaily

crud_ods_wb_sales_report_daily = CRUDODSWBSalesReport(ODSWBSalesReportDaily)
