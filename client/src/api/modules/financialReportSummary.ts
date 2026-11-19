import request from '@/api/request'

export interface FinancialReportSummary {
  id: number
  shop_id: number
  report_id: number
  seller_finance_name?: string
  date_from: string
  date_to: string
  create_date?: string
  report_type?: number
  retail_amount_sum?: string
  cashback_discount_sum?: string
  for_pay_sum?: string
  avg_sale_percent?: string
  delivery_service_sum?: string
  paid_storage_sum?: string
  paid_acceptance_sum?: string
  deduction_sum?: string
  penalty_sum?: string
  additional_payment_sum?: string
  cashback_commission_change_sum?: string
  cashback_amount_sum?: string
  payment_schedule?: string
  bank_payment_sum?: string
  currency?: string
  create_time: string
  update_time?: string
}

export interface FinancialReportSummaryQuery {
  shop_id: number
  date_from?: string
  date_to?: string
  create_date_from?: string
  create_date_to?: string
  report_id?: number
  seller_finance_name?: string
  report_type?: number
  currency?: string
  page: number
  page_size: number
}

export type FinancialReportSummaryExportQuery = Omit<
  FinancialReportSummaryQuery,
  'page' | 'page_size'
>

export interface FinancialReportSummaryPage {
  items: FinancialReportSummary[]
  total: number
  page: number
  page_size: number
}

export const financialReportSummaryApi = {
  list(params: FinancialReportSummaryQuery): Promise<FinancialReportSummaryPage> {
    return request.get('/api/v1/wildberries/financial-report-summaries', { params })
  },

  export(params: FinancialReportSummaryExportQuery): Promise<Blob> {
    return request.get<never, Blob>(
      '/api/v1/wildberries/financial-report-summaries/export',
      {
        params,
        responseType: 'blob'
      }
    )
  }
}
