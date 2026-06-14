<template>
  <div class="summary-panel">
    <div class="panel-header">
      <h3>KI-Zusammenfassung</h3>
      <router-link to="/archive" class="archive-link" title="Alle gespeicherten Zusammenfassungen">
        Archiv
      </router-link>
    </div>

    <div class="panel-body">
      <!-- Noch keine Zusammenfassung -->
      <div v-if="!summary && !loading && !error" class="idle-state">
        <p>Lass Gemini AI dieses Dokument für dich zusammenfassen.</p>
        <button class="summarize-btn" @click="summarize">
          Zusammenfassen
        </button>
      </div>

      <!-- Lädt -->
      <div v-else-if="loading" class="loading-state">
        <div class="pulse-dots">
          <span></span><span></span><span></span>
        </div>
        <p>Gemini liest das Dokument…</p>
        <p class="loading-hint">Das kann bei langen Dokumenten etwas dauern.</p>
      </div>

      <!-- Rate-Limit erreicht -->
      <div v-else-if="rateLimited" class="rate-limit-state">
        <div class="rate-limit-icon">⏳</div>
        <p class="rate-limit-title">Tägliches Limit erreicht</p>
        <p class="rate-limit-message">{{ error }}</p>
        <p class="rate-limit-hint">
          Das Gemini-Free-Tier erlaubt nur eine begrenzte Anzahl Anfragen pro Tag.
          Versuche es morgen erneut.
        </p>
      </div>

      <!-- Fehler -->
      <div v-else-if="error" class="error-state">
        <p>{{ error }}</p>
        <button class="summarize-btn" @click="summarize">Erneut versuchen</button>
      </div>

      <!-- Zusammenfassung anzeigen -->
      <div v-else class="summary-content">
        <div class="summary-actions">
          <button class="action-btn" @click="summarize" title="Neue Zusammenfassung">
            Neu
          </button>
          <button class="action-btn" @click="copyToClipboard" title="Kopieren">
            {{ copied ? 'Kopiert' : 'Kopieren' }}
          </button>
        </div>
        <div class="markdown-body" v-html="renderedSummary"></div>
      </div>
    </div>

    <!-- Footer: täglicher KI-Verbrauch -->
    <div class="panel-footer" :title="`Zurücksetzung täglich um Mitternacht Pacific Time`">
      <span class="usage-label">KI-Anfragen heute</span>
      <span class="usage-count" :class="{ exhausted: usage && usage.used >= usage.limit }">
        {{ usage ? `${usage.used} / ${usage.limit}` : '– / –' }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { marked } from 'marked'
import { filesApi } from '@/api'

const props = defineProps<{
  fileId: string
  filename: string
}>()

const summary = ref('')
const loading = ref(false)
const error = ref('')
const rateLimited = ref(false)
const copied = ref(false)
const usage = ref<{ used: number; limit: number; date: string } | null>(null)

async function fetchUsage() {
  try {
    const { data } = await filesApi.aiUsage()
    usage.value = data
  } catch {
    // Verbrauchsanzeige ist optional – Fehler still ignorieren
  }
}

// Beim Öffnen: zuletzt gespeicherte Zusammenfassung automatisch laden
async function loadSavedSummary() {
  try {
    const { data } = await filesApi.latestSummary(props.fileId)
    if (data && data.content) summary.value = data.content
  } catch {
    // Kein gespeicherter Stand – Panel bleibt im Idle-Zustand
  }
}

onMounted(() => {
  fetchUsage()
  loadSavedSummary()
})

const renderedSummary = computed(() => {
  if (!summary.value) return ''
  return marked.parse(summary.value) as string
})

async function summarize() {
  loading.value = true
  error.value = ''
  rateLimited.value = false
  summary.value = ''
  try {
    const { data } = await filesApi.summarize(props.fileId)
    summary.value = data.summary
  } catch (e: any) {
    error.value = e.response?.data?.detail ?? 'Zusammenfassung fehlgeschlagen.'
    if (e.response?.status === 429) {
      rateLimited.value = true
    }
  } finally {
    loading.value = false
    fetchUsage()
  }
}

async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(summary.value)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = summary.value
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  }
}
</script>

<style scoped>
.summary-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  color: var(--text-primary);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.archive-link {
  font-size: 0.75rem;
  color: var(--text-muted);
  text-decoration: none;
  border: 1px solid var(--border-default);
  border-radius: 3px;
  padding: 0.2rem 0.55rem;
  transition: all 0.15s;
}

.archive-link:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.panel-header h3 {
  margin: 0;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--text-muted);
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.panel-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  flex-shrink: 0;
  padding: 0.6rem 1rem;
  border-top: 1px solid var(--border-default);
  font-size: 0.75rem;
}

.usage-label {
  color: var(--text-muted);
}

.usage-count {
  font-variant-numeric: tabular-nums;
  color: var(--text-primary);
  font-weight: 500;
}

.usage-count.exhausted {
  color: var(--color-red);
}

.idle-state {
  text-align: center;
  color: var(--text-muted);
  padding: 2rem 0;
}

.idle-state p {
  margin: 0 0 1.25rem;
  font-size: 0.8125rem;
  line-height: 1.6;
}

.loading-state {
  text-align: center;
  color: var(--text-muted);
  padding: 2rem 0;
}

.loading-state p {
  margin: 0.5rem 0 0;
  font-size: 0.8125rem;
}

.loading-hint {
  font-size: 0.75rem !important;
  color: var(--text-faint) !important;
}

.pulse-dots {
  display: flex;
  justify-content: center;
  gap: 6px;
  margin-bottom: 1rem;
}

.pulse-dots span {
  width: 7px;
  height: 7px;
  background: var(--accent);
  border-radius: 50%;
  animation: pulse 1.2s ease-in-out infinite;
}

.pulse-dots span:nth-child(2) { animation-delay: 0.2s; }
.pulse-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes pulse {
  0%, 80%, 100% { opacity: 0.25; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1); }
}

.error-state {
  text-align: center;
  color: var(--color-red);
  padding: 1rem 0;
  font-size: 0.8125rem;
}

.error-state p {
  margin: 0 0 1rem;
}

.rate-limit-state {
  text-align: center;
  padding: 1.5rem 0.5rem;
  color: var(--text-muted);
}

.rate-limit-icon {
  font-size: 2rem;
  margin-bottom: 0.75rem;
}

.rate-limit-title {
  margin: 0 0 0.5rem;
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-primary);
}

.rate-limit-message {
  margin: 0 0 0.75rem;
  font-size: 0.8125rem;
  line-height: 1.5;
}

.rate-limit-hint {
  margin: 0;
  font-size: 0.75rem;
  color: var(--text-faint);
  line-height: 1.5;
}

.summarize-btn {
  background: var(--accent);
  color: #fff;
  border: none;
  padding: 0.5rem 1.125rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 500;
  transition: background 0.15s;
}

.summarize-btn:hover {
  background: var(--accent-hover);
}

.summary-actions {
  display: flex;
  gap: 0.4rem;
  margin-bottom: 0.875rem;
}

.action-btn {
  background: var(--bg-tertiary);
  color: var(--text-muted);
  border: 1px solid var(--border-default);
  padding: 0.25rem 0.625rem;
  border-radius: 3px;
  cursor: pointer;
  font-size: 0.75rem;
  transition: all 0.15s;
}

.action-btn:hover {
  background: var(--bg-elevated);
  color: var(--text-primary);
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
</style>
