import request from '@/api/request'

export type SortOrder = 'asc' | 'desc'
export type ExportScope = 'filtered' | 'selected'

export interface WBOrderStatistics {
  shop_id: number
  srid: string
  order_date: string | null
  last_change_date: string | null
  warehouse_name: string | null
  warehouse_name_cn: string | null
  country_name: string | null
  country_name_cn: string | null
  oblast_okrug_name: string | null
  oblast_okrug_name_cn: string | null
  region_name: string | null
  region_name_cn: string | null
  supplier_article: string | null
  nm_id: number | null
  barcode: string | null
  category: string | null
  category_cn: string | null
  subject_name: string | null
  subject_name_cn: string | null
  tech_size: string | null
  tech_size_cn: string | null
  total_price: string | number | null
  discount_percent: number | null
  price_with_disc: string | number | null
  finished_price: string | number | null
  is_cancel: boolean | null
  cancel_date: string | null
  sticker_id: string | null
  g_number: string | null
}

export interface WBOrderStatisticsFilters {
  shop_id?: number
  date_from?: string
  date_to?: string
  srid?: string
  warehouse_name?: string
  country_name?: string
  oblast_okrug_name?: string
  region_name?: string
  supplier_article?: string
  nm_id?: number
  category?: string
  subject_name?: string
  is_cancel?: boolean
  keyword?: string
  sort_order?: SortOrder
}

export interface WBOrderStatisticsQuery extends WBOrderStatisticsFilters {
  page: number
  page_size: number
}

export interface PageResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface WBOrderStatisticsKey {
  shop_id: number
  srid: string
}

export interface WBOrderStatisticsExportRequest {
  scope: ExportScope
  filters?: WBOrderStatisticsFilters
  selected_keys?: WBOrderStatisticsKey[]
}

function buildQueryParams(query: WBOrderStatisticsQuery): URLSearchParams {
  const params = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    params.set(key, String(value))
  })
  return params
}

export const wbOrderStatisticsApi = {
  list(query: WBOrderStatisticsQuery): Promise<PageResponse<WBOrderStatistics>> {
    return request.get('/api/v1/wildberries/order-statistics', {
      params: buildQueryParams(query)
    })
  },

  export(data: WBOrderStatisticsExportRequest): Promise<Blob> {
    return request.post('/api/v1/wildberries/order-statistics/export', data, {
      responseType: 'blob',
      timeout: 120000
    })
  }
}
