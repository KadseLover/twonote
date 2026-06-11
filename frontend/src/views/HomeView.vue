<template>
  <div class="workspace">
    <!-- Kopfzeile -->
    <header class="app-header">
      <h1>TwoNote</h1>
      <div class="header-right">
        <span class="username">{{ auth.username }}</span>
        <button class="btn btn-ghost" @click="handleLogout">Abmelden</button>
      </div>
    </header>

    <div class="workspace-body">
      <!-- Linke Leiste: Upload (oben) + Datei-Liste -->
      <aside class="sidebar" :style="{ width: sidebarWidth + 'px' }">
        <div class="sidebar-upload">
          <FileUpload @uploaded="onFileUploaded" />
        </div>

        <div v-if="filesStore.error" class="error-banner">
          {{ filesStore.error }}
        </div>

        <!-- Breadcrumb-Navigation + Aktualisieren -->
        <div class="sidebar-nav">
          <nav class="breadcrumb" aria-label="Ordner-Navigation">
            <button class="crumb-btn" :class="{ active: filesStore.folderPath.length === 0 }" @click="filesStore.navigateToIndex(-1)">
              Alle Dokumente
            </button>
            <template v-for="(crumb, i) in filesStore.folderPath" :key="crumb.id">
              <span class="crumb-sep">/</span>
              <button
                class="crumb-btn"
                :class="{ active: i === filesStore.folderPath.length - 1 }"
                @click="filesStore.navigateToIndex(i)"
              >
                {{ crumb.name }}
              </button>
            </template>
          </nav>
          <button class="refresh-btn" @click="filesStore.fetchFiles()" :disabled="filesStore.loading" title="Aktualisieren">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" :class="{ spinning: filesStore.loading }">
              <polyline points="23 4 23 10 17 10"/>
              <polyline points="1 20 1 14 7 14"/>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
            </svg>
          </button>
        </div>

        <!-- Datei-Liste (scrollbar) -->
        <div class="sidebar-files">
          <FileSidebarList
            :files="filesStore.files"
            :loading="filesStore.loading"
            :active-id="activeFileId"
            @open="openFile"
            @navigate="navigateIntoFolder"
            @delete="handleDelete"
          />
        </div>
      </aside>

      <!-- Resize-Handle für die Leiste -->
      <div
        class="sidebar-resize"
        :class="{ dragging: isResizing }"
        @pointerdown="startResize"
        @dblclick="resetSidebarWidth"
        title="Ziehen zum Anpassen, Doppelklick zum Zurücksetzen"
      ></div>

      <!-- Rechter Bereich: Dokument-Viewer -->
      <main class="viewer-area">
        <DocumentViewer v-if="activeFileId" :key="activeFileId" :file-id="activeFileId" />
        <div v-else class="empty-viewer">
          <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          <p>Wähle links ein Dokument aus, um es anzuzeigen.</p>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useFilesStore } from '@/stores/files'
import { type DriveFile } from '@/api'
import FileUpload from '@/components/FileUpload.vue'
import FileSidebarList from '@/components/FileSidebarList.vue'
import DocumentViewer from '@/components/DocumentViewer.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const filesStore = useFilesStore()

const activeFileId = computed(() => (route.params.id as string) || '')

// Breite der linken Leiste (anpassbar, in localStorage gespeichert)
const SIDEBAR_DEFAULT = 320
const SIDEBAR_MIN = 220
const SIDEBAR_MAX = 560
const SIDEBAR_STORAGE_KEY = 'twonote.fileSidebarWidth'

const sidebarWidth = ref(loadSidebarWidth())
const isResizing = ref(false)

function loadSidebarWidth(): number {
  const stored = localStorage.getItem(SIDEBAR_STORAGE_KEY)
  const n = stored ? parseInt(stored, 10) : NaN
  if (!isNaN(n) && n >= SIDEBAR_MIN) return Math.min(n, SIDEBAR_MAX)
  return SIDEBAR_DEFAULT
}

function clampWidth(w: number): number {
  return Math.min(Math.max(w, SIDEBAR_MIN), SIDEBAR_MAX)
}

function startResize(e: PointerEvent) {
  isResizing.value = true
  const startX = e.clientX
  const startWidth = sidebarWidth.value
  ;(e.target as HTMLElement).setPointerCapture(e.pointerId)

  const onMove = (ev: PointerEvent) => {
    sidebarWidth.value = clampWidth(startWidth + (ev.clientX - startX))
  }
  const onUp = () => {
    isResizing.value = false
    localStorage.setItem(SIDEBAR_STORAGE_KEY, String(sidebarWidth.value))
    window.removeEventListener('pointermove', onMove)
    window.removeEventListener('pointerup', onUp)
  }
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', onUp)
}

function resetSidebarWidth() {
  sidebarWidth.value = SIDEBAR_DEFAULT
  localStorage.setItem(SIDEBAR_STORAGE_KEY, String(SIDEBAR_DEFAULT))
}

onMounted(() => {
  filesStore.fetchFiles()
})

function handleLogout() {
  auth.logout()
  router.push({ name: 'login' })
}

function navigateIntoFolder(file: DriveFile) {
  filesStore.navigateIntoFolder(file)
}

function openFile(file: DriveFile) {
  filesStore.setActiveFile(file)
  router.push({ name: 'file', params: { id: file.id } })
}

async function handleDelete(file: DriveFile) {
  if (!confirm(`"${file.name}" wirklich löschen?`)) return
  await filesStore.deleteFile(file.id)
  // War die gelöschte Datei gerade geöffnet? Viewer schließen.
  if (file.id === activeFileId.value) {
    router.push({ name: 'home' })
  }
}

function onFileUploaded() {
  filesStore.fetchFiles()
}
</script>

<style scoped>
.workspace {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-primary);
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.5rem;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.app-header h1 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.875rem;
}

.username {
  color: var(--text-muted);
  font-size: 0.8125rem;
}

.workspace-body {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

/* ── Linke Leiste ───────────────────────────────────────────── */
.sidebar {
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  min-height: 0;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-default);
}

.sidebar-upload {
  padding: 1rem;
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.error-banner {
  margin: 0.75rem 1rem 0;
  background: #2d1515;
  color: var(--color-red);
  padding: 0.5rem 0.7rem;
  border-radius: 4px;
  border: 1px solid #4d2020;
  font-size: 0.8125rem;
}

.sidebar-nav {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem 0.5rem;
  flex-shrink: 0;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  flex: 1;
  min-width: 0;
  flex-wrap: wrap;
}

.crumb-sep {
  color: var(--text-faint);
  font-size: 0.75rem;
  flex-shrink: 0;
}

.crumb-btn {
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  font-size: 0.8125rem;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color 0.15s;
}

.crumb-btn:hover {
  color: var(--text-primary);
}

.crumb-btn.active {
  color: var(--text-primary);
  font-weight: 500;
  cursor: default;
}

.refresh-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: none;
  border: 1px solid var(--border-default);
  border-radius: 4px;
  padding: 0.3rem;
  cursor: pointer;
  color: var(--text-muted);
  transition: all 0.15s;
}

.refresh-btn svg {
  width: 14px;
  height: 14px;
}

.refresh-btn svg.spinning {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.refresh-btn:hover:not(:disabled) {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.sidebar-files {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0.25rem 0.5rem 1rem;
}

/* ── Resize-Handle ──────────────────────────────────────────── */
.sidebar-resize {
  width: 5px;
  flex-shrink: 0;
  cursor: col-resize;
  background: transparent;
  transition: background 0.15s;
  touch-action: none;
  user-select: none;
}

.sidebar-resize:hover,
.sidebar-resize.dragging {
  background: var(--accent);
}

/* ── Rechter Viewer-Bereich ─────────────────────────────────── */
.viewer-area {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.empty-viewer {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  color: var(--text-muted);
  text-align: center;
  padding: 2rem;
}

.empty-icon {
  width: 48px;
  height: 48px;
  color: var(--text-faint);
}

.btn {
  padding: 0.4rem 0.875rem;
  border-radius: 4px;
  border: 1px solid var(--border-default);
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 500;
  transition: all 0.15s;
}

.btn-ghost {
  background: transparent;
  color: var(--text-muted);
}

.btn-ghost:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

/* ── Schmale Bildschirme: Leiste oben, Viewer darunter ──────── */
@media (max-width: 760px) {
  .workspace-body {
    flex-direction: column;
  }
  .sidebar {
    width: 100% !important;
    max-height: 45vh;
    border-right: none;
    border-bottom: 1px solid var(--border-default);
  }
  .sidebar-resize {
    display: none;
  }
}
</style>
