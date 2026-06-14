<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <h1>TwoNote</h1>
        <p v-if="isRegister">Ersten Account anlegen – dieser wird zum Admin.</p>
        <p v-else>Bitte melde dich an.</p>
      </div>

      <!-- Lade-Zustand, bis der Setup-Status bekannt ist -->
      <div v-if="needsSetup === null" class="loading-hint">Lädt…</div>

      <form v-else @submit.prevent="handleSubmit">
        <div class="form-group">
          <label for="username">Benutzername</label>
          <input
            id="username"
            v-model="form.username"
            type="text"
            placeholder="Benutzername eingeben"
            required
            minlength="3"
            autocomplete="username"
          />
        </div>

        <div class="form-group">
          <label for="password">Passwort</label>
          <input
            id="password"
            v-model="form.password"
            type="password"
            placeholder="Passwort eingeben"
            required
            minlength="6"
            :autocomplete="isRegister ? 'new-password' : 'current-password'"
          />
        </div>

        <div v-if="error" class="error-message">
          {{ error }}
        </div>

        <button type="submit" class="submit-btn" :disabled="loading">
          <span v-if="loading">Bitte warten…</span>
          <span v-else-if="isRegister">Account anlegen →</span>
          <span v-else>Anmelden →</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api'

const router = useRouter()
const auth = useAuthStore()

// null = Status wird geladen; true = keine Nutzer → Registrieren; false = Anmelden
const needsSetup = ref<boolean | null>(null)
const isRegister = computed(() => needsSetup.value === true)

const form = ref({ username: '', password: '' })
const error = ref('')
const loading = ref(false)

onMounted(async () => {
  try {
    const { data } = await authApi.setupStatus()
    needsSetup.value = !data.has_users
  } catch {
    // Im Zweifel Anmelden anzeigen
    needsSetup.value = false
  }
})

async function handleSubmit() {
  error.value = ''
  loading.value = true
  try {
    if (isRegister.value) {
      await auth.register(form.value.username, form.value.password)
      // Nach Registrierung direkt einloggen
      await auth.login(form.value.username, form.value.password)
    } else {
      await auth.login(form.value.username, form.value.password)
    }
    router.push({ name: 'home' })
  } catch (e: any) {
    error.value = auth.error || 'Ein Fehler ist aufgetreten.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  padding: 1rem;
}

.login-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  padding: 2.5rem;
  width: 100%;
  max-width: 400px;
}

.login-header {
  text-align: center;
  margin-bottom: 2rem;
}

.login-header h1 {
  font-size: 1.75rem;
  font-weight: 600;
  margin: 0 0 0.4rem;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}

.login-header p {
  color: var(--text-muted);
  margin: 0;
  font-size: 0.875rem;
}

.loading-hint {
  text-align: center;
  color: var(--text-muted);
  font-size: 0.875rem;
  padding: 1.5rem 0;
}

.form-group {
  margin-bottom: 1.125rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.35rem;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-muted);
}

.form-group input {
  width: 100%;
  padding: 0.6rem 0.875rem;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 4px;
  font-size: 0.9375rem;
  color: var(--text-primary);
  outline: none;
  transition: border-color 0.15s;
  box-sizing: border-box;
}

.form-group input::placeholder {
  color: var(--text-faint);
}

.form-group input:focus {
  border-color: var(--accent);
}

.error-message {
  background: #2d1515;
  color: var(--color-red);
  padding: 0.6rem 0.875rem;
  border-radius: 4px;
  font-size: 0.8125rem;
  margin-bottom: 1rem;
  border: 1px solid #4d2020;
}

.submit-btn {
  width: 100%;
  padding: 0.7rem;
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 0.9375rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}

.submit-btn:hover:not(:disabled) {
  background: var(--accent-hover);
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
