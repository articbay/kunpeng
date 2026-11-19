import request from '@/api/request'

export interface AdvertsReportDetail {
  id: number
  shop_id: number
  week: string
  advert_id: number
  advert_name: string | null
  advert_status: number | null
  advert_status_label: string | null
  paid_views: number | null
  paid_clicks: number | null
  atbs: number | null
  orders: number | null
  ctr: number | null
  cpc: number | null
  cr: number | null
  sum_cost: number | null
  sum_price: number | null
  create_time: string | null
  update_time: string | null
}

export interface PageResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

interface AvailableWeeksResponse {
  weeks: string[]
}

export const wildberriesApi = {
  // 获取可用周度列表
  getAvailableWeeks(shopId?: number): Promise<string[]> {
    const params = shopId ? { shop_id: shopId } : {}
    return request
      .get<AvailableWeeksResponse, AvailableWeeksResponse>(
        '/api/v1/wildberries/adverts-report/weeks',
        { params }
      )
      .then((response) => response.weeks ?? [])
  },

  // 获取广告周度报表（分页）
  getAdvertsReport(params: {
    shop_id?: number
    week?: string
    advert_id?: number
    advert_status?: number
    page?: number
    page_size?: number
  }): Promise<PageResponse<AdvertsReportDetail>> {
    return request.get('/api/v1/wildberries/adverts-report', { params })
  },

  // 导出Excel
  exportExcel(params: {
    shop_id?: number
    week?: string
    advert_id?: number
    advert_status?: number
  }): Promise<Blob> {
    return request.get('/api/v1/wildberries/adverts-report/export', {
      params,
      responseType: 'blob'
    })
  }
}
