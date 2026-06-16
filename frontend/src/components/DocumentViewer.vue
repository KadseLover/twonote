<template>
  <div class="document-viewer">
    <!-- Speicher-Status als schwebende Anzeige -->
    <transition name="toast">
      <span v-if="saveStatus" class="save-status" :class="saveStatusClass">
        {{ saveStatus }}
      </span>
    </transition>

    <!-- Lade-Zustand -->
    <div v-if="loading" class="loading-overlay">
      <div class="spinner"></div>
      <p>Dokument wird geladen…</p>
    </div>

    <!-- Fehler -->
    <div v-else-if="loadError" class="error-state">
      <p>{{ loadError }}</p>
      <button @click="loadFile">Erneut versuchen</button>
    </div>

    <!-- Viewer-Layout -->
    <div v-else class="viewer-layout">
      <!-- Hauptbereich: PDF-Editor oder Word-Viewer -->
      <div class="viewer-main">
        <PdfEditor
          v-if="docData && isPdf"
          :pdf-data="docData"
          :file-id="fileId"
          @save-status="onSaveStatus"
        />
        <WordViewer
          v-else-if="docData && isWord"
          :doc-data="docData"
          :mime-type="mimeType"
          :filename="filename"
        />
        <div v-else class="error-state">
          <p>Dieser Dateityp wird nicht unterstützt.</p>
        </div>
      </div>

      <!-- Toggle: Zusammenfassungs-Leiste ein-/zuklappen -->
      <button
        class="summary-toggle"
        :title="summaryCollapsed ? 'Zusammenfassung einblenden' : 'Zusammenfassung zuklappen'"
        @click="summaryCollapsed = !summaryCollapsed"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <polyline :points="summaryCollapsed ? '15 18 9 12 15 6' : '9 18 15 12 9 6'"/>
        </svg>
      </button>

      <!-- Resize-Handle -->
      <div
        v-show="!summaryCollapsed"
        class="resize-handle"
        :class="{ dragging: isResizing }"
        @pointerdown="startResize"
        @dblclick="resetSidebarWidth"
        title="Ziehen zum Anpassen, Doppelklick zum Zurücksetzen"
      ></div>

      <!-- Backdrop für die Zusammenfassung als Overlay (mobil) -->
      <div
        v-if="isMobile && !summaryCollapsed"
        class="summary-backdrop"
        @click="summaryCollapsed = true"
      ></div>

      <!-- KI-Zusammenfassung (Seitenleiste) -->
      <aside v-show="!summaryCollapsed" class="summary-sidebar" :style="{ width: sidebarWidth + 'px' }">
        <SummaryPanel :file-id="fileId" :filename="filename" />
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useFilesStore } from '@/stores/files'
import PdfEditor from '@/components/PdfEditor.vue'
import WordViewer from '@/components/WordViewer.vue'
import SummaryPanel from '@/components/SummaryPanel.vue'
import { useIsMobile } from '@/utils/useIsMobile'

const props = defineProps<{
  fileId: string
}>()

const filesStore = useFilesStore()
const { isMobile } = useIsMobile()

const SIDEBAR_DEFAULT = 340
const SIDEBAR_MIN = 240
const SIDEBAR_MAX_RATIO = 0.6
const SIDEBAR_STORAGE_KEY = 'twonote.sidebarWidth'
const SIDEBAR_COLLAPSED_KEY = 'twonote.summaryCollapsed'

const sidebarWidth = ref(loadSidebarWidth())
const isResizing = ref(false)
// Auf dem Handy ist die Zusammenfassung standardmäßig zugeklappt (Overlay).
const summaryCollapsed = ref(
  isMobile.value ? true : localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === '1'
)

watch(summaryCollapsed, (v) => {
  localStorage.setItem(SIDEBAR_COLLAPSED_KEY, v ? '1' : '0')
})

function loadSidebarWidth(): number {
  const stored = localStorage.getItem(SIDEBAR_STORAGE_KEY)
  const n = stored ? parseInt(stored, 10) : NaN
  if (!isNaN(n) && n >= SIDEBAR_MIN) return n
  return SIDEBAR_DEFAULT
}

function clampWidth(w: number): number {
  const max = Math.max(SIDEBAR_MIN + 100, Math.floor(window.innerWidth * SIDEBAR_MAX_RATIO))
  return Math.min(Math.max(w, SIDEBAR_MIN), max)
}

function startResize(e: PointerEvent) {
  isResizing.value = true
  const startX = e.clientX
  const startWidth = sidebarWidth.value
  ;(e.target as HTMLElement).setPointerCapture(e.pointerId)

  const onMove = (ev: PointerEvent) => {
    sidebarWidth.value = clampWidth(startWidth + (startX - ev.clientX))
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

const docData = ref<ArrayBuffer | null>(null)
const mimeType = ref('')
const loading = ref(true)
const loadError = ref('')
const saveStatus = ref('')

const filename = computed(
  () => filesStore.getFileById(props.fileId)?.name ?? 'Dokument'
)

const isPdf = computed(
  () => mimeType.value === 'application/pdf' || filename.value.toLowerCase().endsWith('.pdf')
)
const isWord = computed(() => {
  const m = mimeType.value
  const n = filename.value.toLowerCase()
  return (
    m.includes('wordprocessingml') ||
    m === 'application/msword' ||
    n.endsWith('.docx') ||
    n.endsWith('.doc')
  )
})

const saveStatusClass = computed(() => ({
  'status-saving': saveStatus.value === 'Speichern…' || saveStatus.value === 'Export…',
  'status-saved': saveStatus.value === 'Gespeichert' || saveStatus.value === 'Exportiert',
  'status-error': saveStatus.value.startsWith('Fehler'),
}))

async function loadFile() {
  loading.value = true
  loadError.value = ''
  try {
    const blob = await filesStore.downloadFileBlob(props.fileId)
    if (!blob) throw new Error('Datei konnte nicht geladen werden')
    mimeType.value = blob.type
    docData.value = await blob.arrayBuffer()
  } catch (e: any) {
    loadError.value = e.message || 'Unbekannter Fehler beim Laden'
  } finally {
    loading.value = false
  }
}

function onSaveStatus(status: string) {
  saveStatus.value = status
  if (status === 'Gespeichert' || status === 'Exportiert' || status.startsWith('Fehler')) {
    setTimeout(() => {
      saveStatus.value = ''
    }, 3000)
  }
}

onMounted(() => {
  loadFile()
})
</script>

<style scoped>
.document-viewer {
  position: relative;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--bg-primary);
}

/* Schwebende Speicher-Status-Anzeige */
.save-status {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  z-index: 20;
  font-size: 0.8125rem;
  padding: 0.35rem 0.75rem;
  border-radius: 4px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
  pointer-events: none;
}

.status-saving { background: #1a2a3a; color: #6aaddb; }
.status-saved  { background: #1a2d1a; color: var(--color-green); }
.status-error  { background: #2d1515; color: var(--color-red); }

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.2s, transform 0.2s;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.loading-overlay,
.error-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
  gap: 1rem;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 2px solid var(--border-strong);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.viewer-layout {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.viewer-main {
  flex: 1;
  overflow: auto;
  background: #181818;
}

.summary-sidebar {
  flex-shrink: 0;
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-default);
  overflow-y: auto;
}

.summary-toggle {
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
  border-right: none;
  border-radius: 6px 0 0 6px;
  cursor: pointer;
  color: var(--text-muted);
  transition: all 0.15s;
}

.summary-toggle svg {
  width: 14px;
  height: 14px;
}

.summary-toggle:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.resize-handle {
  width: 5px;
  flex-shrink: 0;
  cursor: col-resize;
  background: transparent;
  transition: background 0.15s;
  touch-action: none;
  user-select: none;
}

.resize-handle:hover,
.resize-handle.dragging {
  background: var(--accent);
}

/* Auf schmalen Bildschirmen wird die Zusammenfassung zum Overlay-Drawer von rechts. */
@media (max-width: 900px) {
  .resize-handle {
    display: none;
  }

  .summary-backdrop {
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 25;
  }

  .summary-sidebar {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    width: min(85%, 340px) !important;
    border-left: 1px solid var(--border-default);
    z-index: 26;
    box-shadow: -4px 0 24px rgba(0, 0, 0, 0.45);
  }
}
</style>
