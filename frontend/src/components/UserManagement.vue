<template>
  <div class="modal-backdrop" @click="$emit('close')"></div>

  <div class="modal" role="dialog" aria-modal="true">
    <h3 class="modal-title">Nutzerverwaltung</h3>

    <div v-if="loadError" class="message error">{{ loadError }}</div>

    <!-- Nutzerliste -->
    <ul v-if="!loading" class="user-list">
      <li v-for="u in users" :key="u.id" class="user-row">
        <template v-if="editId === u.id">
          <!-- Bearbeiten-Formular -->
          <form class="edit-form" @submit.prevent="submitEdit(u)">
            <input
              v-model="edit.username"
              type="text"
              placeholder="Benutzername"
              minlength="3"
              autocomplete="off"
            />
            <input
              v-model="edit.password"
              type="password"
              placeholder="Neues Passwort (leer = unverändert)"
              minlength="6"
              autocomplete="new-password"
            />
            <div class="row-actions">
              <button type="submit" class="btn-primary sm" :disabled="busy">Speichern</button>
              <button type="button" class="btn-secondary sm" @click="cancelEdit">Abbrechen</button>
            </div>
          </form>
        </template>

        <template v-else>
          <div class="user-info">
            <div class="user-avatar">
              <img v-if="u.has_avatar" :src="avatarUrl(u)" class="avatar-img" alt="" />
              <span v-else>{{ (u.username.charAt(0) || '?').toUpperCase() }}</span>
            </div>
            <span class="user-name">{{ u.username }}</span>
            <span v-if="u.id === 1" class="badge">Admin</span>
          </div>
          <div class="row-actions">
            <button class="btn-secondary sm" @click="startEdit(u)">Bearbeiten</button>
            <button
              v-if="u.id !== 1"
              class="btn-danger sm"
              :disabled="busy"
              @click="handleDelete(u)"
            >
              Löschen
            </button>
          </div>
        </template>
      </li>
    </ul>

    <div v-else class="loading-hint">Lade Nutzer…</div>

    <div class="dropdown-divider"></div>

    <!-- Neuen Nutzer anlegen -->
    <form class="add-form" @submit.prevent="submitAdd">
      <h4 class="section-title">Neuen Nutzer anlegen</h4>
      <div class="form-group">
        <input
          v-model="newUser.username"
          type="text"
          placeholder="Benutzername"
          required
          minlength="3"
          autocomplete="off"
        />
      </div>
      <div class="form-group">
        <input
          v-model="newUser.password"
          type="password"
          placeholder="Passwort (mind. 6 Zeichen)"
          required
          minlength="6"
          autocomplete="new-password"
        />
      </div>

      <div v-if="actionError" class="message error">{{ actionError }}</div>
      <div v-if="actionSuccess" class="message success">{{ actionSuccess }}</div>

      <div class="modal-actions">
        <button type="button" class="btn-secondary" @click="$emit('close')">Schließen</button>
        <button type="submit" class="btn-primary" :disabled="busy">Anlegen</button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { authApi, type UserResponse } from '@/api'

defineEmits<{ close: [] }>()

const auth = useAuthStore()

function avatarUrl(u: UserResponse): string {
  return authApi.avatarUrl(u.id, auth.avatarVersion)
}

const users = ref<UserResponse[]>([])
const loading = ref(true)
const loadError = ref('')
const busy = ref(false)
const actionError = ref('')
const actionSuccess = ref('')

const editId = ref<number | null>(null)
const edit = ref({ username: '', password: '' })
const newUser = ref({ username: '', password: '' })

async function loadUsers() {
  loading.value = true
  loadError.value = ''
  try {
    users.value = await auth.fetchUsers()
  } catch {
    loadError.value = auth.error || 'Nutzer konnten nicht geladen werden.'
  } finally {
    loading.value = false
  }
}

function startEdit(u: UserResponse) {
  actionError.value = ''
  actionSuccess.value = ''
  editId.value = u.id
  edit.value = { username: u.username, password: '' }
}

function cancelEdit() {
  editId.value = null
}

async function submitEdit(u: UserResponse) {
  actionError.value = ''
  actionSuccess.value = ''
  busy.value = true
  try {
    const payload: { username?: string; password?: string } = {}
    if (edit.value.username && edit.value.username !== u.username) {
      payload.username = edit.value.username
    }
    if (edit.value.password) payload.password = edit.value.password
    if (Object.keys(payload).length > 0) {
      await auth.updateUser(u.id, payload)
    }
    editId.value = null
    actionSuccess.value = `Nutzer „${edit.value.username}“ wurde aktualisiert.`
    await loadUsers()
  } catch {
    actionError.value = auth.error || 'Änderung fehlgeschlagen.'
  } finally {
    busy.value = false
  }
}

async function handleDelete(u: UserResponse) {
  if (!confirm(`Nutzer „${u.username}“ wirklich löschen?`)) return
  actionError.value = ''
  actionSuccess.value = ''
  busy.value = true
  try {
    await auth.deleteUser(u.id)
    actionSuccess.value = `Nutzer „${u.username}“ wurde gelöscht.`
    await loadUsers()
  } catch {
    actionError.value = auth.error || 'Löschen fehlgeschlagen.'
  } finally {
    busy.value = false
  }
}

async function submitAdd() {
  actionError.value = ''
  actionSuccess.value = ''
  busy.value = true
  try {
    const name = newUser.value.username
    await auth.registerNewUser(name, newUser.value.password)
    actionSuccess.value = `Nutzer „${name}“ wurde angelegt.`
    newUser.value = { username: '', password: '' }
    await loadUsers()
  } catch {
    actionError.value = auth.error || 'Nutzer konnte nicht angelegt werden.'
  } finally {
    busy.value = false
  }
}

onMounted(loadUsers)
</script>

<style scoped>
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
  max-width: 460px;
  max-height: calc(100vh - 3rem);
  overflow-y: auto;
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

.user-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.user-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.5rem 0.6rem;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  border-radius: 5px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.user-avatar {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  border-radius: 50%;
  overflow: hidden;
  background: var(--accent);
  color: #fff;
  font-size: 0.75rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-avatar .avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.user-name {
  font-size: 0.875rem;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.badge {
  font-size: 0.625rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #fff;
  background: var(--accent);
  border-radius: 3px;
  padding: 0.1rem 0.35rem;
}

.row-actions {
  display: flex;
  gap: 0.4rem;
  flex-shrink: 0;
}

.edit-form {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  width: 100%;
}

.edit-form input,
.form-group input {
  width: 100%;
  padding: 0.5rem 0.75rem;
  background: var(--bg-primary);
  border: 1px solid var(--border-default);
  border-radius: 4px;
  font-size: 0.875rem;
  color: var(--text-primary);
  outline: none;
  transition: border-color 0.15s;
}

.edit-form input:focus,
.form-group input:focus {
  border-color: var(--accent);
}

.edit-form input::placeholder,
.form-group input::placeholder {
  color: var(--text-faint);
}

.loading-hint {
  color: var(--text-muted);
  font-size: 0.875rem;
  padding: 0.5rem 0;
}

.dropdown-divider {
  height: 1px;
  background: var(--border-default);
  margin: 1.25rem 0;
}

.section-title {
  margin: 0 0 0.75rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-muted);
}

.form-group {
  margin-bottom: 0.6rem;
}

.message {
  padding: 0.55rem 0.875rem;
  border-radius: 4px;
  font-size: 0.8125rem;
  margin: 0.5rem 0;
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
  margin-top: 0.75rem;
}

.btn-secondary,
.btn-primary,
.btn-danger {
  padding: 0.55rem 1rem;
  border-radius: 4px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.btn-secondary.sm,
.btn-primary.sm,
.btn-danger.sm {
  padding: 0.35rem 0.6rem;
  font-size: 0.75rem;
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

.btn-danger {
  background: transparent;
  border: 1px solid #4d2020;
  color: var(--color-red);
}

.btn-danger:hover:not(:disabled) {
  background: #2d1515;
}

.btn-primary:disabled,
.btn-danger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
