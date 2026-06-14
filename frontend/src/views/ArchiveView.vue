<template>
  <div class="archive">
    <header class="archive-header">
      <button class="back-link" title="Zurück" @click="goBack">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6"/>
        </svg>
        Zurück
      </button>
      <h1>Archiv – KI-Zusammenfassungen</h1>
    </header>

    <div class="archive-body">
      <div v-if="loading" class="state">Lade Archiv…</div>

      <div v-else-if="error" class="state error">{{ error }}</div>

      <div v-else-if="summaries.length === 0" class="state">
        Noch keine Zusammenfassungen gespeichert.
      </div>

      <ul v-else class="entry-list">
        <li v-for="entry in summaries" :key="entry.id" class="entry">
          <button class="entry-head" @click="toggle(entry.id)">
            <div class="entry-meta">
              <span class="entry-name" :title="entry.filename">{{ entry.filename }}</span>
              <span class="entry-date">{{ formatDate(entry.created_at) }}</span>
            </div>
            <svg class="chevron" :class="{ open: openId === entry.id }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </button>

          <div v-if="openId === entry.id" class="entry-content markdown-body" v-html="render(entry.content)"></div>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { marked } from 'marked'
import { filesApi } from '@/api'

const router = useRouter()

function goBack() {
  // Zur vorherigen Seite zurück; falls keine Historie vorhanden, zur Startseite.
  if (window.history.length > 1) router.back()
  else router.push('/')
}

interface Entry {
  id: number
  file_id: string
  filename: string
  content: string
  created_at: string
}

const summaries = ref<Entry[]>([])
const loading = ref(true)
const error = ref('')
const openId = ref<number | null>(null)

function render(md: string): string {
  return marked.parse(md) as string
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  return d.toLocaleString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function toggle(id: number) {
  openId.value = openId.value === id ? null : id
}

onMounted(async () => {
  try {
    const { data } = await filesApi.allSummaries()
    summaries.value = data
    // Erste Zusammenfassung direkt aufklappen
    if (data.length > 0) openId.value = data[0].id
  } catch (e: any) {
    error.value = e.response?.data?.detail ?? 'Archiv konnte nicht geladen werden.'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.archive {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-primary);
  color: var(--text-primary);
}

.archive-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.9rem 1.5rem;
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.archive-header h1 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 600;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-size: 0.8125rem;
  font-family: inherit;
  color: var(--text-muted);
  text-decoration: none;
  background: none;
  cursor: pointer;
  border: 1px solid var(--border-default);
  border-radius: 4px;
  padding: 0.35rem 0.6rem;
  transition: all 0.15s;
}

.back-link svg {
  width: 14px;
  height: 14px;
}

.back-link:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.archive-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 1.5rem;
}

.state {
  color: var(--text-muted);
  text-align: center;
  padding: 3rem 1rem;
  font-size: 0.9rem;
}

.state.error {
  color: var(--color-red);
}

.entry-list {
  list-style: none;
  margin: 0 auto;
  padding: 0;
  max-width: 820px;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.entry {
  background: var(--bg-secondary);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  overflow: hidden;
}

.entry-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  width: 100%;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.75rem 1rem;
  text-align: left;
  color: var(--text-primary);
}

.entry-head:hover {
  background: var(--bg-tertiary);
}

.entry-meta {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}

.entry-name {
  font-size: 0.875rem;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.entry-date {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.chevron {
  width: 16px;
  height: 16px;
  color: var(--text-muted);
  flex-shrink: 0;
  transition: transform 0.15s;
}

.chevron.open {
  transform: rotate(180deg);
}

.entry-content {
  padding: 0.5rem 1rem 1rem;
  border-top: 1px solid var(--border-default);
}

.markdown-body {
  font-size: 0.8125rem;
  line-height: 1.7;
  color: var(--text-primary);
}

.markdown-body :deep(h2) {
  font-size: 0.875rem;
  color: var(--accent-hover);
  margin: 1.25rem 0 0.4rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid var(--border-subtle);
  font-weight: 600;
}

.markdown-body :deep(h3) {
  font-size: 0.8125rem;
  color: var(--accent);
  margin: 1rem 0 0.35rem;
  font-weight: 600;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 1.25rem;
  margin: 0.4rem 0;
}

.markdown-body :deep(li) {
  margin: 0.2rem 0;
}

.markdown-body :deep(strong) {
  color: var(--text-primary);
  font-weight: 600;
}

.markdown-body :deep(p) {
  margin: 0.4rem 0;
}

.markdown-body :deep(blockquote) {
  border-left: 2px solid var(--accent);
  padding-left: 0.75rem;
  color: var(--text-muted);
  margin: 0.75rem 0;
  font-style: italic;
}

@media (max-width: 760px) {
  .archive-header {
    flex-wrap: wrap;
    gap: 0.6rem;
    padding: 0.75rem 1rem;
  }
  .archive-header h1 {
    font-size: 0.95rem;
  }
  .archive-body {
    padding: 1rem;
  }
}
</style>
