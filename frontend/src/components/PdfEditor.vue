<template>
  <div class="pdf-editor">
    <!-- Toolbar -->
    <div class="toolbar">
      <!-- Werkzeuge -->
      <div class="toolbar-group">
        <button
          v-for="tool in tools"
          :key="tool.id"
          class="tool-btn"
          :class="{ active: activeTool === tool.id }"
          :title="tool.label"
          @click="setTool(tool.id)"
        >
          {{ tool.icon }}
        </button>
      </div>

      <div class="toolbar-divider"></div>

      <!-- Farbe -->
      <div class="toolbar-group">
        <label class="color-label" title="Farbe">
          <input type="color" v-model="activeColor" />
          <span>{{ activeColor }}</span>
        </label>
      </div>

      <div class="toolbar-divider"></div>

      <!-- Zoom -->
      <div class="toolbar-group">
        <button class="tool-btn" title="Verkleinern (Strg + −)" @click="zoomOut" :disabled="zoom <= ZOOM_MIN + 0.001">
          −
        </button>
        <button class="tool-btn zoom-display" title="Auf 100 % zurücksetzen" @click="resetZoom">
          {{ Math.round(zoom * 100) }} %
        </button>
        <button class="tool-btn" title="Vergrößern (Strg + +)" @click="zoomIn" :disabled="zoom >= ZOOM_MAX - 0.001">
          +
        </button>
      </div>

      <div class="toolbar-divider"></div>

      <!-- Aktionen -->
      <div class="toolbar-group">
        <button class="tool-btn danger" title="Ausgewähltes löschen" @click="deleteSelected">
          Entfernen
        </button>
        <button class="tool-btn danger" title="Alle Annotationen löschen" @click="clearAll">
          Alle löschen
        </button>
        <button class="tool-btn primary" title="Als PDF speichern" @click="savePdf" :disabled="saving">
          <span v-if="saving">Speichern…</span>
          <span v-else>Speichern</span>
        </button>
      </div>
    </div>

    <!-- Seitenliste -->
    <div class="pages-scroll">
      <div
        v-for="(size, idx) in pageSizes"
        :key="idx"
        class="page-wrapper"
        :style="{ width: size.width * zoom + 'px', height: size.height * zoom + 'px' }"
      >
        <div
          class="page-stack"
          :style="{
            width: size.width + 'px',
            height: size.height + 'px',
            transform: `scale(${zoom})`,
          }"
        >
          <canvas
            :ref="(el: unknown) => setPdfCanvasRef(idx, el as HTMLCanvasElement | null)"
            class="pdf-canvas"
          ></canvas>
          <canvas
            :ref="(el: unknown) => setFabricCanvasRef(idx, el as HTMLCanvasElement | null)"
            class="fabric-canvas"
          ></canvas>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
import * as fabric from 'fabric'
import { PDFDocument } from 'pdf-lib'
import { filesApi } from '@/api'

pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.mjs',
  import.meta.url
).toString()

const PAGE_SCALE = 1.5

// ─── Props & Emits ────────────────────────────────────────────────────────────
const props = defineProps<{
  pdfData: ArrayBuffer
  fileId: string
}>()

const emit = defineEmits<{
  (e: 'save-status', status: string): void
}>()

// ─── State ────────────────────────────────────────────────────────────────────
let pdfDoc: pdfjsLib.PDFDocumentProxy | null = null

const pageSizes = ref<{ width: number; height: number }[]>([])
const pdfCanvasRefs: (HTMLCanvasElement | null)[] = []
const fabricCanvasRefs: (HTMLCanvasElement | null)[] = []
const fabricCanvases: fabric.Canvas[] = []

const activeTool = ref<'select' | 'text' | 'highlight' | 'checkbox'>('select')
const activeColor = ref('#FFD700')
const saving = ref(false)

const ZOOM_MIN = 0.5
const ZOOM_MAX = 2.5
const ZOOM_STEP = 0.1
const zoom = ref(1)

function zoomIn() {
  zoom.value = Math.min(ZOOM_MAX, Math.round((zoom.value + ZOOM_STEP) * 100) / 100)
}
function zoomOut() {
  zoom.value = Math.max(ZOOM_MIN, Math.round((zoom.value - ZOOM_STEP) * 100) / 100)
}
function resetZoom() {
  zoom.value = 1
}

watch(zoom, () => {
  for (const c of fabricCanvases) {
    if (c) c.calcOffset()
  }
})

const tools = [
  { id: 'select',    icon: 'Auswahl',   label: 'Auswählen / Verschieben' },
  { id: 'text',      icon: 'Text',      label: 'Text schreiben' },
  { id: 'highlight', icon: 'Markieren', label: 'Markieren (Highlight)' },
  { id: 'checkbox',  icon: 'Checkbox',  label: 'Checkbox einfügen' },
] as const

function setPdfCanvasRef(idx: number, el: HTMLCanvasElement | null) {
  pdfCanvasRefs[idx] = el
}
function setFabricCanvasRef(idx: number, el: HTMLCanvasElement | null) {
  fabricCanvasRefs[idx] = el
}

// ─── Lifecycle ────────────────────────────────────────────────────────────────
onMounted(async () => {
  const loadingTask = pdfjsLib.getDocument({ data: props.pdfData.slice(0) })
  pdfDoc = await loadingTask.promise

  const sizes: { width: number; height: number }[] = []
  for (let i = 1; i <= pdfDoc.numPages; i++) {
    const page = await pdfDoc.getPage(i)
    const viewport = page.getViewport({ scale: PAGE_SCALE })
    sizes.push({ width: viewport.width, height: viewport.height })
  }
  pageSizes.value = sizes

  await nextTick()

  for (let i = 1; i <= pdfDoc.numPages; i++) {
    await renderPage(i)
    initFabricForPage(i)
  }

  updateAllFabricModes()
})

onBeforeUnmount(() => {
  for (const c of fabricCanvases) c.dispose()
  fabricCanvases.length = 0
})

// ─── PDF rendern ──────────────────────────────────────────────────────────────
async function renderPage(pageNum: number) {
  if (!pdfDoc) return
  const idx = pageNum - 1
  const canvas = pdfCanvasRefs[idx]
  if (!canvas) return

  const page = await pdfDoc.getPage(pageNum)
  const viewport = page.getViewport({ scale: PAGE_SCALE })
  canvas.width = viewport.width
  canvas.height = viewport.height

  const ctx = canvas.getContext('2d')!
  await page.render({ canvasContext: ctx, viewport }).promise
}

// ─── Fabric pro Seite ─────────────────────────────────────────────────────────
function initFabricForPage(pageNum: number) {
  const idx = pageNum - 1
  const el = fabricCanvasRefs[idx]
  const size = pageSizes.value[idx]
  if (!el || !size) return

  const canvas = new fabric.Canvas(el, {
    width: size.width,
    height: size.height,
    selection: true,
    preserveObjectStacking: true,
  })

  let isDrawing = false
  let startX = 0
  let startY = 0
  let highlightRect: fabric.Rect | null = null

  canvas.on('mouse:down', (opt) => {
    const ptr = canvas.getScenePoint(opt.e)
    if (activeTool.value === 'highlight') {
      isDrawing = true
      startX = ptr.x
      startY = ptr.y
      highlightRect = new fabric.Rect({
        left: startX,
        top: startY,
        width: 0,
        height: 0,
        fill: activeColor.value + '55',
        stroke: activeColor.value,
        strokeWidth: 1,
        selectable: true,
        evented: true,
      })
      canvas.add(highlightRect)
    } else if (activeTool.value === 'text') {
      addTextbox(canvas, ptr.x, ptr.y)
    } else if (activeTool.value === 'checkbox') {
      addCheckbox(canvas, ptr.x, ptr.y)
    }
  })

  canvas.on('mouse:move', (opt) => {
    if (!isDrawing || !highlightRect) return
    const ptr = canvas.getScenePoint(opt.e)
    const w = ptr.x - startX
    const h = ptr.y - startY
    highlightRect.set({
      width: Math.abs(w),
      height: Math.abs(h),
      left: w < 0 ? ptr.x : startX,
      top: h < 0 ? ptr.y : startY,
    })
    canvas.renderAll()
  })

  canvas.on('mouse:up', () => {
    if (isDrawing) {
      isDrawing = false
      highlightRect = null
    }
  })

  fabricCanvases[idx] = canvas
}

function updateAllFabricModes() {
  for (const canvas of fabricCanvases) {
    if (!canvas) continue
    canvas.isDrawingMode = false
    canvas.selection = activeTool.value === 'select'
    canvas.forEachObject((obj) => {
      obj.selectable = activeTool.value === 'select'
      obj.evented = activeTool.value === 'select' || obj.type === 'group'
    })
    canvas.renderAll()
  }
}

// ─── Werkzeuge ────────────────────────────────────────────────────────────────
function setTool(tool: typeof activeTool.value) {
  activeTool.value = tool
  updateAllFabricModes()
}

function addTextbox(canvas: fabric.Canvas, x: number, y: number) {
  const textbox = new fabric.Textbox('Text eingeben', {
    left: x,
    top: y,
    width: 180,
    fontSize: 16,
    fill: activeColor.value,
    backgroundColor: 'rgba(255,255,255,0.7)',
    borderColor: activeColor.value,
    cornerColor: activeColor.value,
    selectable: true,
    evented: true,
    editable: true,
  })
  canvas.add(textbox)
  canvas.setActiveObject(textbox)
  textbox.enterEditing()
  canvas.renderAll()
  setTool('select')
}

function addCheckbox(canvas: fabric.Canvas, x: number, y: number) {
  const size = 20
  const box = new fabric.Rect({
    width: size,
    height: size,
    fill: 'rgba(255,255,255,0.9)',
    stroke: activeColor.value,
    strokeWidth: 2,
    rx: 3,
    ry: 3,
  })

  const checkmark = new fabric.Text('✓', {
    fontSize: 14,
    fill: activeColor.value,
    left: 3,
    top: 1,
    selectable: false,
    evented: false,
    visible: false,
  })

  const group = new fabric.Group([box, checkmark], {
    left: x,
    top: y,
    selectable: true,
    evented: true,
    hasControls: true,
    subTargetCheck: false,
  })
  ;(group as any).data = { checked: false }

  group.on('mousedown', () => {
    if (activeTool.value !== 'select') return
    const data = (group as any).data as { checked: boolean }
    data.checked = !data.checked
    const mark = group.item(1) as fabric.Text
    mark.set('visible', data.checked)
    canvas.renderAll()
  })

  canvas.add(group)
  canvas.renderAll()
  setTool('select')
}

function deleteSelected() {
  for (const canvas of fabricCanvases) {
    if (!canvas) continue
    const active = canvas.getActiveObject()
    if (active) {
      canvas.remove(active)
      canvas.discardActiveObject()
      canvas.renderAll()
      return
    }
  }
}

function clearAll() {
  if (!confirm('Alle Annotationen auf allen Seiten löschen?')) return
  for (const canvas of fabricCanvases) {
    if (!canvas) continue
    canvas.clear()
    canvas.renderAll()
  }
}

// ─── PDF speichern ────────────────────────────────────────────────────────────
async function savePdf() {
  if (!pdfDoc) return
  saving.value = true
  emit('save-status', 'Speichern…')

  try {
    const originalBytes = new Uint8Array(props.pdfData.slice(0))
    const pdfLibDoc = await PDFDocument.load(originalBytes)
    const pages = pdfLibDoc.getPages()

    for (let i = 0; i < fabricCanvases.length; i++) {
      const fc = fabricCanvases[i]
      if (!fc || fc.getObjects().length === 0) continue

      const pngDataUrl = fc.toDataURL({ format: 'png', multiplier: 1 })
      const pngBytes = await fetch(pngDataUrl).then((r) => r.arrayBuffer())
      const pngImage = await pdfLibDoc.embedPng(pngBytes)

      const pdfPage = pages[i]
      const { width, height } = pdfPage.getSize()
      pdfPage.drawImage(pngImage, {
        x: 0,
        y: 0,
        width,
        height,
        opacity: 1,
      })
    }

    const pdfBytes = await pdfLibDoc.save()
    const blob = new Blob([pdfBytes as BlobPart], { type: 'application/pdf' })
    const file = new File([blob], 'annotated.pdf', { type: 'application/pdf' })

    await filesApi.update(props.fileId, file)

    emit('save-status', 'Gespeichert')
  } catch (e: any) {
    console.error('Speichern fehlgeschlagen:', e)
    emit('save-status', 'Fehler beim Speichern')
  } finally {
    saving.value = false
  }
}

// Farbänderung → aktives Objekt auf einem beliebigen Canvas neu einfärben
watch(activeColor, (color) => {
  for (const canvas of fabricCanvases) {
    if (!canvas) continue
    const active = canvas.getActiveObject()
    if (!active) continue
    if (active.type === 'textbox' || active.type === 'i-text') {
      active.set('fill', color)
    } else if (active.type === 'rect') {
      active.set({ fill: color + '55', stroke: color })
    }
    canvas.renderAll()
    return
  }
})
</script>

<style scoped>
.pdf-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-primary);
}

/* ── Toolbar ── */
.toolbar {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.4rem 0.875rem;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-default);
  flex-wrap: wrap;
  flex-shrink: 0;
  z-index: 5;
  position: sticky;
  top: 0;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.toolbar-divider {
  width: 1px;
  height: 20px;
  background: var(--border-default);
  margin: 0 0.25rem;
}

.tool-btn {
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-muted);
  padding: 0.3rem 0.55rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8125rem;
  transition: all 0.15s;
  white-space: nowrap;
}

.tool-btn:hover:not(:disabled) {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  border-color: var(--border-default);
}

.tool-btn.active {
  background: #2a2040;
  color: var(--accent-hover);
  border-color: var(--accent);
}

.tool-btn.primary {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}

.tool-btn.primary:hover:not(:disabled) {
  background: var(--accent-hover);
  border-color: var(--accent-hover);
}

.tool-btn.danger:hover {
  background: #2d1515;
  color: var(--color-red);
  border-color: #4d2020;
}

.tool-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.color-label {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  cursor: pointer;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.color-label input[type='color'] {
  width: 26px;
  height: 26px;
  border: 1px solid var(--border-default);
  border-radius: 3px;
  cursor: pointer;
  padding: 2px;
  background: var(--bg-tertiary);
}

/* ── Seitenliste ── */
.pages-scroll {
  flex: 1;
  overflow: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  padding: 1.5rem;
  background: #181818;
}

.page-wrapper {
  position: relative;
  flex-shrink: 0;
}

.page-stack {
  position: absolute;
  top: 0;
  left: 0;
  transform-origin: top left;
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.6);
  background: #fff;
}

.pdf-canvas,
.fabric-canvas {
  position: absolute;
  inset: 0;
}

:deep(.canvas-container) {
  position: absolute !important;
  inset: 0 !important;
}

.zoom-display {
  min-width: 3.5rem;
  text-align: center;
  font-variant-numeric: tabular-nums;
}
</style>
