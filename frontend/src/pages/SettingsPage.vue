<template>
  <section class="page">
    <div
      v-if="floatingMessage.visible"
      class="floating-message"
      :class="floatingMessage.type === 'error' ? 'floating-message--error' : 'floating-message--success'"
    >
      {{ floatingMessage.text }}
    </div>

    <template v-if="activePanel === 'tag-filter'">
      <BreadcrumbHeader
        :show-back="true"
        :crumbs="tagFilterCrumbs"
        @back="closeTagFilterPlaceholder"
      />

      <div class="settings-card settings-card--subpage">
        <div class="subpage-intro">
          <div class="subpage-intro__copy">
            <h3 class="card-title">Tag过滤</h3>
            <p class="card-desc">这里预留给文件名匹配相关的规则配置，当前只保留二级页结构与返回入口。</p>
          </div>
          <span class="placeholder-badge">占位</span>
        </div>

        <div class="placeholder-panel">
          <p class="placeholder-panel__title">计划纳入的配置</p>
          <div class="placeholder-chip-list">
            <span class="placeholder-chip">噪声词列表</span>
            <span class="placeholder-chip">最小 token 长度</span>
            <span class="placeholder-chip">纯数字过滤</span>
            <span class="placeholder-chip">匹配预览</span>
          </div>
        </div>

        <div class="setting-row setting-row--compact">
          <div class="setting-info">
            <span class="setting-label">当前状态</span>
            <span class="setting-desc">后续再接入实际配置、保存与预览逻辑；现在仅用于占位和导航结构调整。</span>
          </div>
          <button class="btn btn--secondary" type="button" @click="closeTagFilterPlaceholder">
            返回标签管理
          </button>
        </div>
      </div>
    </template>

    <template v-else>
      <header class="page-header">
        <div class="page-header__main">
          <h2 class="page-title">设置</h2>
          <p class="page-subtitle">系统管理与常用配置入口</p>
        </div>
        <button class="page-header__action trash-launch" type="button" @click="$router.push('/trash')">
          <span class="trash-launch__icon" aria-hidden="true">
            <svg viewBox="0 0 48 48" fill="none">
              <rect x="6" y="8" width="36" height="32" rx="12" fill="url(#trash-launch-bg)" />
              <path d="M17 20H31" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" />
              <path d="M19 16.5H29" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" />
              <path d="M20.5 22.5V31.5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" />
              <path d="M27.5 22.5V31.5" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" />
              <path d="M15.5 18.5L17.8 14.5L22 16.7" stroke="#047857" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
              <path d="M32.5 29.5L30.2 33.5L26 31.3" stroke="#0f766e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
              <defs>
                <linearGradient id="trash-launch-bg" x1="10" y1="10" x2="38" y2="38" gradientUnits="userSpaceOnUse">
                  <stop stop-color="#ecfccb" />
                  <stop offset="1" stop-color="#fef3c7" />
                </linearGradient>
              </defs>
            </svg>
          </span>
          <span class="trash-launch__copy">
            <span class="trash-launch__title">回收站</span>
            <span class="trash-launch__subtitle">查看已删除项目</span>
          </span>
          <span class="trash-launch__arrow" aria-hidden="true">→</span>
        </button>
      </header>

      <div class="settings-card">
        <h3 class="card-title">缓存管理</h3>
        <p class="card-desc">管理浏览缩略图与月份封面缓存，尺寸调整后会自动触发重建。</p>
        <!-- <div class="card-meta">
          <span class="info-chip">data/cache · 短边 {{ thumbShortSide }}px</span>
          <span class="info-chip">temp · 封面 {{ monthCoverSize }}px</span>
        </div> -->

        <div class="setting-row setting-row--compact">
          <div class="setting-info">
            <span class="setting-label">缩略图短边尺寸</span>
            <span class="setting-desc">影响后续生成到 data/cache 的浏览缩略图。</span>
          </div>
          <div class="thumb-size-group">
            <div class="input-check-wrap">
              <input
                v-model="thumbShortSideDraft"
                class="thumb-size-input"
                type="number"
                inputmode="numeric"
                :min="thumbShortSideMin"
                :max="thumbShortSideMax"
                :disabled="thumbSettingLoading || thumbSettingSaving"
                @keydown.enter.prevent="confirmCacheThumbSetting"
              >
              <button
                v-if="thumbShortSideCanConfirm"
                class="btn-check"
                :disabled="thumbSettingSaving || clearingCache"
                @click="confirmCacheThumbSetting"
              >
                ✓
              </button>
            </div>
          </div>
        </div>

        <div class="setting-row setting-row--compact">
          <div class="setting-info">
            <span class="setting-label">月份封面尺寸</span>
            <span class="setting-desc">影响 temp 内月份封面与后续导入时的封面生成。</span>
          </div>
          <div class="thumb-size-group">
            <div class="input-check-wrap">
              <input
                v-model="monthCoverSizeDraft"
                class="thumb-size-input"
                type="number"
                inputmode="numeric"
                :min="monthCoverSizeMin"
                :max="monthCoverSizeMax"
                :disabled="monthCoverSettingLoading || monthCoverSettingSaving"
                @keydown.enter.prevent="confirmMonthCoverSetting"
              >
              <button
                v-if="monthCoverSizeCanConfirm"
                class="btn-check"
                :disabled="monthCoverSettingSaving || clearingCache"
                @click="confirmMonthCoverSetting"
              >
                ✓
              </button>
            </div>
          </div>
        </div>

        <div class="setting-row setting-row--compact">
          <div class="setting-info">
            <span class="setting-label">清除缓存</span>
            <span v-if="cacheResult" class="setting-desc">
              已删除 {{ cacheResult.deleted }} 个浏览缓存，临时缩略图 {{ cacheResult.temp_deleted }} 个
              <span v-if="cacheResult.error" class="text-red-500"> · {{ cacheResult.error }}</span>
            </span>
            <span v-else class="setting-desc">同时清除 data/cache 与 temp 内的已生成缩略图。</span>
          </div>
          <button
            class="btn btn--danger"
            :disabled="clearingCache"
            @click="clearCache"
          >
            {{ clearingCache ? '清除中…' : '清除缓存' }}
          </button>
        </div>

        <p v-if="thumbSettingError" class="viewer-error">{{ thumbSettingError }}</p>
        <p v-if="monthCoverSettingError" class="viewer-error">{{ monthCoverSettingError }}</p>
      </div>

      <div class="settings-card">
        <h3 class="card-title">页面配置</h3>
        <p class="card-desc">统一控制 BrowsePage 与 TrashPage 的浏览方式；分页模式会启用页码导航，滚动模式保持当前布局。</p>

        <div class="setting-row setting-row--compact">
          <div class="setting-info">
            <span class="setting-label">夜间模式</span>
            <span class="setting-desc">先保留入口，后续接入实际主题切换。</span>
          </div>
          <button class="btn btn--secondary" type="button" @click="openNightModePlaceholder">
            夜间模式
          </button>
        </div>

        <div class="setting-row setting-row--compact">
          <div class="setting-info">
            <span class="setting-label">浏览方式</span>
            <span class="setting-desc">滚动浏览保持当前瀑布流与滚动窗口；分页浏览会在浏览页与回收站页启用页码分页。</span>
          </div>
          <div class="setting-select-wrap">
            <select
              class="setting-select"
              :value="pageBrowseMode"
              :disabled="pageConfigLoading || pageConfigSaving"
              @change="onPageBrowseModeChange"
            >
              <option value="scroll">滚动浏览</option>
              <option value="paged">分页浏览</option>
            </select>
          </div>
        </div>

        <div v-if="pageBrowseMode === 'scroll'" class="setting-row setting-row--compact">
          <div class="setting-info">
            <span class="setting-label">滚动窗口范围</span>
            <span class="setting-desc">控制滚动浏览时围绕当前锚点预热的预览数量，默认 100，即锚点前后各约 50 项。</span>
          </div>
          <div class="setting-select-wrap">
            <select
              class="setting-select"
              :value="String(pageScrollWindowSize)"
              :disabled="pageConfigLoading || pageConfigSaving"
              @change="onPageScrollWindowSizeChange"
            >
              <option
                v-for="option in pageScrollWindowOptions"
                :key="option"
                :value="String(option)"
              >{{ option }}</option>
            </select>
          </div>
        </div>

        <p v-if="pageConfigError" class="viewer-error">{{ pageConfigError }}</p>
      </div>

      <div class="settings-card">
        <h3 class="card-title">配置主分类</h3>
        <div class="setting-row setting-row--compact">
          <div class="setting-info">
            <span class="setting-desc">进入独立页面管理主分类。</span>
          </div>
          <button class="btn btn--secondary" type="button" @click="$router.push('/settings/categories')">
            配置主分类
          </button>
        </div>
      </div>

      <div class="settings-card">
        <h3 class="card-title">标签管理</h3>
        <p class="card-desc">统一处理标签字典导入导出，以及文件名匹配规则的后续配置入口。</p>

        <div class="setting-row setting-row--compact">
          <div class="setting-info">
            <span class="setting-label">标签数据</span>
            <span v-if="tagImportResult" class="setting-desc">
              已导入 {{ tagImportResult.imported }}，更新 {{ tagImportResult.updated }}，跳过 {{ tagImportResult.skipped }}
              <span v-if="tagImportResult.errors && tagImportResult.errors.length" class="text-red-500">
                · {{ tagImportResult.errors.length }} 条错误
              </span>
            </span>
            <span v-else class="setting-desc">导出全部标签，或在弹窗中选择 JSON 文件批量导入。</span>
          </div>
          <div class="setting-actions">
            <button class="btn btn--primary" :disabled="tagExporting" @click="exportTags">
              {{ tagExporting ? '导出中…' : '导出 JSON' }}
            </button>
            <button class="btn btn--outline" :disabled="tagImporting" @click="openTagImportDialog">
              {{ tagImporting ? '导入中…' : '导入 JSON' }}
            </button>
          </div>
        </div>

        <!-- <div class="setting-row setting-row--compact">
          <div class="setting-info">
            <span class="setting-label">Tag过滤</span>
            <span class="setting-desc">进入二级页配置噪声词与文件名匹配规则，当前仅作占位。</span>
          </div>
          <button class="btn btn--secondary" type="button" @click="openTagFilterPlaceholder">
            进入配置
          </button>
        </div> -->

        <p v-if="tagError" class="viewer-error">{{ tagError }}</p>
      </div>

      <div class="settings-card">
        <div class="viewer-card-head">
          <div class="viewer-card-head__copy">
            <h3 class="card-title">图片查看器</h3>
            <p class="card-desc">设置应用内默认查看器，不影响系统全局默认程序。</p>
          </div>
          <span class="info-chip">系统默认：{{ systemViewerName || '未知' }}</span>
        </div>

        <div class="setting-row setting-row--compact setting-row--viewer">
          <div class="setting-info viewer-summary">
            <span class="setting-label">应用内默认查看器</span>
            <span class="setting-desc">支持常见图片格式，点击右侧即可切换。</span>
          </div>

          <button
            type="button"
            class="viewer-current viewer-current--compact"
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
              跟随系统默认
            </span>

            <span class="viewer-current__arrow">{{ viewerPickerOpen ? '▴' : '▾' }}</span>
          </button>
        </div>

        <div v-if="viewerLoading" class="viewer-loading">正在加载可选程序…</div>

        <div v-else-if="viewerPickerOpen" class="viewer-picker-panel viewer-picker-panel--compact">
          <div class="viewer-grid viewer-grid--compact">
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
    </template>

    <input
      ref="tagFileInput"
      type="file"
      accept=".json,application/json"
      style="display:none"
      @change="handleTagFileSelected"
    >

    <TagImportDialog
      :visible="tagImportDialogOpen"
      :busy="tagImporting"
      :conflict="tagImportConflict"
      :file-label="tagImportFileLabel"
      :has-file="Boolean(tagImportFile)"
      :result="tagImportResult"
      :error="tagError"
      @close="closeTagImportDialog"
      @choose-file="chooseTagImportFile"
      @confirm="confirmTagImport"
      @update:conflict="tagImportConflict = $event"
    />
  </section>
</template>

<script>
import BreadcrumbHeader from '../components/BreadcrumbHeader.vue'
import TagImportDialog from '../components/TagImportDialog.vue'
import {
  PAGE_BROWSE_MODE_PAGED,
  PAGE_BROWSE_MODE_SCROLL,
  PAGE_SCROLL_WINDOW_OPTIONS,
  fetchPageConfig,
  savePageConfig,
} from '../utils/pageConfig'

const API_BASE = 'http://127.0.0.1:8000'

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
  name: 'SettingsPage',
  components: {
    BreadcrumbHeader,
    TagImportDialog,
  },

  data() {
    return {
      clearingCache: false,
      cacheResult: null,
      thumbSettingLoading: false,
      thumbSettingSaving: false,
      thumbShortSide: 600,
      thumbShortSideDraft: '600',
      thumbShortSideMin: 100,
      thumbShortSideMax: 4000,
      thumbSettingError: '',
      monthCoverSettingLoading: false,
      monthCoverSettingSaving: false,
      monthCoverSize: 400,
      monthCoverSizeDraft: '400',
      monthCoverSizeMin: 100,
      monthCoverSizeMax: 2000,
      monthCoverSettingError: '',
      pageConfigLoading: false,
      pageConfigSaving: false,
      pageBrowseMode: PAGE_BROWSE_MODE_SCROLL,
      pageScrollWindowSize: 100,
      pageScrollWindowOptions: PAGE_SCROLL_WINDOW_OPTIONS,
      pageConfigError: '',
      floatingMessage: {
        visible: false,
        type: 'success',
        text: '',
      },
      floatingMessageTimer: null,
      viewerOptions: [],
      selectedViewerId: '',
      viewerLoading: false,
      savingViewer: false,
      viewerPickerOpen: false,
      viewerMessage: '',
      viewerError: '',
      systemViewerName: '',
      // 标签管理
      tagExporting: false,
      tagImporting: false,
      tagImportDialogOpen: false,
      tagImportFile: null,
      tagImportFileLabel: '',
      tagImportResult: null,
      tagImportConflict: 'skip',
      tagError: '',
      activePanel: '',
    }
  },

  computed: {
    tagFilterCrumbs() {
      return [
        { label: '设置', title: '设置' },
        { label: '标签管理', title: '标签管理' },
        { label: 'Tag过滤', title: 'Tag过滤', current: true },
      ]
    },

    currentViewer() {
      if (!this.selectedViewerId) return null
      return this.viewerOptions.find(v => v.id === this.selectedViewerId) || null
    },

    parsedThumbShortSide() {
      const value = Number.parseInt(String(this.thumbShortSideDraft), 10)
      return Number.isFinite(value) ? value : null
    },

    thumbShortSideCanConfirm() {
      if (this.parsedThumbShortSide === null) return false
      if (this.parsedThumbShortSide < this.thumbShortSideMin) return false
      if (this.parsedThumbShortSide > this.thumbShortSideMax) return false
      return this.parsedThumbShortSide !== this.thumbShortSide
    },

    parsedMonthCoverSize() {
      const value = Number.parseInt(String(this.monthCoverSizeDraft), 10)
      return Number.isFinite(value) ? value : null
    },

    monthCoverSizeCanConfirm() {
      if (this.parsedMonthCoverSize === null) return false
      if (this.parsedMonthCoverSize < this.monthCoverSizeMin) return false
      if (this.parsedMonthCoverSize > this.monthCoverSizeMax) return false
      return this.parsedMonthCoverSize !== this.monthCoverSize
    },
  },

  created() {
    this.fetchCacheThumbSetting()
    this.fetchMonthCoverSetting()
    this.fetchPageConfigSetting()
    this.fetchViewerOptions()
  },

  beforeUnmount() {
    if (this.floatingMessageTimer) {
      clearTimeout(this.floatingMessageTimer)
      this.floatingMessageTimer = null
    }
  },

  methods: {
    openTagFilterPlaceholder() {
      this.activePanel = 'tag-filter'
    },

    closeTagFilterPlaceholder() {
      this.activePanel = ''
    },

    openNightModePlaceholder() {
      this.showFloatingMessage('success', '夜间模式暂未开放。')
    },

    async fetchPageConfigSetting() {
      this.pageConfigLoading = true
      this.pageConfigError = ''
      try {
        const config = await fetchPageConfig()
        this.pageBrowseMode = config.browseMode || PAGE_BROWSE_MODE_SCROLL
        this.pageScrollWindowSize = config.scrollWindowSize || 100
      } catch (err) {
        this.pageConfigError = `加载页面配置失败：${toErrorMessage(err)}`
      } finally {
        this.pageConfigLoading = false
      }
    },

    async onPageBrowseModeChange(event) {
      const nextMode = String(event?.target?.value || PAGE_BROWSE_MODE_SCROLL)
      const normalizedMode = nextMode === PAGE_BROWSE_MODE_PAGED ? PAGE_BROWSE_MODE_PAGED : PAGE_BROWSE_MODE_SCROLL
      if (normalizedMode === this.pageBrowseMode) return

      this.pageConfigSaving = true
      this.pageConfigError = ''
      try {
        const savedConfig = await savePageConfig({
          browseMode: normalizedMode,
          scrollWindowSize: this.pageScrollWindowSize,
        })
        this.pageBrowseMode = savedConfig.browseMode
        this.pageScrollWindowSize = savedConfig.scrollWindowSize
        this.showFloatingMessage('success', `浏览方式已切换为${savedConfig.browseMode === PAGE_BROWSE_MODE_PAGED ? '分页浏览' : '滚动浏览'}。`)
      } catch (err) {
        this.pageConfigError = `保存页面配置失败：${toErrorMessage(err)}`
        this.showFloatingMessage('error', this.pageConfigError)
      } finally {
        this.pageConfigSaving = false
      }
    },

    async onPageScrollWindowSizeChange(event) {
      const nextSize = Number.parseInt(String(event?.target?.value || ''), 10)
      const normalizedSize = PAGE_SCROLL_WINDOW_OPTIONS.includes(nextSize)
        ? nextSize
        : 100
      if (normalizedSize === this.pageScrollWindowSize) return

      this.pageConfigSaving = true
      this.pageConfigError = ''
      try {
        const savedConfig = await savePageConfig({
          browseMode: this.pageBrowseMode,
          scrollWindowSize: normalizedSize,
        })
        this.pageBrowseMode = savedConfig.browseMode
        this.pageScrollWindowSize = savedConfig.scrollWindowSize
        this.showFloatingMessage('success', `滚动窗口范围已更新为 ${savedConfig.scrollWindowSize}。`)
      } catch (err) {
        this.pageConfigError = `保存页面配置失败：${toErrorMessage(err)}`
        this.showFloatingMessage('error', this.pageConfigError)
      } finally {
        this.pageConfigSaving = false
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
          // prefer cache_deleted returned by backend, fall back to other common names
          deleted = body.cache_deleted ?? body.cacheDeleted ?? body.deleted ?? body.deleted_count ?? body.count ?? 0
          temp_deleted = body.temp_deleted ?? body.tempDeleted ?? 0
          error = body.error ?? null
        }

        this.cacheResult = {
          // normalized
          deleted,
          temp_deleted,
          error,
          // backward-compatible aliases
          cache_deleted: deleted,
          cacheDeleted: deleted,
          deleted_count: deleted,
          count: deleted,
          tempDeleted: temp_deleted,
        }
      } catch (err) {
        this.cacheResult = { deleted: 0, temp_deleted: 0, error: toErrorMessage(err) }
      } finally {
        this.clearingCache = false
      }
    },

    async fetchCacheThumbSetting() {
      this.thumbSettingLoading = true
      this.thumbSettingError = ''
      try {
        const res = await fetch(`${API_BASE}/api/system/cache-thumb-setting`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        const shortSide = Number.parseInt(String(data.short_side_px ?? 600), 10)
        this.thumbShortSide = Number.isFinite(shortSide) ? shortSide : 600
        this.thumbShortSideDraft = String(this.thumbShortSide)
        if (Number.isFinite(Number(data.min_short_side_px))) {
          this.thumbShortSideMin = Number(data.min_short_side_px)
        }
        if (Number.isFinite(Number(data.max_short_side_px))) {
          this.thumbShortSideMax = Number(data.max_short_side_px)
        }
      } catch (err) {
        this.thumbSettingError = `加载缓存缩略图尺寸失败：${toErrorMessage(err)}`
      } finally {
        this.thumbSettingLoading = false
      }
    },

    async confirmCacheThumbSetting() {
      if (!this.thumbShortSideCanConfirm) return

      this.thumbSettingSaving = true
      this.thumbSettingError = ''
      try {
        const res = await fetch(`${API_BASE}/api/system/cache-thumb-setting`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ short_side_px: this.parsedThumbShortSide }),
        })

        if (!res.ok) {
          const data = await res.json().catch(() => ({}))
          throw new Error(data.detail || `HTTP ${res.status}`)
        }

        const data = await res.json()
        const value = Number.parseInt(String(data.short_side_px), 10)
        if (Number.isFinite(value)) {
          this.thumbShortSide = value
          this.thumbShortSideDraft = String(value)
        }

        await this.clearCache()
        this.showFloatingMessage('success', `缩略图短边尺寸已更新为 ${this.thumbShortSide}px，并已触发缓存清理。`)
      } catch (err) {
        this.thumbSettingError = `保存失败：${toErrorMessage(err)}`
        this.showFloatingMessage('error', this.thumbSettingError)
      } finally {
        this.thumbSettingSaving = false
      }
    },

    async fetchMonthCoverSetting() {
      this.monthCoverSettingLoading = true
      this.monthCoverSettingError = ''
      try {
        const res = await fetch(`${API_BASE}/api/system/month-cover-setting`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        const sizePx = Number.parseInt(String(data.size_px ?? 400), 10)
        this.monthCoverSize = Number.isFinite(sizePx) ? sizePx : 400
        this.monthCoverSizeDraft = String(this.monthCoverSize)
        if (Number.isFinite(Number(data.min_size_px))) {
          this.monthCoverSizeMin = Number(data.min_size_px)
        }
        if (Number.isFinite(Number(data.max_size_px))) {
          this.monthCoverSizeMax = Number(data.max_size_px)
        }
      } catch (err) {
        this.monthCoverSettingError = `加载月份封面尺寸失败：${toErrorMessage(err)}`
      } finally {
        this.monthCoverSettingLoading = false
      }
    },

    async confirmMonthCoverSetting() {
      if (!this.monthCoverSizeCanConfirm) return

      this.monthCoverSettingSaving = true
      this.monthCoverSettingError = ''
      try {
        const res = await fetch(`${API_BASE}/api/system/month-cover-setting`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ size_px: this.parsedMonthCoverSize }),
        })

        if (!res.ok) {
          const data = await res.json().catch(() => ({}))
          throw new Error(data.detail || `HTTP ${res.status}`)
        }

        const data = await res.json()
        const value = Number.parseInt(String(data.size_px), 10)
        if (Number.isFinite(value)) {
          this.monthCoverSize = value
          this.monthCoverSizeDraft = String(value)
        }

        await this.clearCache()
        this.showFloatingMessage('success', `月份封面尺寸已更新为 ${this.monthCoverSize}px，并已触发缓存清理。`)
      } catch (err) {
        this.monthCoverSettingError = `保存失败：${toErrorMessage(err)}`
        this.showFloatingMessage('error', this.monthCoverSettingError)
      } finally {
        this.monthCoverSettingSaving = false
      }
    },

    showFloatingMessage(type, text) {
      if (this.floatingMessageTimer) {
        clearTimeout(this.floatingMessageTimer)
        this.floatingMessageTimer = null
      }

      this.floatingMessage = {
        visible: true,
        type,
        text,
      }

      this.floatingMessageTimer = setTimeout(() => {
        this.floatingMessage.visible = false
      }, 2600)
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
        this.viewerError = `加载失败：${toErrorMessage(err)}`
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
        this.viewerError = `保存失败：${toErrorMessage(err)}`
      } finally {
        this.savingViewer = false
      }
    },

    // ── 标签管理 ─────────────────────────────────────────────────────────────
    async exportTags() {
      this.tagExporting = true
      this.tagError = ''
      try {
        const res = await fetch(`${API_BASE}/api/tags/export/json`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const blob = await res.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'tags_export.json'
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
      } catch (err) {
        this.tagError = `导出失败：${toErrorMessage(err)}`
      } finally {
        this.tagExporting = false
      }
    },

    openTagImportDialog() {
      if (this.tagImporting) return
      this.tagImportDialogOpen = true
      this.tagError = ''
    },

    closeTagImportDialog() {
      if (this.tagImporting) return
      this.tagImportDialogOpen = false
    },

    chooseTagImportFile() {
      const input = this.$refs.tagFileInput
      if (!input) {
        this.tagError = '导入控件不可用，请刷新页面后重试'
        return
      }
      input.value = ''
      input.click()
    },

    handleTagFileSelected(event) {
      const file = event.target.files && event.target.files[0]
      if (!file) return
      this.tagImportFile = file
      this.tagImportFileLabel = file.name || '已选择文件'
      this.tagError = ''
    },

    async confirmTagImport() {
      if (!this.tagImportFile) {
        this.tagError = '请先选择一个 JSON 文件'
        return
      }
      this.tagImporting = true
      this.tagError = ''
      this.tagImportResult = null
      try {
        const text = await this.tagImportFile.text()
        let parsed
        try {
          parsed = JSON.parse(text)
        } catch {
          throw new Error('文件不是合法 JSON')
        }
        // 兼容导出格式（含 tags 数组）或直接是数组
        const tags = Array.isArray(parsed) ? parsed : (parsed.tags || [])
        if (!Array.isArray(tags)) throw new Error('JSON 中未找到 tags 数组')

        const res = await fetch(`${API_BASE}/api/tags/import/json`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tags, on_conflict: this.tagImportConflict }),
        })
        if (!res.ok) {
          const d = await res.json().catch(() => ({}))
          throw new Error(d.detail || `HTTP ${res.status}`)
        }
        this.tagImportResult = await res.json()
        this.tagImportDialogOpen = false
        this.showFloatingMessage('success', '标签导入完成。')
      } catch (err) {
        this.tagError = `导入失败：${toErrorMessage(err)}`
        this.showFloatingMessage('error', this.tagError)
      } finally {
        this.tagImporting = false
      }
    },
  },
}
</script>

<style scoped lang="css">
.page { @apply flex flex-col gap-4; }

.floating-message {
  @apply fixed top-5 right-5 z-50 text-sm px-3 py-2 rounded-lg shadow-lg border;
}

.floating-message--success {
  @apply bg-emerald-50 text-emerald-700 border-emerald-300;
}

.floating-message--error {
  @apply bg-red-50 text-red-700 border-red-300;
}

.page-header { @apply flex items-end justify-between gap-4; }
.page-header__main { @apply flex flex-col gap-1; }
.page-title { @apply text-2xl font-semibold text-slate-900 m-0; }
.page-subtitle { @apply text-sm text-slate-500 m-0; }
.page-header__action {
  border: 0;
  background: transparent;
  padding: 0;
}

.trash-launch {
  display: inline-flex;
  align-items: center;
  gap: 0.9rem;
  min-height: 76px;
  min-width: 252px;
  padding: 0.8rem 1rem;
  border: 1px solid rgba(16, 185, 129, 0.18);
  border-radius: 22px;
  background:
    radial-gradient(circle at top left, rgba(220, 252, 231, 0.95), transparent 55%),
    linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(255, 247, 237, 0.98));
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
  color: #0f172a;
  text-align: left;
  cursor: pointer;
  transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease, background 180ms ease;
}

.trash-launch:hover {
  transform: translateY(-2px);
  border-color: rgba(13, 148, 136, 0.24);
  box-shadow: 0 18px 34px rgba(15, 23, 42, 0.12);
}

.trash-launch__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.8);
  color: #0f766e;
  flex-shrink: 0;
}

.trash-launch__icon svg {
  width: 36px;
  height: 36px;
}

.trash-launch__copy {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
  flex: 1 1 auto;
}

.trash-launch__title {
  color: #0f172a;
  font-size: 1rem;
  font-weight: 800;
  letter-spacing: 0.01em;
}

.trash-launch__subtitle {
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 600;
}

.trash-launch__arrow {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: #0f766e;
  font-size: 1rem;
  font-weight: 800;
  flex-shrink: 0;
}

.settings-card {
  @apply bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-col gap-3;
}
.settings-card--subpage {
  min-height: 260px;
}
.card-title { @apply text-base font-semibold text-slate-700 m-0; }
.card-desc { @apply text-xs text-slate-400 m-0 leading-relaxed; }

.card-meta {
  @apply flex flex-wrap items-center gap-2;
}

.info-chip {
  @apply inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-medium text-slate-500 bg-slate-100 border border-slate-200;
}

.setting-row {
  @apply flex items-start justify-between gap-3;
}
.setting-row--compact {
  @apply gap-3;
}

.setting-row--viewer {
  @apply items-center;
}

.setting-info { @apply flex flex-col gap-0.5 min-w-0; }
.setting-label { @apply text-sm font-medium text-slate-700; }
.setting-desc { @apply text-xs text-slate-400 leading-5; }

.subpage-intro {
  @apply flex items-start justify-between gap-3;
}

.subpage-intro__copy {
  @apply flex flex-col gap-1 min-w-0;
}

.placeholder-badge {
  @apply inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-semibold text-amber-700 bg-amber-50 border border-amber-200;
}

.placeholder-panel {
  @apply rounded-xl border border-dashed border-slate-300 bg-slate-50 px-3 py-3 flex flex-col gap-2;
}

.placeholder-panel__title {
  @apply text-xs font-semibold text-slate-600 m-0;
}

.placeholder-chip-list {
  @apply flex flex-wrap gap-2;
}

.placeholder-chip {
  @apply inline-flex items-center rounded-full px-2.5 py-1 text-[11px] text-slate-500 bg-white border border-slate-200;
}

@media (max-width: 640px) {
  .page-header {
    @apply flex-col items-stretch;
  }

  .trash-launch {
    width: 100%;
    min-width: 0;
  }

  .subpage-intro,
  .setting-row,
  .setting-row--viewer {
    @apply flex-col items-stretch;
  }
}

.viewer-card-head {
  @apply flex flex-wrap items-center justify-between gap-2;
}

.viewer-card-head__copy {
  @apply flex flex-col gap-1 min-w-0;
}

.viewer-summary {
  @apply pr-2;
}

.viewer-current {
  @apply inline-flex items-center gap-2 bg-indigo-50 text-indigo-700 px-3 py-1.5 rounded-lg border border-indigo-200
         transition-colors duration-150 cursor-pointer;
}
.viewer-current--compact {
  min-height: 40px;
}
.viewer-current:hover:not(:disabled) {
  @apply border-indigo-400 bg-indigo-100;
}
.viewer-current:disabled {
  @apply opacity-50 cursor-not-allowed;
}
.viewer-current__name { @apply text-xs font-semibold max-w-40 truncate; }
.viewer-current__arrow { @apply text-[10px] text-indigo-600 ml-1; }
.viewer-empty { @apply text-xs text-slate-500; }

.viewer-loading { @apply text-xs text-slate-500; }
.viewer-picker-panel {
  @apply border border-slate-200 rounded-xl bg-slate-50 p-2;
}
.viewer-picker-panel--compact {
  @apply p-1.5;
}
.viewer-grid {
  @apply grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2;
}
.viewer-grid--compact {
  @apply gap-1.5;
}
.viewer-item {
  @apply flex items-center gap-2 px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white text-left
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
  @apply inline-flex items-center justify-center w-6 h-6 rounded-md bg-white border border-slate-200
         text-xs font-semibold text-slate-700 flex-shrink-0 overflow-hidden;
}
.viewer-icon--system {
  @apply bg-slate-100 text-slate-500;
}
.viewer-icon__img {
  @apply w-full h-full object-contain;
}
.viewer-item__name {
  @apply text-xs text-slate-700 truncate;
}
.viewer-item__tag {
  @apply ml-auto text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500;
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
.btn--primary { @apply bg-indigo-600 text-white; }
.btn--primary:not(:disabled):hover { @apply bg-indigo-700; }
.btn--secondary { @apply bg-slate-100 text-slate-700 border border-slate-300; }
.btn--secondary:not(:disabled):hover { @apply bg-slate-200; }
.btn--outline { @apply bg-white text-slate-700 border border-slate-300; }
.btn--outline:not(:disabled):hover { @apply bg-slate-50; }

.setting-actions {
  @apply flex items-center gap-1.5 flex-wrap justify-end;
}

.thumb-size-group {
  @apply flex items-center gap-2;
}

.setting-select-wrap {
  @apply flex items-center gap-2;
}

.setting-select {
  @apply min-w-[8rem] text-sm border border-slate-300 rounded-lg px-3 py-2 bg-white text-slate-700;
}

.input-check-wrap {
  @apply relative;
}

.thumb-size-input {
  @apply w-28 text-sm border border-slate-300 rounded px-2 py-1.5 pr-7 bg-white text-slate-700;
}

.thumb-size-input::-webkit-outer-spin-button,
.thumb-size-input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.thumb-size-input[type='number'] {
  appearance: textfield;
  -moz-appearance: textfield;
}

.btn-check {
  @apply absolute right-1 top-1/2 -translate-y-1/2 inline-flex items-center justify-center w-5 h-5 text-[11px] rounded border border-emerald-300 bg-emerald-50 text-emerald-700 transition-colors duration-150;
}

.btn-check:hover:not(:disabled) {
  @apply bg-emerald-100 border-emerald-400;
}

.btn-check:disabled {
  @apply opacity-50 cursor-not-allowed;
}
</style>
