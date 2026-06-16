<template>
  <transition name="dialog-fade">
    <div class="overlay" @click.self="$emit('close')">
      <div class="dialog" role="dialog" aria-modal="true">
        <header class="head">
          <h3 class="title">Versionen</h3>
          <button class="close-btn" title="Schließen" @click="$emit('close')">×</button>
        </header>

        <div v-if="loading" class="state">
          <div class="spinner"></div>
        </div>

        <div v-else-if="error" class="state error">{{ error }}</div>

        <div v-else-if="versions.length === 0" class="state">
          Noch keine gespeicherten Versionen.
        </div>

        <ul v-else class="versions">
          <li
            v-for="(version, idx) in versions"
            :key="version.id"
            class="version"
            :class="{ active: version.id === currentVersionId }"
          >
            <button class="version-main" @click="$emit('select', version.id)">
              <div class="version-info">
                <span class="version-label">{{ version.label || `Version ${versions.length - idx}` }}</span>
                <span class="version-meta">{{ formatDate(version.updated_at) }}</span>
              </div>
              <span v-if="version.id === currentVersionId" class="badge">angezeigt</span>
            </button>
          </li>
        </ul>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { filesApi, type AnnotationVersion } from '@/api'

const props = defineProps<{
  fileId: string
  currentVersionId: number | null
}>()

defineEmits<{
  (e: 'select', versionId: number): void
  (e: 'close'): void
}>()

const versions = ref<AnnotationVersion[]>([])
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    const { data } = await filesApi.listAnnotationVersions(props.fileId)
    versions.value = data.versions
  } catch (e: any) {
    error.value = e.response?.data?.detail ?? 'Versionen konnten nicht geladen werden.'
  } finally {
    loading.value = false
  }
})

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.55);
  padding: 1rem;
}

.dialog {
  width: 100%;
  max-width: 440px;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: 8px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border-default);
}

.title {
  margin: 0;
  font-size: 1.0625rem;
  color: var(--text-primary);
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  font-size: 1.5rem;
  line-height: 1;
  cursor: pointer;
  padding: 0 0.25rem;
}

.close-btn:hover {
  color: var(--text-primary);
}

.state {
  padding: 2rem;
  text-align: center;
  color: var(--text-muted);
  font-size: 0.875rem;
}

.state.error {
  color: var(--color-red);
}

.spinner {
  width: 26px;
  height: 26px;
  margin: 0 auto;
  border: 2px solid var(--border-strong);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.versions {
  list-style: none;
  margin: 0;
  padding: 0.5rem;
  overflow-y: auto;
}

.version + .version {
  margin-top: 0.25rem;
}

.version-main {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  background: var(--bg-tertiary);
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 0.65rem 0.85rem;
  cursor: pointer;
  text-align: left;
  transition: all 0.15s;
}

.version-main:hover {
  background: var(--bg-elevated);
}

.version.active .version-main {
  border-color: var(--accent);
}

.version-info {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  min-width: 0;
}

.version-label {
  font-size: 0.875rem;
  color: var(--text-primary);
  font-weight: 500;
}

.version-meta {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.badge {
  flex-shrink: 0;
  font-size: 0.7rem;
  color: var(--accent-hover);
  background: #2a2040;
  border: 1px solid var(--accent);
  border-radius: 4px;
  padding: 0.15rem 0.4rem;
}

.dialog-fade-enter-active,
.dialog-fade-leave-active {
  transition: opacity 0.15s;
}

.dialog-fade-enter-from,
.dialog-fade-leave-to {
  opacity: 0;
}
</style>
