<template>
  <section class="top-level-page search-page" :style="pageVars">
    <div class="search-page__shell">
      <div class="search-page__top-shell">
        <TopLevelPageHeader
          title="搜索"
          subtitle="单输入统一搜索文件名、Tag，或直接输入图片路径后按 quick hash 反查。"
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
            placeholder="输入文件名，name:文件名，tag:角色名，或 media/2024-01/example.jpg"
            @keyup.esc="clearSearch"
          >
          <button v-if="rawQuery" type="button" class="search-bar__clear" @click="clearSearch">清空</button>
        </label>

        <div class="search-page__hints">
          <span class="search-page__hint">默认：文件名 + Tag 混合匹配</span>
          <span class="search-page__hint">文件名：<strong>name:文件名</strong> 或 <strong>$文件名</strong></span>
          <span class="search-page__hint">Tag：<strong>tag:角色名</strong> 或 <strong>#角色名</strong></span>
          <span class="search-page__hint">路径：<strong>path:media/2024-01/a.jpg</strong></span>
        </div>

        <div v-if="hasQuery" class="search-page__status-panel">
          <div class="search-page__status-copy">
            <span class="search-page__status-kicker">搜索结果</span>
            <strong class="search-page__status-main">{{ resultSummary }}</strong>
            <p class="search-page__status-note">一级页面仅显示当前布局下的前 3 行预览，完整结果可进入二级页面。</p>
          </div>
          <div class="search-page__status-meta">
            <span class="search-page__status-pill">预览 {{ previewResults.length }} / {{ searchResponse.total || 0 }}</span>
            <span v-if="searchResponse.quick_hash" class="search-page__status-pill">Quick Hash：{{ shortQuickHash }}</span>
          </div>
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
          <p>输入后立即搜索。普通文本默认匹配文件名与 Tag；name: 或 $ 可切换为仅文件名搜索；路径会切换为 quick hash 反查。</p>
        </div>

        <div v-else-if="!searchResponse.items.length" class="search-empty">
          <span class="search-empty__icon">∅</span>
          <p>{{ emptyStateText }}</p>
        </div>

        <section v-else ref="resultViewport" class="search-result-preview">
          <header class="search-result-preview__header">
            <div class="search-result-preview__header-main">
              <h3 class="search-result-preview__title">搜索结果</h3>
              <p class="search-result-preview__subtitle">
                当前按 {{ effectiveModeLabel }} 预览前 {{ SEARCH_PREVIEW_ROWS }} 行，点击卡片先查看详情，再选择定位或查看原图。
              </p>
            </div>
            <button
              class="search-result-preview__open-all"
              type="button"
              :disabled="!previewResults.length"
              @click="openSearchResultsPage"
            >
              查看全部
            </button>
          </header>

          <div class="search-result-preview__summary-row">
            <span class="search-result-preview__summary-pill">当前列数：{{ previewColumnCount }}</span>
            <span class="search-result-preview__summary-pill">一级预览：{{ previewResults.length }} 张</span>
            <span v-if="hasMoreResults" class="search-result-preview__summary-pill search-result-preview__summary-pill--accent">
              还有 {{ hiddenResultCount }} 条结果在二级页中显示
            </span>
          </div>

          <div class="search-result-preview__viewport">
            <div class="search-result-grid">
              <ThumbCard
                v-for="item in previewResults"
                :key="item.id"
                :src="resolvedSearchPreviewUrl(item)"
                class="search-result-card"
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
  </section>
</template>

<script>
import LoadingSpinner from '../components/LoadingSpinner.vue'
import SelectionDetailOverlay from '../components/SelectionDetailOverlay.vue'
import TagChipList from '../components/TagChipList.vue'
import ThumbCard from '../components/ThumbCard.vue'
import TopLevelPageHeader from './TopLevelPageHeader.vue'
import {
  API_BASE,
  TOP_LEVEL_PAGE_STANDARD,
  buildBrowseLocation,
  buildOriginalMediaUrl,
  detectSearchMode,
  formatMatchedByLabel,
  formatSearchModeLabel,
  resolvePreviewUrl,
  shortenQuickHash,
  topLevelPageVars,
} from './topLevelPageConvention'

const SEARCH_PREVIEW_ROWS = 3
const SEARCH_GRID_GAP_PX = 24

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

export default {
  name: 'SearchPage',
  components: {
    LoadingSpinner,
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
      resultResizeObserver: null,
      viewportWidth: typeof window !== 'undefined' ? window.innerWidth : 0,
      viewportHeight: typeof window !== 'undefined' ? window.innerHeight : 0,
      detailVisible: false,
      detailItem: null,
    }
  },
  computed: {
    SEARCH_PREVIEW_ROWS() {
      return SEARCH_PREVIEW_ROWS
    },
    pageVars() {
      return topLevelPageVars()
    },
    modeInfo() {
      return detectSearchMode(this.rawQuery)
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
    resultSummary() {
      if (!this.hasQuery) return ''
      const total = Number(this.searchResponse.total || 0)
      if (this.modeInfo.mode === 'path' && this.searchResponse.quick_hash) {
        return `已按路径解析并用 quick hash 找到 ${total} 条结果`
      }
      return `共找到 ${total} 条结果`
    },
    shortQuickHash() {
      return shortenQuickHash(this.searchResponse.quick_hash)
    },
    emptyStateText() {
      if (this.modeInfo.mode === 'path') {
        return '未找到该路径对应的图片，或该图片当前不在可见范围内。'
      }
      if (this.modeInfo.mode === 'filename') {
        return '没有匹配结果。可以尝试更短的文件名，或切回普通文本做文件名 + Tag 混合搜索。'
      }
      return '没有匹配结果。可以尝试更短的文件名、name: / $ 文件名专搜、tag: 前缀，或直接输入 media 路径。'
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
    previewItemLimit() {
      return Math.max(SEARCH_PREVIEW_ROWS, this.previewColumnCount * SEARCH_PREVIEW_ROWS)
    },
    previewResults() {
      return this.searchResponse.items.slice(0, this.previewItemLimit)
    },
    hasMoreResults() {
      return Number(this.searchResponse.total || 0) > this.previewResults.length
    },
    hiddenResultCount() {
      return Math.max(0, Number(this.searchResponse.total || 0) - this.previewResults.length)
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
        },
      ]
    },
    detailNameField() {
      return createDetailField(this.detailItem?.name || '未命名图片')
    },
    detailCategoryField() {
      const categoryId = Number(this.detailItem?.category_id)
      return createDetailField(Number.isInteger(categoryId) && categoryId > 0 ? `#${categoryId}` : '')
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
  },
  watch: {
    rawQuery() {
      this.syncRouteQuery()
      this.scheduleSearch()
    },
    '$route.query.q': {
      immediate: true,
      handler(value) {
        const nextValue = typeof value === 'string' ? value : ''
        if (nextValue !== this.rawQuery) {
          this.rawQuery = nextValue
        }
      },
    },
  },
  mounted() {
    this.installResultResizeObserver()
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
    this.resultResizeObserver?.disconnect?.()
    window.removeEventListener('resize', this.handleWindowResize)
  },
  methods: {
    resolvePreviewUrl,
    buildOriginalMediaUrl,
    formatMatchedByLabel,
    resolvedSearchPreviewUrl(item) {
      return this.resolvePreviewUrl(item) || this.buildOriginalMediaUrl(item?.media_rel_path)
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
        ? item.matched_by.map(value => this.formatMatchedByLabel(value)).filter(Boolean)
        : []
      return labels.join(' · ')
    },
    clearSearch() {
      this.rawQuery = ''
      this.errorMessage = ''
      this.searchResponse = createEmptySearchResponse()
      this.closeSearchDetail()
      if (this.requestController) {
        this.requestController.abort()
        this.requestController = null
      }
      if (this.debounceTimer) {
        window.clearTimeout(this.debounceTimer)
        this.debounceTimer = null
      }
    },
    syncRouteQuery() {
      const nextValue = this.rawQuery || undefined
      const currentValue = typeof this.$route.query.q === 'string' ? this.$route.query.q : undefined
      if (nextValue === currentValue) {
        return
      }

      const query = { ...this.$route.query }
      if (nextValue) {
        query.q = nextValue
      } else {
        delete query.q
      }
      this.$router.replace({ query }).catch(() => {})
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
      const { mode, normalizedQuery } = this.modeInfo
      if (!normalizedQuery) {
        return
      }

      if (this.requestController) {
        this.requestController.abort()
      }
      const controller = new AbortController()
      this.requestController = controller
      this.loading = true
      this.errorMessage = ''

      try {
        const params = new URLSearchParams({
          q: normalizedQuery,
          mode,
          limit: String(TOP_LEVEL_PAGE_STANDARD.searchResultLimit),
        })
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
        this.$nextTick(() => {
          this.installResultResizeObserver()
          this.refreshResultViewportMetrics()
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
      if (Math.abs(nextWidth - this.resultViewportWidth) > 1) {
        this.resultViewportWidth = nextWidth
      }
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
      this.$router.push({
        path: '/search/results',
        query: { q: this.rawQuery },
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

.search-bar__clear {
  @apply rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-500 transition hover:bg-slate-100;
}

.search-page__hints {
  @apply flex flex-wrap gap-2 text-xs text-slate-500;
}

.search-page__hint {
  @apply rounded-full bg-slate-100 px-3 py-1;
}

.search-page__status-panel {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1.15rem;
  border: 1px solid rgba(16, 185, 129, 0.18);
  border-radius: 1.5rem;
  background:
    linear-gradient(135deg, rgba(236, 253, 245, 0.96), rgba(255, 255, 255, 0.96)),
    radial-gradient(circle at top right, rgba(16, 185, 129, 0.12), transparent 42%);
}

.search-page__status-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.22rem;
}

.search-page__status-kicker {
  @apply text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700;
}

.search-page__status-main {
  @apply text-base font-semibold text-slate-900;
}

.search-page__status-note {
  @apply m-0 text-sm text-slate-600;
}

.search-page__status-meta {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.55rem;
}

.search-page__status-pill {
  @apply inline-flex items-center rounded-full border border-emerald-100 bg-white/85 px-3 py-1 text-xs font-semibold text-slate-600;
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

.search-result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, var(--top-level-thumb-edge)), var(--top-level-thumb-edge)));
  gap: 1.5rem;
  justify-content: center;
  align-content: start;
}

.search-result-card {
  width: min(100%, var(--top-level-thumb-edge));
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

  .search-result-preview__header,
  .search-page__status-panel {
    flex-direction: column;
  }

  .search-page__status-meta {
    justify-content: flex-start;
  }
}

@media (max-width: 640px) {
  .search-result-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .search-result-card {
    width: 100%;
  }

  .search-result-preview,
  .search-page__status-panel,
  .search-bar {
    border-radius: 1.4rem;
  }
}
</style>