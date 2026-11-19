import request from '@/api/request'
import type { ExportScope, GoodsPeriodMetrics, GoodsProductShopDetail, Metric, PageResponse, RankingMetric } from './ozonGoodsDailyAnalysis'

export type WBGoodsDataStatus = 'has_orders' | 'has_returns' | 'has_funnel' | 'has_ad'
export type WBGoodsAnomaly = 'ad_spend_no_orders' | 'high_return_rate' | 'clicks_no_cart' | 'cart_no_orders' | 'high_cancel_rate' | 'click_scope_conflict' | 'ad_currency_conflict'

export interface WBGoodsDailyItem {
  stat_date: string
  shop_id: number
  nm_id: number
  vendor_code: string | null
  product_title: string | null
  product_title_cn: string | null
  brand_name: string | null
  subject_name: string | null
  subject_name_cn: string | null
  has_funnel_data: boolean
  has_order_data: boolean
  has_return_data: boolean
  has_ad_data: boolean
  product_rating: Metric
  feedback_rating: Metric
  traffic_clicks: number | null
  traffic_cart_qty: number | null
  traffic_wishlist_qty: number | null
  funnel_order_qty: number | null
  funnel_buyout_qty: number | null
  funnel_cancel_qty: number | null
  funnel_order_amount: Metric
  funnel_buyout_amount: Metric
  funnel_cancel_amount: Metric
  order_cnt: number
  order_qty: number
  cancelled_order_cnt: number
  cancelled_qty: number
  order_amount_sum: Metric
  finished_amount_sum: Metric
  return_cnt: number
  return_qty: number
  return_ready_cnt: number
  return_completed_cnt: number
  return_expired_cnt: number
  ad_campaign_cnt: number | null
  ad_views: number | null
  ad_clicks: number | null
  ad_to_cart: number | null
  ad_order_cnt: number | null
  ad_cancelled_cnt: number | null
  ad_sales_qty: number | null
  ad_spend_amount: Metric
  ad_attributed_sales_amount: Metric
  ad_currency: string | null
  has_ad_currency_conflict: boolean
  traffic_cart_rate: Metric
  traffic_order_rate: Metric
  traffic_buyout_rate: Metric
  order_cancel_rate: Metric
  return_rate_ordered: Metric
  return_rate_buyout: Metric
  ad_ctr: Metric
  ad_cart_rate: Metric
  ad_cvr: Metric
  ad_cpc: Metric
  ad_cpo: Metric
  ad_roas: Metric
  ad_drr: Metric
  ad_click_share: Metric
  estimated_organic_clicks: number | null
  has_click_scope_conflict: boolean
  create_time: string
  update_time: string | null
}

export interface WBGoodsDailyFilters {
  shop_id?: number
  date_from?: string
  date_to?: string
  nm_id?: number
  vendor_code?: string
  keyword?: string
  data_status?: WBGoodsDataStatus
  anomaly?: WBGoodsAnomaly
  sort_order?: 'asc' | 'desc'
}

export interface WBGoodsDailyKey { stat_date: string; shop_id: number; nm_id: number }

export interface WBGoodsDailySummary {
  metrics: {
    sales_amount: Metric
    order_qty: number
    funnel_order_qty: number
    has_funnel_data: boolean
    return_qty: number
    return_rate: Metric
    ad_spend: Metric
    ad_attributed_sales: Metric
    ad_roas: Metric
    ad_drr: Metric
    sales_currency: string | null
    ad_currency: string | null
    has_currency_conflict: boolean
  }
  trend: Array<{ stat_date: string; sales_amount: Metric; ad_spend: Metric; order_qty: number; return_qty: number; return_rate: Metric }>
  ranking: Array<{ nm_id: number; vendor_code: string | null; product_title_cn: string | null; product_title: string | null; sales_amount: Metric; order_qty: number; return_qty: number; return_rate: Metric; ad_spend: Metric; ad_roas: Metric }>
  updated_at: string | null
}

export interface WBGoodsProductDetail {
  nm_id: number
  vendor_code: string | null
  product_title: string | null
  product_title_cn: string | null
  brand_name: string | null
  subject_name: string | null
  subject_name_cn: string | null
  period_from: string
  period_to: string
  metrics: GoodsPeriodMetrics
  shops: GoodsProductShopDetail[]
}

function params(values: object) {
  const result = new URLSearchParams()
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') result.set(key, String(value))
  })
  return result
}

export const wbGoodsDailyAnalysisApi = {
  list(query: WBGoodsDailyFilters & { page: number; page_size: number }): Promise<PageResponse<WBGoodsDailyItem>> {
    return request.get('/api/v1/wildberries/goods-daily-analysis', { params: params(query) })
  },
  summary(query: WBGoodsDailyFilters & { ranking_metric: RankingMetric }): Promise<WBGoodsDailySummary> {
    return request.get('/api/v1/wildberries/goods-daily-analysis/summary', { params: params(query) })
  },
  productDetail(nmId: number, query: WBGoodsDailyFilters): Promise<WBGoodsProductDetail> {
    return request.get(`/api/v1/wildberries/goods-daily-analysis/products/${nmId}`, { params: params(query) })
  },
  export(data: { scope: ExportScope; filters: WBGoodsDailyFilters; selected_keys: WBGoodsDailyKey[] }): Promise<Blob> {
    return request.post('/api/v1/wildberries/goods-daily-analysis/export', data, { responseType: 'blob', timeout: 120000 })
  }
}
