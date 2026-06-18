<template>
  <div class="document-viewer">
    <div class="viewer-layout">
      <!-- Hauptbereich: OnlyOffice-Editor (Co-Editing) -->
      <div class="viewer-main">
        <OnlyOfficeEditor :file-id="fileId" />
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
import { ref, computed, watch } from 'vue'
import { useFilesStore } from '@/stores/files'
import OnlyOfficeEditor from '@/components/OnlyOfficeEditor.vue'
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

const filename = computed(
  () => filesStore.getFileById(props.fileId)?.name ?? 'Dokument'
)
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

.viewer-layout {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.viewer-main {
  flex: 1;
  min-width: 0;
  overflow: hidden;
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
