import request from '@/api/request'

// ===== 仪表盘数据类型（对应后端 schemas/dashboard.py）=====

export interface DateRange {
  date_from: string
  date_to: string
  days: number
}

export interface KpiBlock {
  gmv: number
  orders: number
  units: number
  returns: number
  return_rate: number
  ad_spend: number
  drr: number
  avg_order_value: number
  shop_count: number
}

export interface TrendPoint {
  date: string
  wb_gmv: number
  ozon_gmv: number
  wb_orders: number
  ozon_orders: number
  wb_ad_spend: number
  ozon_ad_spend: number
  wb_returns: number
  ozon_returns: number
}

export interface PlatformStat {
  platform: string
  platform_label: string
  gmv: number
  orders: number
  units: number
  returns: number
  return_rate: number
  ad_spend: number
  drr: number
  shop_count: number
}

export interface ShopStat {
  shop_id: number
  shop_name: string
  platform: string
  platform_label: string
  gmv: number
  orders: number
  units: number
  returns: number
  return_rate: number
  ad_spend: number
  drr: number
}

export interface TopProduct {
  platform: string
  platform_label: string
  ext_id: string
  name: string
  gmv: number
  units: number
}

export interface DashboardSummary {
  range: DateRange
  kpi: KpiBlock
  trend: TrendPoint[]
  platforms: PlatformStat[]
  shops: ShopStat[]
  top_products: TopProduct[]
  generated_at: string | null
}

export interface DashboardQuery {
  days?: number
  platform?: string
  shop_id?: number
  top_limit?: number
}

export const dashboardApi = {
  // 获取仪表盘总览
  summary(params: DashboardQuery = {}): Promise<DashboardSummary> {
    return request.get('/api/v1/dashboard/summary', { params })
  },
}
