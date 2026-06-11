<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <h1>TwoNote</h1>
        <p>Dein persönlicher Dokumenten-Manager</p>
      </div>

      <!-- Tab-Umschalter -->
      <div class="tab-switcher">
        <button :class="{ active: mode === 'login' }" @click="mode = 'login'">
          Anmelden
        </button>
        <button :class="{ active: mode === 'register' }" @click="mode = 'register'">
          Registrieren
        </button>
      </div>

      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label for="username">Benutzername</label>
          <input
            id="username"
            v-model="form.username"
            type="text"
            placeholder="Benutzername eingeben"
            required
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
            autocomplete="current-password"
            minlength="6"
          />
        </div>

        <div v-if="error" class="error-message">
          {{ error }}
        </div>

        <button type="submit" class="submit-btn" :disabled="loading">
          <span v-if="loading">Bitte warten…</span>
          <span v-else-if="mode === 'login'">Anmelden →</span>
          <span v-else>Registrieren →</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const mode = ref<'login' | 'register'>('login')
const form = ref({ username: '', password: '' })
const error = ref('')
const loading = ref(false)

async function handleSubmit() {
  error.value = ''
  loading.value = true
  try {
    if (mode.value === 'login') {
      await auth.login(form.value.username, form.value.password)
      router.push({ name: 'home' })
    } else {
      await auth.register(form.value.username, form.value.password)
      // Nach Registrierung direkt einloggen
      await auth.login(form.value.username, form.value.password)
      router.push({ name: 'home' })
    }
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

.tab-switcher {
  display: flex;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 4px;
  padding: 3px;
  margin-bottom: 1.5rem;
}

.tab-switcher button {
  flex: 1;
  padding: 0.4rem;
  border: none;
  background: transparent;
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.875rem;
  color: var(--text-muted);
  transition: all 0.15s;
}

.tab-switcher button.active {
  background: var(--bg-elevated);
  color: var(--text-primary);
  font-weight: 500;
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
