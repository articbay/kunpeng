import request from '@/api/request'

export interface User {
  id: number
  email: string
  full_name?: string
  is_active: boolean
  is_superuser: boolean
  created_at: string
}

export interface UserCreateForm {
  email: string
  password: string
  full_name?: string
}

export interface UserUpdateForm {
  email?: string
  full_name?: string
  is_active?: boolean
  is_superuser?: boolean
}

export interface ChangePasswordForm {
  new_password: string
}

export const userApi = {
  // 获取用户列表
  list(): Promise<User[]> {
    return request.get('/api/v1/auth/users')
  },

  // 获取单个用户
  get(userId: number): Promise<User> {
    return request.get(`/api/v1/auth/users/${userId}`)
  },

  // 创建用户
  create(data: UserCreateForm): Promise<User> {
    return request.post('/api/v1/auth/users', data)
  },

  // 更新用户
  update(userId: number, data: UserUpdateForm): Promise<User> {
    return request.put(`/api/v1/auth/users/${userId}`, data)
  },

  // 删除用户
  delete(userId: number): Promise<{ message: string }> {
    return request.delete(`/api/v1/auth/users/${userId}`)
  },

  // 修改密码
  changePassword(userId: number, data: ChangePasswordForm): Promise<{ message: string }> {
    return request.put(`/api/v1/auth/users/${userId}/password`, data)
  },

  // 启用/停用用户
  toggleStatus(userId: number, isActive: boolean): Promise<User> {
    return request.put(`/api/v1/auth/users/${userId}/status`, null, { params: { is_active: isActive } })
  },
}
