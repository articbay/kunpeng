import request from '@/api/request'

export type OzonCustomerVoiceExportScope = 'filtered' | 'selected'

export interface OzonCustomerVoice {
  shop_id: number
  review_id: string
  month: string | null
  offer_id: string | null
  sku: number | null
  product_name: string | null
  product_name_cn: string | null
  posting_number: string | null
  order_status: string | null
  order_status_cn: string | null
  review_text: string | null
  review_text_cn: string | null
  published_at: string | null
  review_status: string | null
  review_status_cn: string | null
  rating: number | null
  photos_amount: number | null
  videos_amount: number | null
  comments_amount: number | null
}

export interface OzonCustomerVoiceFilters {
  shop_id?: number
  date_from?: string
  date_to?: string
  offer_id?: string
  sku?: number
  rating?: number
  order_status?: string
  review_status?: string
  keyword?: string
  sort_order?: 'asc' | 'desc'
}

export interface OzonCustomerVoiceQuery extends OzonCustomerVoiceFilters {
  page: number
  page_size: number
}

export interface OzonCustomerVoicePageResponse {
  items: OzonCustomerVoice[]
  total: number
  page: number
  page_size: number
}

export interface OzonCustomerVoiceKey {
  shop_id: number
  review_id: string
}

function params(query: OzonCustomerVoiceQuery): URLSearchParams {
  const result = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') result.set(key, String(value))
  })
  return result
}

export const ozonCustomerVoiceApi = {
  list(query: OzonCustomerVoiceQuery): Promise<OzonCustomerVoicePageResponse> {
    return request.get('/api/v1/ozon/customer-voice', { params: params(query) })
  },
  export(data: {
    scope: OzonCustomerVoiceExportScope
    filters?: OzonCustomerVoiceFilters
    selected_keys?: OzonCustomerVoiceKey[]
  }): Promise<Blob> {
    return request.post('/api/v1/ozon/customer-voice/export', data, {
      responseType: 'blob',
      timeout: 120000
    })
  }
}
