/**
 * IndexedDB-basierter Cache für heruntergeladene Dateien (PDF/Word).
 *
 * Ziel: Nach dem ersten Laden wird der Datei-Blob lokal gespeichert, sodass das
 * erneute Öffnen ohne Netzwerk-Download auskommt. Invalidierung erfolgt über die
 * `modifiedTime` aus Google Drive — ändert sich die Datei, ist der Cache-Eintrag
 * automatisch „stale" und wird neu geladen.
 *
 * Aufräumstrategie: LRU mit Gesamt-Größenlimit (MAX_CACHE_BYTES). Beim Überschreiten
 * werden die am längsten nicht genutzten Einträge entfernt.
 *
 * Alle Operationen sind so gekapselt, dass ein Cache-Fehler (z. B. privater Modus,
 * deaktiviertes IndexedDB, Quota voll) niemals den eigentlichen Download blockiert.
 */

const DB_NAME = 'twonote-files'
const DB_VERSION = 1
const STORE = 'files'
const MAX_CACHE_BYTES = 50 * 1024 * 1024 // 50 MB

interface CacheEntry {
  fileId: string
  modifiedTime: string
  blob: Blob
  size: number
  lastAccess: number
}

let dbPromise: Promise<IDBDatabase> | null = null

function openDb(): Promise<IDBDatabase> {
  if (dbPromise) return dbPromise

  dbPromise = new Promise((resolve, reject) => {
    if (typeof indexedDB === 'undefined') {
      reject(new Error('IndexedDB nicht verfügbar'))
      return
    }

    const req = indexedDB.open(DB_NAME, DB_VERSION)

    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(STORE)) {
        const store = db.createObjectStore(STORE, { keyPath: 'fileId' })
        store.createIndex('lastAccess', 'lastAccess')
      }
    }

    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })

  // Bei Fehler erlauben, dass ein späterer Aufruf erneut öffnet.
  dbPromise.catch(() => {
    dbPromise = null
  })

  return dbPromise
}

function tx(db: IDBDatabase, mode: IDBTransactionMode): IDBObjectStore {
  return db.transaction(STORE, mode).objectStore(STORE)
}

function promisify<T>(req: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

/**
 * Liefert den gecachten Blob, wenn ein Eintrag mit exakt passender `modifiedTime`
 * existiert. Bei Treffer wird `lastAccess` aktualisiert (LRU). Sonst `null`.
 */
export async function getCachedFile(
  fileId: string,
  modifiedTime: string,
): Promise<Blob | null> {
  try {
    const db = await openDb()
    const entry = await promisify(tx(db, 'readonly').get(fileId) as IDBRequest<CacheEntry | undefined>)

    if (!entry || entry.modifiedTime !== modifiedTime) return null

    // lastAccess aktualisieren (best effort, Ergebnis nicht abwarten nötig)
    entry.lastAccess = Date.now()
    try {
      tx(db, 'readwrite').put(entry)
    } catch {
      /* ignorieren */
    }

    return entry.blob
  } catch (e) {
    console.warn('[fileCache] getCachedFile fehlgeschlagen:', e)
    return null
  }
}

/**
 * Schreibt einen Datei-Blob in den Cache und erzwingt anschließend das Größenbudget.
 */
export async function putCachedFile(
  fileId: string,
  modifiedTime: string,
  blob: Blob,
): Promise<void> {
  try {
    const db = await openDb()
    const entry: CacheEntry = {
      fileId,
      modifiedTime,
      blob,
      size: blob.size,
      lastAccess: Date.now(),
    }
    await promisify(tx(db, 'readwrite').put(entry))
    await enforceBudget(db)
  } catch (e) {
    console.warn('[fileCache] putCachedFile fehlgeschlagen:', e)
  }
}

/**
 * Entfernt einen einzelnen Eintrag (z. B. wenn die Datei gelöscht wurde).
 */
export async function evictFile(fileId: string): Promise<void> {
  try {
    const db = await openDb()
    await promisify(tx(db, 'readwrite').delete(fileId))
  } catch (e) {
    console.warn('[fileCache] evictFile fehlgeschlagen:', e)
  }
}

/**
 * Summiert die Gesamtgröße aller Einträge und löscht – beginnend beim am längsten
 * nicht genutzten Eintrag – solange, bis MAX_CACHE_BYTES wieder eingehalten wird.
 */
async function enforceBudget(db: IDBDatabase): Promise<void> {
  const entries = await promisify(
    tx(db, 'readonly').getAll() as IDBRequest<CacheEntry[]>,
  )

  let total = entries.reduce((sum, e) => sum + (e.size || 0), 0)
  if (total <= MAX_CACHE_BYTES) return

  // Älteste zuerst (kleinster lastAccess)
  entries.sort((a, b) => a.lastAccess - b.lastAccess)

  const store = tx(db, 'readwrite')
  for (const entry of entries) {
    if (total <= MAX_CACHE_BYTES) break
    store.delete(entry.fileId)
    total -= entry.size || 0
  }
}
