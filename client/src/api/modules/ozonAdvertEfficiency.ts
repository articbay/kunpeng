import request from '@/api/request'

export type OzonAdvertEfficiencyExportScope = 'filtered' | 'selected'
export type OzonAdvertMetric = number | string | null

export interface OzonAdvertEfficiency {
  shop_id: number
  stat_date: string
  sku: number
  product_name: string | null
  product_name_cn: string | null
  category_name: string | null
  category_name_cn: string | null
  payment_type: string | null
  placement: string | null
  campaign_id: string
  campaign_name: string | null
  money_spent: OzonAdvertMetric
  drr: OzonAdvertMetric
  orders_money: OzonAdvertMetric
  orders: number | null
  ctr: OzonAdvertMetric
  views: number | null
  clicks: number | null
  to_cart: number | null
  to_cart_conversion_rate: OzonAdvertMetric
  cost_per_order: OzonAdvertMetric
  cost_per_click: OzonAdvertMetric
}

export interface OzonAdvertEfficiencyFilters {
  shop_id?: number
  date_from?: string
  date_to?: string
  sku?: number
  campaign_id?: string
  keyword?: string
  sort_order?: 'asc' | 'desc'
}

export interface OzonAdvertEfficiencyQuery extends OzonAdvertEfficiencyFilters {
  page: number
  page_size: number
}

export interface OzonAdvertEfficiencyPageResponse {
  items: OzonAdvertEfficiency[]
  total: number
  page: number
  page_size: number
}

export interface OzonAdvertEfficiencyKey {
  shop_id: number
  stat_date: string
  sku: number
  campaign_id: string
}

function params(query: OzonAdvertEfficiencyQuery): URLSearchParams {
  const result = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') result.set(key, String(value))
  })
  return result
}

export const ozonAdvertEfficiencyApi = {
  list(query: OzonAdvertEfficiencyQuery): Promise<OzonAdvertEfficiencyPageResponse> {
    return request.get('/api/v1/ozon/advert-efficiency', { params: params(query) })
  },
  export(data: {
    scope: OzonAdvertEfficiencyExportScope
    filters?: OzonAdvertEfficiencyFilters
    selected_keys?: OzonAdvertEfficiencyKey[]
  }): Promise<Blob> {
    return request.post('/api/v1/ozon/advert-efficiency/export', data, {
      responseType: 'blob',
      timeout: 120000
    })
  }
}
