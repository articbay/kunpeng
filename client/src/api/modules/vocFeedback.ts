import request from '@/api/request'

export type AnswerStatus = 'answered' | 'unanswered'
export type SortOrder = 'asc' | 'desc'
export type ExportScope = 'filtered' | 'selected'

export interface WBVOCFeedback {
  shop_id: number
  feedback_id: string
  created_date: string | null
  supplier_article: string | null
  nm_id: number | null
  product_name: string | null
  product_name_cn: string | null
  product_valuation: number | null
  brand_name: string | null
  text: string | null
  text_cn: string | null
  pros: string | null
  pros_cn: string | null
  cons: string | null
  cons_cn: string | null
  user_name: string | null
  color: string | null
  color_cn: string | null
  size: string | null
  size_cn: string | null
  answer: string | null
  answer_cn: string | null
  parent_feedback_id: string | null
  child_feedback_id: string | null
}

export interface WBVOCFeedbackFilters {
  shop_id?: number
  date_from?: string
  date_to?: string
  product_valuations?: number[]
  supplier_article?: string
  nm_id?: number
  brand_name?: string
  keyword?: string
  answer_status?: AnswerStatus
  sort_order?: SortOrder
}

export interface WBVOCFeedbackQuery extends WBVOCFeedbackFilters {
  page: number
  page_size: number
}

export interface PageResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface WBVOCFeedbackKey {
  shop_id: number
  feedback_id: string
}

export interface WBVOCFeedbackExportRequest {
  scope: ExportScope
  filters?: WBVOCFeedbackFilters
  selected_keys?: WBVOCFeedbackKey[]
}

function buildQueryParams(query: WBVOCFeedbackQuery): URLSearchParams {
  const params = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    if (Array.isArray(value)) {
      value.forEach((item) => params.append(key, String(item)))
      return
    }
    params.set(key, String(value))
  })
  return params
}

export const vocFeedbackApi = {
  list(query: WBVOCFeedbackQuery): Promise<PageResponse<WBVOCFeedback>> {
    return request.get('/api/v1/wildberries/voc/feedbacks', {
      params: buildQueryParams(query)
    })
  },

  export(data: WBVOCFeedbackExportRequest): Promise<Blob> {
    return request.post('/api/v1/wildberries/voc/feedbacks/export', data, {
      responseType: 'blob',
      timeout: 120000
    })
  }
}
