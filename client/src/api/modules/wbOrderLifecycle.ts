import request from '@/api/request'

export type WBLifecycleStage = 'new' | 'assembling' | 'in_delivery' | 'wb_received' | 'ready_for_pickup' | 'sold' | 'cancelled' | 'returned' | 'unknown'
export type WBLifecycleAnomaly = 'missing_current_status' | 'return_identity_conflict' | 'terminal_without_time'
export type WBOrderLifecycleExportScope = 'filtered' | 'selected'

export interface WBOrderLifecycleItem {
  shop_id: number
  srid: string
  order_id: number | null
  order_uid: string | null
  supply_id: string | null
  sticker_id: string | null
  g_number: string | null
  nm_id: number | null
  supplier_article: string | null
  barcode: string | null
  product_title: string | null
  product_title_cn: string | null
  subject_name: string | null
  subject_name_cn: string | null
  tech_size: string | null
  tech_size_cn: string | null
  delivery_type: string | null
  warehouse_name: string | null
  warehouse_name_cn: string | null
  country_name: string | null
  country_name_cn: string | null
  region_name: string | null
  region_name_cn: string | null
  total_price: string | number | null
  price_with_disc: string | number | null
  finished_price: string | number | null
  converted_price: string | number | null
  currency_code: number | null
  order_at: string
  last_change_at: string | null
  cancelled_at: string | null
  supplier_status: string | null
  supplier_status_cn: string | null
  wb_status: string | null
  wb_status_cn: string | null
  lifecycle_stage: WBLifecycleStage
  lifecycle_stage_cn: string
  is_cancelled: boolean
  is_sold: boolean
  is_terminal: boolean
  supply_name: string | null
  supply_is_done: boolean | null
  supply_created_at: string | null
  supply_scan_at: string | null
  supply_closed_at: string | null
  supply_rejected_at: string | null
  sale_at: string | null
  sale_last_change_at: string | null
  sale_id: string | null
  sale_event_type: string | null
  finance_row_cnt: number
  finance_sale_row_cnt: number
  finance_first_sale_at: string | null
  return_cnt: number
  latest_return_srid: string | null
  latest_return_order_id: number | null
  latest_return_status: string | null
  latest_return_status_cn: string | null
  latest_return_type: string | null
  latest_return_type_cn: string | null
  latest_return_reason: string | null
  latest_return_reason_cn: string | null
  return_ready_at: string | null
  return_completed_at: string | null
  return_expired_at: string | null
  return_link_method: string | null
  has_return_identity_conflict: boolean
  has_statistics_order_data: boolean
  has_marketplace_order_data: boolean
  has_supply_data: boolean
  has_sale_data: boolean
  has_finance_data: boolean
  has_return_data: boolean
  create_time: string
  update_time: string | null
}

export interface WBOrderLifecycleFilters {
  shop_id?: number
  date_from?: string
  date_to?: string
  srid?: string
  order_id?: number
  supply_id?: string
  nm_id?: number
  supplier_article?: string
  supplier_status?: string
  wb_status?: string
  return_status?: string
  return_reason?: string
  keyword?: string
  stage?: WBLifecycleStage
  anomaly?: WBLifecycleAnomaly
  sort_order?: 'asc' | 'desc'
}

export interface WBOrderLifecycleKey { shop_id: number; srid: string }
export interface WBPageResponse<T> { items: T[]; total: number; page: number; page_size: number }

export interface WBOrderLifecycleSummary {
  metrics: {
    order_count: number
    sold_count: number
    sold_rate: number
    cancelled_count: number
    cancelled_rate: number
    returned_count: number
    returned_rate: number
    terminal_count: number
    marketplace_covered_count: number
  }
  stages: Array<{ stage: string; label: string; order_count: number }>
  trend: Array<{ stat_date: string; order_count: number; sold_count: number; cancelled_count: number; returned_count: number }>
  statuses: Array<{ wb_status: string | null; wb_status_cn: string | null; order_count: number }>
  updated_at: string | null
}

function params(values: object) {
  const result = new URLSearchParams()
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') result.set(key, String(value))
  })
  return result
}

export const wbOrderLifecycleApi = {
  list(query: WBOrderLifecycleFilters & { page: number; page_size: number }): Promise<WBPageResponse<WBOrderLifecycleItem>> {
    return request.get('/api/v1/wildberries/order-lifecycle', { params: params(query) })
  },
  summary(query: WBOrderLifecycleFilters): Promise<WBOrderLifecycleSummary> {
    return request.get('/api/v1/wildberries/order-lifecycle/summary', { params: params(query) })
  },
  export(data: { scope: WBOrderLifecycleExportScope; filters: WBOrderLifecycleFilters; selected_keys: WBOrderLifecycleKey[] }): Promise<Blob> {
    return request.post('/api/v1/wildberries/order-lifecycle/export', data, { responseType: 'blob', timeout: 120000 })
  }
}
