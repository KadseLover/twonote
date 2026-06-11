<template>
  <div class="user-menu">
    <!-- Trigger: runder Avatar-Button oben rechts -->
    <button
      class="avatar-btn"
      :class="{ active: menuOpen }"
      title="Konto-Menü"
      @click="menuOpen = !menuOpen"
    >
      {{ initial }}
    </button>

    <!-- Dropdown -->
    <template v-if="menuOpen">
      <!-- Transparenter Backdrop schließt das Menü bei Klick daneben -->
      <div class="menu-backdrop" @click="menuOpen = false"></div>

      <div class="dropdown">
        <div class="dropdown-header">
          <span class="dropdown-label">Angemeldet als</span>
          <span class="dropdown-user">{{ auth.username }}</span>
        </div>

        <div class="dropdown-divider"></div>

        <button v-if="auth.isFirstUser" class="dropdown-item" @click="openAddUser">
          Nutzer hinzufügen
        </button>

        <button class="dropdown-item danger" @click="handleLogout">
          Abmelden
        </button>
      </div>
    </template>

    <!-- Add-User-Modal (nur erster Nutzer) -->
    <template v-if="addUserOpen">
      <div class="modal-backdrop" @click="closeAddUser"></div>

      <div class="modal" role="dialog" aria-modal="true">
        <h3 class="modal-title">Neuen Nutzer anlegen</h3>

        <form @submit.prevent="submitAddUser">
          <div class="form-group">
            <label for="new-username">Benutzername</label>
            <input
              id="new-username"
              v-model="newUser.username"
              type="text"
              placeholder="Benutzername"
              required
              minlength="3"
              autocomplete="off"
            />
          </div>

          <div class="form-group">
            <label for="new-password">Passwort</label>
            <input
              id="new-password"
              v-model="newUser.password"
              type="password"
              placeholder="Passwort (mind. 6 Zeichen)"
              required
              minlength="6"
              autocomplete="new-password"
            />
          </div>

          <div v-if="addError" class="message error">{{ addError }}</div>
          <div v-if="addSuccess" class="message success">{{ addSuccess }}</div>

          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="closeAddUser">
              Schließen
            </button>
            <button type="submit" class="btn-primary" :disabled="adding">
              <span v-if="adding">Anlegen…</span>
              <span v-else>Anlegen</span>
            </button>
          </div>
        </form>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const menuOpen = ref(false)
const addUserOpen = ref(false)

const initial = computed(() => (auth.username.charAt(0) || '?').toUpperCase())

function handleLogout() {
  menuOpen.value = false
  auth.logout()
  router.push({ name: 'login' })
}

// ── Add-User ────────────────────────────────────────────────────────────────
const newUser = ref({ username: '', password: '' })
const adding = ref(false)
const addError = ref('')
const addSuccess = ref('')

function openAddUser() {
  menuOpen.value = false
  addError.value = ''
  addSuccess.value = ''
  newUser.value = { username: '', password: '' }
  addUserOpen.value = true
}

function closeAddUser() {
  addUserOpen.value = false
}

async function submitAddUser() {
  addError.value = ''
  addSuccess.value = ''
  adding.value = true
  try {
    const name = newUser.value.username
    await auth.registerNewUser(name, newUser.value.password)
    addSuccess.value = `Nutzer „${name}“ wurde angelegt.`
    newUser.value = { username: '', password: '' }
  } catch {
    addError.value = auth.error || 'Nutzer konnte nicht angelegt werden.'
  } finally {
    adding.value = false
  }
}

// Esc schließt Menü/Modal
function onKeydown(e: KeyboardEvent) {
  if (e.key !== 'Escape') return
  if (addUserOpen.value) addUserOpen.value = false
  else menuOpen.value = false
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
.user-menu {
  position: fixed;
  top: 0.6rem;
  right: 0.75rem;
  z-index: 50;
}

/* ── Trigger ── */
.avatar-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1px solid var(--border-default);
  background: var(--accent);
  color: #fff;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, box-shadow 0.15s;
}

.avatar-btn:hover,
.avatar-btn.active {
  background: var(--accent-hover);
  box-shadow: 0 0 0 2px rgba(127, 109, 242, 0.35);
}

/* ── Dropdown ── */
.menu-backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
}

.dropdown {
  position: absolute;
  top: 44px;
  right: 0;
  min-width: 200px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.55);
  padding: 0.35rem;
  z-index: 41;
}

.dropdown-header {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  padding: 0.5rem 0.6rem 0.55rem;
}

.dropdown-label {
  font-size: 0.6875rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-faint);
}

.dropdown-user {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dropdown-divider {
  height: 1px;
  background: var(--border-default);
  margin: 0.25rem 0;
}

.dropdown-item {
  display: block;
  width: 100%;
  text-align: left;
  background: transparent;
  border: none;
  border-radius: 4px;
  padding: 0.5rem 0.6rem;
  font-size: 0.8125rem;
  color: var(--text-primary);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.dropdown-item:hover {
  background: var(--bg-tertiary);
}

.dropdown-item.danger {
  color: var(--text-muted);
}

.dropdown-item.danger:hover {
  background: #2d1515;
  color: var(--color-red);
}

/* ── Modal ── */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  z-index: 60;
}

.modal {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: calc(100vw - 2rem);
  max-width: 380px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  padding: 1.5rem;
  z-index: 61;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6);
}

.modal-title {
  margin: 0 0 1.25rem;
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--text-primary);
}

.form-group {
  margin-bottom: 1rem;
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

.message {
  padding: 0.55rem 0.875rem;
  border-radius: 4px;
  font-size: 0.8125rem;
  margin-bottom: 1rem;
}

.message.error {
  background: #2d1515;
  color: var(--color-red);
  border: 1px solid #4d2020;
}

.message.success {
  background: #1a2d1a;
  color: var(--color-green);
  border: 1px solid #234a23;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.6rem;
  margin-top: 0.25rem;
}

.btn-secondary,
.btn-primary {
  padding: 0.55rem 1rem;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-secondary {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-muted);
}

.btn-secondary:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.btn-primary {
  background: var(--accent);
  border: 1px solid var(--accent);
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background: var(--accent-hover);
  border-color: var(--accent-hover);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
