<template>
  <div class="home">
    <!-- Header -->
    <header class="app-header">
      <div class="header-left">
        <h1>TwoNote</h1>
      </div>
      <div class="header-right">
        <span class="username">{{ auth.username }}</span>
        <button class="btn btn-ghost" @click="handleLogout">Abmelden</button>
      </div>
    </header>

    <main class="main-content">
      <!-- Upload-Bereich -->
      <section class="upload-section">
        <FileUpload @uploaded="onFileUploaded" />
      </section>

      <!-- Fehler-Meldung -->
      <div v-if="filesStore.error" class="error-banner">
        {{ filesStore.error }}
      </div>

      <!-- Datei-Liste -->
      <section class="files-section">
        <div class="section-header">
          <!-- Breadcrumb-Navigation -->
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

          <button class="btn btn-secondary" @click="filesStore.fetchFiles()" :disabled="filesStore.loading">
            <span v-if="filesStore.loading">Laden…</span>
            <span v-else>Aktualisieren</span>
          </button>
        </div>

        <FileList
          :files="filesStore.files"
          :loading="filesStore.loading"
          @open="openEditor"
          @navigate="navigateIntoFolder"
          @delete="handleDelete"
        />
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useFilesStore } from '@/stores/files'
import { type DriveFile } from '@/api'
import FileUpload from '@/components/FileUpload.vue'
import FileList from '@/components/FileList.vue'

const router = useRouter()
const auth = useAuthStore()
const filesStore = useFilesStore()

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

function openEditor(file: DriveFile) {
  filesStore.setActiveFile(file)
  router.push({ name: 'editor', params: { id: file.id } })
}

async function handleDelete(file: DriveFile) {
  if (!confirm(`"${file.name}" wirklich löschen?`)) return
  await filesStore.deleteFile(file.id)
}

function onFileUploaded() {
  filesStore.fetchFiles()
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  background: var(--bg-primary);
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 2rem;
  background: var(--bg-primary);
  border-bottom: 1px solid var(--border-default);
  position: sticky;
  top: 0;
  z-index: 10;
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

.main-content {
  max-width: 1100px;
  margin: 0 auto;
  padding: 1.75rem 2rem;
}

.upload-section {
  margin-bottom: 1.5rem;
}

.error-banner {
  background: #2d1515;
  color: var(--color-red);
  padding: 0.7rem 0.875rem;
  border-radius: 4px;
  border: 1px solid #4d2020;
  margin-bottom: 1.25rem;
  font-size: 0.875rem;
}

.files-section {
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: 4px;
  padding: 1.25rem 1.5rem;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
  gap: 1rem;
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  flex: 1;
  min-width: 0;
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

.btn-secondary {
  background: var(--bg-tertiary);
  color: var(--text-muted);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--bg-elevated);
  color: var(--text-primary);
}

.btn-secondary:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
