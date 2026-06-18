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

  // Ordner-Navigation
  const currentFolderId = ref<string | undefined>(undefined)
  const folderPath = ref<{ id: string; name: string }[]>([])

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
    folderPath.value.push({ id: folder.id, name: folder.name })
    currentFolderId.value = folder.id
    fetchFiles()
  }

  function navigateToIndex(index: number): void {
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

  function setActiveFile(file: DriveFile | null): void {
    activeFile.value = file
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
    currentFolderId,
    folderPath,
    fetchFiles,
    navigateIntoFolder,
    navigateToIndex,
    uploadFile,
    createFolder,
    deleteFile,
    setActiveFile,
    getFileById,
  }
})
