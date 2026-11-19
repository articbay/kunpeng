import request from '@/api/request'

export type SortOrder = 'asc' | 'desc'
export type ExportScope = 'filtered' | 'selected'

export interface WBOrder {
  shop_id: number
  order_id: number
  supply_id: string | null
  sticker_id: string | null
  order_dt: string | null
  title: string | null
  title_cn: string | null
  tech_size: string | null
  tech_size_cn: string | null
  color: string | null
  color_cn: string | null
  barcode_ori: string | null
  barcode_hand: string | null
  retail_price: string | number | null
  currency: string | null
  nm_id: number | null
  supplier_article: string | null
  warehouse_id: number | null
  warehouse_name: string | null
  warehouse_name_cn: string | null
  wb_status: string | null
  wb_status_cn: string | null
  address: string | null
  address_cn: string | null
  is_b2b: boolean | null
  delivery_type: string | null
  supplier_status: string | null
  supplier_status_cn: string | null
  is_cancellable: boolean | null
  price: string | number | null
  converted_price: string | number | null
  currency_code: number | null
  converted_currency_code: number | null
  order_price: string | number | null
  currency_name: string | null
  office_id: number | null
  cargo_type: number | null
  cross_border_type: number | null
  is_zero_order: boolean | null
}

export interface WBOrderFilters {
  shop_id?: number
  date_from?: string
  date_to?: string
  order_id?: number
  supply_id?: string
  sticker_id?: string
  nm_id?: number
  supplier_article?: string
  warehouse_id?: number
  wb_status?: string
  supplier_status?: string
  delivery_type?: string
  is_cancellable?: boolean
  is_b2b?: boolean
  is_zero_order?: boolean
  keyword?: string
  sort_order?: SortOrder
}

export interface WBOrderQuery extends WBOrderFilters {
  page: number
  page_size: number
}

export interface PageResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface WBOrderKey {
  shop_id: number
  order_id: number
}

export interface WBOrderExportRequest {
  scope: ExportScope
  filters?: WBOrderFilters
  selected_keys?: WBOrderKey[]
}

function buildQueryParams(query: WBOrderQuery): URLSearchParams {
  const params = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    params.set(key, String(value))
  })
  return params
}

export const wbOrderApi = {
  list(query: WBOrderQuery): Promise<PageResponse<WBOrder>> {
    return request.get('/api/v1/wildberries/orders', {
      params: buildQueryParams(query)
    })
  },

  export(data: WBOrderExportRequest): Promise<Blob> {
    return request.post('/api/v1/wildberries/orders/export', data, {
      responseType: 'blob',
      timeout: 120000
    })
  }
}
