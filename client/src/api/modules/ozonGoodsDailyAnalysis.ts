import request from '@/api/request'

export type ExportScope = 'filtered' | 'selected'
export type GoodsDataStatus = 'has_orders' | 'has_returns' | 'has_funnel' | 'has_ad' | 'has_traffic'
export type GoodsAnomaly = 'ad_spend_no_orders' | 'high_return_rate' | 'clicks_no_cart' | 'cart_no_orders'
export type RankingMetric = 'sales_amount' | 'order_qty' | 'ad_spend' | 'ad_roas' | 'return_rate'
export type Metric = number | string | null

export interface OzonGoodsDailyItem {
  stat_date: string
  shop_id: number
  sku: number
  offer_id: string | null
  product_name: string | null
  product_name_cn: string | null
  category_name: string | null
  category_name_cn: string | null
  order_cnt: number
  order_line_cnt: number
  order_qty: number
  delivered_qty: number
  cancelled_qty: number
  sales_amount_sum: Metric
  sales_currency: string | null
  return_cnt: number
  return_qty: number
  return_amount_sum: Metric
  return_amount_currency: string | null
  storage_fee_sum: Metric
  storage_fee_currency: string | null
  utilization_fee_sum: Metric
  utilization_fee_currency: string | null
  commission_amount_sum: Metric
  commission_currency: string | null
  return_rate_ordered: Metric
  return_rate_delivered: Metric
  has_currency_conflict: boolean
  has_funnel_data: boolean
  has_traffic_metrics: boolean
  funnel_ordered_units: number | null
  funnel_revenue: Metric
  traffic_views_search: number | null
  traffic_views_pdp: number | null
  traffic_views: number | null
  traffic_visitors_search: number | null
  traffic_visitors_pdp: number | null
  traffic_visitors: number | null
  traffic_to_cart_search: number | null
  traffic_to_cart_pdp: number | null
  traffic_to_cart: number | null
  traffic_cart_rate: Metric
  has_ad_data: boolean
  ad_campaign_cnt: number | null
  ad_views: number | null
  ad_clicks: number | null
  ad_to_cart: number | null
  ad_spend_amount: Metric
  ad_spend_currency: string | null
  ad_attributed_order_cnt: number | null
  ad_attributed_sales_amount: Metric
  ad_ctr: Metric
  ad_cart_rate: Metric
  ad_cpc: Metric
  ad_cpo: Metric
  ad_roas: Metric
  ad_drr: Metric
  create_time: string
  update_time: string | null
}

export interface GoodsDailyFilters {
  shop_id?: number
  date_from?: string
  date_to?: string
  sku?: number
  offer_id?: string
  keyword?: string
  data_status?: GoodsDataStatus
  anomaly?: GoodsAnomaly
  sort_order?: 'asc' | 'desc'
}

export interface GoodsDailyKey { stat_date: string; shop_id: number; sku: number }
export interface PageResponse<T> { items: T[]; total: number; page: number; page_size: number }

export interface GoodsDailySummary {
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
  trend: Array<{
    stat_date: string
    sales_amount: Metric
    ad_spend: Metric
    order_qty: number
    return_qty: number
    return_rate: Metric
  }>
  ranking: Array<{
    sku: number
    offer_id: string | null
    product_name_cn: string | null
    product_name: string | null
    sales_amount: Metric
    order_qty: number
    return_qty: number
    return_rate: Metric
    ad_spend: Metric
    ad_roas: Metric
  }>
  updated_at: string | null
}

export interface GoodsPeriodMetrics {
  sales_amount: Metric
  order_qty: number
  return_qty: number
  return_rate: Metric
  ad_spend: Metric
  ad_attributed_sales: Metric
  ad_roas: Metric
}

export interface GoodsProductShopDetail {
  shop_id: number
  shop_name: string | null
  metrics: GoodsPeriodMetrics
}

export interface OzonGoodsProductDetail {
  sku: number
  offer_id: string | null
  product_name: string | null
  product_name_cn: string | null
  category_name: string | null
  category_name_cn: string | null
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

export const ozonGoodsDailyAnalysisApi = {
  list(query: GoodsDailyFilters & { page: number; page_size: number }): Promise<PageResponse<OzonGoodsDailyItem>> {
    return request.get('/api/v1/ozon/goods-daily-analysis', { params: params(query) })
  },
  summary(query: GoodsDailyFilters & { ranking_metric: RankingMetric }): Promise<GoodsDailySummary> {
    return request.get('/api/v1/ozon/goods-daily-analysis/summary', { params: params(query) })
  },
  productDetail(sku: number, query: GoodsDailyFilters): Promise<OzonGoodsProductDetail> {
    return request.get(`/api/v1/ozon/goods-daily-analysis/products/${sku}`, { params: params(query) })
  },
  export(data: { scope: ExportScope; filters: GoodsDailyFilters; selected_keys: GoodsDailyKey[] }): Promise<Blob> {
    return request.post('/api/v1/ozon/goods-daily-analysis/export', data, { responseType: 'blob', timeout: 120000 })
  }
}
