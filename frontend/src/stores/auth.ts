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
  // Cache-Buster für Avatar-URLs (bei Upload/Entfernen erhöht).
  const avatarVersion = ref(Date.now())

  // Getters
  const isLoggedIn = computed(() => !!token.value)
  const username = computed(() => user.value?.username ?? '')
  // Der allererste registrierte Account (id 1) darf neue Nutzer anlegen.
  const isFirstUser = computed(() => user.value?.id === 1)

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

  async function fetchUsers(): Promise<UserResponse[]> {
    error.value = null
    try {
      const { data } = await authApi.listUsers()
      return data
    } catch (e: any) {
      error.value = e.response?.data?.detail ?? 'Nutzer konnten nicht geladen werden.'
      throw e
    }
  }

  async function updateUser(
    id: number,
    payload: { username?: string; password?: string }
  ): Promise<void> {
    error.value = null
    try {
      await authApi.updateUser(id, payload)
    } catch (e: any) {
      error.value = e.response?.data?.detail ?? 'Nutzer konnte nicht geändert werden.'
      throw e
    }
  }

  async function deleteUser(id: number): Promise<void> {
    error.value = null
    try {
      await authApi.deleteUser(id)
    } catch (e: any) {
      error.value = e.response?.data?.detail ?? 'Nutzer konnte nicht gelöscht werden.'
      throw e
    }
  }

  async function uploadAvatar(file: File): Promise<void> {
    error.value = null
    try {
      const { data } = await authApi.uploadAvatar(file)
      user.value = data
      localStorage.setItem('twonote_user', JSON.stringify(data))
      avatarVersion.value = Date.now()
    } catch (e: any) {
      error.value = e.response?.data?.detail ?? 'Profilbild konnte nicht hochgeladen werden.'
      throw e
    }
  }

  async function removeAvatar(): Promise<void> {
    error.value = null
    try {
      const { data } = await authApi.removeAvatar()
      user.value = data
      localStorage.setItem('twonote_user', JSON.stringify(data))
      avatarVersion.value = Date.now()
    } catch (e: any) {
      error.value = e.response?.data?.detail ?? 'Profilbild konnte nicht entfernt werden.'
      throw e
    }
  }

  return {
    token,
    user,
    loading,
    error,
    avatarVersion,
    isLoggedIn,
    username,
    isFirstUser,
    login,
    logout,
    register,
    registerNewUser,
    fetchUsers,
    updateUser,
    deleteUser,
    uploadAvatar,
    removeAvatar,
  }
})
