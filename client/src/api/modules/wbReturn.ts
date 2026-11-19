import request from '@/api/request'

export type SortOrder = 'asc' | 'desc'
export type ExportScope = 'filtered' | 'selected'

export interface WBReturn {
  shop_id: number
  brand: string | null
  subject_name: string | null
  subject_name_cn: string | null
  barcode: string | null
  nm_id: number | null
  bar_code: string | null
  sticker_id: string | null
  status: string | null
  status_cn: string | null
  ready_to_return_dt: string | null
  completed_dt: string | null
  expired_dt: string | null
  return_type: string | null
  return_type_cn: string | null
  order_date: string | null
  reason: string | null
  reason_cn: string | null
  order_id: number | null
  srid: string
  dst_office_address: string | null
  dst_office_address_cn: string | null
  dst_office_id: number | null
}

export interface WBReturnFilters {
  shop_id?: number
  date_from?: string
  date_to?: string
  nm_id?: number
  order_id?: number
  brand?: string
  subject_name?: string
  status?: string
  return_type?: string
  keyword?: string
  sort_order?: SortOrder
}

export interface WBReturnQuery extends WBReturnFilters {
  page: number
  page_size: number
}

export interface PageResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface WBReturnKey {
  shop_id: number
  srid: string
}

export interface WBReturnExportRequest {
  scope: ExportScope
  filters?: WBReturnFilters
  selected_keys?: WBReturnKey[]
}

function buildQueryParams(query: WBReturnQuery): URLSearchParams {
  const params = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    params.set(key, String(value))
  })
  return params
}

export const wbReturnApi = {
  list(query: WBReturnQuery): Promise<PageResponse<WBReturn>> {
    return request.get('/api/v1/wildberries/returns', {
      params: buildQueryParams(query)
    })
  },

  export(data: WBReturnExportRequest): Promise<Blob> {
    return request.post('/api/v1/wildberries/returns/export', data, {
      responseType: 'blob',
      timeout: 120000
    })
  }
}
