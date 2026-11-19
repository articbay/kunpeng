import request from '@/api/request'

export type OzonReturnSortOrder = 'asc' | 'desc'
export type OzonReturnExportScope = 'filtered' | 'selected'

export interface OzonReturn {
  shop_id: number
  return_id: number
  nm_id: number
  schema: string | null
  product_name: string | null
  product_name_cn: string | null
  posting_number: string | null
  offer_id: string | null
  order_date: string | null
  return_date: string | null
  status_id: number | null
  status_display_name: string | null
  status_display_name_cn: string | null
  status_sys_name: string | null
  status_change_at: string | null
  compensation_status_id: number | null
  compensation_status_display_name: string | null
  compensation_status_display_name_cn: string | null
  compensation_status_sys_name: string | null
  compensation_status_change_at: string | null
  return_reason_name: string | null
  return_reason_name_cn: string | null
  buyer_comment: string | null
  buyer_comment_cn: string | null
  quantity: number | null
  is_opened: boolean | null
  target_place_name: string | null
  target_place_name_cn: string | null
  target_place_address: string | null
  target_place_address_cn: string | null
  ready_to_pickup_at: string | null
  place_name: string | null
  place_name_cn: string | null
  picked_up_at: string | null
  storage_days: number | null
  storage_expire_at: string | null
  logistic_barcode: string | null
  storage_fee_amount: string | null
  storage_fee_currency: string | null
  utilization_fee_amount: string | null
  utilization_fee_currency: string | null
  price_amount: string | null
  price_currency: string | null
  commission_percent: string | null
  commission_amount: string | null
  commission_currency: string | null
  price_without_commission_amount: string | null
  price_without_commission_currency: string | null

  brand_name: string | null
  category_name: string | null
  category_name_cn: string | null
  product_barcode: string | null
  exemplar_id: number | null
  utilization_forecast_at: string | null
  pickup_duration_hours: string | null
  order_id: number | null
  order_number: string | null
  srid: string | null
  place_id: number | null
  place_address: string | null
  place_address_cn: string | null
  target_place_id: number | null
  return_type: string | null
  is_super_econom: boolean | null
}

export interface OzonReturnFilters {
  shop_id?: number
  date_from?: string
  date_to?: string
  return_id?: number
  nm_id?: number
  posting_number?: string
  order_id?: number
  order_number?: string
  offer_id?: string
  brand_name?: string
  category_name?: string
  product_name?: string
  status?: string
  return_type?: string
  schema?: string
  keyword?: string
  sort_order?: OzonReturnSortOrder
}

export interface OzonReturnQuery extends OzonReturnFilters {
  page: number
  page_size: number
}

export interface OzonReturnPageResponse {
  items: OzonReturn[]
  total: number
  page: number
  page_size: number
}

export interface OzonReturnKey {
  shop_id: number
  return_id: number
  nm_id: number
}

export interface OzonReturnExportRequest {
  scope: OzonReturnExportScope
  filters?: OzonReturnFilters
  selected_keys?: OzonReturnKey[]
}

function buildQueryParams(query: OzonReturnQuery): URLSearchParams {
  const params = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    params.set(key, String(value))
  })
  return params
}

export const ozonReturnApi = {
  list(query: OzonReturnQuery): Promise<OzonReturnPageResponse> {
    return request.get('/api/v1/ozon/returns', {
      params: buildQueryParams(query)
    })
  },

  export(data: OzonReturnExportRequest): Promise<Blob> {
    return request.post('/api/v1/ozon/returns/export', data, {
      responseType: 'blob',
      timeout: 120000
    })
  }
}
