<template>
  <div class="onlyoffice-editor">
    <!-- Lade-/Fehlerzustand über dem Editor -->
    <div v-if="loading" class="state">
      <div class="spinner"></div>
      <p>Editor wird geladen…</p>
    </div>
    <div v-else-if="errorMsg" class="state error">
      <p>{{ errorMsg }}</p>
      <button @click="reload">Erneut versuchen</button>
    </div>

    <!-- Platzhalter, in den OnlyOffice den Editor-Iframe einhängt -->
    <div :id="containerId" class="editor-host"></div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { filesApi, authApi } from '@/api'
import { useIsMobile } from '@/utils/useIsMobile'

const props = defineProps<{
  fileId: string
}>()

const { isMobile } = useIsMobile()

const loading = ref(true)
const errorMsg = ref('')
// Eindeutige Element-ID – DocsAPI.DocEditor erwartet eine ID, keine Element-Referenz.
const containerId = `onlyoffice-${Math.random().toString(36).slice(2)}`

let editor: any = null

// Das DocsAPI-Script wird pro Document-Server-URL nur einmal geladen (über alle
// Editor-Instanzen hinweg). Erneutes Laden würde window.DocsAPI doppelt definieren.
let docsApiPromise: Promise<void> | null = null

function loadDocsApi(serverUrl: string): Promise<void> {
  if ((window as any).DocsAPI) return Promise.resolve()
  if (docsApiPromise) return docsApiPromise
  docsApiPromise = new Promise<void>((resolve, reject) => {
    const script = document.createElement('script')
    script.src = `${serverUrl.replace(/\/$/, '')}/web-apps/apps/api/documents/api.js`
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => {
      docsApiPromise = null // erlaubt einen erneuten Versuch
      reject(new Error('Der Document Server ist nicht erreichbar.'))
    }
    document.head.appendChild(script)
  })
  return docsApiPromise
}

async function initEditor() {
  loading.value = true
  errorMsg.value = ''
  try {
    const { data } = await filesApi.onlyofficeConfig(props.fileId)
    await loadDocsApi(data.documentServerUrl)

    // Server liefert die signierte Config; Präsentation + Client-Events ergänzen wir hier
    // (diese Felder sind nicht Teil der JWT-Signatur).
    const config = {
      ...data.config,
      width: '100%',
      height: '100%',
      type: isMobile.value ? 'mobile' : 'desktop',
      events: {
        onAppReady: () => { loading.value = false },
        onError: (event: any) => {
          console.error('OnlyOffice-Fehler:', event)
          errorMsg.value = 'Im Editor ist ein Fehler aufgetreten.'
          loading.value = false
        },
        // Avatare/Namen der Mitbearbeiter liefern (eigenes Bild kommt aus der Config,
        // die der anderen müssen über setUsers nachgereicht werden).
        onRequestUsers: handleRequestUsers,
      },
    }

    destroyEditor()
    editor = new (window as any).DocsAPI.DocEditor(containerId, config)
  } catch (e: any) {
    console.error('OnlyOffice-Editor konnte nicht gestartet werden:', e)
    errorMsg.value = e?.response?.data?.detail || e?.message || 'Editor konnte nicht geladen werden.'
    loading.value = false
  }
}

// OnlyOffice fragt beim Öffnen der Mitbearbeiter-Liste/Kommentare nach Nutzer-Infos.
// Wir lösen die IDs in Name + (absolute) Avatar-URL auf und reichen sie via setUsers nach.
async function handleRequestUsers(event: any) {
  try {
    const payload = event?.data ?? event ?? {}
    const c = payload.c ?? 'info'
    const rawIds = Array.isArray(payload.id) ? payload.id : payload.id != null ? [payload.id] : []
    if (rawIds.length === 0) {
      editor?.setUsers?.({ c, users: [] })
      return
    }
    const { data } = await authApi.usersInfo(rawIds)
    const origin = window.location.origin
    const users = data.map((u) => ({
      id: String(u.id),
      name: u.username,
      image: u.has_avatar ? `${origin}/api/auth/avatars/${u.id}` : undefined,
    }))
    editor?.setUsers?.({ c, users })
  } catch (e) {
    console.warn('onRequestUsers fehlgeschlagen:', e)
  }
}

function destroyEditor() {
  try {
    editor?.destroyEditor?.()
  } catch (e) {
    console.warn('OnlyOffice destroyEditor fehlgeschlagen:', e)
  }
  editor = null
}

function reload() {
  initEditor()
}

onMounted(initEditor)
onBeforeUnmount(destroyEditor)
</script>

<style scoped>
.onlyoffice-editor {
  position: relative;
  height: 100%;
  width: 100%;
  background: var(--bg-primary);
}

.editor-host {
  height: 100%;
  width: 100%;
}

/* OnlyOffice rendert einen Iframe – sicherstellen, dass er die volle Fläche füllt. */
.editor-host :deep(iframe) {
  border: 0;
  width: 100%;
  height: 100%;
}

.state {
  position: absolute;
  inset: 0;
  z-index: 5;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  background: var(--bg-primary);
  color: var(--text-muted);
  text-align: center;
  padding: 2rem;
}

.state.error {
  color: var(--color-red);
}

.state button {
  background: var(--accent);
  color: #fff;
  border: none;
  border-radius: 4px;
  padding: 0.4rem 0.9rem;
  cursor: pointer;
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
</style>
