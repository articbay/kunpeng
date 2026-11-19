import request from '@/api/request'

export type OzonSalesFunnelExportScope = 'filtered' | 'selected'
export type OzonSalesFunnelMetric = number | string | null

export interface OzonSalesFunnel {
  id: number
  source_ods_id: number
  shop_id: number
  offer_id: string | null
  sku: number
  product_name: string | null
  product_name_cn: string | null
  category_name: string | null
  category_name_cn: string | null
  stat_date: string
  hits_view_search: number | null
  hits_view_pdp: number | null
  hits_view: number | null
  session_view_search: number | null
  session_view_pdp: number | null
  session_view: number | null
  hits_tocart_search: number | null
  hits_tocart_pdp: number | null
  hits_tocart: number | null
  conv_tocart_search: OzonSalesFunnelMetric
  conv_tocart_pdp: OzonSalesFunnelMetric
  conv_tocart: OzonSalesFunnelMetric
  ordered_units: number | null
  revenue: OzonSalesFunnelMetric
  delivered_units: number | null
  cancellations: number | null
  returns: number | null
  position_category: OzonSalesFunnelMetric
  cart_to_order_rate: OzonSalesFunnelMetric
  has_core_metrics: boolean
  has_outcome_metrics: boolean
  source_synced_at: string | null
  create_time: string
  update_time: string | null
}

export interface OzonSalesFunnelFilters {
  shop_id?: number
  date_from?: string
  date_to?: string
  sku?: number
  offer_id?: string
  keyword?: string
  sort_order?: 'asc' | 'desc'
}

export interface OzonSalesFunnelQuery extends OzonSalesFunnelFilters {
  page: number
  page_size: number
}

export interface OzonSalesFunnelPageResponse {
  items: OzonSalesFunnel[]
  total: number
  page: number
  page_size: number
}

export interface OzonSalesFunnelKey {
  shop_id: number
  stat_date: string
  sku: number
}

function params(query: OzonSalesFunnelQuery): URLSearchParams {
  const result = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') result.set(key, String(value))
  })
  return result
}

export const ozonSalesFunnelApi = {
  list(query: OzonSalesFunnelQuery): Promise<OzonSalesFunnelPageResponse> {
    return request.get('/api/v1/ozon/sales-funnel', { params: params(query) })
  },
  export(data: {
    scope: OzonSalesFunnelExportScope
    filters?: OzonSalesFunnelFilters
    selected_keys?: OzonSalesFunnelKey[]
  }): Promise<Blob> {
    return request.post('/api/v1/ozon/sales-funnel/export', data, {
      responseType: 'blob',
      timeout: 120000
    })
  }
}
