import request from '@/api/request'

export type OzonFulfillmentType = 'FBS' | 'FBO'
export type OzonOrderSortOrder = 'asc' | 'desc'
export type OzonOrderExportScope = 'filtered' | 'selected'

export interface OzonOrder {
  shop_id: number
  fulfillment_type: OzonFulfillmentType
  posting_number: string
  sku: number
  order_type_name: string
  order_id: number | null
  order_number: string | null
  in_process_month: string | null
  in_process_date: string | null
  in_process_hour: number | null
  in_process_at: string | null
  shipment_date: string | null
  status_code: string | null
  substatus_code: string | null
  status_name_cn: string | null
  delivery_date: string | null
  transferred_to_delivery_at: string | null
  delivery_duration_1_hours: string | number | null
  delivery_duration_2_hours: string | number | null
  delivery_level_1: string | null
  delivery_level_2: string | null
  shipment_amount: string | number | null
  shipment_currency: string | null
  product_name: string | null
  product_name_cn: string | null
  offer_id: string | null
  seller_price: string | number | null
  product_currency: string | null
  buyer_paid_amount: string | number | null
  buyer_currency: string | null
  quantity: number | null
  delivery_fee: string | number | null
  related_posting_number: string | null
  is_marketplace_buyout: boolean | null
  old_price: string | number | null
  discount_percent: string | number | null
  discount_amount: string | number | null
  promotion_actions: unknown
  product_volume_weight: string | number | null
  cluster_from: string | null
  cluster_to: string | null
  promised_delivery_at: string | null
  shipment_assessment: string | null
  ozon_warehouse_name: string | null
  delivery_region: string | null
  delivery_city: string | null
  delivery_city_cn: string | null
  delivery_type: string | null
  is_premium: boolean | null
  is_legal: boolean | null
  payment_type: string | null
  buyer_address: string | null
  buyer_name: string | null
  buyer_email: string | null
  addressee_name: string | null
  buyer_phone: string | null
  delivery_address: string | null
  postal_code: string | null
  seller_warehouse_name: string | null
  shipment_method: string | null
  logistics_company: string | null
  delivery_method_name: string | null
  shipment_date_without_delay: string | null
  cancellation_at: string | null
  declared_total_weight: string | number | null
  actual_total_weight: string | number | null
  shipment_volume_weight: string | number | null
  product_color: string | null
  product_size: string | null
}

export interface OzonOrderFilters {
  shop_id?: number
  date_from?: string
  date_to?: string
  fulfillment_type?: OzonFulfillmentType
  posting_number?: string
  order_id?: number
  order_number?: string
  sku?: number
  offer_id?: string
  status_code?: string
  substatus_code?: string
  warehouse_name?: string
  delivery_region?: string
  delivery_city?: string
  payment_type?: string
  keyword?: string
  sort_order?: OzonOrderSortOrder
}

export interface OzonOrderQuery extends OzonOrderFilters {
  page: number
  page_size: number
}

export interface OzonOrderKey {
  shop_id: number
  fulfillment_type: OzonFulfillmentType
  posting_number: string
  sku: number
}

export interface OzonOrderExportRequest {
  scope: OzonOrderExportScope
  filters?: OzonOrderFilters
  selected_keys?: OzonOrderKey[]
}

export interface PageResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

function buildQueryParams(query: OzonOrderQuery): URLSearchParams {
  const params = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    params.set(key, String(value))
  })
  return params
}

export const ozonOrderApi = {
  list(query: OzonOrderQuery): Promise<PageResponse<OzonOrder>> {
    return request.get('/api/v1/ozon/orders', {
      params: buildQueryParams(query)
    })
  },

  export(data: OzonOrderExportRequest): Promise<Blob> {
    return request.post('/api/v1/ozon/orders/export', data, {
      responseType: 'blob',
      timeout: 120000
    })
  }
}
