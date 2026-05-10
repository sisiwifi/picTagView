<template>
  <section class="top-level-page search-page" :style="pageVars">
    <div class="search-page__shell">
      <div class="search-page__top-shell">
        <TopLevelPageHeader
          title="搜索"
          subtitle="单输入统一搜索文件名、Tag、本地图片 quick hash 与时间范围。"
        >
          <div class="search-page__mode-pill">当前模式：{{ effectiveModeLabel }}</div>
        </TopLevelPageHeader>

        <label class="search-bar" for="search-input">
          <span class="search-bar__icon">⌕</span>
          <input
            id="search-input"
            v-model="rawQuery"
            class="search-bar__input"
            type="text"
            autocomplete="off"
            spellcheck="false"
            placeholder="输入文件名、file:文件名、import:开始~结束，或 create:开始~结束"
            @keyup.esc="clearSearch"
          >
          <div class="search-bar__actions">
            <button class="search-bar__tool" type="button" title="按图搜索" @click.stop.prevent="triggerFilePicker">
              <span class="search-bar__tool-icon" aria-hidden="true">📷</span>
              <span class="search-bar__tool-label">按图搜索</span>
            </button>
            <button class="search-bar__tool" type="button" title="时间范围" @click.stop.prevent="openTimeRangeDialog">
              <span class="search-bar__tool-icon" aria-hidden="true">🕒</span>
              <span class="search-bar__tool-label">时间范围</span>
            </button>
            <button v-if="rawQuery" type="button" class="search-bar__clear" @click.stop.prevent="clearSearch">清空</button>
          </div>
        </label>

        <input
          ref="fileInput"
          class="search-page__file-input"
          type="file"
          accept="image/*"
          @change="handleFileSelection"
        >

        <div class="search-page__hints">
          <span class="search-page__hint">默认：文件名 + Tag 混合匹配</span>
          <span class="search-page__hint">文件名：<strong>name:文件名</strong> 或 <strong>$文件名</strong></span>
          <span class="search-page__hint">Tag：<strong>tag:角色名</strong> 或 <strong>#角色名</strong></span>
          <span class="search-page__hint">文件搜图：<strong>file:文件名</strong>，建议直接点按图搜索按钮选择图片</span>
          <span class="search-page__hint">时间：<strong>import/create:2026-03-21 01:45:18~2026-03-22 02:00:00</strong></span>
        </div>
      </div>

      <div class="search-page__result-shell">
        <LoadingSpinner v-if="loading" />

        <div v-else-if="errorMessage" class="search-empty search-empty--error">
          <span class="search-empty__icon">!</span>
          <p>{{ errorMessage }}</p>
        </div>

        <div v-else-if="!hasQuery" class="search-empty">
          <span class="search-empty__icon">⌕</span>
          <p>输入后立即搜索。普通文本默认匹配文件名与 Tag；按图搜索按钮可按本地图片 quick hash 搜索；时间范围按钮可辅助写入导入时间或创建时间范围。</p>
        </div>

        <div v-else-if="!searchResponse.items.length" class="search-empty">
          <span class="search-empty__icon">∅</span>
          <p>{{ emptyStateText }}</p>
        </div>

        <section v-else class="search-result-preview">
          <header class="search-result-preview__header">
            <div class="search-result-preview__header-main">
              <h3 class="search-result-preview__title">搜索结果</h3>
              <p class="search-result-preview__subtitle">{{ resultViewportSubtitle }}</p>
            </div>
            <button
              class="search-result-preview__open-all"
              type="button"
              :disabled="!searchResponse.items.length"
              @click="openSearchResultsPage"
            >
              查看全部
            </button>
          </header>

          <div class="search-result-preview__summary-row">
            <span class="search-result-preview__summary-pill">{{ resultSummary }}</span>
            <span class="search-result-preview__summary-pill">当前模式：{{ effectiveModeLabel }}</span>
            <span v-if="searchResponse.quick_hash" class="search-result-preview__summary-pill">Quick Hash：{{ shortQuickHash }}</span>
            <span v-if="modeInfo.mode === 'file' && modeInfo.displayToken" class="search-result-preview__summary-pill">样本文件：{{ modeInfo.displayToken }}</span>
            <span v-if="activeTimeRangeText" class="search-result-preview__summary-pill">时间范围：{{ activeTimeRangeText }}</span>
            <span class="search-result-preview__summary-pill search-result-preview__summary-pill--accent">当前窗口渲染 {{ virtualResults.length }} / {{ searchResponse.total || 0 }}</span>
          </div>

          <div ref="resultViewport" class="search-result-preview__viewport" @scroll.passive="handleResultViewportScroll">
            <div class="search-result-virtual" :style="virtualCanvasStyle">
              <div class="search-result-virtual__window" :style="virtualWindowStyle">
                <div class="search-result-grid" :style="virtualGridStyle">
                  <ThumbCard
                    v-for="item in virtualResults"
                    :key="item.id"
                    :src="resolvedSearchCardPreviewUrl(item)"
                    :badge-label="animatedBadgeLabel(item)"
                    class="search-result-card"
                    :style="virtualCardStyle"
                    :overlay-opacity="0.16"
                    :rounded="'1.4rem'"
                    @click="openSearchDetail(item)"
                  >
                    <article class="search-result-card__body">
                      <div class="search-result-card__badges">
                        <span
                          v-for="badge in item.matched_by"
                          :key="`${item.id}-${badge}`"
                          class="search-result-card__badge"
                        >
                          {{ formatMatchedByLabel(badge) }}
                        </span>
                      </div>

                      <div class="search-result-card__meta">
                        <div class="search-result-card__copy">
                          <h3 class="search-result-card__title">{{ item.name || '未命名图片' }}</h3>
                          <p class="search-result-card__path">{{ item.media_rel_path || '无路径信息' }}</p>
                        </div>

                        <div class="search-result-card__tag-wrap">
                          <TagChipList
                            v-if="tagsForItem(item).length"
                            class="search-result-card__tag-list"
                            :tags="tagsForItem(item)"
                            compact
                          />
                          <div v-else class="search-result-card__tag-placeholder">暂无标签</div>
                        </div>

                        <div class="search-result-card__actions" @click.stop>
                          <button type="button" class="search-result-card__action" @click="openSearchDetail(item)">详情</button>
                          <button
                            type="button"
                            class="search-result-card__action search-result-card__action--ghost"
                            :disabled="!canOpenBrowseLocation(item)"
                            @click="openBrowseLocation(item)"
                          >定位</button>
                        </div>
                      </div>
                    </article>
                  </ThumbCard>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>

    <SelectionDetailOverlay
      :visible="detailVisible"
      :layer-style="detailLayerStyle"
      :panel-style="detailPanelStyle"
      :preview-items="detailPreviewItems"
      :is-multi="false"
      :name-field="detailNameField"
      :category-field="detailCategoryField"
      :tags-field="detailTagsField"
      :size-field="detailSizeField"
      size-label="尺寸"
      :imported-field="detailImportedField"
      imported-label="路径"
      :created-field="detailCreatedField"
      created-label="匹配方式"
      :raw-name="detailRawName"
      :raw-category-id="detailRawCategoryId"
      :raw-created-at="null"
      primary-action-label="定位到原位置"
      primary-action-tone="accent"
      :can-open-primary-action="canOpenDetailPrimaryAction"
      :primary-action-disabled="!canOpenDetailPrimaryAction"
      secondary-action-label="查看原图"
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
      @close="closeSearchDetail"
      @open-primary="openDetailPrimaryAction"
      @secondary-action="openDetailSecondaryAction"
      @preview-error="onDetailPreviewError"
    />

    <SearchTimeRangeDialog
      :visible="timeDialogVisible"
      :initial-field="timeDialogInitialField"
      :initial-start-text="timeDialogInitialStartText"
      :initial-end-text="timeDialogInitialEndText"
      @close="closeTimeRangeDialog"
      @apply="applyTimeRangeQuery"
    />
  </section>
</template>

<script>
import LoadingSpinner from '../components/LoadingSpinner.vue'
import SearchTimeRangeDialog from '../components/SearchTimeRangeDialog.vue'
import SelectionDetailOverlay from '../components/SelectionDetailOverlay.vue'
import TagChipList from '../components/TagChipList.vue'
import ThumbCard from '../components/ThumbCard.vue'
import { resolveAnimatedBadgeLabel } from '../utils/animatedMedia'
import TopLevelPageHeader from './TopLevelPageHeader.vue'
import {
  API_BASE,
  TOP_LEVEL_PAGE_STANDARD,
  buildBrowseLocation,
  buildOriginalMediaUrl,
  buildSearchRequestParams,
  buildTimeRangeQuery,
  detectSearchMode,
  formatMatchedByLabel,
  formatSearchModeLabel,
  resolvePreviewUrl,
  shortenQuickHash,
  topLevelPageVars,
} from './topLevelPageConvention'

const SEARCH_GRID_GAP_PX = 24
const SEARCH_VIRTUAL_ROWS = 3
const SEARCH_OVERSCAN_ROWS = 1

function createEmptySearchResponse() {
  return {
    query: '',
    requested_mode: 'auto',
    resolved_mode: 'auto',
    limit: TOP_LEVEL_PAGE_STANDARD.searchResultLimit,
    total: 0,
    source_media_rel_path: null,
    quick_hash: null,
    included_tags: [],
    items: [],
  }
}

function createDetailField(text = '') {
  const normalized = String(text || '').trim()
  return {
    text: normalized,
    isVarious: false,
    isEmpty: normalized.length === 0,
  }
}

function formatDimensionText(item) {
  const width = Number(item?.width)
  const height = Number(item?.height)
  if (!Number.isFinite(width) || width <= 0 || !Number.isFinite(height) || height <= 0) {
    return ''
  }
  return `${width} × ${height} px`
}

function splitTimeRangeText(rangeText) {
  const [startText = '', endText = ''] = String(rangeText || '').split('~').map(segment => segment.trim())
  return { startText, endText }
}

function formatSearchDetailMatchedByLabel(value) {
  switch (value) {
    case 'quick_hash':
    case 'path':
      return '按文件搜索'
    case 'filename':
      return '文件名匹配'
    case 'tag':
      return '标签匹配'
    case 'imported_at':
      return '按导入时间搜索'
    case 'file_created_at':
      return '按创建时间搜索'
    default:
      return formatMatchedByLabel(value)
  }
}

export default {
  name: 'SearchPage',
  components: {
    LoadingSpinner,
    SearchTimeRangeDialog,
    SelectionDetailOverlay,
    TagChipList,
    ThumbCard,
    TopLevelPageHeader,
  },
  data() {
    return {
      rawQuery: '',
      loading: false,
      errorMessage: '',
      searchResponse: createEmptySearchResponse(),
      debounceTimer: null,
      requestController: null,
      resultViewportWidth: 0,
      resultViewportHeight: 0,
      resultViewportScrollTop: 0,
      resultResizeObserver: null,
      viewportWidth: typeof window !== 'undefined' ? window.innerWidth : 0,
      viewportHeight: typeof window !== 'undefined' ? window.innerHeight : 0,
      detailVisible: false,
      detailItem: null,
      categoryDisplayMap: {},
      fileQuickHash: '',
      fileTokenFromPicker: '',
      skipNextScheduledSearch: false,
      timeDialogVisible: false,
      previewRepairQueue: [],
      previewRepairTimer: null,
      previewRepairInFlight: false,
      previewRepairAttemptTokens: {},
    }
  },
  computed: {
    pageVars() {
      return topLevelPageVars()
    },
    modeInfo() {
      return detectSearchMode(this.rawQuery, { quickHash: this.fileQuickHash })
    },
    hasQuery() {
      return this.modeInfo.normalizedQuery.length > 0
    },
    effectiveModeLabel() {
      const resolved = this.searchResponse.resolved_mode
      if (this.hasQuery && resolved && resolved !== 'auto') {
        return formatSearchModeLabel(resolved)
      }
      return formatSearchModeLabel(this.modeInfo.mode)
    },
    resultTagMap() {
      return this.searchResponse.included_tags.reduce((map, tag) => {
        map[tag.id] = tag
        return map
      }, {})
    },
    activeTimeRangeText() {
      if (!['imported_at', 'file_created_at'].includes(this.modeInfo.mode)) {
        return ''
      }
      return this.modeInfo.normalizedQuery
    },
    resultSummary() {
      if (!this.hasQuery) return ''
      const total = Number(this.searchResponse.total || 0)
      if (this.modeInfo.mode === 'file' && this.searchResponse.quick_hash) {
        return `已按所选本地图片的 quick hash 找到 ${total} 条结果`
      }
      if (this.modeInfo.mode === 'imported_at') {
        return `按导入时间范围找到 ${total} 条结果`
      }
      if (this.modeInfo.mode === 'file_created_at') {
        return `按创建时间范围找到 ${total} 条结果`
      }
      return `共找到 ${total} 条结果`
    },
    resultViewportSubtitle() {
      if (this.modeInfo.mode === 'file') {
        return '当前按本地样本图片的 Quick Hash 连续滚动浏览结果，页面只渲染视口附近的卡片。'
      }
      if (['imported_at', 'file_created_at'].includes(this.modeInfo.mode)) {
        return '当前按秒级时间范围连续滚动浏览结果，页面只渲染视口附近的卡片。'
      }
      return '连续滚动浏览当前搜索结果，页面只渲染视口附近的卡片，滚动时按锚点继续加载。'
    },
    shortQuickHash() {
      return shortenQuickHash(this.searchResponse.quick_hash)
    },
    emptyStateText() {
      if (this.modeInfo.mode === 'filename') {
        return '没有匹配结果。可以尝试更短的文件名，或切回普通文本做文件名 + Tag 混合搜索。'
      }
      if (this.modeInfo.mode === 'file') {
        return '未找到与当前本地样本图片 quick hash 对应的结果。可以重新选择一张图片，或切回文件名 / Tag 搜索。'
      }
      if (this.modeInfo.mode === 'imported_at') {
        return '当前导入时间范围内没有匹配结果。请检查时间区间是否过窄。'
      }
      if (this.modeInfo.mode === 'file_created_at') {
        return '当前创建时间范围内没有匹配结果。请检查时间区间是否过窄。'
      }
      return '没有匹配结果。可以尝试更短的文件名、name: / $ 文件名专搜、tag: 前缀，或使用相机 / 时钟按钮辅助输入。'
    },
    previewColumnCount() {
      const availableWidth = Number(this.resultViewportWidth || 0)
      if (!Number.isFinite(availableWidth) || availableWidth <= 0) {
        return 1
      }
      return Math.max(
        1,
        Math.floor((availableWidth + SEARCH_GRID_GAP_PX) / (TOP_LEVEL_PAGE_STANDARD.thumbEdgePx + SEARCH_GRID_GAP_PX))
      )
    },
    virtualCardWidth() {
      const availableWidth = Math.max(0, Number(this.resultViewportWidth || 0))
      const columns = Math.max(1, this.previewColumnCount)
      const rawWidth = Math.floor((availableWidth - SEARCH_GRID_GAP_PX * Math.max(0, columns - 1)) / columns)
      return Math.max(160, Math.min(TOP_LEVEL_PAGE_STANDARD.thumbEdgePx, rawWidth || TOP_LEVEL_PAGE_STANDARD.thumbEdgePx))
    },
    virtualGridWidth() {
      return this.previewColumnCount * this.virtualCardWidth + Math.max(0, this.previewColumnCount - 1) * SEARCH_GRID_GAP_PX
    },
    virtualRowStride() {
      return this.virtualCardWidth + SEARCH_GRID_GAP_PX
    },
    totalVirtualRows() {
      if (!this.searchResponse.items.length) return 0
      return Math.ceil(this.searchResponse.items.length / this.previewColumnCount)
    },
    visibleVirtualRows() {
      if (!this.resultViewportHeight) {
        return SEARCH_VIRTUAL_ROWS
      }
      return Math.max(
        SEARCH_VIRTUAL_ROWS,
        Math.ceil((this.resultViewportHeight + SEARCH_GRID_GAP_PX) / Math.max(this.virtualRowStride, 1))
      )
    },
    virtualStartRow() {
      if (!this.searchResponse.items.length) return 0
      return Math.max(0, Math.floor(this.resultViewportScrollTop / Math.max(this.virtualRowStride, 1)) - SEARCH_OVERSCAN_ROWS)
    },
    virtualEndRow() {
      return Math.min(this.totalVirtualRows, this.virtualStartRow + this.visibleVirtualRows + SEARCH_OVERSCAN_ROWS * 2)
    },
    virtualStartIndex() {
      return this.virtualStartRow * this.previewColumnCount
    },
    virtualEndIndex() {
      return Math.min(this.searchResponse.items.length, this.virtualEndRow * this.previewColumnCount)
    },
    virtualResults() {
      return this.searchResponse.items.slice(this.virtualStartIndex, this.virtualEndIndex)
    },
    virtualOffsetY() {
      return this.virtualStartRow * this.virtualRowStride
    },
    virtualTotalHeight() {
      if (!this.totalVirtualRows) return 0
      return this.totalVirtualRows * this.virtualCardWidth + Math.max(0, this.totalVirtualRows - 1) * SEARCH_GRID_GAP_PX
    },
    virtualCanvasStyle() {
      return {
        height: `${Math.max(0, this.virtualTotalHeight)}px`,
      }
    },
    virtualWindowStyle() {
      return {
        transform: `translate(-50%, ${this.virtualOffsetY}px)`,
      }
    },
    virtualGridStyle() {
      return {
        width: `${Math.max(this.virtualGridWidth, this.virtualCardWidth)}px`,
        gridTemplateColumns: `repeat(${this.previewColumnCount}, ${this.virtualCardWidth}px)`,
      }
    },
    virtualCardStyle() {
      return {
        width: `${this.virtualCardWidth}px`,
      }
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
      if (this.viewportHeight > this.viewportWidth) {
        return {
          width: 'min(100%, 540px)',
          height: 'min(100%, 92vh)',
        }
      }
      return {
        width: 'min(1080px, 84vw)',
        height: 'min(760px, 84vh)',
      }
    },
    detailPreviewItems() {
      if (!this.detailItem) return []
      return [
        {
          key: this.detailItem.media_rel_path || this.detailItem.id || this.detailItem.name || 'search-detail',
          name: this.detailItem.name || '未命名图片',
          type: 'image',
          previewUrl: this.resolvedSearchPreviewUrl(this.detailItem),
          aspectRatio: this.detailAspectRatio(this.detailItem),
          animationLabel: this.animatedBadgeLabel(this.detailItem),
        },
      ]
    },
    detailNameField() {
      return createDetailField(this.detailItem?.name || '未命名图片')
    },
    detailCategoryField() {
      return createDetailField(this.detailCategoryText(this.detailItem))
    },
    detailTagsField() {
      return this.buildTagsField(this.detailItem)
    },
    detailSizeField() {
      return createDetailField(formatDimensionText(this.detailItem))
    },
    detailImportedField() {
      return createDetailField(this.detailItem?.media_rel_path || '')
    },
    detailCreatedField() {
      return createDetailField(this.detailMatchedByText(this.detailItem))
    },
    detailRawName() {
      return this.detailItem?.name || ''
    },
    detailRawCategoryId() {
      const categoryId = Number(this.detailItem?.category_id)
      return Number.isInteger(categoryId) && categoryId > 0 ? categoryId : null
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
      return this.canOpenBrowseLocation(this.detailItem)
    },
    canOpenDetailSecondaryAction() {
      return Boolean(this.buildOriginalMediaUrl(this.detailItem?.media_rel_path))
    },
    timeDialogInitialField() {
      return this.modeInfo.mode === 'file_created_at' ? 'file_created_at' : 'imported_at'
    },
    timeDialogInitialStartText() {
      if (!['imported_at', 'file_created_at'].includes(this.modeInfo.mode)) {
        return ''
      }
      return splitTimeRangeText(this.modeInfo.normalizedQuery).startText
    },
    timeDialogInitialEndText() {
      if (!['imported_at', 'file_created_at'].includes(this.modeInfo.mode)) {
        return ''
      }
      return splitTimeRangeText(this.modeInfo.normalizedQuery).endText
    },
  },
  watch: {
    virtualResults: {
      handler(items) {
        this.enqueueMissingPreviewRepairs(items)
      },
    },
    rawQuery() {
      if (this.modeInfo.mode === 'file' && this.fileQuickHash && this.rawQuery !== this.fileTokenFromPicker) {
        this.fileQuickHash = ''
      }
      if (this.modeInfo.mode !== 'file' && this.fileQuickHash) {
        this.fileQuickHash = ''
      }
      if (this.modeInfo.mode !== 'file') {
        this.fileTokenFromPicker = ''
      }
      this.syncRouteQuery()
      if (this.skipNextScheduledSearch) {
        this.skipNextScheduledSearch = false
        return
      }
      this.scheduleSearch()
    },
    '$route.fullPath': {
      immediate: true,
      handler() {
        const nextQuickHash = typeof this.$route.query.quick_hash === 'string' ? this.$route.query.quick_hash : ''
        if (nextQuickHash !== this.fileQuickHash) {
          this.fileQuickHash = nextQuickHash
        }
        const nextValue = typeof this.$route.query.q === 'string' ? this.$route.query.q : ''
        this.fileTokenFromPicker = nextQuickHash && nextValue.startsWith('file:') ? nextValue : ''
        if (nextValue !== this.rawQuery) {
          this.rawQuery = nextValue
        }
      },
    },
  },
  mounted() {
    this.installResultResizeObserver()
    this.ensureCategoryLabelsLoaded()
    window.addEventListener('resize', this.handleWindowResize, { passive: true })
  },
  beforeUnmount() {
    if (this.debounceTimer) {
      window.clearTimeout(this.debounceTimer)
      this.debounceTimer = null
    }
    if (this.requestController) {
      this.requestController.abort()
      this.requestController = null
    }
    if (this.previewRepairTimer) {
      window.clearTimeout(this.previewRepairTimer)
      this.previewRepairTimer = null
    }
    this.resultResizeObserver?.disconnect?.()
    window.removeEventListener('resize', this.handleWindowResize)
  },
  methods: {
    animatedBadgeLabel: resolveAnimatedBadgeLabel,
    resolvePreviewUrl,
    buildOriginalMediaUrl,
    formatMatchedByLabel,
    resolvedSearchCardPreviewUrl(item) {
      return this.resolvePreviewUrl(item)
    },
    resolvedSearchPreviewUrl(item) {
      return this.resolvePreviewUrl(item) || this.buildOriginalMediaUrl(item?.media_rel_path)
    },
    detailCategoryText(item) {
      const categoryId = Number(item?.category_id)
      if (!Number.isInteger(categoryId) || categoryId <= 0) return ''
      return this.categoryDisplayMap[categoryId] || `#${categoryId}`
    },
    tagsForItem(item) {
      return (item?.tags || [])
        .map(tagId => this.resultTagMap[tagId])
        .filter(Boolean)
        .slice(0, 6)
    },
    buildTagsField(item) {
      const tags = this.tagsForItem(item)
      return {
        text: '',
        isVarious: false,
        isEmpty: tags.length === 0,
        items: tags,
      }
    },
    detailAspectRatio(item) {
      const width = Number(item?.width)
      const height = Number(item?.height)
      if (!Number.isFinite(width) || width <= 0 || !Number.isFinite(height) || height <= 0) {
        return '4 / 3'
      }
      return `${width} / ${height}`
    },
    detailMatchedByText(item) {
      const labels = Array.isArray(item?.matched_by)
        ? item.matched_by.map(value => formatSearchDetailMatchedByLabel(value)).filter(Boolean)
        : []
      return labels.join(' · ')
    },
    async ensureCategoryLabelsLoaded(force = false) {
      if (!force && Object.keys(this.categoryDisplayMap).length) return
      try {
        const res = await fetch(`${API_BASE}/api/categories`)
        if (!res.ok) return
        const data = await res.json()
        const nextMap = {}
        for (const category of (data.items || [])) {
          if (!Number.isInteger(category?.id)) continue
          nextMap[category.id] = category.display_name || category.name || `#${category.id}`
        }
        this.categoryDisplayMap = nextMap
      } catch {
        // Ignore category label load failures and keep fallback ids visible.
      }
    },
    previewRepairStateKey(item) {
      const imageId = Number(item?.id)
      return Number.isInteger(imageId) && imageId > 0 ? String(imageId) : ''
    },
    previewRepairToken(item) {
      return `${item?.cache_thumb_url || ''}|${item?.thumb_url || ''}`
    },
    shouldRepairPreview(item) {
      return Boolean(this.previewRepairStateKey(item)) && !this.resolvePreviewUrl(item)
    },
    enqueueMissingPreviewRepairs(items) {
      if (!Array.isArray(items) || !items.length) return
      let didQueue = false
      const nextAttemptTokens = { ...this.previewRepairAttemptTokens }
      const nextQueue = [...this.previewRepairQueue]

      for (const item of items) {
        if (!this.shouldRepairPreview(item)) continue
        const stateKey = this.previewRepairStateKey(item)
        const token = this.previewRepairToken(item)
        if (!stateKey || nextAttemptTokens[stateKey] === token) continue

        nextAttemptTokens[stateKey] = token
        const imageId = Number(item?.id)
        if (Number.isInteger(imageId) && imageId > 0 && !nextQueue.includes(imageId)) {
          nextQueue.push(imageId)
          didQueue = true
        }
      }

      if (!didQueue) return
      this.previewRepairAttemptTokens = nextAttemptTokens
      this.previewRepairQueue = nextQueue
      if (this.previewRepairTimer) {
        window.clearTimeout(this.previewRepairTimer)
      }
      this.previewRepairTimer = window.setTimeout(() => {
        this.previewRepairTimer = null
        this.flushPreviewRepairQueue()
      }, 90)
    },
    async flushPreviewRepairQueue() {
      const repairIds = [...new Set(this.previewRepairQueue.filter(id => Number.isInteger(id) && id > 0))]
      this.previewRepairQueue = []
      if (!repairIds.length) return

      if (this.previewRepairInFlight) {
        this.previewRepairQueue = [...new Set([...this.previewRepairQueue, ...repairIds])]
        return
      }

      this.previewRepairInFlight = true
      try {
        const res = await fetch(`${API_BASE}/api/admin/refresh?mode=quick`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            repair_cache: true,
            image_ids: repairIds,
          }),
        })
        if (!res.ok) return
        await res.json().catch(() => null)
        await this.refreshPreviewMetadata(repairIds)
      } catch {
        // Ignore targeted preview repair failures and keep placeholders visible.
      } finally {
        this.previewRepairInFlight = false
        if (this.previewRepairQueue.length) {
          this.flushPreviewRepairQueue()
        }
      }
    },
    async refreshPreviewMetadata(imageIds) {
      if (!Array.isArray(imageIds) || !imageIds.length) return
      try {
        const res = await fetch(`${API_BASE}/api/images/meta?ids=${imageIds.join(',')}`)
        if (!res.ok) return

        const data = await res.json()
        const metaMap = new Map((data.items || []).map(meta => [meta.id, meta]))
        if (!metaMap.size) return

        const nextAttemptTokens = { ...this.previewRepairAttemptTokens }
        const nextItems = this.searchResponse.items.map((item) => {
          if (!Number.isInteger(item?.id)) return item
          const meta = metaMap.get(item.id)
          if (!meta) return item

          const width = Number(meta.width)
          const height = Number(meta.height)
          const nextItem = {
            ...item,
            category_id: Number.isInteger(meta.category_id) && meta.category_id > 0 ? meta.category_id : item.category_id,
            cache_thumb_url: meta.cache_thumb_url || '',
            thumb_url: meta.thumb_url || '',
            width: Number.isFinite(width) && width > 0 ? width : item.width,
            height: Number.isFinite(height) && height > 0 ? height : item.height,
          }

          const stateKey = this.previewRepairStateKey(nextItem)
          if (stateKey && nextAttemptTokens[stateKey] !== this.previewRepairToken(nextItem)) {
            delete nextAttemptTokens[stateKey]
          }

          return nextItem
        })

        this.previewRepairAttemptTokens = nextAttemptTokens
        this.searchResponse = {
          ...this.searchResponse,
          items: nextItems,
        }
      } catch {
        // Ignore preview metadata refresh failures.
      }
    },
    clearSearch() {
      this.rawQuery = ''
      this.fileQuickHash = ''
      this.fileTokenFromPicker = ''
      this.errorMessage = ''
      this.searchResponse = createEmptySearchResponse()
      this.previewRepairQueue = []
      this.previewRepairInFlight = false
      this.previewRepairAttemptTokens = {}
      this.closeSearchDetail()
      this.closeTimeRangeDialog()
      this.resultViewportScrollTop = 0
      this.resetResultViewportScroll()
      if (this.requestController) {
        this.requestController.abort()
        this.requestController = null
      }
      if (this.debounceTimer) {
        window.clearTimeout(this.debounceTimer)
        this.debounceTimer = null
      }
      if (this.previewRepairTimer) {
        window.clearTimeout(this.previewRepairTimer)
        this.previewRepairTimer = null
      }
    },
    syncRouteQuery() {
      const query = { ...this.$route.query }
      const nextValue = this.rawQuery || undefined
      const nextQuickHash = this.modeInfo.mode === 'file' && this.fileQuickHash ? this.fileQuickHash : undefined
      const currentValue = typeof this.$route.query.q === 'string' ? this.$route.query.q : undefined
      const currentQuickHash = typeof this.$route.query.quick_hash === 'string' ? this.$route.query.quick_hash : undefined
      if (nextValue === currentValue && nextQuickHash === currentQuickHash) {
        return
      }

      if (nextValue) {
        query.q = nextValue
      } else {
        delete query.q
      }
      if (nextQuickHash) {
        query.quick_hash = nextQuickHash
      } else {
        delete query.quick_hash
      }
      this.$router.replace({ query }).catch(() => {})
    },
    resetResultViewportScroll() {
      const viewport = this.$refs.resultViewport
      if (!viewport) return
      viewport.scrollTop = 0
    },
    scheduleSearch() {
      if (this.debounceTimer) {
        window.clearTimeout(this.debounceTimer)
      }

      if (!this.hasQuery) {
        this.loading = false
        this.errorMessage = ''
        this.searchResponse = createEmptySearchResponse()
        if (this.requestController) {
          this.requestController.abort()
          this.requestController = null
        }
        return
      }

      this.debounceTimer = window.setTimeout(() => {
        this.performSearch()
      }, TOP_LEVEL_PAGE_STANDARD.searchDebounceMs)
    },
    async performSearch() {
      const { modeInfo, params } = buildSearchRequestParams(this.rawQuery, { quickHash: this.fileQuickHash })
      if (!modeInfo.normalizedQuery) {
        return
      }

      if (modeInfo.validationError) {
        this.loading = false
        this.searchResponse = createEmptySearchResponse()
        this.errorMessage = modeInfo.validationError
        return
      }

      if (this.requestController) {
        this.requestController.abort()
      }
      const controller = new AbortController()
      this.requestController = controller
      this.loading = true
      this.errorMessage = ''
      this.resultViewportScrollTop = 0

      try {
        params.set('limit', String(TOP_LEVEL_PAGE_STANDARD.searchResultLimit))
        const response = await fetch(`${API_BASE}/api/search/images?${params.toString()}`, {
          signal: controller.signal,
        })
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }
        const payload = await response.json()
        if (controller.signal.aborted) {
          return
        }
        this.searchResponse = {
          ...createEmptySearchResponse(),
          ...payload,
        }
        this.previewRepairQueue = []
        this.previewRepairAttemptTokens = {}
        this.$nextTick(() => {
          this.installResultResizeObserver()
          this.refreshResultViewportMetrics()
          this.resetResultViewportScroll()
        })
      } catch (error) {
        if (error?.name === 'AbortError') {
          return
        }
        this.searchResponse = createEmptySearchResponse()
        this.errorMessage = '搜索接口不可用，请确认前后端服务均已启动。'
      } finally {
        if (this.requestController === controller) {
          this.requestController = null
        }
        if (!controller.signal.aborted) {
          this.loading = false
        }
      }
    },
    triggerFilePicker() {
      const input = this.$refs.fileInput
      if (!input) return
      input.value = ''
      input.click()
    },
    async handleFileSelection(event) {
      const file = event?.target?.files?.[0]
      event.target.value = ''
      if (!file) return

      if (this.requestController) {
        this.requestController.abort()
      }
      const controller = new AbortController()
      this.requestController = controller
      this.loading = true
      this.errorMessage = ''
      this.closeSearchDetail()

      try {
        const formData = new FormData()
        formData.append('file', file, file.name)
        const response = await fetch(`${API_BASE}/api/search/by-file?limit=${TOP_LEVEL_PAGE_STANDARD.searchResultLimit}`, {
          method: 'POST',
          body: formData,
          signal: controller.signal,
        })
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }
        const payload = await response.json()
        if (controller.signal.aborted) {
          return
        }
        this.fileQuickHash = String(payload?.quick_hash || '').trim()
        this.fileTokenFromPicker = `file:${file.name}`
        this.searchResponse = {
          ...createEmptySearchResponse(),
          ...payload,
        }
        this.previewRepairQueue = []
        this.previewRepairAttemptTokens = {}
        this.skipNextScheduledSearch = true
        this.rawQuery = this.fileTokenFromPicker
        this.$nextTick(() => {
          this.installResultResizeObserver()
          this.refreshResultViewportMetrics()
          this.resetResultViewportScroll()
        })
      } catch (error) {
        if (error?.name === 'AbortError') {
          return
        }
        this.searchResponse = createEmptySearchResponse()
        this.fileQuickHash = ''
        this.fileTokenFromPicker = ''
        this.errorMessage = '本地图片 quick hash 搜索失败，请确认后端服务正常运行。'
      } finally {
        if (this.requestController === controller) {
          this.requestController = null
        }
        if (!controller.signal.aborted) {
          this.loading = false
        }
      }
    },
    openTimeRangeDialog() {
      this.timeDialogVisible = true
    },
    closeTimeRangeDialog() {
      this.timeDialogVisible = false
    },
    applyTimeRangeQuery(payload) {
      if (!payload?.queryText) return
      this.fileQuickHash = ''
      this.fileTokenFromPicker = ''
      this.rawQuery = buildTimeRangeQuery(payload.fieldType, payload.startText, payload.endText) || payload.queryText
      this.timeDialogVisible = false
    },
    installResultResizeObserver() {
      const viewport = this.$refs.resultViewport
      if (!viewport || typeof ResizeObserver === 'undefined') return
      if (!this.resultResizeObserver) {
        this.resultResizeObserver = new ResizeObserver(() => {
          this.refreshResultViewportMetrics()
        })
      }
      this.resultResizeObserver.disconnect()
      this.resultResizeObserver.observe(viewport)
      this.refreshResultViewportMetrics()
    },
    refreshResultViewportMetrics() {
      const viewport = this.$refs.resultViewport
      const nextWidth = viewport?.clientWidth || 0
      const nextHeight = viewport?.clientHeight || 0
      this.resultViewportWidth = nextWidth
      this.resultViewportHeight = nextHeight
    },
    handleResultViewportScroll(event) {
      this.resultViewportScrollTop = event?.target?.scrollTop || 0
    },
    handleWindowResize() {
      this.viewportWidth = typeof window !== 'undefined' ? window.innerWidth : this.viewportWidth
      this.viewportHeight = typeof window !== 'undefined' ? window.innerHeight : this.viewportHeight
      this.refreshResultViewportMetrics()
    },
    canOpenBrowseLocation(item) {
      return Boolean(buildBrowseLocation(item?.media_rel_path, { focusId: item?.id }))
    },
    openSearchDetail(item) {
      if (!item) return
      this.detailItem = item
      this.detailVisible = true
    },
    closeSearchDetail() {
      this.detailVisible = false
      this.detailItem = null
    },
    openSearchResultsPage() {
      if (!this.hasQuery) return
      const query = { q: this.rawQuery }
      if (this.modeInfo.mode === 'file' && this.fileQuickHash) {
        query.quick_hash = this.fileQuickHash
      }
      this.$router.push({
        path: '/search/results',
        query,
      }).catch(() => {})
    },
    openBrowseLocation(item) {
      const target = buildBrowseLocation(item?.media_rel_path, { focusId: item?.id })
      if (!target) {
        return
      }
      this.closeSearchDetail()
      this.$router.push(target).catch(() => {})
    },
    openDetailPrimaryAction() {
      if (!this.detailItem) return
      this.openBrowseLocation(this.detailItem)
    },
    openDetailSecondaryAction() {
      const originalUrl = this.buildOriginalMediaUrl(this.detailItem?.media_rel_path)
      if (!originalUrl || typeof window === 'undefined') return
      window.open(originalUrl, '_blank', 'noopener')
    },
    onDetailPreviewError() {
      // Keep the detail overlay open and fall back to the built-in skeleton.
    },
  },
}
</script>

<style scoped lang="css">
.top-level-page {
  @apply flex flex-col gap-6;
}

.search-page {
  min-height: 0;
}

.search-page__shell {
  display: flex;
  flex-direction: column;
  min-height: calc(100dvh - 5rem);
  height: calc(100dvh - 5rem);
  gap: 1rem;
}

.search-page__top-shell {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  flex: 0 0 auto;
}

.search-page__result-shell {
  display: flex;
  flex: 1 1 auto;
  min-height: 0;
}

.search-page__mode-pill {
  @apply rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700;
}

.search-bar {
  @apply flex items-center gap-3 rounded-[1.7rem] border border-slate-200 bg-white px-4 py-3 shadow-sm;
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.05);
}

.search-bar__icon {
  @apply text-lg leading-none text-slate-400;
}

.search-bar__input {
  @apply min-w-0 flex-1 border-0 bg-transparent p-0 text-base text-slate-900 outline-none;
}

.search-bar__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.55rem;
  align-items: center;
}

.search-bar__tool,
.search-bar__clear {
  @apply rounded-full border text-xs font-semibold transition;
}

.search-bar__tool {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  min-height: 2.15rem;
  padding: 0.4rem 0.82rem;
  border-color: rgba(167, 243, 208, 0.96);
  background: rgba(236, 253, 245, 0.92);
  color: #047857;
}

.search-bar__tool:hover {
  border-color: rgba(110, 231, 183, 0.96);
  background: rgba(220, 252, 231, 0.98);
  color: #065f46;
}

.search-bar__tool:focus-visible,
.search-bar__clear:focus-visible {
  outline: 2px solid rgba(16, 185, 129, 0.28);
  outline-offset: 2px;
}

.search-bar__tool-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1rem;
  height: 1rem;
  font-size: 0.85rem;
  line-height: 1;
}

.search-bar__tool-label {
  font-size: 0.76rem;
  line-height: 1;
  letter-spacing: 0.01em;
  white-space: nowrap;
}

.search-bar__clear {
  @apply border-slate-200 text-slate-500 hover:bg-slate-100;
  min-height: 2.3rem;
  padding: 0.45rem 0.9rem;
}

.search-page__file-input {
  display: none;
}

.search-page__hints {
  @apply flex flex-wrap gap-2 text-xs text-slate-500;
}

.search-page__hint {
  @apply rounded-full bg-slate-100 px-3 py-1;
}

.search-empty {
  @apply flex min-h-[260px] w-full flex-1 flex-col items-center justify-center rounded-[1.8rem] border border-dashed border-slate-300 bg-slate-50 px-6 py-16 text-center text-sm text-slate-500;
}

.search-empty--error {
  @apply border-rose-200 bg-rose-50 text-rose-600;
}

.search-empty__icon {
  @apply mb-3 block text-5xl leading-none;
}

.search-result-preview {
  display: flex;
  flex: 1 1 auto;
  min-height: 0;
  flex-direction: column;
  gap: 0.9rem;
  width: 100%;
  padding: 1rem;
  border: 1px solid rgba(16, 185, 129, 0.18);
  border-radius: 1.8rem;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.98)),
    radial-gradient(circle at top right, rgba(16, 185, 129, 0.08), transparent 40%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.74);
}

.search-result-preview__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.search-result-preview__header-main {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.3rem;
}

.search-result-preview__title {
  @apply m-0 text-lg font-semibold text-slate-900;
}

.search-result-preview__subtitle {
  @apply m-0 text-sm text-slate-500;
}

.search-result-preview__open-all {
  @apply rounded-full border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-700 transition-colors;
}

.search-result-preview__open-all:hover:not(:disabled) {
  @apply bg-emerald-100 text-emerald-800;
}

.search-result-preview__open-all:disabled {
  @apply cursor-not-allowed opacity-60;
}

.search-result-preview__summary-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.search-result-preview__summary-pill {
  @apply inline-flex items-center rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-600;
}

.search-result-preview__summary-pill--accent {
  @apply border-emerald-100 bg-emerald-50 text-emerald-700;
}

.search-result-preview__viewport {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding-right: 0.2rem;
}

.search-result-virtual {
  position: relative;
  width: 100%;
}

.search-result-virtual__window {
  position: absolute;
  top: 0;
  left: 50%;
  will-change: transform;
}

.search-result-grid {
  display: grid;
  gap: 1.5rem;
  justify-content: center;
  align-content: start;
  margin: 0 auto;
}

.search-result-card {
  aspect-ratio: 1 / 1;
}

.search-result-card__body {
  @apply flex h-full w-full flex-col justify-between p-4 text-left;
  min-height: 0;
}

.search-result-card__badges {
  @apply flex flex-wrap gap-2;
  align-self: flex-start;
}

.search-result-card__badge {
  @apply rounded-full px-2.5 py-1 text-[11px] font-medium tracking-[0.04em] text-white;
  background: rgba(15, 23, 42, 0.72);
  border: 1px solid rgba(255, 255, 255, 0.16);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.14);
}

.search-result-card__meta {
  display: flex;
  min-height: 0;
  flex-direction: column;
  gap: 0.72rem;
  padding: 0.9rem;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 1.25rem;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.82), rgba(15, 23, 42, 0.72));
  color: #ffffff;
  box-shadow: 0 16px 30px rgba(15, 23, 42, 0.22);
}

.search-result-card__copy {
  display: flex;
  min-height: 0;
  flex-direction: column;
  gap: 0.28rem;
}

.search-result-card__title {
  @apply m-0 text-sm font-semibold leading-snug;
  display: -webkit-box;
  line-clamp: 2;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.search-result-card__path {
  @apply m-0 text-xs text-white/75;
  display: -webkit-box;
  line-clamp: 2;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-all;
}

.search-result-card__tag-wrap {
  min-height: 1.5rem;
  max-height: 3.45rem;
  overflow: hidden;
}

.search-result-card__tag-list :deep(.tag-chip) {
  background: rgba(255, 255, 255, 0.96) !important;
  color: #0f172a !important;
  border-color: rgba(226, 232, 240, 0.92) !important;
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.12);
}

.search-result-card__tag-placeholder {
  @apply text-xs text-white/60;
}

.search-result-card__actions {
  @apply flex gap-2;
  flex-wrap: wrap;
}

.search-result-card__action {
  @apply rounded-full border px-3 py-1 text-xs font-semibold transition;
  border-color: rgba(255, 255, 255, 0.18);
  background: rgba(255, 255, 255, 0.18);
  color: #ffffff;
}

.search-result-card__action:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.28);
}

.search-result-card__action--ghost {
  background: transparent;
}

.search-result-card__action:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

@media (max-width: 900px) {
  .search-page__result-shell {
    min-height: 0;
  }

  .search-result-preview__header {
    flex-direction: column;
  }
}

@media (max-width: 640px) {
  .search-bar {
    align-items: flex-start;
  }

  .search-bar__actions {
    width: 100%;
    justify-content: flex-start;
  }

  .search-bar__tool {
    flex: 0 0 auto;
  }

  .search-result-preview,
  .search-bar {
    border-radius: 1.4rem;
  }
}
</style>