<template>
  <div class="user-menu">
    <!-- Trigger: runder Avatar-Button -->
    <button
      class="avatar-btn"
      :class="{ active: menuOpen }"
      title="Konto-Menü"
      @click="menuOpen = !menuOpen"
    >
      {{ initial }}
    </button>

    <!-- Dropdown (öffnet nach oben) -->
    <template v-if="menuOpen">
      <!-- Transparenter Backdrop schließt das Menü bei Klick daneben -->
      <div class="menu-backdrop" @click="menuOpen = false"></div>

      <div class="dropdown">
        <div class="dropdown-header">
          <span class="dropdown-label">Angemeldet als</span>
          <span class="dropdown-user">{{ auth.username }}</span>
        </div>

        <div class="dropdown-divider"></div>

        <button v-if="auth.isFirstUser" class="dropdown-item" @click="openUserManagement">
          Nutzer verwalten
        </button>

        <button class="dropdown-item danger" @click="handleLogout">
          Abmelden
        </button>
      </div>
    </template>

    <!-- Nutzerverwaltung (nur Admin) -->
    <UserManagement v-if="userMgmtOpen" @close="userMgmtOpen = false" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import UserManagement from '@/components/UserManagement.vue'

const router = useRouter()
const auth = useAuthStore()

const menuOpen = ref(false)
const userMgmtOpen = ref(false)

const initial = computed(() => (auth.username.charAt(0) || '?').toUpperCase())

function handleLogout() {
  menuOpen.value = false
  auth.logout()
  router.push({ name: 'login' })
}

function openUserManagement() {
  menuOpen.value = false
  userMgmtOpen.value = true
}

// Esc schließt Menü/Modal
function onKeydown(e: KeyboardEvent) {
  if (e.key !== 'Escape') return
  if (userMgmtOpen.value) userMgmtOpen.value = false
  else menuOpen.value = false
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
.user-menu {
  position: relative;
}

/* ── Trigger ── */
.avatar-btn {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 1px solid var(--border-default);
  background: var(--accent);
  color: #fff;
  font-size: 0.9rem;
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
  bottom: 44px;
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
</style>
