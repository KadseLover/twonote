<template>
  <div class="word-viewer">
    <div v-if="loading" class="state">
      <div class="spinner"></div>
      <p>Word-Dokument wird konvertiert…</p>
    </div>

    <div v-else-if="errorMsg" class="state error">
      <p>{{ errorMsg }}</p>
    </div>

    <div v-else class="document-frame">
      <article class="document" v-html="html"></article>
      <div v-if="warnings.length" class="warnings">
        <details>
          <summary>{{ warnings.length }} Hinweis(e) beim Konvertieren</summary>
          <ul>
            <li v-for="(w, i) in warnings" :key="i">{{ w }}</li>
          </ul>
        </details>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import mammoth from 'mammoth/mammoth.browser'

const props = defineProps<{
  docData: ArrayBuffer
  mimeType: string
  filename: string
}>()

const loading = ref(true)
const errorMsg = ref('')
const html = ref('')
const warnings = ref<string[]>([])

const LEGACY_DOC = 'application/msword'

onMounted(async () => {
  const isLegacy =
    props.mimeType === LEGACY_DOC ||
    props.filename.toLowerCase().endsWith('.doc')

  if (isLegacy) {
    errorMsg.value =
      'Dieses Dokument liegt im alten .doc-Format vor und kann hier nicht angezeigt werden. ' +
      'Bitte konvertiere es in .docx oder lade es über den Download-Button herunter.'
    loading.value = false
    return
  }

  try {
    const result = await mammoth.convertToHtml({ arrayBuffer: props.docData })
    html.value = result.value
    warnings.value = result.messages.map((m: { message: string }) => m.message)
  } catch (e: any) {
    console.error('Word-Konvertierung fehlgeschlagen:', e)
    errorMsg.value = 'Das Dokument konnte nicht angezeigt werden.'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.word-viewer {
  height: 100%;
  overflow: auto;
  background: #181818;
  padding: 1.5rem;
}

.state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  height: 100%;
  color: var(--text-muted);
  text-align: center;
}

.state.error {
  color: var(--color-red);
  max-width: 480px;
  margin: 0 auto;
  padding-top: 4rem;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 2px solid var(--border-strong);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.document-frame {
  max-width: 820px;
  margin: 0 auto;
}

.document {
  background: #fff;
  color: #111;
  padding: 3.5rem 4rem;
  border-radius: 4px;
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.6);
  font-family: 'Calibri', 'Segoe UI', sans-serif;
  font-size: 14px;
  line-height: 1.55;
}

.document :deep(h1),
.document :deep(h2),
.document :deep(h3),
.document :deep(h4) {
  color: #111;
  margin: 1.2em 0 0.4em;
  font-weight: 600;
}
.document :deep(h1) { font-size: 1.8em; }
.document :deep(h2) { font-size: 1.45em; }
.document :deep(h3) { font-size: 1.2em; }

.document :deep(p) {
  margin: 0 0 0.7em;
}

.document :deep(table) {
  border-collapse: collapse;
  margin: 1em 0;
  width: 100%;
}

.document :deep(table td),
.document :deep(table th) {
  border: 1px solid #c0c0c0;
  padding: 0.35rem 0.55rem;
  vertical-align: top;
}

.document :deep(ul),
.document :deep(ol) {
  margin: 0.4em 0 0.8em 1.5em;
}

.document :deep(img) {
  max-width: 100%;
  height: auto;
}

.document :deep(a) {
  color: #1a4fa6;
}

.warnings {
  margin-top: 1rem;
  font-size: 0.8125rem;
  color: var(--text-muted);
  max-width: 820px;
  margin-left: auto;
  margin-right: auto;
}

.warnings summary {
  cursor: pointer;
  padding: 0.4rem 0.6rem;
  background: var(--bg-secondary);
  border-radius: 3px;
}

.warnings ul {
  margin: 0.4rem 0 0 1rem;
}
</style>
