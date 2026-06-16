<template>
  <div class="file-upload">
  <div
    class="upload-zone"
    :class="{ 'drag-over': isDragging, uploading: isUploading }"
    @dragover.prevent="isDragging = true"
    @dragleave="isDragging = false"
    @drop.prevent="handleDrop"
    @click="triggerFileInput"
  >
    <!-- Hidden inputs -->
    <input
      ref="fileInput"
      type="file"
      accept=".pdf,.docx,.doc"
      multiple
      style="display: none"
      @change="handleFileInputChange"
    />

    <!-- Normaler Zustand -->
    <div v-if="!isUploading" class="upload-content">
      <svg class="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="16 16 12 12 8 16"></polyline>
        <line x1="12" y1="12" x2="12" y2="21"></line>
        <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3"></path>
      </svg>
      <p class="upload-text">
        <strong>Klicken oder Dateien hierher ziehen</strong>
      </p>
      <p class="upload-hint">PDF, Word (.docx, .doc) – mehrere Dateien gleichzeitig möglich</p>
      <button class="folder-btn" @click.stop="triggerFolderInput">
        Ordner hochladen
      </button>
    </div>

    <!-- Upload läuft -->
    <div v-else class="upload-content">
      <div class="progress-ring">
        <svg viewBox="0 0 36 36">
          <circle cx="18" cy="18" r="15.9" fill="none" stroke="#e5e7eb" stroke-width="3" />
          <circle
            cx="18" cy="18" r="15.9"
            fill="none"
            stroke="#4f46e5"
            stroke-width="3"
            stroke-dasharray="100"
            :stroke-dashoffset="100 - uploadProgressDisplay"
            stroke-linecap="round"
            transform="rotate(-90 18 18)"
          />
        </svg>
        <span class="progress-text">{{ uploadProgressDisplay }}%</span>
      </div>
      <p class="upload-status-text">{{ uploadStatusText }}</p>
    </div>

    <!-- Fehler -->
    <div v-if="localError" class="upload-error">{{ localError }}</div>
  </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useFilesStore } from '@/stores/files'

const emit = defineEmits<{
  (e: 'uploaded'): void
}>()

const filesStore = useFilesStore()
const fileInput = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)
const localError = ref('')

const folderUploading = ref(false)
const folderProgress = ref(0)
const folderStatusText = ref('')

const isUploading = computed(() => filesStore.uploading || folderUploading.value)
const uploadProgressDisplay = computed(() =>
  folderUploading.value ? folderProgress.value : filesStore.uploadProgress
)
const uploadStatusText = computed(() =>
  folderUploading.value ? folderStatusText.value : (filesStore.uploading ? 'Wird hochgeladen…' : '')
)

const ALLOWED_TYPES = new Set([
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/msword',
])

function isAllowedFile(f: File): boolean {
  const name = f.name.toLowerCase()
  return (
    ALLOWED_TYPES.has(f.type) ||
    name.endsWith('.pdf') ||
    name.endsWith('.docx') ||
    name.endsWith('.doc')
  )
}

function triggerFileInput() {
  if (!isUploading.value) fileInput.value?.click()
}

// Ordner-Input wird programmatisch erstellt damit webkitdirectory zuverlässig gesetzt ist
function triggerFolderInput() {
  if (isUploading.value) return
  const input = document.createElement('input')
  input.type = 'file'
  input.setAttribute('webkitdirectory', '')
  input.setAttribute('directory', '')
  input.multiple = true
  input.addEventListener('change', () => {
    if (input.files && input.files.length > 0) {
      handleFolderFiles(Array.from(input.files))
    }
  })
  input.click()
}

// ─── Datei-Upload ─────────────────────────────────────────────────────────────

async function uploadFiles(fileList: FileList) {
  localError.value = ''
  isDragging.value = false

  const files = Array.from(fileList).filter(isAllowedFile)
  if (files.length === 0) {
    localError.value = 'Nur PDF und Word-Dokumente werden akzeptiert.'
    return
  }

  let anySuccess = false
  for (const file of files) {
    // Gleichnamige Datei → es entsteht immer ein neuer Eintrag (kein Überschreiben).
    const result = await filesStore.uploadFile(file)
    if (result) anySuccess = true
    else localError.value = filesStore.error ?? 'Upload fehlgeschlagen.'
  }

  if (anySuccess) emit('uploaded')
}

async function handleDrop(e: DragEvent) {
  isDragging.value = false
  if (!e.dataTransfer) return

  // Prüfen ob Ordner dabei sind (DataTransferItem API)
  const items = Array.from(e.dataTransfer.items)
  const hasDirectory = items.some(
    (item) => item.kind === 'file' && (item as any).webkitGetAsEntry?.()?.isDirectory
  )

  if (hasDirectory) {
    const filesWithPath: { file: File; relativePath: string }[] = []
    await Promise.all(
      items.map((item) => {
        const entry = (item as any).webkitGetAsEntry?.()
        if (entry) return collectEntries(entry, '', filesWithPath)
      })
    )
    const allowed = filesWithPath.filter((fp) => isAllowedFile(fp.file))
    if (allowed.length > 0) {
      await uploadFilesWithPaths(allowed)
    } else {
      localError.value = 'Keine PDF oder Word-Dateien im Ordner gefunden.'
    }
  } else {
    uploadFiles(e.dataTransfer.files)
  }
}

function collectEntries(
  entry: any,
  basePath: string,
  result: { file: File; relativePath: string }[]
): Promise<void> {
  if (entry.isFile) {
    return new Promise((resolve) => {
      entry.file((f: File) => {
        result.push({ file: f, relativePath: basePath + f.name })
        resolve()
      })
    })
  } else if (entry.isDirectory) {
    const reader = entry.createReader()
    return new Promise((resolve) => {
      reader.readEntries(async (entries: any[]) => {
        for (const child of entries) {
          await collectEntries(child, basePath + entry.name + '/', result)
        }
        resolve()
      })
    })
  }
  return Promise.resolve()
}

function handleFileInputChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files) {
    uploadFiles(input.files)
    input.value = ''
  }
}

// ─── Ordner-Upload (gemeinsame Logik für Button + Drag&Drop) ──────────────────

function handleFolderFiles(allFiles: File[]) {
  // webkitRelativePath nutzen (vom input[webkitdirectory] gesetzt)
  const filesWithPath = allFiles
    .filter(isAllowedFile)
    .map((f) => ({ file: f, relativePath: f.webkitRelativePath || f.name }))
  if (filesWithPath.length > 0) uploadFilesWithPaths(filesWithPath)
  else localError.value = 'Keine PDF oder Word-Dateien im Ordner gefunden.'
}

async function uploadFilesWithPaths(
  filesWithPath: { file: File; relativePath: string }[]
) {
  localError.value = ''
  folderUploading.value = true
  folderProgress.value = 0

  try {
    const folderIdCache = new Map<string, string>()
    const rootFolderId = filesStore.currentFolderId

    // Einzigartige Ordnerpfade, nach Tiefe sortiert
    const allPaths = new Set<string>()
    for (const { relativePath } of filesWithPath) {
      const parts = relativePath.split('/')
      for (let i = 1; i < parts.length; i++) {
        allPaths.add(parts.slice(0, i).join('/'))
      }
    }
    const sortedPaths = Array.from(allPaths).sort((a, b) => {
      const da = a.split('/').length
      const db = b.split('/').length
      return da !== db ? da - db : a.localeCompare(b)
    })

    // Ordner in Drive anlegen
    folderStatusText.value = 'Ordnerstruktur wird erstellt…'
    for (const folderPath of sortedPaths) {
      const parts = folderPath.split('/')
      const folderName = parts[parts.length - 1]
      const parentPath = parts.slice(0, -1).join('/')
      const parentId = parentPath ? folderIdCache.get(parentPath) : rootFolderId

      const created = await filesStore.createFolder(folderName, parentId)
      if (created) {
        folderIdCache.set(folderPath, created.id)
      } else {
        localError.value = filesStore.error ?? 'Ordner erstellen fehlgeschlagen.'
        return
      }
    }

    // Dateien hochladen
    let uploaded = 0
    for (const { file, relativePath } of filesWithPath) {
      const parts = relativePath.split('/')
      const parentPath = parts.slice(0, -1).join('/')
      const targetFolderId = folderIdCache.get(parentPath) ?? rootFolderId

      folderStatusText.value = `Datei ${uploaded + 1} von ${filesWithPath.length}`
      folderProgress.value = Math.round((uploaded / filesWithPath.length) * 100)

      const result = await filesStore.uploadFile(file, targetFolderId)
      if (result) uploaded++
      else localError.value = filesStore.error ?? 'Upload fehlgeschlagen.'
    }

    folderProgress.value = 100
    if (uploaded > 0) emit('uploaded')
  } finally {
    folderUploading.value = false
    folderProgress.value = 0
    folderStatusText.value = ''
  }
}
</script>

<style scoped>
.upload-zone {
  border: 1px dashed var(--border-strong);
  border-radius: 4px;
  padding: 1.75rem 2rem;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  background: var(--bg-secondary);
  position: relative;
  user-select: none;
}

.upload-zone:hover,
.upload-zone.drag-over {
  border-color: var(--accent);
  background: #221f33;
}

.upload-zone.uploading {
  cursor: default;
  border-color: var(--accent);
  background: #221f33;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.4rem;
  color: var(--text-muted);
}

.upload-icon {
  width: 32px;
  height: 32px;
  color: var(--text-faint);
  margin-bottom: 0.25rem;
  transition: color 0.15s;
}

.upload-zone:hover .upload-icon,
.upload-zone.drag-over .upload-icon {
  color: var(--accent);
}

.upload-text {
  margin: 0;
  color: var(--text-primary);
  font-size: 0.9375rem;
}

.upload-hint {
  margin: 0;
  font-size: 0.775rem;
  color: var(--text-muted);
}

.folder-btn {
  margin-top: 0.5rem;
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  color: var(--text-muted);
  padding: 0.3rem 0.75rem;
  border-radius: 3px;
  font-size: 0.775rem;
  cursor: pointer;
  transition: all 0.15s;
}

.folder-btn:hover {
  background: var(--bg-elevated);
  color: var(--text-primary);
  border-color: var(--border-strong);
}

.progress-ring {
  position: relative;
  width: 52px;
  height: 52px;
  margin-bottom: 0.5rem;
}

.progress-ring svg {
  width: 100%;
  height: 100%;
}

.progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--accent);
}

.upload-status-text {
  margin: 0;
  font-size: 0.8125rem;
  color: var(--text-muted);
}

.upload-error {
  margin-top: 0.75rem;
  color: var(--color-red);
  font-size: 0.8125rem;
  background: #2d1515;
  padding: 0.4rem 0.7rem;
  border-radius: 3px;
  border: 1px solid #4d2020;
}

.progress-ring svg circle:first-child { stroke: var(--border-strong); }
.progress-ring svg circle:last-child  { stroke: var(--accent); }
</style>
