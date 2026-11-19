import request from '@/api/request'

export type LifecycleStage = 'pending_shipment' | 'shipped' | 'transferred' | 'delivery_node' | 'cancelled' | 'returned'
export type LifecycleAnomaly = 'promise_passed_without_delivery_node' | 'return_qty_exceeds_ordered' | 'return_status_missing'
export type ExportScope = 'filtered' | 'selected'

export interface OzonOrderLifecycleItem {
  shop_id: number
  fulfillment_type: 'FBS' | 'FBO'
  posting_number: string
  sku: number
  order_id: number | null
  order_number: string | null
  offer_id: string | null
  product_name: string | null
  product_name_cn: string | null
  quantity: number | null
  status_code: string | null
  substatus_code: string | null
  status_name_cn: string | null
  in_process_at: string | null
  shipment_date: string | null
  transferred_to_delivery_at: string | null
  delivery_date: string | null
  promised_delivery_at: string | null
  cancellation_at: string | null
  return_cnt: number
  return_qty: number
  first_return_date: string | null
  latest_return_id: number | null
  latest_return_status_sys_name: string | null
  latest_return_status_display_name_cn: string | null
  latest_return_status_change_at: string | null
  latest_return_reason_name_cn: string | null
  last_ready_to_pickup_at: string | null
  last_picked_up_at: string | null
  create_time: string
  update_time: string | null
}

export interface LifecycleFilters {
  shop_id?: number
  date_from?: string
  date_to?: string
  fulfillment_type?: 'FBS' | 'FBO'
  posting_number?: string
  order_number?: string
  sku?: number
  offer_id?: string
  status_code?: string
  substatus_code?: string
  return_status?: string
  return_reason?: string
  keyword?: string
  stage?: LifecycleStage
  anomaly?: LifecycleAnomaly
  sort_order?: 'asc' | 'desc'
}

export interface LifecycleKey { shop_id: number; fulfillment_type: 'FBS' | 'FBO'; posting_number: string; sku: number }
export interface PageResponse<T> { items: T[]; total: number; page: number; page_size: number }

export interface LifecycleSummary {
  metrics: {
    posting_count: number
    item_row_count: number
    order_qty: number
    shipped_posting_count: number
    shipped_rate: number
    cancelled_posting_count: number
    cancelled_rate: number
    returned_item_count: number
    returned_item_rate: number
    return_qty: number
  }
  stages: Array<{ stage: string; label: string; posting_count: number }>
  trend: Array<{ stat_date: string; posting_count: number; order_qty: number; cancelled_posting_count: number; return_qty: number }>
  statuses: Array<{ status_code: string | null; status_name_cn: string | null; posting_count: number }>
  updated_at: string | null
}

function params(values: object) {
  const result = new URLSearchParams()
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') result.set(key, String(value))
  })
  return result
}

export const ozonOrderLifecycleApi = {
  list(query: LifecycleFilters & { page: number; page_size: number }): Promise<PageResponse<OzonOrderLifecycleItem>> {
    return request.get('/api/v1/ozon/order-lifecycle', { params: params(query) })
  },
  summary(query: LifecycleFilters): Promise<LifecycleSummary> {
    return request.get('/api/v1/ozon/order-lifecycle/summary', { params: params(query) })
  },
  export(data: { scope: ExportScope; filters: LifecycleFilters; selected_keys: LifecycleKey[] }): Promise<Blob> {
    return request.post('/api/v1/ozon/order-lifecycle/export', data, { responseType: 'blob', timeout: 120000 })
  }
}

