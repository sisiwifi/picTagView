<template>
  <section class="page" :style="pageVars">
    <TopLevelPageHeader
      title="图库管理"
      subtitle="选择并导入图片到系统，并从这里进入最近导入与图库总览。"
    />

    <div class="card">
      <h3 class="card-title">导入新图片</h3>
      <p class="card-hint">
        选择文件夹后，图片将按文件修改时间自动归入
        <code class="inline-code">media/YYYY-M/</code>。
        子文件夹将作为整体单元处理。
      </p>

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
        <button
          v-if="importing"
          class="btn btn--danger"
          :disabled="stopRequested"
          @click="stopImport"
        >
          {{ stopRequested ? '停止中…' : '停止导入' }}
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

      <div class="import-feedback">
        <p v-if="status" class="status-text">{{ status }}</p>

        <div v-if="importing && currentItem" class="live-indicator">
          <span class="live-indicator__spinner"></span>
          <span class="live-indicator__name">{{ currentItem }}</span>
        </div>

        <p v-if="importing && totalFiles > 0" class="progress-text">
          {{ currentFolderLabel ? `${currentFolderLabel} · ` : '' }}{{ doneFiles }} / {{ totalFiles }} 张
        </p>

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
    </div>

    <section
      v-for="section in overviewSections"
      :key="section.scope"
      class="gallery-overview"
    >
      <div class="gallery-overview__head">
        <div class="gallery-overview__head-main">
          <h3 class="gallery-overview__title">{{ section.title }}</h3>
          <p class="gallery-overview__hint">{{ section.hint }}</p>
        </div>
        <button
          class="gallery-overview__open"
          type="button"
          :disabled="section.loading || !section.total"
          @click="openOverviewList(section.scope)"
        >
          查看全部
        </button>
      </div>

      <LoadingSpinner v-if="section.loading" />

      <div v-else-if="section.error" class="gallery-overview__empty gallery-overview__empty--error">
        <span class="gallery-overview__empty-icon">!</span>
        <p>{{ section.error }}</p>
      </div>

      <div v-else-if="!section.total" class="gallery-overview__empty">
        <span class="gallery-overview__empty-icon">□</span>
        <p>{{ section.emptyText }}</p>
      </div>

      <div v-else class="gallery-overview__grid" :style="overviewGridStyle(section)">
        <ThumbCard
          v-for="slot in section.displaySlots"
          :key="slot.key"
          :src="resolvedOverviewUrl(slot.item)"
          :badge-label="slot.isSummary ? '' : animatedBadgeLabel(slot.item)"
          :class="['gallery-overview__card', { 'gallery-overview__card--summary': slot.isSummary }]"
          :overlay-opacity="slot.isSummary ? 0.24 : 0"
          :rounded="'1.25rem'"
          @click="openOverviewSlot(section.scope, slot)"
        >
          <div v-if="slot.isSummary" class="gallery-overview__summary-overlay">
            <span class="gallery-overview__summary-title">{{ section.summaryTitle }}</span>
            <span class="gallery-overview__summary-count">{{ section.total }} 个</span>
          </div>
        </ThumbCard>
      </div>
    </section>

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

    <SelectionDetailOverlay
      :visible="detailOverlayVisible"
      :layer-style="detailLayerStyle"
      :panel-style="detailPanelStyle"
      :preview-items="detailPreviewItems"
      :is-multi="false"
      :name-field="detailNameField"
      :category-field="detailCategoryField"
      :tags-field="detailTagsField"
      :size-field="detailSizeField"
      :size-label="'尺寸'"
      :imported-field="detailImportedField"
      :created-field="detailCreatedField"
      :raw-name="detailRawName"
      :raw-category-id="detailRawCategoryId"
      :raw-created-at="detailRawCreatedAt"
      primary-action-label="查看原图"
      primary-action-tone="accent"
      :can-open-primary-action="canOpenDetailPrimaryAction"
      :primary-action-disabled="!canOpenDetailPrimaryAction"
      secondary-action-label="进入列表"
      secondary-action-tone="neutral"
      :secondary-action-disabled="!canOpenDetailSecondaryAction"
      :metadata-permissions="detailMetadataPermissions"
      :can-open-collection-menu="false"
      :collection-menu-disabled="true"
      :can-edit-tags="false"
      :tag-menu-disabled="true"
      :can-edit-name="false"
      :can-edit-category="false"
      :can-edit-created-at="false"
      :edit-busy="false"
      current-date-group=""
      :category-options="[]"
      @close="closeOverviewDetail"
      @open-primary="openDetailPrimaryAction"
      @secondary-action="openDetailSecondaryAction"
      @preview-error="onDetailPreviewError"
    />
  </section>
</template>

<script>
import FolderImportDialog from '../components/FolderImportDialog.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import SelectionDetailOverlay from '../components/SelectionDetailOverlay.vue'
import ThumbCard from '../components/ThumbCard.vue'
import { resolveAnimatedBadgeLabel } from '../utils/animatedMedia'
import TopLevelPageHeader from './TopLevelPageHeader.vue'
import {
  API_BASE,
  buildOriginalMediaUrl,
  resolvePreviewUrl,
  topLevelPageVars,
} from './topLevelPageConvention'

const DEFAULT_CATEGORY_ID = 1
const AUTO_CATEGORY_KEY = 'auto'
const IMPORT_CHUNK = 50
const IMAGE_EXT_RE = /\.(jpe?g|png|webp|gif|bmp|tiff?)$/i
const IMPORT_STOP_ERROR_NAME = 'ImportStoppedError'

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

function createImportStopError() {
  const error = new Error('导入已停止')
  error.name = IMPORT_STOP_ERROR_NAME
  return error
}

function isImportStopError(err) {
  return Boolean(err && (err.name === IMPORT_STOP_ERROR_NAME || err.name === 'AbortError'))
}

function createEmptyOverview(scope) {
  return {
    scope,
    total: 0,
    items: [],
  }
}

export default {
  name: 'GalleryPage',
  components: {
    FolderImportDialog,
    LoadingSpinner,
    SelectionDetailOverlay,
    ThumbCard,
    TopLevelPageHeader,
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
      stopRequested: false,
      recentOverview: createEmptyOverview('recent'),
      allOverview: createEmptyOverview('all'),
      recentOverviewLoading: false,
      allOverviewLoading: false,
      recentOverviewError: '',
      allOverviewError: '',
      viewportWidth: typeof window !== 'undefined' ? window.innerWidth : 0,
      viewportHeight: typeof window !== 'undefined' ? window.innerHeight : 0,
      detailOverlayVisible: false,
      detailScope: 'recent',
      detailItem: null,
    }
  },

  computed: {
    pageVars() {
      return topLevelPageVars()
    },
    categoryDisplayMap() {
      return this.importCategories.reduce((map, category) => {
        if (!Number.isInteger(category?.id)) return map
        map[category.id] = category.display_name || category.name || `#${category.id}`
        return map
      }, {})
    },
    isPortrait() {
      return this.viewportHeight > this.viewportWidth
    },
    overviewSlotCount() {
      return this.isPortrait ? 3 : 5
    },
    overviewSections() {
      return [
        this.buildOverviewSection({
          scope: 'recent',
          title: '最近导入',
          hint: '一级页点击图片直接查看详情，点击最后一格进入完整列表。',
          emptyText: '最近暂无导入记录。',
          overview: this.recentOverview,
          loading: this.recentOverviewLoading,
          error: this.recentOverviewError,
        }),
        this.buildOverviewSection({
          scope: 'all',
          title: '图库总览',
          hint: '拉平全部可见图片做一级预览，完整列表与日期视图二级页保持一致。',
          emptyText: '图库中暂无可见图片。',
          overview: this.allOverview,
          loading: this.allOverviewLoading,
          error: this.allOverviewError,
        }),
      ]
    },
    detailLayerStyle() {
      return {
        top: '0px',
        right: '0px',
        bottom: '0px',
        left: '0px',
      }
    },
    detailPanelStyle() {
      if (this.isPortrait) {
        return {
          width: 'min(100%, 540px)',
          height: 'min(100%, 92vh)',
        }
      }
      return {
        width: 'min(1120px, 84vw)',
        height: 'min(760px, 84vh)',
      }
    },
    detailPreviewItems() {
      if (!this.detailItem) return []
      return [
        {
          key: this.detailItem.media_rel_path || this.detailItem.id || this.detailItem.name || 'detail',
          name: this.detailNameText(this.detailItem),
          type: 'image',
          previewUrl: this.resolvedOverviewUrl(this.detailItem),
          aspectRatio: this.detailAspectRatio(this.detailItem),
          animationLabel: this.animatedBadgeLabel(this.detailItem),
        },
      ]
    },
    detailNameField() {
      return this.buildDetailField([this.detailNameText(this.detailItem)])
    },
    detailCategoryField() {
      return this.buildDetailField([this.detailCategoryText(this.detailItem)])
    },
    detailTagsField() {
      return this.buildTagsField(this.detailItem)
    },
    detailSizeField() {
      return this.buildDetailField([this.detailSizeText(this.detailItem)])
    },
    detailImportedField() {
      return this.buildDetailField([this.detailImportedText(this.detailItem)])
    },
    detailCreatedField() {
      return this.buildDetailField([this.detailCreatedText(this.detailItem)])
    },
    detailRawName() {
      return this.detailNameText(this.detailItem)
    },
    detailRawCategoryId() {
      const categoryId = Number(this.detailItem?.category_id)
      return Number.isInteger(categoryId) && categoryId > 0 ? categoryId : null
    },
    detailRawCreatedAt() {
      return this.detailItem?.file_created_at || null
    },
    detailMetadataPermissions() {
      return {
        name: false,
        category: false,
        tags: false,
        createdAt: false,
      }
    },
    canOpenDetailPrimaryAction() {
      return Boolean(buildOriginalMediaUrl(this.detailItem?.media_rel_path))
    },
    canOpenDetailSecondaryAction() {
      return Boolean(this.detailItem && (this.detailScope === 'recent' || this.detailScope === 'all'))
    },
  },

  created() {
    this._activeImportController = null
    this.fetchGalleryOverviews()
    this.loadCategoryDisplayLabels()
    this._checkMissingThumbs()
    if (typeof window !== 'undefined') {
      window.addEventListener('resize', this.onResize)
      window.addEventListener('library-refreshed', this.onLibraryRefreshed)
    }
  },

  beforeUnmount() {
    this.abortActiveImportRequest()
    if (typeof window !== 'undefined') {
      window.removeEventListener('resize', this.onResize)
      window.removeEventListener('library-refreshed', this.onLibraryRefreshed)
    }
  },

  activated() {
    this.fetchGalleryOverviews()
    this.loadCategoryDisplayLabels()
    this._checkMissingThumbs()
  },

  methods: {
    animatedBadgeLabel: resolveAnimatedBadgeLabel,
    resolvePreviewUrl,
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

    abortActiveImportRequest() {
      if (!this._activeImportController) return
      this._activeImportController.abort()
      this._activeImportController = null
    },

    stopImport() {
      if (!this.importing || this.stopRequested) return
      this.stopRequested = true
      this.status = '正在停止导入…'
      this.abortActiveImportRequest()
    },

    onResize() {
      this.viewportWidth = typeof window !== 'undefined' ? window.innerWidth : this.viewportWidth
      this.viewportHeight = typeof window !== 'undefined' ? window.innerHeight : this.viewportHeight
    },

    onLibraryRefreshed() {
      this.fetchGalleryOverviews()
    },

    async loadCategoryDisplayLabels(force = false) {
      if (!force && this.importCategories.length) return
      try {
        const res = await fetch(`${API_BASE}/api/categories`)
        if (!res.ok) return
        const data = await res.json()
        this.importCategories = Array.isArray(data.items)
          ? data.items.filter(category => category && category.is_active !== false)
          : []
      } catch {
        // Keep category labels optional on the overview page.
      }
    },

    async fetchGalleryOverviews() {
      await Promise.all([
        this.fetchGalleryOverview('recent'),
        this.fetchGalleryOverview('all'),
      ])
    },

    async fetchGalleryOverview(scope) {
      const loadingKey = scope === 'recent' ? 'recentOverviewLoading' : 'allOverviewLoading'
      const errorKey = scope === 'recent' ? 'recentOverviewError' : 'allOverviewError'
      const overviewKey = scope === 'recent' ? 'recentOverview' : 'allOverview'

      this[loadingKey] = true
      this[errorKey] = ''
      try {
        const params = new URLSearchParams({ limit: '12' })
        const response = await fetch(`${API_BASE}/api/gallery/${scope}/overview?${params.toString()}`)
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const payload = await response.json()
        this[overviewKey] = {
          ...createEmptyOverview(scope),
          ...payload,
        }
      } catch {
        this[overviewKey] = createEmptyOverview(scope)
        this[errorKey] = '预览接口不可用，请确认前后端服务均已启动。'
      } finally {
        this[loadingKey] = false
      }
    },

    buildOverviewSection({ scope, title, hint, emptyText, overview, loading, error }) {
      const displaySlots = this.getOverviewDisplaySlots(scope, overview)
      return {
        scope,
        title,
        hint,
        emptyText,
        total: Number(overview?.total || 0),
        loading,
        error,
        displaySlots,
        summaryTitle: scope === 'recent' ? '最近导入' : '图库总览',
      }
    },

    getOverviewDisplaySlots(scope, overview) {
      const total = Number(overview?.total || 0)
      if (!total) return []
      const items = Array.isArray(overview?.items) ? overview.items : []
      const visibleItems = items.slice(0, this.overviewSlotCount)
      if (!visibleItems.length) return []

      if (total > this.overviewSlotCount) {
        return visibleItems.map((item, index) => ({
          item,
          isSummary: index === visibleItems.length - 1,
          key: `${scope}:${item.media_rel_path || item.id || item.name || index}:${index === visibleItems.length - 1 ? 'summary' : 'detail'}`,
        }))
      }
      return visibleItems.map((item, index) => ({
        item,
        isSummary: false,
        key: `${scope}:${item.media_rel_path || item.id || item.name || index}:detail`,
      }))
    },

    overviewGridStyle(section) {
      const slotCount = section.displaySlots?.length || 0
      const minimumColumns = this.isPortrait ? 2 : 3
      const columnCount = Math.max(Math.min(this.overviewSlotCount, minimumColumns), slotCount)
      return {
        '--gallery-overview-columns': String(columnCount),
      }
    },

    resolvedOverviewUrl(item) {
      return this.resolvePreviewUrl(item) || buildOriginalMediaUrl(item?.media_rel_path)
    },

    openOverviewList(scope) {
      const target = scope === 'recent' ? '/gallery/recent' : '/gallery/all'
      this.$router.push(target).catch(() => {})
    },

    openOverviewSlot(scope, slot) {
      if (!slot?.item) return
      if (slot.isSummary) {
        this.openOverviewList(scope)
        return
      }
      this.openOverviewDetail(scope, slot.item)
    },

    openOverviewDetail(scope, item) {
      if (!item) return
      this.detailScope = scope
      this.detailItem = item
      this.detailOverlayVisible = true
    },

    closeOverviewDetail() {
      this.detailOverlayVisible = false
      this.detailItem = null
    },

    openDetailPrimaryAction() {
      const originalUrl = buildOriginalMediaUrl(this.detailItem?.media_rel_path)
      if (!originalUrl) return
      if (typeof window !== 'undefined') {
        window.open(originalUrl, '_blank', 'noopener')
      }
    },

    openDetailSecondaryAction() {
      if (!this.canOpenDetailSecondaryAction) return
      this.openOverviewList(this.detailScope)
      this.closeOverviewDetail()
    },

    onDetailPreviewError() {
      // Keep the read-only overlay open and allow the built-in skeleton fallback.
    },

    detailNameText(item) {
      return item?.name || item?.full_filename || '未命名'
    },

    detailCategoryText(item) {
      const categoryId = Number(item?.category_id)
      if (!Number.isInteger(categoryId) || categoryId <= 0) return ''
      return this.categoryDisplayMap[categoryId] || `#${categoryId}`
    },

    detailAspectRatio(item) {
      const width = Number(item?.width)
      const height = Number(item?.height)
      if (!Number.isFinite(width) || width <= 0 || !Number.isFinite(height) || height <= 0) {
        return '4 / 3'
      }
      return `${width} / ${height}`
    },

    buildTagsField(item) {
      const tagIds = Array.isArray(item?.tags)
        ? [...new Set(item.tags.filter(tagId => Number.isInteger(tagId) && tagId > 0))]
        : []
      if (!tagIds.length) {
        return {
          text: '',
          isVarious: false,
          isEmpty: true,
          items: [],
        }
      }
      return {
        text: tagIds.map(tagId => `#${tagId}`).join(' · '),
        isVarious: false,
        isEmpty: false,
        items: [],
      }
    },

    buildDetailField(values, options = {}) {
      const emptyText = Object.prototype.hasOwnProperty.call(options, 'emptyText')
        ? options.emptyText
        : '—'
      const normalized = Array.isArray(values)
        ? values.map(value => (value == null ? '' : String(value).trim()))
        : []

      if (!normalized.length) {
        return {
          text: emptyText,
          isVarious: false,
          isEmpty: !emptyText,
        }
      }

      const first = normalized[0]
      const allSame = normalized.every(value => value === first)
      if (!allSame) {
        return {
          text: 'various',
          isVarious: true,
          isEmpty: false,
        }
      }

      const isEmpty = first.length === 0
      return {
        text: isEmpty ? emptyText : first,
        isVarious: false,
        isEmpty,
      }
    },

    formatDateTime(value) {
      if (!value) return ''
      const date = value instanceof Date ? value : new Date(value)
      if (Number.isNaN(date.getTime())) return ''

      const pad = segment => String(segment).padStart(2, '0')
      return [
        `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`,
        `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`,
      ].join(' ')
    },

    formatFileSizeMb(bytesValue) {
      const bytes = Number(bytesValue)
      if (!Number.isFinite(bytes) || bytes < 0) return ''
      const megaBytes = bytes / (1024 * 1024)
      if (!Number.isFinite(megaBytes)) return ''
      const formatted = megaBytes >= 100
        ? megaBytes.toFixed(1)
        : megaBytes.toFixed(2)
      return formatted.replace(/\.00$/, '').replace(/(\.\d)0$/, '$1')
    },

    detailSizeText(item) {
      const width = Number(item?.width)
      const height = Number(item?.height)
      const parts = []
      if (Number.isFinite(width) && width > 0 && Number.isFinite(height) && height > 0) {
        parts.push(`${width} × ${height} px`)
      }
      const fileSizeMb = this.formatFileSizeMb(item?.file_size)
      if (fileSizeMb) {
        parts.push(`${fileSizeMb} MB`)
      }
      return parts.join(' · ')
    },

    detailImportedText(item) {
      return this.formatDateTime(item?.imported_at)
    },

    detailCreatedText(item) {
      return this.formatDateTime(item?.file_created_at)
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

    async importFolderRow(row, recentImportModeState) {
      const { batches } = this.buildImportBatches(row.files)
      let importedCount = 0
      let skippedCount = 0

      for (const batch of batches) {
        if (this.stopRequested) throw createImportStopError()

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
        fd.append('recent_import_mode', recentImportModeState?.nextMode || 'replace')

        const controller = new AbortController()
        this._activeImportController = controller
        let res
        try {
          res = await fetch(`${API_BASE}/api/import`, { method: 'POST', body: fd, signal: controller.signal })
        } catch (err) {
          if (this.stopRequested || isImportStopError(err)) {
            throw createImportStopError()
          }
          throw err
        } finally {
          if (this._activeImportController === controller) {
            this._activeImportController = null
          }
        }

        if (!res.ok) {
          const message = await this.readErrorMessage(res, '导入失败，请检查后端服务')
          throw new Error(message)
        }

        const data = await res.json()
        if (recentImportModeState?.nextMode === 'replace') {
          recentImportModeState.nextMode = 'append'
        }
        importedCount += Array.isArray(data.imported) ? data.imported.length : 0
        skippedCount += Array.isArray(data.skipped) ? data.skipped.length : 0
        this.doneFiles = Math.min(this.doneFiles + batch.imageCount, this.totalFiles)

        if (this.stopRequested) throw createImportStopError()
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
      let stopIndex = -1
      let shouldRefreshOverview = false
      const recentImportModeState = { nextMode: 'replace' }

      this.importing = true
      this.stopRequested = false
      window.__ptvImporting = true
      this.clearNotice()
      this.importDialogError = ''
      this.importDialogOpen = false
      this.totalFiles = rowsToImport.reduce((sum, row) => sum + row.imageCount, 0)
      this.doneFiles = 0

      try {
        for (const [index, row] of rowsToImport.entries()) {
          if (this.stopRequested) {
            stopIndex = index
            break
          }

          this.currentFolderLabel = row.label
          this.status = `正在导入（${index + 1}/${rowsToImport.length}）${row.label}…`
          try {
            const result = await this.importFolderRow(row, recentImportModeState)
            importedCount += result.importedCount
            skippedCount += result.skippedCount
          } catch (err) {
            if (isImportStopError(err)) {
              stopIndex = index
              break
            }
            failedRows.push({
              id: row.id,
              label: row.label,
              error: toErrorMessage(err),
            })
          }
        }

        if (stopIndex >= 0) {
          const keepIdSet = new Set([
            ...failedRows.map(item => item.id),
            ...rowsToImport.slice(stopIndex).map(row => row.id),
          ])
          this.importDialogRows = this.importDialogRows.filter(row => keepIdSet.has(row.id))
          this.selectedImportRowIds = []
          this.importDialogError = '导入已停止，已保留当前及未完成的文件夹，可继续导入。'
          this.importDialogOpen = this.importDialogRows.length > 0
          this.status = `导入已停止：已导入 ${importedCount} 张，重复跳过 ${skippedCount} 张。`
        } else if (failedRows.length) {
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
        shouldRefreshOverview = importedCount > 0
      } finally {
        this.importing = false
        this.stopRequested = false
        this.abortActiveImportRequest()
        window.__ptvImporting = false
        this.currentFolderLabel = ''
        this.currentItem = ''
        this.totalFiles = 0
        this.doneFiles = 0
        if (shouldRefreshOverview) {
          await this.fetchGalleryOverviews()
          if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('library-refreshed'))
          }
        }
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
        await this.fetchGalleryOverviews()
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
.btn--danger { @apply bg-rose-600 text-white; }
.btn--danger:not(:disabled):hover { @apply bg-rose-700; }
.btn__icon { @apply inline-block; }
.spinning  { animation: spin 0.8s linear infinite; }

.hidden-input { @apply hidden; }

/* Status / progress */
.import-feedback {
  @apply flex flex-col gap-3;
}

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
  max-height: 10rem;
  overflow: auto;
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

.gallery-overview {
  @apply flex flex-col gap-4 rounded-[1.5rem] border border-slate-200 bg-white p-5 shadow-sm;
}

.gallery-overview__head {
  @apply flex items-start justify-between gap-4;
}

.gallery-overview__head-main {
  @apply flex min-w-0 flex-col gap-1;
}

.gallery-overview__title {
  @apply m-0 text-lg font-semibold text-slate-900;
}

.gallery-overview__hint {
  @apply m-0 text-sm leading-relaxed text-slate-500;
}

.gallery-overview__open {
  @apply rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs font-medium text-slate-600 transition;
}

.gallery-overview__open:hover:not(:disabled) {
  @apply bg-slate-100 text-slate-800;
}

.gallery-overview__open:disabled {
  @apply cursor-not-allowed opacity-50;
}

.gallery-overview__grid {
  display: grid;
  grid-template-columns: repeat(var(--gallery-overview-columns), minmax(0, 1fr));
  gap: 1rem;
}

.gallery-overview__card {
  width: 100%;
  aspect-ratio: 1 / 1;
}

.gallery-overview__card--summary {
  @apply relative;
}

.gallery-overview__summary-overlay {
  @apply absolute inset-0 flex flex-col items-center justify-center px-4 text-center text-white;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.06) 0%, rgba(15, 23, 42, 0.62) 100%);
}

.gallery-overview__summary-title {
  @apply text-base font-semibold;
  text-shadow: 0 2px 16px rgba(15, 23, 42, 0.45);
}

.gallery-overview__summary-count {
  @apply mt-2 text-sm text-white/90;
  text-shadow: 0 2px 14px rgba(15, 23, 42, 0.4);
}

.gallery-overview__empty {
  @apply rounded-[1.25rem] border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center text-sm text-slate-500;
}

.gallery-overview__empty--error {
  @apply border-rose-200 bg-rose-50 text-rose-600;
}

.gallery-overview__empty-icon {
  @apply mb-2 block text-3xl leading-none;
}

@media (max-width: 820px) {
  .gallery-overview__head {
    @apply flex-col items-stretch;
  }
}

@media (max-width: 640px) {
  .gallery-overview__grid {
    gap: 0.85rem;
  }
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
