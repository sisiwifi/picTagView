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
          @click="triggerFolder"
        >
          选择图片文件夹并导入
        </button>
        <button
          class="btn btn--secondary"
          :disabled="importing || refreshing"
          title="扫描媒体库：删除已失效记录，补全缺失缩略图"
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
        @change="handleFolder"
      />

      <!-- Status line -->
      <p v-if="status" class="status-text">{{ status }}</p>

      <!-- Live import indicator -->
      <div v-if="importing && currentItem" class="live-indicator">
        <span class="live-indicator__spinner"></span>
        <span class="live-indicator__name">{{ currentItem }}</span>
      </div>

      <!-- Batch progress -->
      <p v-if="importing && totalBatches > 0" class="progress-text">
        {{ doneBatches }} / {{ totalBatches }} 批次完成
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
  </section>
</template>

<script>
const API_BASE = 'http://127.0.0.1:8000'

export default {
  name: 'GalleryPage',

  data() {
    return {
      status:        '',
      importing:     false,
      currentItem:   '',
      totalBatches:  0,
      doneBatches:   0,
      refreshing:    false,
      noticeVisible: false,
      noticeType:    'info',
      noticeTitle:   '',
      noticeLines:   [],
      checkingThumbs: false,
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

    async runRefresh() {
      this.refreshing    = true
      this.clearNotice()
      this.status        = '正在刷新媒体库…'
      try {
        const res = await fetch(`${API_BASE}/api/admin/refresh`, { method: 'POST' })
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

    triggerFolder() { this.$refs.folderInput.click() },

    async handleFolder(event) {
      const files = Array.from(event.target.files || [])
      if (!files.length) return

      const rootName = (files[0].webkitRelativePath || files[0].name).split('/')[0]

      const directFiles = []
      const subdirMap   = {}
      for (const file of files) {
        const parts = (file.webkitRelativePath || file.name).split('/')
        if (parts.length <= 2) {
          directFiles.push(file)
        } else {
          const sub = parts[1]
          if (!subdirMap[sub]) subdirMap[sub] = []
          subdirMap[sub].push(file)
        }
      }

      // Group direct files into chunks of 50 to reduce HTTP overhead
      const CHUNK = 50
      const directBatches = []
      for (let i = 0; i < directFiles.length; i += CHUNK) {
        const chunk = directFiles.slice(i, i + CHUNK)
        const label = chunk.length === 1 ? chunk[0].name : `${chunk.length} 张图片`
        directBatches.push({ label, files: chunk })
      }
      const batches = [
        ...directBatches,
        ...Object.entries(subdirMap).map(([sub, fs]) => ({ label: `${sub}/`, files: fs })),
      ]

      this.importing    = true
      window.__ptvImporting = true
      this.clearNotice()
      this.status       = `正在导入 ${rootName}…`
      this.totalBatches = batches.length
      this.doneBatches  = 0

      const allImported = []
      const allSkipped  = []
      try {
        for (const batch of batches) {
          this.currentItem = batch.label
          const fd = new FormData()
          const ts = []
          const createdTs = []
          for (const f of batch.files) {
            fd.append('files', f, f.webkitRelativePath || f.name)
            ts.push(f.lastModified)
            createdTs.push(null)
          }
          fd.append('last_modified_json', JSON.stringify(ts))
          fd.append('created_time_json', JSON.stringify(createdTs))

          const res = await fetch(`${API_BASE}/api/import`, { method: 'POST', body: fd })
          if (!res.ok) throw new Error('导入失败，请检查后端服务')
          const data = await res.json()
          allImported.push(...data.imported)
          allSkipped.push(...data.skipped)
          this.doneBatches++
        }
        this.showNotice({
          type: 'success',
          title: `导入完成：${allImported.length} 张`,
          lines: [`重复跳过：${allSkipped.length} 张`],
        })
        this.status  = '导入完成。'
      } catch (err) {
        this.showNotice({ type: 'error', title: '导入失败', lines: [`${err.message}`] })
        this.status = ''
      } finally {
        this.importing   = false
        window.__ptvImporting = false
        this.currentItem = ''
        event.target.value = ''
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
