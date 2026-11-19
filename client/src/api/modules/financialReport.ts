import request from '@/api/request'

export interface FinancialReportDetail {
  id: number
  shop_id: number
  date_from: string
  rrd_id: number
  nm_id?: number
  vendor_code?: string
  title?: string
  subject_name?: string
  sku?: string
  tech_size?: string
  doc_type_name?: string
  seller_oper_name?: string
  quantity?: number
  retail_amount?: string
  commission_percent?: string
  ppvz_sales_commission?: string
  acquiring_fee?: string
  delivery_service?: string
  paid_storage?: string
  penalty?: string
  deduction?: string
  for_pay?: string
}

export interface FinancialReportQuery {
  shop_id: number
  date_from?: string
  date_to?: string
  nm_id?: number
  vendor_code?: string
  rrd_id?: number
  order_id?: number
  seller_oper_name?: string
  doc_type_name?: string
  brand_name?: string
  page: number
  page_size: number
}

export type FinancialReportExportQuery = Omit<FinancialReportQuery, 'page' | 'page_size'>

export interface FinancialReportPage {
  items: FinancialReportDetail[]
  total: number
  page: number
  page_size: number
}

export const financialReportApi = {
  list(params: FinancialReportQuery): Promise<FinancialReportPage> {
    return request.get('/api/v1/wildberries/financial-report-details', { params })
  },

  export(params: FinancialReportExportQuery): Promise<Blob> {
    return request.get<never, Blob>(
      '/api/v1/wildberries/financial-report-details/export',
      {
        params,
        responseType: 'blob'
      }
    )
  }
}
