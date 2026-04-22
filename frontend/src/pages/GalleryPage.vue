<template>
  <section class="page">
    <header class="page-header">
      <h2 class="page-title">图库管理</h2>
      <p class="page-subtitle">选择并导入图片到系统。</p>
    </header>

    <div class="card">
      <h3 class="card-title">导入新图片</h3>
      <p class="card-hint">
        选择文件夹后，图片将按文件修改时间自动归入
        <code class="inline-code">media/YYYY-M/</code>。
        子文件夹将作为整体单元处理。
      </p>

      <!-- Action buttons -->
      <div class="action-row">
        <button
          class="btn btn--primary"
          :disabled="importing || refreshing"
          @click="openImportDialog"
        >
          选择图片文件夹并导入
        </button>
        <button
          class="btn btn--secondary"
          :disabled="importing || refreshing"
          title="全量扫描媒体库：修复记录并收编新文件"
          @click="runRefresh"
        >
          <span :class="['btn__icon', { spinning: refreshing }]">🔄</span>
          刷新
        </button>
      </div>

      <input
        ref="folderInput"
        type="file"
        class="hidden-input"
        webkitdirectory
        directory
        multiple
        @change="handleFolderSelection"
      />

      <!-- Status line -->
      <p v-if="status" class="status-text">{{ status }}</p>

      <!-- Live import indicator -->
      <div v-if="importing && currentItem" class="live-indicator">
        <span class="live-indicator__spinner"></span>
        <span class="live-indicator__name">{{ currentItem }}</span>
      </div>

      <!-- Per-file progress -->
      <p v-if="importing && totalFiles > 0" class="progress-text">
        {{ currentFolderLabel ? `${currentFolderLabel} · ` : '' }}{{ doneFiles }} / {{ totalFiles }} 张
      </p>

      <!-- Unified notice -->
      <div v-if="noticeVisible" :class="['result-box', `result-box--${noticeType}`]">
        <div class="result-box__header">
          <p class="result-box__line result-box__line--heading">{{ noticeTitle }}</p>
          <button class="result-box__close" type="button" @click="closeNotice">×</button>
        </div>
        <p v-for="(line, idx) in noticeLines" :key="idx" class="result-box__line result-box__line--muted">
          {{ line }}
        </p>
      </div>
    </div>

    <FolderImportDialog
      :visible="importDialogOpen"
      :busy="importing"
      :rows="importDialogRows"
      :selected-ids="selectedImportRowIds"
      :categories="importCategories"
      :error="importDialogError"
      @close="closeImportDialog"
      @add-row="triggerFolderPicker"
      @delete-selected="deleteSelectedImportRows"
      @confirm="confirmImportDialog"
      @toggle-row="toggleImportRowSelection"
      @update-category="updateImportRowCategory"
    />
  </section>
</template>

<script>
import FolderImportDialog from '../components/FolderImportDialog.vue'

const API_BASE = 'http://127.0.0.1:8000'
const DEFAULT_CATEGORY_ID = 1
const AUTO_CATEGORY_KEY = 'auto'
const IMPORT_CHUNK = 50
const IMAGE_EXT_RE = /\.(jpe?g|png|webp|gif|bmp|tiff?)$/i

function toErrorMessage(err) {
  if (!err) return '未知错误'
  if (typeof err === 'string') return err
  if (err instanceof Error) return err.message
  try {
    return JSON.stringify(err)
  } catch {
    return String(err)
  }
}

export default {
  name: 'GalleryPage',
  components: {
    FolderImportDialog,
  },

  data() {
    return {
      status:        '',
      importing:     false,
      currentItem:   '',
      totalFiles:    0,
      doneFiles:     0,
      refreshing:    false,
      noticeVisible: false,
      noticeType:    'info',
      noticeTitle:   '',
      noticeLines:   [],
      importDialogOpen: false,
      importDialogRows: [],
      selectedImportRowIds: [],
      importCategories: [],
      importDialogError: '',
      nextImportRowId: 1,
      checkingThumbs: false,
      currentFolderLabel: '',
    }
  },

  created() {
    this._checkMissingThumbs()
  },

  activated() {
    this._checkMissingThumbs()
  },

  methods: {
    showNotice({ type = 'info', title = '', lines = [] }) {
      this.noticeType = type
      this.noticeTitle = title
      this.noticeLines = lines
      this.noticeVisible = true
    },

    closeNotice() {
      this.noticeVisible = false
    },

    clearNotice() {
      this.noticeVisible = false
      this.noticeType = 'info'
      this.noticeTitle = ''
      this.noticeLines = []
    },

    defaultImportCategoryValue() {
      const defaultCategory = this.importCategories.find(category => Number(category.id) === DEFAULT_CATEGORY_ID)
      if (defaultCategory) return String(defaultCategory.id)
      const firstCategory = this.importCategories[0]
      return firstCategory ? String(firstCategory.id) : String(DEFAULT_CATEGORY_ID)
    },

    async ensureImportCategoriesLoaded(force = false) {
      if (!force && this.importCategories.length) return true
      try {
        const res = await fetch(`${API_BASE}/api/categories`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        const categories = Array.isArray(data.items)
          ? data.items.filter(category => category && category.is_active !== false)
          : []
        this.importCategories = categories
        return true
      } catch (err) {
        this.importDialogError = `加载主分类失败：${toErrorMessage(err)}`
        this.showNotice({ type: 'error', title: '加载主分类失败', lines: [toErrorMessage(err)] })
        return false
      }
    },

    async openImportDialog() {
      if (this.importing || this.refreshing) return
      const loaded = await this.ensureImportCategoriesLoaded()
      if (!loaded) return
      this.importDialogError = ''
      this.importDialogOpen = true
    },

    closeImportDialog() {
      if (this.importing) return
      this.resetImportDialog()
    },

    resetImportDialog() {
      this.importDialogOpen = false
      this.importDialogRows = []
      this.selectedImportRowIds = []
      this.importDialogError = ''
    },

    triggerFolderPicker() {
      if (this.importing) return
      const input = this.$refs.folderInput
      if (!input) return
      input.value = ''
      input.click()
    },

    handleFolderSelection(event) {
      const files = Array.from(event.target.files || [])
      event.target.value = ''
      if (!files.length) return

      const rootName = (files[0].webkitRelativePath || files[0].name).split('/')[0] || '未命名目录'
      const imageCount = files.filter(file => IMAGE_EXT_RE.test(file.name || '')).length
      const row = {
        id: this.nextImportRowId,
        label: rootName,
        files,
        fileCount: files.length,
        imageCount,
        categoryValue: this.defaultImportCategoryValue(),
      }

      this.nextImportRowId += 1
      this.importDialogRows = [...this.importDialogRows, row]
      this.importDialogError = ''
      if (!this.importDialogOpen) {
        this.importDialogOpen = true
      }
    },

    toggleImportRowSelection(rowId) {
      if (this.importing) return
      if (this.selectedImportRowIds.includes(rowId)) {
        this.selectedImportRowIds = this.selectedImportRowIds.filter(id => id !== rowId)
        return
      }
      this.selectedImportRowIds = [...this.selectedImportRowIds, rowId]
    },

    updateImportRowCategory({ rowId, value }) {
      this.importDialogRows = this.importDialogRows.map(row => (
        row.id === rowId ? { ...row, categoryValue: value } : row
      ))
      this.importDialogError = ''
    },

    deleteSelectedImportRows() {
      if (this.importing || !this.selectedImportRowIds.length) return
      const selectedIdSet = new Set(this.selectedImportRowIds)
      this.importDialogRows = this.importDialogRows.filter(row => !selectedIdSet.has(row.id))
      this.selectedImportRowIds = []
      if (!this.importDialogRows.length) {
        this.importDialogError = ''
      }
    },

    buildImportBatches(files) {
      const directFiles = []
      const subdirMap = {}

      for (const file of files) {
        const parts = (file.webkitRelativePath || file.name).split('/')
        if (parts.length <= 2) {
          directFiles.push(file)
        } else {
          const subdir = parts[1]
          if (!subdirMap[subdir]) subdirMap[subdir] = []
          subdirMap[subdir].push(file)
        }
      }

      const directBatches = []
      for (let index = 0; index < directFiles.length; index += IMPORT_CHUNK) {
        const chunk = directFiles.slice(index, index + IMPORT_CHUNK)
        directBatches.push({
          files: chunk,
          imageCount: chunk.filter(file => IMAGE_EXT_RE.test(file.name || '')).length,
        })
      }

      const nestedBatches = []
      for (const [subdir, nestedFiles] of Object.entries(subdirMap)) {
        const batchTotal = Math.max(1, Math.ceil(nestedFiles.length / IMPORT_CHUNK))
        for (let index = 0; index < nestedFiles.length; index += IMPORT_CHUNK) {
          const chunk = nestedFiles.slice(index, index + IMPORT_CHUNK)
          nestedBatches.push({
            subdir,
            files: chunk,
            imageCount: chunk.filter(file => IMAGE_EXT_RE.test(file.name || '')).length,
            batchIndex: Math.floor(index / IMPORT_CHUNK) + 1,
            batchTotal,
          })
        }
      }

      return {
        batches: [...directBatches, ...nestedBatches],
        totalImageCount: files.filter(file => IMAGE_EXT_RE.test(file.name || '')).length,
      }
    },

    async readErrorMessage(response, fallbackMessage) {
      const rawText = await response.text().catch(() => '')
      if (rawText) {
        try {
          const data = JSON.parse(rawText)
          if (typeof data.detail === 'string' && data.detail) return data.detail
          if (Array.isArray(data.detail) && data.detail.length) {
            return data.detail.map(item => item.msg || item.message || String(item)).join('；')
          }
          if (typeof data.message === 'string' && data.message) return data.message
        } catch {
          return rawText
        }
      }
      return fallbackMessage || `HTTP ${response.status}`
    },

    async importFolderRow(row) {
      const { batches } = this.buildImportBatches(row.files)
      let importedCount = 0
      let skippedCount = 0

      for (const batch of batches) {
        const firstFile = batch.files[0]
        this.currentItem = batch.subdir
          ? `${row.label}/${batch.subdir}/${batch.batchTotal > 1 ? `(${batch.batchIndex}/${batch.batchTotal})` : ''}`
          : (firstFile ? `${row.label}/${firstFile.name}` : row.label)

        const fd = new FormData()
        const lastModifiedTimes = []
        const createdTimes = []
        for (const file of batch.files) {
          fd.append('files', file, file.webkitRelativePath || file.name)
          lastModifiedTimes.push(file.lastModified)
          createdTimes.push(null)
        }
        fd.append('last_modified_json', JSON.stringify(lastModifiedTimes))
        fd.append('created_time_json', JSON.stringify(createdTimes))
        fd.append('category_id', row.categoryValue)

        const res = await fetch(`${API_BASE}/api/import`, { method: 'POST', body: fd })
        if (!res.ok) {
          const message = await this.readErrorMessage(res, '导入失败，请检查后端服务')
          throw new Error(message)
        }

        const data = await res.json()
        importedCount += Array.isArray(data.imported) ? data.imported.length : 0
        skippedCount += Array.isArray(data.skipped) ? data.skipped.length : 0
        this.doneFiles = Math.min(this.doneFiles + batch.imageCount, this.totalFiles)
      }

      return { importedCount, skippedCount }
    },

    async confirmImportDialog() {
      if (this.importing) return
      if (!this.importDialogRows.length) {
        this.importDialogError = '请先添加至少一个文件夹。'
        return
      }
      if (this.importDialogRows.some(row => row.categoryValue === AUTO_CATEGORY_KEY)) {
        this.importDialogError = 'Auto 主分类暂未实现，请为每一行选择具体主分类。'
        return
      }

      const rowsToImport = [...this.importDialogRows]
      const failedRows = []
      let importedCount = 0
      let skippedCount = 0

      this.importing = true
      window.__ptvImporting = true
      this.clearNotice()
      this.importDialogError = ''
      this.importDialogOpen = false
      this.totalFiles = rowsToImport.reduce((sum, row) => sum + row.imageCount, 0)
      this.doneFiles = 0

      try {
        for (const [index, row] of rowsToImport.entries()) {
          this.currentFolderLabel = row.label
          this.status = `正在导入（${index + 1}/${rowsToImport.length}）${row.label}…`
          try {
            const result = await this.importFolderRow(row)
            importedCount += result.importedCount
            skippedCount += result.skippedCount
          } catch (err) {
            failedRows.push({
              id: row.id,
              label: row.label,
              error: toErrorMessage(err),
            })
          }
        }

        if (failedRows.length) {
          const failedIdSet = new Set(failedRows.map(item => item.id))
          this.importDialogRows = this.importDialogRows.filter(row => failedIdSet.has(row.id))
          this.selectedImportRowIds = []
          this.importDialogError = [
            '部分文件夹导入失败，已保留失败项，可调整后重试。',
            ...failedRows.map(item => `${item.label}：${item.error}`),
          ].join('；')
          this.importDialogOpen = true
          this.status = '部分导入完成。'
        } else {
          this.resetImportDialog()
          this.status = `导入完成：${importedCount} 张，重复跳过 ${skippedCount} 张。`
        }
      } finally {
        this.importing = false
        window.__ptvImporting = false
        this.currentFolderLabel = ''
        this.currentItem = ''
        this.totalFiles = 0
        this.doneFiles = 0
      }
    },

    async runRefresh() {
      this.refreshing    = true
      this.clearNotice()
      this.status        = '正在全量刷新媒体库…'
      try {
        const res = await fetch(`${API_BASE}/api/admin/refresh?mode=full`, { method: 'POST' })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        this.showNotice({
          type: 'success',
          title: `刷新完成，当前共 ${data.total_images} 张图片`,
          lines: data.pruned ? [`🗑 已删除失效记录：${data.pruned} 条`] : [],
        })
        this.status = ''
      } catch (err) {
        this.showNotice({ type: 'error', title: '刷新失败', lines: [`${err.message}`] })
        this.status = ''
      } finally {
        this.refreshing = false
      }
    },

    // On page load/activation: silently check for missing month-cover thumbnails.
    // If any are found, trigger an immediate refresh so the calendar view stays
    // up-to-date when the user navigates there.
    async _checkMissingThumbs() {
      if (this.checkingThumbs || this.importing) return
      this.checkingThumbs = true
      try {
        const r = await fetch(`${API_BASE}/api/dates`)
        if (!r.ok) return
        const d = await r.json()
        const allMonths = (d.years || []).flatMap(y => y.months || [])
        if (!allMonths.some(m => !m.thumb_url)) return
        const res = await fetch(`${API_BASE}/api/admin/refresh`, { method: 'POST' })
        if (!res.ok) return
        const data = await res.json()
        window.dispatchEvent(new CustomEvent('library-refreshed', { detail: data }))
      } catch { /* ignore */ }
      finally { this.checkingThumbs = false }
    },
  },
}
</script>

<style scoped lang="css">
.page { @apply flex flex-col gap-6; }
.page-header { @apply flex flex-col gap-1; }
.page-title  { @apply text-2xl font-semibold text-slate-900 m-0; }
.page-subtitle { @apply text-sm text-slate-500 m-0; }

/* Card */
.card {
  @apply bg-white border border-slate-200 rounded-xl p-5 shadow-sm
         flex flex-col gap-3;
}
.card-title { @apply text-base font-medium text-slate-700 m-0; }
.card-hint  { @apply text-xs text-slate-400 m-0 leading-relaxed; }
.inline-code {
  @apply bg-slate-100 rounded px-1;
  font-family: monospace;
  font-size: 0.85em;
}

/* Buttons */
.action-row { @apply flex gap-2 flex-wrap items-center; }
.btn {
  @apply inline-flex items-center gap-1.5 px-4 py-2 rounded text-sm font-medium
         cursor-pointer border-0 transition-all duration-150;
}
.btn:disabled { @apply opacity-50 cursor-not-allowed; }
.btn--primary { @apply bg-indigo-600 text-white; }
.btn--primary:not(:disabled):hover { @apply bg-indigo-700; }
.btn--secondary { @apply bg-white text-slate-600 border border-slate-300 shadow-sm; }
.btn--secondary:not(:disabled):hover { @apply bg-slate-50; }
.btn__icon { @apply inline-block; }
.spinning  { animation: spin 0.8s linear infinite; }

.hidden-input { @apply hidden; }

/* Status / progress */
.status-text   { @apply text-sm text-slate-500 m-0; }
.progress-text { @apply text-xs text-slate-400 m-0; }

/* Live import indicator */
.live-indicator {
  @apply flex items-center gap-2 px-3 py-2
         bg-indigo-50 border border-indigo-100 rounded-lg;
}
.live-indicator__spinner {
  @apply flex-shrink-0 inline-block w-3 h-3 border-2 border-indigo-300 rounded-full;
  border-top-color: #4f46e5;
  animation: spin 0.7s linear infinite;
}
.live-indicator__name {
  @apply font-mono text-xs text-indigo-700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Result box */
.result-box {
  @apply border border-slate-200 bg-slate-50 rounded-lg p-3
         flex flex-col gap-0.5;
}
.result-box__header {
  @apply flex items-center justify-between gap-2;
}
.result-box__close {
  @apply border-0 bg-transparent text-slate-400 text-base leading-none cursor-pointer px-1;
}
.result-box__close:hover {
  @apply text-slate-600;
}
.result-box__line          { @apply text-sm m-0; }
.result-box__line--heading { @apply font-semibold text-slate-700; }
.result-box__line--primary { @apply text-slate-700; }
.result-box__line--muted   { @apply text-slate-500; }
.result-box__line--error   { @apply text-red-600; }

.result-box--success {
  @apply bg-slate-50 border-slate-200;
}
.result-box--error {
  @apply bg-red-50 border-red-200;
}
.result-box--error .result-box__line--heading {
  @apply text-red-700;
}
.result-box--error .result-box__line--muted {
  @apply text-red-600;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
