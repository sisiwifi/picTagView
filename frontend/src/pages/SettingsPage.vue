<template>
  <section class="page">
    <header class="page-header">
      <h2 class="page-title">设置</h2>
      <p class="page-subtitle">个性化与系统管理</p>
    </header>

    <!-- 外观 -->
    <div class="settings-card">
      <h3 class="card-title">外观</h3>
      <div class="setting-row">
        <div class="setting-info">
          <span class="setting-label">深色模式</span>
          <span class="setting-desc">切换深色 / 浅色界面</span>
        </div>
        <button
          class="switch"
          :class="{ 'switch--on': isDark }"
          :aria-label="isDark ? '切换为浅色模式' : '切换为深色模式'"
          @click="toggleDark"
        >
          <span class="switch__knob"></span>
        </button>
      </div>
    </div>

    <!-- 缓存管理 -->
    <div class="settings-card">
      <h3 class="card-title">缓存管理</h3>
      <p class="card-desc">
        缓存文件夹存储已生成的原比例缩略图（400px WebP），用于相册内图片预览。
        清除后下次进入相册时会自动重新生成。
      </p>
      <div class="setting-row">
        <div class="setting-info">
          <span class="setting-label">清除缓存</span>
          <span v-if="cacheResult" class="setting-desc">
            已删除 {{ cacheResult.deleted }} 个缓存文件
            <span v-if="cacheResult.temp_deleted">（临时缩略图已删除 {{ cacheResult.temp_deleted }} 个）</span>
            <span v-if="cacheResult.error" class="text-red-500"> — 错误：{{ cacheResult.error }}</span>
          </span>
          <span v-else class="setting-desc">删除 data/cache/ 内所有缩略图文件</span>
        </div>
        <button
          class="btn btn--danger"
          :disabled="clearingCache"
          @click="clearCache"
        >
          {{ clearingCache ? '清除中…' : '清除缓存' }}
        </button>
      </div>
    </div>

    <!-- 图片查看器 -->
    <div class="settings-card">
      <h3 class="card-title">图片查看器</h3>
      <p class="card-desc">
        点击相册中的图片时，将优先使用你在本应用内选择的默认查看器打开原图，不影响系统全局默认设置。
      </p>

      <div class="setting-row">
        <div class="setting-info">
          <span class="setting-label">当前应用内默认</span>
          <span class="setting-desc">覆盖常见图片格式（jpg/png/webp/bmp/gif/tiff/heic/avif）</span>
        </div>

        <button
          type="button"
          class="viewer-current"
          :disabled="viewerLoading || savingViewer"
          @click="toggleViewerPicker"
        >
          <span class="viewer-icon">
            <img
              v-if="currentViewer && currentViewer.icon_url"
              :src="toAbsoluteIconUrl(currentViewer.icon_url)"
              :alt="currentViewer.display_name"
              class="viewer-icon__img"
            >
            <span v-else>{{ currentViewer ? (currentViewer.icon_text || '?') : 'S' }}</span>
          </span>

          <span class="viewer-current__name" v-if="currentViewer">
            {{ currentViewer.display_name }}
          </span>
          <span class="viewer-empty" v-else>
            未选择（跟随系统默认）
          </span>

          <span class="viewer-current__arrow">{{ viewerPickerOpen ? '▴' : '▾' }}</span>
        </button>
      </div>

      <p class="viewer-tip">系统当前默认：{{ systemViewerName || '未知' }}</p>

      <div v-if="viewerLoading" class="viewer-loading">正在加载可选程序…</div>

      <div v-else-if="viewerPickerOpen" class="viewer-picker-panel">
        <div class="viewer-grid">
          <button
            type="button"
            class="viewer-item"
            :class="{ 'viewer-item--active': selectedViewerId === '' }"
            :disabled="savingViewer"
            @click="selectViewer('')"
          >
            <span class="viewer-icon viewer-icon--system">S</span>
            <span class="viewer-item__name">跟随系统默认</span>
          </button>

          <button
            v-for="viewer in viewerOptions"
            :key="viewer.id"
            type="button"
            class="viewer-item"
            :class="{ 'viewer-item--active': selectedViewerId === viewer.id }"
            :disabled="savingViewer"
            @click="selectViewer(viewer.id)"
          >
            <span class="viewer-icon">
              <img
                v-if="viewer.icon_url"
                :src="toAbsoluteIconUrl(viewer.icon_url)"
                :alt="viewer.display_name"
                class="viewer-icon__img"
              >
              <span v-else>{{ viewer.icon_text || '?' }}</span>
            </span>
            <span class="viewer-item__name">{{ viewer.display_name }}</span>
            <span v-if="viewer.is_system_default" class="viewer-item__tag">系统默认</span>
          </button>
        </div>
      </div>

      <p v-if="viewerMessage" class="viewer-message">{{ viewerMessage }}</p>
      <p v-if="viewerError" class="viewer-error">{{ viewerError }}</p>
      <p class="viewer-tip" v-if="savingViewer">正在保存默认查看器…</p>
    </div>
  </section>
</template>

<script>
const API_BASE = 'http://127.0.0.1:8000'

export default {
  name: 'SettingsPage',

  data() {
    return {
      isDark: false,
      clearingCache: false,
      cacheResult: null,
      viewerOptions: [],
      selectedViewerId: '',
      viewerLoading: false,
      savingViewer: false,
      viewerPickerOpen: false,
      viewerMessage: '',
      viewerError: '',
      systemViewerName: '',
    }
  },

  computed: {
    currentViewer() {
      if (!this.selectedViewerId) return null
      return this.viewerOptions.find(v => v.id === this.selectedViewerId) || null
    },
  },

  created() {
    this.isDark = document.documentElement.classList.contains('dark')
    this.fetchViewerOptions()
  },

  methods: {
    toggleDark() {
      this.isDark = !this.isDark
      if (this.isDark) {
        document.documentElement.classList.add('dark')
        localStorage.setItem('theme', 'dark')
      } else {
        document.documentElement.classList.remove('dark')
        localStorage.setItem('theme', 'light')
      }
    },

    async clearCache() {
      this.clearingCache = true
      this.cacheResult = null
      try {
        const res = await fetch(`${API_BASE}/api/cache`, { method: 'DELETE' })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const body = await res.json().catch(() => null)

        let deleted = 0
        let temp_deleted = 0
        let error = null

        if (typeof body === 'number') {
          deleted = body
        } else if (body && typeof body === 'object') {
          deleted = body.deleted ?? body.deleted_count ?? body.count ?? 0
          temp_deleted = body.temp_deleted ?? body.tempDeleted ?? 0
          error = body.error ?? null
        }

        this.cacheResult = { deleted, temp_deleted, error }
      } catch (err) {
        this.cacheResult = { deleted: 0, temp_deleted: 0, error: err.message }
      } finally {
        this.clearingCache = false
      }
    },

    async fetchViewerOptions() {
      this.viewerLoading = true
      this.viewerError = ''
      this.viewerMessage = ''
      try {
        const res = await fetch(`${API_BASE}/api/system/image-viewers`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const d = await res.json()
        this.viewerOptions = Array.isArray(d.viewers) ? d.viewers : []
        this.selectedViewerId = d.selected_viewer_id || ''
        this.systemViewerName = d.system_default || '未知'
      } catch (err) {
        this.viewerError = `加载失败：${err.message}`
      } finally {
        this.viewerLoading = false
      }
    },

    toggleViewerPicker() {
      if (this.viewerLoading || this.savingViewer) return
      this.viewerPickerOpen = !this.viewerPickerOpen
    },

    toAbsoluteIconUrl(iconUrl) {
      if (!iconUrl) return ''
      if (iconUrl.startsWith('http://') || iconUrl.startsWith('https://')) return iconUrl
      return `${API_BASE}${iconUrl}`
    },

    async selectViewer(viewerId) {
      if (this.savingViewer) return
      this.viewerError = ''
      this.viewerMessage = ''
      this.savingViewer = true
      try {
        const res = await fetch(`${API_BASE}/api/system/viewer-preference`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ viewer_id: viewerId || '' }),
        })
        if (!res.ok) {
          const data = await res.json().catch(() => ({}))
          throw new Error(data.detail || `HTTP ${res.status}`)
        }

        this.selectedViewerId = viewerId || ''
        this.viewerMessage = viewerId ? '应用内默认查看器已更新。' : '已切换为“跟随系统默认”。'
        this.viewerPickerOpen = false
      } catch (err) {
        this.viewerError = `保存失败：${err.message}`
      } finally {
        this.savingViewer = false
      }
    },
  },
}
</script>

<style scoped lang="css">
.page { @apply flex flex-col gap-6; }

.page-header { @apply flex flex-col gap-1; }
.page-title { @apply text-2xl font-semibold text-slate-900 m-0; }
.page-subtitle { @apply text-sm text-slate-500 m-0; }

.settings-card {
  @apply bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col gap-4;
}
.card-title { @apply text-base font-semibold text-slate-700 m-0; }
.card-desc { @apply text-xs text-slate-400 m-0 leading-relaxed; }

.setting-row {
  @apply flex items-center justify-between gap-4;
}
.setting-info { @apply flex flex-col gap-0.5; }
.setting-label { @apply text-sm font-medium text-slate-700; }
.setting-desc { @apply text-xs text-slate-400; }

.viewer-current {
  @apply inline-flex items-center gap-2 bg-indigo-50 text-indigo-700 px-3 py-1.5 rounded-lg border border-indigo-200
         transition-colors duration-150 cursor-pointer;
}
.viewer-current:hover:not(:disabled) {
  @apply border-indigo-400 bg-indigo-100;
}
.viewer-current:disabled {
  @apply opacity-50 cursor-not-allowed;
}
.viewer-current__name { @apply text-sm font-medium max-w-48 truncate; }
.viewer-current__arrow { @apply text-xs text-indigo-600 ml-1; }
.viewer-empty { @apply text-xs text-slate-500; }

.viewer-loading { @apply text-xs text-slate-500; }
.viewer-picker-panel {
  @apply border border-slate-200 rounded-xl bg-slate-50 p-2;
}
.viewer-grid {
  @apply grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2;
}
.viewer-item {
  @apply flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-200 bg-white text-left
         transition-all duration-150 cursor-pointer;
}
.viewer-item:hover:not(:disabled) {
  @apply border-indigo-300 bg-indigo-50;
}
.viewer-item:disabled {
  @apply opacity-50 cursor-not-allowed;
}
.viewer-item--active {
  @apply border-indigo-500 bg-indigo-50;
}
.viewer-icon {
  @apply inline-flex items-center justify-center w-7 h-7 rounded-md bg-white border border-slate-200
         text-xs font-semibold text-slate-700 flex-shrink-0 overflow-hidden;
}
.viewer-icon--system {
  @apply bg-slate-100 text-slate-500;
}
.viewer-icon__img {
  @apply w-full h-full object-contain;
}
.viewer-item__name {
  @apply text-sm text-slate-700 truncate;
}
.viewer-item__tag {
  @apply ml-auto text-[11px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500;
}
.viewer-tip {
  @apply text-xs text-slate-400 m-0;
}
.viewer-message {
  @apply text-xs text-emerald-600 m-0;
}
.viewer-error {
  @apply text-xs text-red-600 m-0;
}

.switch {
  @apply relative inline-flex flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent
         transition-colors duration-200 ease-in-out;
  width: 2.75rem;
  height: 1.5rem;
  background-color: #cbd5e1;
}
.switch--on { background-color: #4f46e5; }
.switch__knob {
  @apply pointer-events-none inline-block rounded-full bg-white shadow ring-0
         transition duration-200 ease-in-out;
  width: 1rem;
  height: 1rem;
  transform: translateX(0.25rem) translateY(1px);
}
.switch--on .switch__knob { transform: translateX(1.5rem) translateY(1px); }

.btn {
  @apply inline-flex items-center gap-1.5 px-4 py-2 rounded text-sm font-medium
         cursor-pointer border-0 transition-all duration-150;
}
.btn:disabled { @apply opacity-50 cursor-not-allowed; }
.btn--danger { @apply bg-red-500 text-white; }
.btn--danger:not(:disabled):hover { @apply bg-red-600; }
</style>
