<template>
  <div class="ai-panel">
    <div class="panel-header">
      <h3>KI-Panel</h3>
      <router-link to="/archive" class="archive-link" title="Alle gespeicherten Zusammenfassungen">
        Archiv
      </router-link>
    </div>

    <!-- Tab-Leiste -->
    <div class="tab-bar" role="tablist">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'summary' }"
        role="tab"
        @click="activeTab = 'summary'"
      >
        Zusammenfassung
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'qa' }"
        role="tab"
        @click="openQaTab"
      >
        Fragen
      </button>
    </div>

    <!-- ─────────── Tab 1: Zusammenfassung ─────────── -->
    <div v-if="activeTab === 'summary'" class="panel-body">
      <!-- Noch keine Zusammenfassung -->
      <div v-if="!summary && !loading && !error" class="idle-state">
        <p>{{ target.kind === 'folder'
          ? 'Lass Gemini AI diesen Ordner (inkl. Unterordner) zusammenfassen.'
          : 'Lass Gemini AI dieses Dokument für dich zusammenfassen.' }}</p>
        <button class="summarize-btn" @click="summarize">Zusammenfassen</button>
      </div>

      <!-- Lädt -->
      <div v-else-if="loading" class="loading-state">
        <div class="pulse-dots"><span></span><span></span><span></span></div>
        <p>{{ target.kind === 'folder' ? 'Gemini liest die Dateien…' : 'Gemini liest das Dokument…' }}</p>
        <p class="loading-hint">Das kann bei vielen/langen Dokumenten etwas dauern.</p>
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
          <button class="action-btn" @click="summarize" title="Neue Zusammenfassung">Neu</button>
          <button class="action-btn" @click="copyToClipboard" title="Kopieren">
            {{ copied ? 'Kopiert' : 'Kopieren' }}
          </button>
        </div>
        <div class="markdown-body" v-html="renderedSummary"></div>
      </div>
    </div>

    <!-- ─────────── Tab 2: Fragen (Q&A mit Rückfragen) ─────────── -->
    <div v-else class="panel-body qa-body">
      <div ref="chatScroll" class="qa-messages">
        <!-- Leerzustand -->
        <div v-if="messages.length === 0 && !chatLoading" class="idle-state">
          <p>{{ target.kind === 'folder'
            ? 'Stelle eine Frage zum Inhalt dieses Ordners. Du kannst danach Rückfragen stellen.'
            : 'Stelle eine Frage zu diesem Dokument. Du kannst danach Rückfragen stellen.' }}</p>
        </div>

        <!-- Verlauf -->
        <div
          v-for="(msg, i) in messages"
          :key="i"
          class="chat-msg"
          :class="msg.role"
        >
          <div v-if="msg.role === 'user'" class="chat-bubble user">{{ msg.content }}</div>
          <div v-else class="chat-bubble assistant markdown-body" v-html="renderMarkdown(msg.content)"></div>
        </div>

        <!-- Antwort lädt -->
        <div v-if="chatLoading" class="chat-msg assistant">
          <div class="chat-bubble assistant">
            <div class="pulse-dots"><span></span><span></span><span></span></div>
          </div>
        </div>
      </div>

      <!-- Fehler-/Rate-Limit-Hinweis -->
      <div v-if="chatError" class="qa-error" :class="{ 'rate-limit': chatRateLimited }">
        {{ chatError }}
      </div>

      <!-- Eingabe -->
      <div class="qa-input-row">
        <button
          v-if="messages.length > 0"
          class="action-btn new-chat-btn"
          title="Neue Unterhaltung beginnen"
          @click="newChat"
        >
          Neu
        </button>
        <textarea
          v-model="question"
          class="qa-input"
          rows="2"
          :placeholder="messages.length ? 'Rückfrage stellen…' : 'Frage stellen…'"
          :disabled="chatLoading"
          @keydown.enter.exact.prevent="sendQuestion"
        ></textarea>
        <button
          class="qa-send-btn"
          :disabled="chatLoading || !question.trim()"
          @click="sendQuestion"
        >
          Senden
        </button>
      </div>
    </div>

    <!-- Footer: täglicher KI-Verbrauch -->
    <div class="panel-footer" @mouseenter="onFooterEnter" @mouseleave="onFooterLeave">
      <span class="usage-label">KI-Anfragen heute</span>
      <span class="usage-count" :class="{ exhausted: usage && usage.used >= usage.limit }">
        {{ usage ? `${usage.used} / ${usage.limit}` : '– / –' }}
      </span>

      <!-- Tooltip: wann/wie lange bis zum Reset -->
      <div v-if="showTooltip && usage?.resets_at" class="reset-tooltip">
        <div class="reset-tooltip-line">Reset um <strong>{{ resetLocalTime }}</strong> Uhr</div>
        <div class="reset-tooltip-line">noch <strong>{{ remainingText }}</strong></div>
        <div class="reset-tooltip-sub">täglich · Pacific Time</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { marked } from 'marked'
import { filesApi, type ChatMessage } from '@/api'

const props = defineProps<{
  target: { kind: 'file' | 'folder'; id: string; name: string }
}>()

const activeTab = ref<'summary' | 'qa'>('summary')

// ─── Zusammenfassung ───
const summary = ref('')
const loading = ref(false)
const error = ref('')
const rateLimited = ref(false)
const copied = ref(false)
const usage = ref<{ used: number; limit: number; date: string; resets_at: string } | null>(null)

// ─── Reset-Tooltip im Footer ───
const showTooltip = ref(false)
const now = ref(Date.now())
let tick: number | undefined

function onFooterEnter() {
  now.value = Date.now()
  showTooltip.value = true
  tick = window.setInterval(() => (now.value = Date.now()), 1000)
}

function onFooterLeave() {
  showTooltip.value = false
  if (tick) {
    clearInterval(tick)
    tick = undefined
  }
}

onBeforeUnmount(() => {
  if (tick) clearInterval(tick)
})

const resetLocalTime = computed(() => {
  if (!usage.value?.resets_at) return ''
  return new Date(usage.value.resets_at).toLocaleTimeString('de-DE', {
    hour: '2-digit',
    minute: '2-digit',
  })
})

const remainingText = computed(() => {
  if (!usage.value?.resets_at) return ''
  const ms = new Date(usage.value.resets_at).getTime() - now.value
  if (ms <= 0) return 'gleich'
  const totalMin = Math.floor(ms / 60000)
  const h = Math.floor(totalMin / 60)
  const m = totalMin % 60
  if (h > 0) return `${h} Std ${m} Min`
  if (m > 0) return `${m} Min`
  return 'weniger als 1 Min'
})

// ─── Q&A ───
const messages = ref<ChatMessage[]>([])
const sessionId = ref<string | null>(null)
const question = ref('')
const chatLoading = ref(false)
const chatError = ref('')
const chatRateLimited = ref(false)
const chatLoaded = ref(false)
const chatScroll = ref<HTMLElement | null>(null)

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
    const { data } = await filesApi.latestSummary(props.target.id)
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

function renderMarkdown(text: string): string {
  return marked.parse(text) as string
}

async function summarize() {
  loading.value = true
  error.value = ''
  rateLimited.value = false
  summary.value = ''
  try {
    const { data } = props.target.kind === 'folder'
      ? await filesApi.summarizeFolder(props.target.id)
      : await filesApi.summarize(props.target.id)
    summary.value = data.summary
  } catch (e: any) {
    error.value = e.response?.data?.detail ?? 'Zusammenfassung fehlgeschlagen.'
    if (e.response?.status === 429) rateLimited.value = true
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

// ─── Q&A-Logik ───
function openQaTab() {
  activeTab.value = 'qa'
  loadLatestChat()
}

async function loadLatestChat() {
  if (chatLoaded.value) return
  chatLoaded.value = true
  try {
    const { data } = await filesApi.latestChat(props.target.id)
    if (data) {
      sessionId.value = data.session_id
      messages.value = data.messages
      scrollChatToBottom()
    }
  } catch {
    // Kein gespeicherter Verlauf – leer starten
  }
}

function newChat() {
  messages.value = []
  sessionId.value = null
  chatError.value = ''
  chatRateLimited.value = false
}

async function sendQuestion() {
  const q = question.value.trim()
  if (!q || chatLoading.value) return
  chatError.value = ''
  chatRateLimited.value = false
  // Optimistische Anzeige der eigenen Frage
  messages.value.push({ role: 'user', content: q, created_at: new Date().toISOString() })
  question.value = ''
  chatLoading.value = true
  scrollChatToBottom()
  try {
    const { data } = await filesApi.chat(props.target.id, {
      question: q,
      session_id: sessionId.value ?? undefined,
      target_kind: props.target.kind,
    })
    sessionId.value = data.session_id
    messages.value = data.messages
  } catch (e: any) {
    messages.value.pop() // optimistische Frage zurücknehmen
    question.value = q // zum erneuten Versuch wiederherstellen
    chatError.value = e.response?.data?.detail ?? 'Frage fehlgeschlagen.'
    if (e.response?.status === 429) chatRateLimited.value = true
  } finally {
    chatLoading.value = false
    fetchUsage()
    scrollChatToBottom()
  }
}

function scrollChatToBottom() {
  nextTick(() => {
    if (chatScroll.value) chatScroll.value.scrollTop = chatScroll.value.scrollHeight
  })
}
</script>

<style scoped>
.ai-panel {
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

/* ── Tab-Leiste ── */
.tab-bar {
  display: flex;
  gap: 0.25rem;
  padding: 0.5rem 1rem 0;
  border-bottom: 1px solid var(--border-default);
  flex-shrink: 0;
}

.tab-btn {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  padding: 0.35rem 0.5rem 0.5rem;
  cursor: pointer;
  font-size: 0.8125rem;
  color: var(--text-muted);
  transition: color 0.15s, border-color 0.15s;
}

.tab-btn:hover {
  color: var(--text-primary);
}

.tab-btn.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
  font-weight: 500;
}

.panel-body {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  min-height: 0;
}

.panel-footer {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  flex-shrink: 0;
  padding: 0.6rem 1rem;
  border-top: 1px solid var(--border-default);
  font-size: 0.75rem;
}

.reset-tooltip {
  position: absolute;
  bottom: calc(100% + 6px);
  right: 1rem;
  z-index: 30;
  background: var(--bg-elevated);
  border: 1px solid var(--border-default);
  border-radius: 6px;
  padding: 0.5rem 0.7rem;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
  white-space: nowrap;
  pointer-events: none;
}

.reset-tooltip-line {
  font-size: 0.75rem;
  color: var(--text-primary);
  line-height: 1.5;
}

.reset-tooltip-line strong {
  color: var(--accent-hover);
  font-weight: 600;
}

.reset-tooltip-sub {
  margin-top: 0.2rem;
  font-size: 0.6875rem;
  color: var(--text-faint);
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

/* ── Q&A ── */
.qa-body {
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}

.qa-messages {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.chat-msg {
  display: flex;
}

.chat-msg.user {
  justify-content: flex-end;
}

.chat-msg.assistant {
  justify-content: flex-start;
}

.chat-bubble {
  max-width: 90%;
  border-radius: 8px;
  padding: 0.5rem 0.75rem;
  font-size: 0.8125rem;
  line-height: 1.6;
}

.chat-bubble.user {
  background: var(--accent);
  color: #fff;
  white-space: pre-wrap;
  word-break: break-word;
}

.chat-bubble.assistant {
  background: var(--bg-tertiary);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  width: 100%;
  max-width: 100%;
}

.qa-error {
  margin: 0 1rem;
  padding: 0.5rem 0.7rem;
  border-radius: 4px;
  font-size: 0.75rem;
  background: #2d1515;
  color: var(--color-red);
  border: 1px solid #4d2020;
}

.qa-error.rate-limit {
  background: var(--bg-tertiary);
  color: var(--text-muted);
  border-color: var(--border-default);
}

.qa-input-row {
  display: flex;
  align-items: flex-end;
  gap: 0.4rem;
  padding: 0.6rem 1rem 0.75rem;
  border-top: 1px solid var(--border-default);
  flex-shrink: 0;
}

.new-chat-btn {
  flex-shrink: 0;
  align-self: stretch;
}

.qa-input {
  flex: 1;
  min-width: 0;
  resize: none;
  background: var(--bg-primary);
  border: 1px solid var(--border-default);
  border-radius: 4px;
  padding: 0.4rem 0.5rem;
  color: var(--text-primary);
  font-size: 0.8125rem;
  font-family: inherit;
  line-height: 1.4;
}

.qa-input:focus {
  outline: none;
  border-color: var(--accent);
}

.qa-send-btn {
  flex-shrink: 0;
  background: var(--accent);
  color: #fff;
  border: none;
  padding: 0.45rem 0.85rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 500;
  transition: background 0.15s;
}

.qa-send-btn:hover:not(:disabled) {
  background: var(--accent-hover);
}

.qa-send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
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

.markdown-body :deep(p:first-child) {
  margin-top: 0;
}

.markdown-body :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-body :deep(blockquote) {
  border-left: 2px solid var(--accent);
  padding-left: 0.75rem;
  color: var(--text-muted);
  margin: 0.75rem 0;
  font-style: italic;
}
</style>
