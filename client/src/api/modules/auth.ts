import request from '../request'

export interface LoginForm {
  email: string
  password: string
}

export interface RegisterForm {
  email: string
  password: string
  fullName?: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface UserInfo {
  id: number
  email: string
  full_name?: string
  is_active: boolean
  is_superuser: boolean
  create_time?: string
}

export const authApi = {
  // 登录
  login(data: LoginForm): Promise<TokenResponse> {
    return request.post('/api/v1/auth/login', data)
  },

  // 注册
  register(data: RegisterForm): Promise<UserInfo> {
    return request.post('/api/v1/auth/register', data)
  },

  // 获取当前用户信息
  getCurrentUser(): Promise<UserInfo> {
    return request.get('/api/v1/auth/me')
  }
}
