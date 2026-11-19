import request from '@/api/request'

export interface ShopAccessOption {
  shop_id: number
  shop_name: string
  platform: string
  granted: boolean
}

export interface ShopAccessResponse {
  user_id: number
  shops: ShopAccessOption[]
}

export const shopAccessApi = {
  get(userId: number): Promise<ShopAccessResponse> {
    return request.get(`/api/v1/shop-access/users/${userId}`)
  },

  update(userId: number, shopIds: number[]): Promise<ShopAccessResponse> {
    return request.put(`/api/v1/shop-access/users/${userId}`, { shop_ids: shopIds })
  }
}
