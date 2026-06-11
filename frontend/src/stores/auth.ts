import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type UserResponse } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  // State
  const token = ref<string | null>(localStorage.getItem('twonote_token'))
  const user = ref<UserResponse | null>(
    JSON.parse(localStorage.getItem('twonote_user') || 'null')
  )
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const isLoggedIn = computed(() => !!token.value)
  const username = computed(() => user.value?.username ?? '')

  // Actions
  async function login(username: string, password: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const { data } = await authApi.login({ username, password })
      token.value = data.access_token
      localStorage.setItem('twonote_token', data.access_token)

      // Nutzer-Infos laden
      const { data: me } = await authApi.me()
      user.value = me
      localStorage.setItem('twonote_user', JSON.stringify(me))
    } catch (e: any) {
      error.value =
        e.response?.data?.detail ?? 'Login fehlgeschlagen. Bitte prüfe deine Eingaben.'
      throw e
    } finally {
      loading.value = false
    }
  }

  function logout(): void {
    token.value = null
    user.value = null
    localStorage.removeItem('twonote_token')
    localStorage.removeItem('twonote_user')
  }

  async function register(username: string, password: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      await authApi.register({ username, password })
    } catch (e: any) {
      error.value =
        e.response?.data?.detail ?? 'Registrierung fehlgeschlagen.'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function registerNewUser(username: string, password: string): Promise<void> {
    loading.value = true
    error.value = null
    try {
      await authApi.registerAuth({ username, password })
    } catch (e: any) {
      error.value =
        e.response?.data?.detail ?? 'Registrierung fehlgeschlagen.'
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    token,
    user,
    loading,
    error,
    isLoggedIn,
    username,
    login,
    logout,
    register,
    registerNewUser,
  }
})
