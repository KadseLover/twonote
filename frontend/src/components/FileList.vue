<template>
  <div class="file-list">
    <!-- Lade-Zustand -->
    <div v-if="loading" class="state-container">
      <div class="spinner"></div>
      <p>Dateien werden geladen…</p>
    </div>

    <!-- Leer -->
    <div v-else-if="sortedFiles.length === 0" class="state-container empty">
      <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
      </svg>
      <p>Noch keine Dokumente vorhanden.</p>
      <p class="hint">Lade oben deine ersten PDFs oder Word-Dokumente hoch.</p>
    </div>

    <!-- Datei-Tabelle -->
    <table v-else class="files-table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Typ</th>
          <th>Zuletzt geändert</th>
          <th>Größe</th>
          <th>Aktionen</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="file in sortedFiles" :key="file.id" class="file-row" :class="{ 'folder-row': isFolder(file) }">
          <td class="file-name">
            <button
              class="name-btn"
              :class="{ 'folder-name-btn': isFolder(file) }"
              @click="isFolder(file) ? $emit('navigate', file) : $emit('open', file)"
              :title="file.name"
            >
              <svg v-if="isFolder(file)" class="row-icon folder-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
              </svg>
              <svg v-else class="row-icon file-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
              {{ file.name }}
            </button>
          </td>
          <td class="file-type">
            <span class="type-badge" :class="getTypeBadgeClass(file.mimeType)">
              {{ getTypeLabel(file.mimeType) }}
            </span>
          </td>
          <td class="file-date">{{ formatDate(file.modifiedTime) }}</td>
          <td class="file-size">{{ isFolder(file) ? '—' : formatSize(file.size) }}</td>
          <td class="file-actions">
            <button
              v-if="isOpenable(file)"
              class="action-btn"
              @click="$emit('open', file)"
              :title="file.mimeType === 'application/pdf' ? 'PDF bearbeiten' : 'Word-Dokument anzeigen'"
            >
              Öffnen
            </button>
            <button
              v-if="!isFolder(file)"
              class="action-btn"
              @click="handleDownload(file)"
              title="Herunterladen"
            >
              Download
            </button>
            <button
              class="action-btn delete"
              @click="$emit('delete', file)"
              title="Löschen"
            >
              Löschen
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { filesApi, type DriveFile } from '@/api'

const FOLDER_MIME = 'application/vnd.google-apps.folder'

const props = defineProps<{
  files: DriveFile[]
  loading: boolean
}>()

defineEmits<{
  (e: 'open', file: DriveFile): void
  (e: 'navigate', file: DriveFile): void
  (e: 'delete', file: DriveFile): void
}>()

const sortedFiles = computed(() => {
  return [...props.files].sort((a, b) => {
    const aFolder = a.mimeType === FOLDER_MIME ? 0 : 1
    const bFolder = b.mimeType === FOLDER_MIME ? 0 : 1
    return aFolder - bFolder
  })
})

function isFolder(file: DriveFile): boolean {
  return file.mimeType === FOLDER_MIME
}

function isOpenable(file: DriveFile): boolean {
  if (isFolder(file)) return false
  const m = file.mimeType
  const n = file.name.toLowerCase()
  return (
    m === 'application/pdf' ||
    m.includes('wordprocessingml') ||
    m === 'application/msword' ||
    n.endsWith('.pdf') ||
    n.endsWith('.docx') ||
    n.endsWith('.doc')
  )
}

function getTypeLabel(mimeType: string): string {
  if (mimeType === FOLDER_MIME) return 'Ordner'
  if (mimeType === 'application/pdf') return 'PDF'
  if (mimeType.includes('wordprocessingml')) return 'Word'
  if (mimeType.includes('msword')) return 'Word'
  return 'Datei'
}

function getTypeBadgeClass(mimeType: string): string {
  if (mimeType === FOLDER_MIME) return 'badge-folder'
  if (mimeType === 'application/pdf') return 'badge-pdf'
  if (mimeType.includes('word')) return 'badge-word'
  return 'badge-other'
}

function formatDate(iso: string): string {
  if (!iso) return '—'
  return new Intl.DateTimeFormat('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(iso))
}

function formatSize(size?: string): string {
  if (!size) return '—'
  const bytes = parseInt(size)
  if (isNaN(bytes)) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

async function handleDownload(file: DriveFile) {
  try {
    const response = await filesApi.download(file.id)
    const blob = response.data as Blob
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = file.name
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch {
    alert('Download fehlgeschlagen.')
  }
}
</script>

<style scoped>
.file-list {
  min-height: 100px;
}

.state-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: var(--text-muted);
  text-align: center;
  gap: 0.5rem;
}

.empty-icon {
  width: 36px;
  height: 36px;
  color: var(--text-faint);
  margin-bottom: 0.5rem;
}

.hint {
  font-size: 0.8125rem;
  color: var(--text-faint);
}

.spinner {
  width: 28px;
  height: 28px;
  border: 2px solid var(--border-strong);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.files-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.files-table th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-default);
  font-weight: 500;
}

.file-row {
  border-bottom: 1px solid var(--border-subtle);
  transition: background 0.1s;
}

.file-row:hover {
  background: var(--bg-tertiary);
}

.file-row td {
  padding: 0.625rem 0.75rem;
  vertical-align: middle;
}

.file-name {
  max-width: 320px;
}

.name-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--accent);
  font-size: 0.875rem;
  text-align: left;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 0;
}

.name-btn:hover {
  color: var(--accent-hover);
  text-decoration: underline;
}

.folder-name-btn {
  color: var(--text-primary);
}

.folder-name-btn:hover {
  color: var(--accent);
}

.row-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.folder-icon {
  color: var(--text-muted);
}

.file-icon {
  color: var(--text-faint);
}

.folder-row {
  background: transparent;
}

.type-badge {
  padding: 0.15rem 0.5rem;
  border-radius: 3px;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.badge-folder { background: var(--bg-elevated); color: var(--text-muted); }
.badge-pdf    { background: #2d1515; color: #d97070; }
.badge-word   { background: #1a2233; color: #6a9fd8; }
.badge-other  { background: var(--bg-elevated); color: var(--text-muted); }

.file-date, .file-size {
  color: var(--text-muted);
  white-space: nowrap;
  font-size: 0.8125rem;
}

.file-actions {
  display: flex;
  gap: 0.25rem;
}

.action-btn {
  background: none;
  border: 1px solid var(--border-default);
  border-radius: 3px;
  padding: 0.2rem 0.5rem;
  cursor: pointer;
  font-size: 0.75rem;
  color: var(--text-muted);
  transition: all 0.15s;
  white-space: nowrap;
}

.action-btn:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.action-btn.delete:hover {
  background: #2d1515;
  border-color: #4d2020;
  color: var(--color-red);
}
</style>
