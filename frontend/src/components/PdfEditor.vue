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

      <!-- Farben -->
      <div class="toolbar-group">
        <label class="color-label" title="Textfarbe">
          <input type="color" v-model="textColor" />
          <span>Text</span>
        </label>
        <label class="color-label" title="Markierungsfarbe">
          <input type="color" v-model="highlightColor" />
          <span>Markierung</span>
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
        <button class="tool-btn" title="Mit Notizen als PDF herunterladen" @click="exportPdf" :disabled="exporting">
          <span v-if="exporting">Export…</span>
          <span v-else>Export</span>
        </button>
      </div>

      <div class="toolbar-divider"></div>

      <div class="toolbar-group">
        <button class="tool-btn" title="Versionen ansehen" @click="showVersions = true">
          Versionen
        </button>
        <button class="tool-btn primary" title="Notizen speichern (bleiben bearbeitbar)" @click="save" :disabled="saving || !dirty">
          <span v-if="saving">Speichern…</span>
          <span v-else>Speichern</span>
        </button>
      </div>
    </div>

    <!-- Dokument: eine durchgehende Fläche über alle Seiten -->
    <div class="pages-scroll">
      <div
        class="doc"
        :style="{ width: docWidth * zoom + 'px', height: docHeight * zoom + 'px' }"
      >
        <!-- PDF-Seiten als scharfe Bitmaps -->
        <canvas
          v-for="(page, idx) in pageLayout"
          :key="idx"
          :ref="(el: unknown) => setPdfCanvasRef(idx, el as HTMLCanvasElement | null)"
          class="pdf-canvas"
          :style="{
            left: (docWidth - page.width) / 2 * zoom + 'px',
            top: page.offsetY * zoom + 'px',
            width: page.width * zoom + 'px',
            height: page.height * zoom + 'px',
          }"
        ></canvas>

        <!-- EINE Fabric-Overlay-Canvas über das ganze Dokument -->
        <canvas ref="fabricCanvasRef" class="fabric-overlay"></canvas>
      </div>
    </div>

    <ConflictDialog
      :visible="!!conflict"
      :filename="conflict?.filename"
      title="Speichern"
      message="Es gibt bereits gespeicherte Stände. Wie möchtest du speichern?"
      @choose="onConflictChoose"
    />

    <VersionHistory
      v-if="showVersions"
      :file-id="fileId"
      :current-version-id="loadedVersionId"
      @select="openVersion"
      @close="showVersions = false"
    />

    <PromptDialog
      :visible="namePrompt"
      title="Version benennen"
      message="Vergib einen Namen für diese Version (optional)."
      placeholder="z. B. Entwurf 2"
      confirm-text="Speichern"
      @submit="onNameSubmit"
      @cancel="onNameCancel"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import * as fabric from 'fabric'
import { PDFDocument } from 'pdf-lib'
import { useFilesStore } from '@/stores/files'
import { filesApi } from '@/api'
import ConflictDialog from '@/components/ConflictDialog.vue'
import type { ConflictChoice } from '@/components/ConflictDialog.vue'
import VersionHistory from '@/components/VersionHistory.vue'
import PromptDialog from '@/components/PromptDialog.vue'

// Vite liefert über den `?url`-Import die korrekte, gebundelte Worker-URL.
// (Ein `new URL('pdfjs-dist/...', import.meta.url)` würde Vite NICHT auflösen.)
pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorkerUrl

const PAGE_SCALE = 1.5
const PAGE_GAP = 24 // logischer Abstand zwischen den Seiten (px bei Zoom 1)
const SANS_FONT = 'Arial, Helvetica, sans-serif'

const PLACEHOLDER_TEXT = 'Text eingeben…'
const PLACEHOLDER_FILL = '#9ca3af' // gedämpftes Grau – nur Hinweis, kein echter Inhalt

// Zeichnet bei leerem IText einen gedämpften Placeholder (statt echtem Vorgabetext, den
// man erst löschen müsste). Wird per Instanz angehängt – das Objekt bleibt ein normales
// `i-text` (kein neuer Serialisierungstyp), sodass gespeicherte Stände immer ladbar sind.
// Leere Felder werden ohnehin beim Verlassen entfernt, der Placeholder wird nie persistiert.
function attachPlaceholder(obj: fabric.IText, placeholder: string) {
  const baseRender = (fabric.IText.prototype as any)._render
  ;(obj as any)._render = function (ctx: CanvasRenderingContext2D) {
    baseRender.call(this, ctx)
    if (this.text === '') {
      ctx.save()
      ctx.fillStyle = PLACEHOLDER_FILL
      ctx.font = `${this.fontStyle} ${this.fontWeight} ${this.fontSize}px ${this.fontFamily}`
      ctx.textAlign = 'left'
      ctx.textBaseline = 'top'
      // Lokale Koordinaten sind zentriert → Textstart oben-links.
      ctx.fillText(placeholder, -this.width / 2, -this.height / 2)
      ctx.restore()
    }
  }
}

// Sichere Obergrenzen für die Canvas-Backing-Store-Größe. Browser brechen die
// Allokation darüber ab ("Canvas is already in error state"): Firefox bei
// 32767px/Seite, Chrome bei ~16384² px Fläche. 16384 ist für beide sicher.
const MAX_CANVAS_DIM = 16384
const MAX_CANVAS_AREA = MAX_CANVAS_DIM * MAX_CANVAS_DIM

// ─── Props & Emits ────────────────────────────────────────────────────────────
const props = defineProps<{
  pdfData: ArrayBuffer
  fileId: string
}>()

const emit = defineEmits<{
  (e: 'save-status', status: string): void
}>()

const filesStore = useFilesStore()

// ─── State ────────────────────────────────────────────────────────────────────
let pdfDoc: pdfjsLib.PDFDocumentProxy | null = null

const pageSizes = ref<{ width: number; height: number }[]>([])
const pdfCanvasRefs: (HTMLCanvasElement | null)[] = []
const fabricCanvasRef = ref<HTMLCanvasElement | null>(null)
let fabricCanvas: fabric.Canvas | null = null

const activeTool = ref<'select' | 'text' | 'highlight'>('select')
const textColor = ref('#000000')       // Schrift: standardmäßig schwarz
const highlightColor = ref('#ffeb3b')  // Markierung: standardmäßig gelb
const saving = ref(false)
const exporting = ref(false)

// Versionen / Notiz-Stände
const showVersions = ref(false)
const loadedVersionId = ref<number | null>(null)  // aktuell geladener Stand
const dirty = ref(false)                           // seit Laden/Speichern geändert?

// Speicher-Dialog (Überschreiben / Eigene Version / Abbrechen)
const conflict = ref<{ filename: string } | null>(null)
let conflictResolver: ((choice: ConflictChoice) => void) | null = null

function askConflict(filename: string): Promise<ConflictChoice> {
  conflict.value = { filename }
  return new Promise((resolve) => {
    conflictResolver = resolve
  })
}

function onConflictChoose(choice: ConflictChoice) {
  conflict.value = null
  conflictResolver?.(choice)
  conflictResolver = null
}

// Namens-Dialog für eine neue Version
const namePrompt = ref(false)
let nameResolver: ((value: string | null) => void) | null = null

function askVersionName(): Promise<string | null> {
  namePrompt.value = true
  return new Promise((resolve) => {
    nameResolver = resolve
  })
}

function onNameSubmit(value: string) {
  namePrompt.value = false
  nameResolver?.(value)
  nameResolver = null
}

function onNameCancel() {
  namePrompt.value = false
  nameResolver?.(null)
  nameResolver = null
}

// Fabric-Objekt-Eigenschaften, die zusätzlich zum Standard serialisiert werden
// müssen, damit die Ebene exakt so wiederhergestellt wird (z. B. Textmarker).
const SERIALIZE_PROPS = ['globalCompositeOperation', 'perPixelTargetFind']

const ZOOM_MIN = 0.5
const ZOOM_MAX = 2.5
const ZOOM_STEP = 0.1
const zoom = ref(1)

// ─── Layout: alle Seiten vertikal gestapelt in EINEM Koordinatenraum ──────────
// Jede Seite sitzt bei `offsetY` (logische px); horizontal im Dokument zentriert.
const pageLayout = computed(() => {
  let offsetY = 0
  return pageSizes.value.map((s) => {
    const entry = { width: s.width, height: s.height, offsetY }
    offsetY += s.height + PAGE_GAP
    return entry
  })
})
const docWidth = computed(() =>
  pageSizes.value.reduce((max, s) => Math.max(max, s.width), 0),
)
const docHeight = computed(() => {
  const total = pageSizes.value.reduce((sum, s) => sum + s.height + PAGE_GAP, 0)
  return Math.max(0, total - PAGE_GAP)
})

function zoomIn() {
  zoom.value = Math.min(ZOOM_MAX, Math.round((zoom.value + ZOOM_STEP) * 100) / 100)
}
function zoomOut() {
  zoom.value = Math.max(ZOOM_MIN, Math.round((zoom.value - ZOOM_STEP) * 100) / 100)
}
function resetZoom() {
  zoom.value = 1
}

let rerenderTimer: ReturnType<typeof setTimeout> | undefined
watch(zoom, () => {
  applyFabricZoom()
  // Seiten in der neuen Zoom-Stufe scharf neu rendern (entkoppelt für flüssiges Zoomen)
  clearTimeout(rerenderTimer)
  rerenderTimer = setTimeout(rerenderAllPages, 150)
})

// Begrenzt die Backing-Store-Auflösung des Fabric-Overlays. Das Overlay spannt
// sich über ALLE Seiten (docHeight = Summe aller Seitenhöhen); bei langen
// Dokumenten würde docHeight × zoom × devicePixelRatio das Canvas-Limit des
// Browsers sprengen und die Allokation fehlschlagen lassen. Wir senken dafür
// nur die Pixeldichte der Annotationsebene – die PDF-Seiten selbst bleiben als
// eigene Canvases scharf. Klick-/Hit-Testing bleibt korrekt, weil Fabric in
// getPointer durch denselben Faktor teilt und wieder multipliziert.
function safeRetinaScaling(): number {
  const dpr = window.devicePixelRatio || 1
  const w = Math.max(1, docWidth.value * zoom.value)
  const h = Math.max(1, docHeight.value * zoom.value)
  const limit = Math.min(
    dpr,
    MAX_CANVAS_DIM / w,
    MAX_CANVAS_DIM / h,
    Math.sqrt(MAX_CANVAS_AREA / (w * h)),
  )
  return Math.max(0.05, limit)
}

// Fabric-Overlay folgt dem Zoom über die interne Skalierung (scharfe Vektoren),
// nicht über CSS-transform.
function applyFabricZoom() {
  if (!fabricCanvas) return
  fabricCanvas.setZoom(zoom.value)
  fabricCanvas.setDimensions({
    width: docWidth.value * zoom.value,
    height: docHeight.value * zoom.value,
  })
  fabricCanvas.requestRenderAll()
}

const tools = [
  { id: 'select',    icon: 'Auswahl',   label: 'Auswählen / Verschieben' },
  { id: 'text',      icon: 'Text',      label: 'Text schreiben' },
  { id: 'highlight', icon: 'Markieren', label: 'Markieren (Textmarker)' },
] as const

function setPdfCanvasRef(idx: number, el: HTMLCanvasElement | null) {
  pdfCanvasRefs[idx] = el
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

  initFabric()
  await loadAnnotations()

  for (let i = 1; i <= pdfDoc.numPages; i++) {
    await renderPage(i)
  }

  updateFabricMode()
  window.addEventListener('keydown', onKeyDown)
})

// Neuesten Notiz-Stand laden und als bearbeitbare Objekte herstellen.
async function loadAnnotations() {
  if (!fabricCanvas) return
  try {
    const { data } = await filesApi.listAnnotationVersions(props.fileId)
    if (data.latest_id == null) {
      dirty.value = false
      return
    }
    await loadVersionData(data.latest_id)
  } catch (e) {
    console.error('Notiz-Stände konnten nicht geladen werden:', e)
  }
}

// Einen bestimmten Stand in den Editor laden (ersetzt die aktuelle Ebene).
async function loadVersionData(versionId: number) {
  if (!fabricCanvas) return
  const { data } = await filesApi.getAnnotationVersion(props.fileId, versionId)
  await fabricCanvas.loadFromJSON(JSON.parse(data.data))
  loadedVersionId.value = versionId
  applyFabricZoom()
  updateFabricMode()
  // Das Laden löst object:added-Events aus → erst danach als „sauber" markieren.
  dirty.value = false
}

// Aus dem Versionen-Dialog gewählten Stand öffnen.
async function openVersion(versionId: number) {
  showVersions.value = false
  if (versionId === loadedVersionId.value) return
  if (!fabricCanvas) return
  if (dirty.value && !confirm('Ungespeicherte Änderungen verwerfen und die gewählte Version laden?')) {
    return
  }
  fabricCanvas.clear()
  try {
    await loadVersionData(versionId)
  } catch (e) {
    console.error('Version konnte nicht geladen werden:', e)
  }
}

onBeforeUnmount(() => {
  clearTimeout(rerenderTimer)
  window.removeEventListener('keydown', onKeyDown)
  if (fabricCanvas) {
    fabricCanvas.dispose()
    fabricCanvas = null
  }
})

// Entf/Backspace löscht das ausgewählte Element – außer während Texteingabe.
function onKeyDown(e: KeyboardEvent) {
  if (e.key !== 'Delete' && e.key !== 'Backspace') return
  const canvas = fabricCanvas
  if (!canvas) return

  const target = e.target as HTMLElement | null
  if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) return

  const active = canvas.getActiveObject()
  if (!active || (active as { isEditing?: boolean }).isEditing) return

  e.preventDefault()
  deleteSelected()
}

// ─── PDF rendern ──────────────────────────────────────────────────────────────
// Render-Auflösung folgt Zoom und Bildschirm-Pixeldichte, damit die Seite beim
// Hineinzoomen scharf bleibt. Begrenzt (Faktor 3), um den Speicher zu schonen.
function currentRenderScale(): number {
  const dpr = window.devicePixelRatio || 1
  const quality = Math.min(zoom.value * dpr, 3)
  return PAGE_SCALE * quality
}

async function renderPage(pageNum: number) {
  if (!pdfDoc) return
  const idx = pageNum - 1
  const canvas = pdfCanvasRefs[idx]
  if (!canvas) return

  const page = await pdfDoc.getPage(pageNum)
  // Bitmap in hoher Auflösung rendern; die Anzeigegröße bleibt über CSS bei der
  // logischen Seitengröße, sodass die Bitmap scharf heruntergerechnet wird.
  const viewport = page.getViewport({ scale: currentRenderScale() })
  canvas.width = viewport.width
  canvas.height = viewport.height

  const ctx = canvas.getContext('2d')!
  await page.render({ canvasContext: ctx, viewport }).promise
}

async function rerenderAllPages() {
  if (!pdfDoc) return
  for (let i = 1; i <= pdfDoc.numPages; i++) {
    await renderPage(i)
  }
}

// ─── Fabric: eine Canvas über alle Seiten ─────────────────────────────────────
function initFabric() {
  const el = fabricCanvasRef.value
  if (!el) return

  // Ohne width/height konstruieren: der Konstruktor würde den Backing-Store
  // sonst sofort (vor dem getRetinaScaling-Override) ungebremst allokieren.
  const canvas = new fabric.Canvas(el, {
    selection: true,
    preserveObjectStacking: true,
    enableRetinaScaling: true,
  })
  // Backing-Store-Auflösung deckeln, bevor Dimensionen gesetzt werden.
  canvas.getRetinaScaling = safeRetinaScaling

  // Zustand beim Drücken festhalten – bevor Fabric das Editieren beendet.
  let wasEditingOnPress = false
  canvas.on('mouse:down:before', () => {
    const active = canvas.getActiveObject() as fabric.IText | undefined
    wasEditingOnPress = !!active && (active as any).isEditing === true
  })

  canvas.on('mouse:down', (opt) => {
    if (activeTool.value !== 'text') return
    // Klick, der ein Textfeld verlässt: nur Editiermodus beenden, kein neues Feld anlegen.
    if (wasEditingOnPress) return
    // Neues Feld nur auf leerer Fläche anlegen (nicht auf bestehende Objekte).
    if (opt.target) return
    const ptr = canvas.getScenePoint(opt.e)
    addText(ptr.x, ptr.y)
  })

  // Leer verlassene Textfelder (nur Placeholder, nichts getippt) wieder entfernen –
  // so wird kein leeres Objekt gespeichert oder bleibt unsichtbar liegen.
  canvas.on('text:editing:exited', (opt) => {
    const obj = (opt as unknown as { target?: fabric.IText }).target
    if (obj && !obj.text.trim()) {
      canvas.remove(obj)
      canvas.requestRenderAll()
    }
  })

  // Frisch gezeichneter Textmarker-Strich: einheitlich überlagern und auswählbar.
  canvas.on('path:created', (opt) => {
    const path = (opt as unknown as { path: fabric.Path }).path
    if (!path) return
    path.set({
      globalCompositeOperation: 'multiply',
      selectable: activeTool.value === 'select',
      evented: activeTool.value === 'select',
      perPixelTargetFind: true,
    })
    canvas.requestRenderAll()
  })

  // Änderungen markieren (aktiviert den Speichern-Button + löst den Dialog aus).
  const markDirty = () => { dirty.value = true }
  canvas.on('object:added', markDirty)
  canvas.on('object:modified', markDirty)
  canvas.on('object:removed', markDirty)
  canvas.on('path:created', markDirty)
  canvas.on('text:changed', markDirty)

  fabricCanvas = canvas
  applyFabricZoom()
}

function makeHighlighterBrush(canvas: fabric.Canvas) {
  const brush = new fabric.PencilBrush(canvas)
  brush.width = 18
  brush.color = highlightColor.value + '66' // halbtransparent → Text bleibt lesbar
  brush.strokeLineCap = 'round'
  brush.strokeLineJoin = 'round'
  brush.decimate = 4
  return brush
}

function updateFabricMode() {
  const canvas = fabricCanvas
  if (!canvas) return

  const isSelect = activeTool.value === 'select'
  const isHighlight = activeTool.value === 'highlight'

  canvas.isDrawingMode = isHighlight
  if (isHighlight) {
    canvas.freeDrawingBrush = makeHighlighterBrush(canvas)
  }
  canvas.selection = isSelect
  canvas.forEachObject((obj) => {
    obj.selectable = isSelect
    obj.evented = isSelect
  })
  canvas.requestRenderAll()
}

// ─── Werkzeuge ────────────────────────────────────────────────────────────────
function setTool(tool: typeof activeTool.value) {
  activeTool.value = tool
  updateFabricMode()
}

function addText(x: number, y: number) {
  const canvas = fabricCanvas
  if (!canvas) return
  // Leer starten → sofort tippen ohne Vorgabetext zu löschen. Breite wächst mit dem Inhalt.
  const text = new fabric.IText('', {
    left: x,
    top: y,
    fontSize: 16,
    fontFamily: SANS_FONT,
    fill: textColor.value,
    backgroundColor: 'rgba(255,255,255,0.7)',
    borderColor: textColor.value,
    cornerColor: textColor.value,
    selectable: true,
    evented: true,
    editable: true,
  })
  attachPlaceholder(text, PLACEHOLDER_TEXT)
  canvas.add(text)
  canvas.setActiveObject(text)
  text.enterEditing()
  canvas.requestRenderAll()
  // Im Text-Modus bleiben – kein automatischer Wechsel zu „Auswählen".
}

function deleteSelected() {
  const canvas = fabricCanvas
  if (!canvas) return
  const active = canvas.getActiveObjects()
  if (active.length === 0) return
  for (const obj of active) canvas.remove(obj)
  canvas.discardActiveObject()
  canvas.requestRenderAll()
}

function clearAll() {
  if (!confirm('Alle Annotationen auf allen Seiten löschen?')) return
  if (!fabricCanvas) return
  fabricCanvas.clear()
  fabricCanvas.requestRenderAll()
}

// ─── Notizen speichern (bearbeitbare Ebene) ───────────────────────────────────
// Die Annotationen werden als fabric-JSON in der DB abgelegt – das Original-PDF
// bleibt unangetastet, daher bleiben Texte/Markierungen dauerhaft editierbar.
async function save() {
  if (!fabricCanvas || !dirty.value) return

  // Bei vorhandenem Stand: überschreiben oder als eigene Version ablegen?
  let mode: 'create' | 'overwrite' = 'create'
  if (loadedVersionId.value !== null) {
    const filename = filesStore.getFileById(props.fileId)?.name ?? 'Dokument'
    const choice = await askConflict(filename)
    if (choice === 'cancel') return
    mode = choice === 'version' ? 'create' : 'overwrite'
  }

  // Beim Anlegen einer neuen Version einen Namen abfragen (optional).
  let label = ''
  if (mode === 'create') {
    const name = await askVersionName()
    if (name === null) return // abgebrochen
    label = name.trim()
  }

  saving.value = true
  emit('save-status', 'Speichern…')
  try {
    const json = JSON.stringify(fabricCanvas.toObject(SERIALIZE_PROPS))
    if (mode === 'overwrite' && loadedVersionId.value !== null) {
      await filesApi.updateAnnotationVersion(props.fileId, loadedVersionId.value, json)
    } else {
      const { data } = await filesApi.createAnnotationVersion(props.fileId, json, label)
      loadedVersionId.value = data.id
    }
    dirty.value = false
    emit('save-status', 'Gespeichert')
  } catch (e: any) {
    console.error('Speichern fehlgeschlagen:', e)
    emit('save-status', 'Fehler beim Speichern')
    // dirty bleibt true → Änderungen bleiben im Canvas erhalten und können erneut
    // gespeichert werden. Sichtbarer Hinweis, damit der Fehler nicht unbemerkt bleibt.
    const detail = e?.response?.data?.detail
    alert(`Speichern fehlgeschlagen${detail ? `: ${detail}` : '.'}\nDeine Änderungen sind noch da – bitte erneut versuchen.`)
  } finally {
    saving.value = false
  }
}

// ─── Als PDF exportieren (abgeflacht, mit Notizen) ─────────────────────────────
// Eine durchgehende Canvas → je Seite die passende Region zuschneiden und in eine
// Kopie des PDFs einbetten. Das Ergebnis wird heruntergeladen (Original bleibt).
async function exportPdf() {
  if (!pdfDoc || !fabricCanvas) return
  exporting.value = true
  emit('save-status', 'Export…')

  const canvas = fabricCanvas
  const prevZoom = canvas.getZoom()

  try {
    const originalBytes = new Uint8Array(props.pdfData.slice(0))
    const pdfLibDoc = await PDFDocument.load(originalBytes)
    const pages = pdfLibDoc.getPages()

    // Für den Export in logische Koordinaten zurückschalten.
    canvas.discardActiveObject()
    canvas.setZoom(1)
    canvas.setDimensions({ width: docWidth.value, height: docHeight.value })
    canvas.renderAll()

    const layout = pageLayout.value
    const OUTPUT_MULT = 2

    for (let i = 0; i < pages.length && i < layout.length; i++) {
      const page = layout[i]
      const region = {
        left: (docWidth.value - page.width) / 2,
        top: page.offsetY,
        width: page.width,
        height: page.height,
      }
      const pageCanvas = canvas.toCanvasElement(OUTPUT_MULT, region)
      const pngDataUrl = pageCanvas.toDataURL('image/png')
      const pngBytes = await fetch(pngDataUrl).then((r) => r.arrayBuffer())
      const pngImage = await pdfLibDoc.embedPng(pngBytes)

      const pdfPage = pages[i]
      const { width, height } = pdfPage.getSize()
      pdfPage.drawImage(pngImage, { x: 0, y: 0, width, height, opacity: 1 })
    }

    const pdfBytes = await pdfLibDoc.save()
    const blob = new Blob([pdfBytes as BlobPart], { type: 'application/pdf' })

    // Im Browser herunterladen.
    const baseName = (filesStore.getFileById(props.fileId)?.name ?? 'dokument').replace(/\.pdf$/i, '')
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${baseName} (Notizen).pdf`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    emit('save-status', 'Exportiert')
  } catch (e: any) {
    console.error('Export fehlgeschlagen:', e)
    emit('save-status', 'Fehler beim Export')
  } finally {
    // Anzeige-Zoom wiederherstellen.
    canvas.setZoom(prevZoom)
    canvas.setDimensions({
      width: docWidth.value * prevZoom,
      height: docHeight.value * prevZoom,
    })
    canvas.requestRenderAll()
    exporting.value = false
  }
}

// Textfarbe ändern → ausgewählten Text neu einfärben.
watch(textColor, (color) => {
  if (!fabricCanvas) return
  const active = fabricCanvas.getActiveObject()
  if (active && (active.type === 'textbox' || active.type === 'i-text')) {
    active.set('fill', color)
    fabricCanvas.requestRenderAll()
  }
})

// Markierungsfarbe ändern → Pinsel und ausgewählten Marker aktualisieren.
watch(highlightColor, (color) => {
  if (!fabricCanvas) return
  if (fabricCanvas.isDrawingMode && fabricCanvas.freeDrawingBrush) {
    fabricCanvas.freeDrawingBrush.color = color + '66'
  }
  const active = fabricCanvas.getActiveObject()
  if (active && active.type === 'path') {
    active.set('stroke', color + '66')
    fabricCanvas.requestRenderAll()
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

/* ── Dokumentfläche ── */
.pages-scroll {
  flex: 1;
  overflow: auto;
  display: flex;
  justify-content: center;
  padding: 1.5rem;
  background: #181818;
}

.doc {
  position: relative;
  flex-shrink: 0;
}

.pdf-canvas {
  position: absolute;
  background: #fff;
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.6);
}

/* Fabric legt einen .canvas-container über das ganze Dokument. */
.fabric-overlay {
  position: absolute;
  top: 0;
  left: 0;
}

:deep(.canvas-container) {
  position: absolute !important;
  top: 0 !important;
  left: 0 !important;
}

.zoom-display {
  min-width: 3.5rem;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

/* ── Touch / schmale Bildschirme ── */
@media (max-width: 760px) {
  /* Toolbar als eine horizontal scrollbare Reihe statt mehrzeiligem Umbruch */
  .toolbar {
    flex-wrap: nowrap;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
  }
  .toolbar::-webkit-scrollbar {
    display: none;
  }
  .toolbar-group {
    flex-shrink: 0;
  }
  .tool-btn {
    min-height: 38px;
    padding: 0.45rem 0.7rem;
  }
  /* Farbwähler-Beschriftung ausblenden, nur Farbfeld zeigen */
  .color-label span {
    display: none;
  }
  .pages-scroll {
    padding: 0.5rem;
  }
}
</style>
