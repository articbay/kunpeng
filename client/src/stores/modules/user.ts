import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type UserInfo, type LoginForm } from '@/api/modules/auth'

export const useUserStore = defineStore('user', () => {
  const token = ref<string>(localStorage.getItem('token') || '')
  const userInfo = ref<UserInfo | null>(null)

  const isLoggedIn = computed(() => !!token.value)
  const isSuperuser = computed(() => userInfo.value?.is_superuser === true)

  async function login(form: LoginForm) {
    const res = await authApi.login(form)
    token.value = res.access_token
    localStorage.setItem('token', res.access_token)
    await fetchUserInfo()
  }

  async function fetchUserInfo() {
    if (!token.value) return
    userInfo.value = await authApi.getCurrentUser()
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
  }

  return {
    token,
    userInfo,
    isLoggedIn,
    isSuperuser,
    login,
    fetchUserInfo,
    logout
  }
})
