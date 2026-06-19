import { defineStore } from 'pinia'
import { ref } from 'vue'
import { filesApi, type DriveFile } from '@/api'

const FOLDER_MIME = 'application/vnd.twonote.folder'

export const useFilesStore = defineStore('files', () => {
  // State
  const files = ref<DriveFile[]>([])
  const loading = ref(false)
  const uploading = ref(false)
  const uploadProgress = ref(0)
  const error = ref<string | null>(null)
  const activeFile = ref<DriveFile | null>(null)
  // Für die KI-Ordneransicht: zuletzt geöffneter Ordner (Namensauflösung).
  const activeFolder = ref<{ id: string; name: string } | null>(null)

  // Ordner-Navigation
  const currentFolderId = ref<string | undefined>(undefined)
  const folderPath = ref<{ id: string; name: string }[]>([])

  // Mehrfachauswahl (gilt nur für die aktuelle Ordneransicht)
  const selectedIds = ref<string[]>([])

  // Actions
  async function fetchFiles(): Promise<void> {
    loading.value = true
    error.value = null
    try {
      const { data } = await filesApi.list(currentFolderId.value)
      files.value = data.files
    } catch (e: any) {
      error.value = e.response?.data?.detail ?? 'Dateien konnten nicht geladen werden.'
    } finally {
      loading.value = false
    }
  }

  function navigateIntoFolder(folder: DriveFile): void {
    clearSelection()
    folderPath.value.push({ id: folder.id, name: folder.name })
    currentFolderId.value = folder.id
    fetchFiles()
  }

  function navigateToIndex(index: number): void {
    clearSelection()
    if (index < 0) {
      // Zurück zur Wurzel
      folderPath.value = []
      currentFolderId.value = undefined
    } else {
      folderPath.value = folderPath.value.slice(0, index + 1)
      currentFolderId.value = folderPath.value[index].id
    }
    fetchFiles()
  }

  async function uploadFile(file: File, folderId?: string): Promise<DriveFile | null> {
    uploading.value = true
    uploadProgress.value = 0
    error.value = null
    const targetFolder = folderId ?? currentFolderId.value
    try {
      const { data } = await filesApi.upload(
        file,
        (percent) => { uploadProgress.value = percent },
        targetFolder,
      )
      // Nur in aktuelle Ansicht einfügen wenn der Zielordner der aktuelle ist
      if (targetFolder === currentFolderId.value) {
        files.value.unshift(data.file)
      }
      return data.file
    } catch (e: any) {
      error.value = e.response?.data?.detail ?? 'Upload fehlgeschlagen.'
      return null
    } finally {
      uploading.value = false
      uploadProgress.value = 0
    }
  }

  async function createFolder(name: string, parentId?: string): Promise<DriveFile | null> {
    const target = parentId ?? currentFolderId.value
    try {
      const { data } = await filesApi.createFolder(name, target)
      return data.folder
    } catch (e: any) {
      error.value = e.response?.data?.detail ?? 'Ordner erstellen fehlgeschlagen.'
      return null
    }
  }

  async function deleteFile(fileId: string): Promise<boolean> {
    error.value = null
    try {
      await filesApi.delete(fileId)
      files.value = files.value.filter((f) => f.id !== fileId)
      if (activeFile.value?.id === fileId) {
        activeFile.value = null
      }
      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail ?? 'Löschen fehlgeschlagen.'
      return false
    }
  }

  // ─── Mehrfachauswahl ───
  function isSelected(id: string): boolean {
    return selectedIds.value.includes(id)
  }

  function toggleSelection(id: string): void {
    if (isSelected(id)) {
      selectedIds.value = selectedIds.value.filter((x) => x !== id)
    } else {
      selectedIds.value = [...selectedIds.value, id]
    }
  }

  function selectOnly(id: string): void {
    selectedIds.value = [id]
  }

  function clearSelection(): void {
    selectedIds.value = []
  }

  async function moveItems(ids: string[], parentId: string | null): Promise<boolean> {
    error.value = null
    // Ziel-Ordner nie in sich selbst verschieben.
    const toMove = ids.filter((id) => id !== parentId)
    if (toMove.length === 0) return false
    try {
      await filesApi.move(toMove, parentId)
      clearSelection()
      await fetchFiles()
      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail ?? 'Verschieben fehlgeschlagen.'
      return false
    }
  }

  async function deleteMany(ids: string[]): Promise<boolean> {
    error.value = null
    try {
      await Promise.all(ids.map((id) => filesApi.delete(id)))
      files.value = files.value.filter((f) => !ids.includes(f.id))
      if (activeFile.value && ids.includes(activeFile.value.id)) {
        activeFile.value = null
      }
      clearSelection()
      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail ?? 'Löschen fehlgeschlagen.'
      // Liste neu laden, da evtl. ein Teil gelöscht wurde
      await fetchFiles()
      return false
    }
  }

  function setActiveFile(file: DriveFile | null): void {
    activeFile.value = file
  }

  function setActiveFolder(folder: DriveFile | null): void {
    activeFolder.value = folder ? { id: folder.id, name: folder.name } : null
  }

  function getFileById(id: string): DriveFile | undefined {
    return files.value.find((f) => f.id !== undefined && f.id === id && f.mimeType !== FOLDER_MIME)
  }

  return {
    files,
    loading,
    uploading,
    uploadProgress,
    error,
    activeFile,
    activeFolder,
    currentFolderId,
    folderPath,
    selectedIds,
    fetchFiles,
    navigateIntoFolder,
    navigateToIndex,
    uploadFile,
    createFolder,
    deleteFile,
    deleteMany,
    moveItems,
    isSelected,
    toggleSelection,
    selectOnly,
    clearSelection,
    setActiveFile,
    setActiveFolder,
    getFileById,
  }
})
