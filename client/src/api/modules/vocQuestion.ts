import request from '@/api/request'

export type AnswerStatus = 'answered' | 'unanswered'
export type SortOrder = 'asc' | 'desc'
export type ExportScope = 'filtered' | 'selected'

export interface WBVOCQuestion {
  shop_id: number
  question_id: string
  created_date: string | null
  supplier_article: string | null
  nm_id: number | null
  brand_name: string | null
  text: string | null
  text_cn: string | null
  answer: string | null
  answer_cn: string | null
}

export interface WBVOCQuestionFilters {
  shop_id?: number
  date_from?: string
  date_to?: string
  supplier_article?: string
  nm_id?: number
  brand_name?: string
  keyword?: string
  answer_status?: AnswerStatus
  sort_order?: SortOrder
}

export interface WBVOCQuestionQuery extends WBVOCQuestionFilters {
  page: number
  page_size: number
}

export interface PageResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface WBVOCQuestionKey {
  shop_id: number
  question_id: string
}

export interface WBVOCQuestionExportRequest {
  scope: ExportScope
  filters?: WBVOCQuestionFilters
  selected_keys?: WBVOCQuestionKey[]
}

function buildQueryParams(query: WBVOCQuestionQuery): URLSearchParams {
  const params = new URLSearchParams()
  Object.entries(query).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    params.set(key, String(value))
  })
  return params
}

export const vocQuestionApi = {
  list(query: WBVOCQuestionQuery): Promise<PageResponse<WBVOCQuestion>> {
    return request.get('/api/v1/wildberries/voc/questions', {
      params: buildQueryParams(query)
    })
  },

  export(data: WBVOCQuestionExportRequest): Promise<Blob> {
    return request.post('/api/v1/wildberries/voc/questions/export', data, {
      responseType: 'blob',
      timeout: 120000
    })
  }
}
