import request from '@/api/request'

export interface Shop {
  id: number
  name: string
  platform: string
  platform_shop_id?: string
  api_key?: string
  // Ozon 广告 Performance API 独立凭证
  performance_client_id?: string
  performance_client_secret?: string
  user_id: number
}

export interface ShopCreateForm {
  name: string
  platform: string
  platform_shop_id?: string
  api_key?: string
  performance_client_id?: string
  performance_client_secret?: string
}

export interface ShopUpdateForm {
  name?: string
  platform?: string
  platform_shop_id?: string
  api_key?: string
  performance_client_id?: string
  performance_client_secret?: string
}

export const shopApi = {
  // 获取店铺列表
  list(): Promise<Shop[]> {
    return request.get('/api/v1/shops/shops')
  },

  // 获取单个店铺
  get(shopId: number): Promise<Shop> {
    return request.get(`/api/v1/shops/shops/${shopId}`)
  },

  // 创建店铺
  create(data: ShopCreateForm): Promise<Shop> {
    return request.post('/api/v1/shops/shops', data)
  },

  // 更新店铺
  update(shopId: number, data: ShopUpdateForm): Promise<Shop> {
    return request.put(`/api/v1/shops/shops/${shopId}`, data)
  },

  // 删除店铺
  delete(shopId: number): Promise<{ message: string }> {
    return request.delete(`/api/v1/shops/shops/${shopId}`)
  },
}
