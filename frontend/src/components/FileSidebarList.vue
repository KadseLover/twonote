<template>
  <div class="sidebar-list">
    <!-- Lade-Zustand -->
    <div v-if="loading" class="state-container">
      <div class="spinner"></div>
    </div>

    <!-- Leer -->
    <div v-else-if="sortedFiles.length === 0" class="state-container empty">
      <p>Keine Dokumente</p>
      <p class="hint">Lade oben Dateien oder Ordner hoch.</p>
    </div>

    <!-- Datei-/Ordner-Liste -->
    <ul v-else class="rows">
      <li
        v-for="file in sortedFiles"
        :key="file.id"
        class="row"
        :class="{ active: file.id === activeId, folder: isFolder(file) }"
      >
        <button
          class="row-main"
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
          <span class="row-name">{{ file.name }}</span>
        </button>

        <div class="row-actions">
          <button
            v-if="!isFolder(file)"
            class="action-btn"
            @click.stop="handleDownload(file)"
            title="Herunterladen"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
          </button>
          <button
            class="action-btn delete"
            @click.stop="$emit('delete', file)"
            title="Löschen"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
          </button>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { filesApi, type DriveFile } from '@/api'

const FOLDER_MIME = 'application/vnd.google-apps.folder'

const props = defineProps<{
  files: DriveFile[]
  loading: boolean
  activeId?: string
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
.sidebar-list {
  min-height: 60px;
}

.state-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 1.5rem 1rem;
  color: var(--text-muted);
  text-align: center;
  gap: 0.35rem;
  font-size: 0.8125rem;
}

.state-container .hint {
  font-size: 0.75rem;
  color: var(--text-faint);
}

.spinner {
  width: 22px;
  height: 22px;
  border: 2px solid var(--border-strong);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.rows {
  list-style: none;
  margin: 0;
  padding: 0;
}

.row {
  display: flex;
  align-items: center;
  border-radius: 4px;
  transition: background 0.1s;
}

.row:hover {
  background: var(--bg-tertiary);
}

.row.active {
  background: var(--bg-elevated);
}

.row-main {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.4rem 0.5rem;
  color: var(--text-primary);
  font-size: 0.8125rem;
  text-align: left;
}

.row-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.row:not(.folder) .row-main {
  color: var(--accent);
}

.row.active .row-main {
  color: var(--text-primary);
  font-weight: 500;
}

.row-icon {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
}

.folder-icon { color: var(--text-muted); }
.file-icon { color: var(--text-faint); }

.row-actions {
  display: flex;
  gap: 0.1rem;
  padding-right: 0.35rem;
  opacity: 0;
  transition: opacity 0.1s;
}

.row:hover .row-actions,
.row.active .row-actions {
  opacity: 1;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  border-radius: 3px;
  padding: 0.25rem;
  cursor: pointer;
  color: var(--text-muted);
  transition: all 0.15s;
}

.action-btn svg {
  width: 14px;
  height: 14px;
}

.action-btn:hover {
  background: var(--bg-elevated);
  color: var(--text-primary);
}

.action-btn.delete:hover {
  color: var(--color-red);
}
</style>
