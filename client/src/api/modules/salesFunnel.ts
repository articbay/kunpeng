import request from '@/api/request'

export interface SalesFunnelDetail {
  id: number
  shop_id: number
  date_from: string
  date_to: string
  vendor_code?: string
  nm_id: number
  title?: string
  subject_name?: string
  brand_name?: string
  tags?: unknown
  product_rating?: number
  feedback_rating?: string
  open_count?: number
  cart_count?: number
  add_to_wishlist?: number
  order_count?: number
  buyout_count?: number
  cancel_count?: number
  add_to_cart_percent?: string
  cart_to_order_percent?: string
  buyout_percent?: string
  order_sum?: string
  buyout_sum?: string
  cancel_sum?: string
  create_time: string
  update_time?: string
}

export interface SalesFunnelQuery {
  shop_id: number
  date_from?: string
  date_to?: string
  nm_id?: number
  vendor_code?: string
  title?: string
  subject_name?: string
  brand_name?: string
  page: number
  page_size: number
}

export type SalesFunnelExportQuery = Omit<SalesFunnelQuery, 'page' | 'page_size'>

export interface SalesFunnelPage {
  items: SalesFunnelDetail[]
  total: number
  page: number
  page_size: number
}

export const salesFunnelApi = {
  list(params: SalesFunnelQuery): Promise<SalesFunnelPage> {
    return request.get('/api/v1/wildberries/sales-funnel-details', { params })
  },

  export(params: SalesFunnelExportQuery): Promise<Blob> {
    return request.get<never, Blob>(
      '/api/v1/wildberries/sales-funnel-details/export',
      {
        params,
        responseType: 'blob'
      }
    )
  }
}
