<template>
  <div class="folder-viewer">
    <header class="folder-header">
      <svg class="folder-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
        <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
      </svg>
      <span class="folder-name">{{ folderName }}</span>
    </header>

    <div class="folder-panel">
      <AiPanel :target="{ kind: 'folder', id: folderId, name: folderName }" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useFilesStore } from '@/stores/files'
import AiPanel from '@/components/AiPanel.vue'

const props = defineProps<{
  folderId: string
}>()

const filesStore = useFilesStore()

// Name aus dem zuletzt geöffneten Ordner bzw. der aktuellen Liste; Fallback "Ordner".
const folderName = computed(() => {
  if (filesStore.activeFolder?.id === props.folderId) return filesStore.activeFolder.name
  const match = filesStore.files.find((f) => f.id === props.folderId)
  return match?.name ?? 'Ordner'
})
</script>

<style scoped>
.folder-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--bg-primary);
}

.folder-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
  padding: 0.75rem 1.25rem;
  border-bottom: 1px solid var(--border-default);
  background: var(--bg-secondary);
}

.folder-icon {
  width: 18px;
  height: 18px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.folder-name {
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Panel mittig mit angenehmer Lesebreite */
.folder-panel {
  flex: 1;
  min-height: 0;
  width: 100%;
  max-width: 760px;
  margin: 0 auto;
  overflow: hidden;
}
</style>
