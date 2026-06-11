<template>
  <div class="editor-view">
    <!-- Header -->
    <header class="editor-header">
      <div class="header-left">
        <button class="btn-back" @click="router.push({ name: 'home' })">
          ← Zurück
        </button>
        <h2 class="file-name">{{ filename }}</h2>
      </div>
      <div class="header-right">
        <span v-if="saveStatus" class="save-status" :class="saveStatusClass">
          {{ saveStatus }}
        </span>
      </div>
    </header>

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

    <!-- Editor-Layout -->
    <div v-else class="editor-layout">
      <!-- Hauptbereich: PDF-Editor oder Word-Viewer -->
      <div class="editor-main">
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

      <!-- Resize-Handle -->
      <div
        class="resize-handle"
        :class="{ dragging: isResizing }"
        @pointerdown="startResize"
        @dblclick="resetSidebarWidth"
        title="Ziehen zum Anpassen, Doppelklick zum Zurücksetzen"
      ></div>

      <!-- KI-Zusammenfassung (Seitenleiste) -->
      <aside class="editor-sidebar" :style="{ width: sidebarWidth + 'px' }">
        <SummaryPanel :file-id="fileId" :filename="filename" />
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useFilesStore } from '@/stores/files'
import PdfEditor from '@/components/PdfEditor.vue'
import WordViewer from '@/components/WordViewer.vue'
import SummaryPanel from '@/components/SummaryPanel.vue'

const route = useRoute()
const router = useRouter()
const filesStore = useFilesStore()

const SIDEBAR_DEFAULT = 340
const SIDEBAR_MIN = 240
const SIDEBAR_MAX_RATIO = 0.7
const SIDEBAR_STORAGE_KEY = 'twonote.sidebarWidth'

const sidebarWidth = ref(loadSidebarWidth())
const isResizing = ref(false)

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

const fileId = computed(() => route.params.id as string)
const docData = ref<ArrayBuffer | null>(null)
const mimeType = ref('')
const loading = ref(true)
const loadError = ref('')
const saveStatus = ref('')

const filename = computed(
  () => filesStore.getFileById(fileId.value)?.name ?? 'Dokument'
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
  'status-saving': saveStatus.value === 'Speichern…',
  'status-saved': saveStatus.value === 'Gespeichert',
  'status-error': saveStatus.value.startsWith('Fehler'),
}))

async function loadFile() {
  loading.value = true
  loadError.value = ''
  try {
    const blob = await filesStore.downloadFileBlob(fileId.value)
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
  if (status === 'Gespeichert' || status.startsWith('Fehler')) {
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
.editor-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-primary);
}

.editor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.6rem 1.25rem;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.875rem;
}

.btn-back {
  background: transparent;
  border: 1px solid var(--border-default);
  color: var(--text-muted);
  padding: 0.35rem 0.7rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8125rem;
  transition: all 0.15s;
}

.btn-back:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.file-name {
  margin: 0;
  font-size: 0.9375rem;
  color: var(--text-primary);
  max-width: 400px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.save-status {
  font-size: 0.8125rem;
  padding: 0.25rem 0.625rem;
  border-radius: 3px;
}

.status-saving { background: #1a2a3a; color: #6aaddb; }
.status-saved  { background: #1a2d1a; color: var(--color-green); }
.status-error  { background: #2d1515; color: var(--color-red); }

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

.editor-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.editor-main {
  flex: 1;
  overflow: auto;
  background: #181818;
}

.editor-sidebar {
  flex-shrink: 0;
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-default);
  overflow-y: auto;
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

@media (max-width: 900px) {
  .editor-layout {
    flex-direction: column;
  }
  .resize-handle {
    display: none;
  }
  .editor-sidebar {
    width: 100% !important;
    height: 300px;
    border-left: none;
    border-top: 1px solid var(--border-default);
  }
}
</style>
