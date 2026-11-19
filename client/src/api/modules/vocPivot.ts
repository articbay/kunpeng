import request from '@/api/request'

export interface WBVOCPivotFilters {
  shop_id?: number
  date_from?: string
  date_to?: string
  nm_id?: number
  supplier_article?: string
  brand_name?: string
}

export interface WBVOCPivotExportRequest {
  filters: WBVOCPivotFilters
}

export const vocPivotApi = {
  export(data: WBVOCPivotExportRequest): Promise<Blob> {
    return request.post('/api/v1/wildberries/voc/pivot/export', data, {
      responseType: 'blob',
      timeout: 120000
    })
  }
}
