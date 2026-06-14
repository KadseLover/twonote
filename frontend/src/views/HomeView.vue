<template>
  <div class="workspace">
    <!-- Mobile-Topbar mit Hamburger (nur ≤760px) -->
    <header class="mobile-topbar">
      <button class="hamburger-btn" title="Menü" @click="mobileNavOpen = !mobileNavOpen">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <line x1="3" y1="6" x2="21" y2="6"/>
          <line x1="3" y1="12" x2="21" y2="12"/>
          <line x1="3" y1="18" x2="21" y2="18"/>
        </svg>
      </button>
      <span class="topbar-title">TwoNote</span>
    </header>

    <div class="workspace-body">
      <!-- Backdrop für die mobile Schublade -->
      <div
        v-if="isMobile && mobileNavOpen"
        class="mobile-backdrop"
        @click="mobileNavOpen = false"
      ></div>

      <!-- Linke Leiste: Upload (oben) + Datei-Liste -->
      <aside
        v-show="isMobile || !sidebarCollapsed"
        class="sidebar"
        :class="{ 'mobile-open': mobileNavOpen }"
        :style="{ width: sidebarWidth + 'px' }"
      >
        <div class="sidebar-upload">
          <button class="upload-toggle" @click="uploadCollapsed = !uploadCollapsed">
            <span>Hochladen</span>
            <svg class="chevron" :class="{ collapsed: uploadCollapsed }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </button>
          <FileUpload v-show="!uploadCollapsed" @uploaded="onFileUploaded" />
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
          <button class="refresh-btn" @click="sidebarCollapsed = true" title="Leiste zuklappen">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="15 18 9 12 15 6"/>
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

        <!-- Footer: Home-Button (Viewer schließen) + Profil-Menü -->
        <div class="sidebar-footer">
          <button
            class="home-btn"
            :disabled="!activeFileId"
            title="Dokument schließen"
            @click="goHome"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
              <polyline points="9 22 9 12 15 12 15 22"/>
            </svg>
          </button>
          <UserMenu />
        </div>
      </aside>

      <!-- Resize-Handle für die Leiste -->
      <div
        v-show="!sidebarCollapsed"
        class="sidebar-resize"
        :class="{ dragging: isResizing }"
        @pointerdown="startResize"
        @dblclick="resetSidebarWidth"
        title="Ziehen zum Anpassen, Doppelklick zum Zurücksetzen"
      ></div>

      <!-- Aufklapp-Knopf wenn die Leiste zugeklappt ist -->
      <button
        v-show="sidebarCollapsed"
        class="sidebar-expand"
        title="Dateien einblenden"
        @click="sidebarCollapsed = false"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </button>

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
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useFilesStore } from '@/stores/files'
import { type DriveFile } from '@/api'
import FileUpload from '@/components/FileUpload.vue'
import FileSidebarList from '@/components/FileSidebarList.vue'
import DocumentViewer from '@/components/DocumentViewer.vue'
import UserMenu from '@/components/UserMenu.vue'
import { useIsMobile } from '@/utils/useIsMobile'

const route = useRoute()
const router = useRouter()
const filesStore = useFilesStore()

const { isMobile } = useIsMobile()
const mobileNavOpen = ref(false)

const activeFileId = computed(() => (route.params.id as string) || '')

// Breite der linken Leiste (anpassbar, in localStorage gespeichert)
const SIDEBAR_DEFAULT = 320
const SIDEBAR_MIN = 220
const SIDEBAR_MAX = 560
const SIDEBAR_STORAGE_KEY = 'twonote.fileSidebarWidth'
const SIDEBAR_COLLAPSED_KEY = 'twonote.fileSidebarCollapsed'

const sidebarWidth = ref(loadSidebarWidth())
const isResizing = ref(false)
const sidebarCollapsed = ref(localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === '1')

watch(sidebarCollapsed, (v) => {
  localStorage.setItem(SIDEBAR_COLLAPSED_KEY, v ? '1' : '0')
})

const UPLOAD_COLLAPSED_KEY = 'twonote.uploadCollapsed'
const uploadCollapsed = ref(localStorage.getItem(UPLOAD_COLLAPSED_KEY) === '1')

watch(uploadCollapsed, (v) => {
  localStorage.setItem(UPLOAD_COLLAPSED_KEY, v ? '1' : '0')
})

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

function navigateIntoFolder(file: DriveFile) {
  filesStore.navigateIntoFolder(file)
}

function openFile(file: DriveFile) {
  filesStore.setActiveFile(file)
  router.push({ name: 'file', params: { id: file.id } })
  // Auf dem Handy: Schublade schließen, damit der Viewer sichtbar wird.
  mobileNavOpen.value = false
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

function goHome() {
  router.push({ name: 'home' })
  mobileNavOpen.value = false
}
</script>

<style scoped>
.workspace {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-primary);
}

/* ── Mobile-Topbar (nur ≤760px sichtbar) ────────────────────── */
.mobile-topbar {
  display: none;
  align-items: center;
  gap: 0.75rem;
  flex-shrink: 0;
  padding: 0.5rem 0.75rem;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-default);
}

.hamburger-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background: none;
  border: 1px solid var(--border-default);
  border-radius: 4px;
  color: var(--text-primary);
  cursor: pointer;
}

.hamburger-btn svg {
  width: 20px;
  height: 20px;
}

.topbar-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.mobile-backdrop {
  display: none;
}

.workspace-body {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  position: relative;
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

.upload-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  background: none;
  border: none;
  padding: 0 0 0.6rem;
  cursor: pointer;
  color: var(--text-muted);
  font-size: 0.6875rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  transition: color 0.15s;
}

.upload-toggle:hover {
  color: var(--text-primary);
}

.upload-toggle .chevron {
  width: 15px;
  height: 15px;
  transition: transform 0.15s;
}

.upload-toggle .chevron.collapsed {
  transform: rotate(-90deg);
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

/* ── Footer: Home + Profil ──────────────────────────────────── */
.sidebar-footer {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
  padding: 0.6rem 0.75rem;
  border-top: 1px solid var(--border-default);
}

.home-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  background: none;
  border: 1px solid var(--border-default);
  border-radius: 4px;
  cursor: pointer;
  color: var(--text-muted);
  transition: all 0.15s;
}

.home-btn svg {
  width: 16px;
  height: 16px;
}

.home-btn:hover:not(:disabled) {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.home-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Profil-Menü ans rechte Ende schieben */
.sidebar-footer :deep(.user-menu) {
  margin-left: auto;
}

/* ── Aufklapp-Knopf (zugeklappte Leiste) ────────────────────── */
.sidebar-expand {
  align-self: flex-start;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 22px;
  height: 48px;
  margin-top: 0.6rem;
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-left: none;
  border-radius: 0 6px 6px 0;
  cursor: pointer;
  color: var(--text-muted);
  transition: all 0.15s;
}

.sidebar-expand svg {
  width: 14px;
  height: 14px;
}

.sidebar-expand:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
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

/* ── Schmale Bildschirme: Datei-Liste als Schublade (Overlay) ── */
@media (max-width: 760px) {
  .mobile-topbar {
    display: flex;
  }

  /* Sidebar wird zur fixierten Schublade, die von links einschiebt */
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: min(85%, 320px) !important;
    max-width: 320px;
    border-right: 1px solid var(--border-default);
    z-index: 70;
    transform: translateX(-100%);
    transition: transform 0.2s ease;
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.45);
  }

  .sidebar.mobile-open {
    transform: translateX(0);
  }

  .mobile-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 65;
  }

  /* Desktop-Resize/Collapse-Bedienelemente auf Mobil ausblenden */
  .sidebar-resize,
  .sidebar-expand {
    display: none;
  }

  /* Den „Leiste zuklappen"-Chevron im sidebar-nav ausblenden (zweiter refresh-btn) */
  .sidebar-nav .refresh-btn:last-child {
    display: none;
  }

  .viewer-area {
    width: 100%;
  }
}
</style>
