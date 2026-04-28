<template>
  <section class="page" :class="{ 'page--paged': isPagedBrowseMode }">
    <TrashPageHeader
      :item-count="totalCount"
      :sort-by="sortBy"
      :sort-dir="sortDir"
      :clear-disabled="actionBusy || !totalCount"
      @back="goBack"
      @clear-trash="clearTrash"
      @update:sortBy="onSortModeSelect"
      @toggle-sort-dir="toggleSortDir"
    >
      <div class="vm-btns" role="group" aria-label="视图模式">
        <button
          class="vm-btn"
          :class="{ active: viewMode === 'grid' }"
          title="瀑布流"
          @click="switchViewMode('grid')"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <rect x="1" y="1" width="5" height="5" rx="1" fill="currentColor"/>
            <rect x="8" y="1" width="5" height="5" rx="1" fill="currentColor"/>
            <rect x="1" y="8" width="5" height="5" rx="1" fill="currentColor"/>
            <rect x="8" y="8" width="5" height="5" rx="1" fill="currentColor"/>
          </svg>
        </button>
        <button
          class="vm-btn"
          :class="{ active: viewMode === 'list' }"
          title="列表显示"
          @click="switchViewMode('list')"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <rect x="1" y="2" width="12" height="2" rx="1" fill="currentColor"/>
            <rect x="1" y="6" width="12" height="2" rx="1" fill="currentColor"/>
            <rect x="1" y="10" width="12" height="2" rx="1" fill="currentColor"/>
          </svg>
        </button>
        <button
          class="vm-btn"
          :class="{ active: selectionMode }"
          :title="selectionMode ? '退出选择模式' : '进入选择模式'"
          :aria-pressed="selectionMode ? 'true' : 'false'"
          @click="toggleSelectionMode()"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M3 1L3 11L6 8.5L8 13L9.5 12.3L7.5 7.8L11 7.8Z" fill="currentColor"/>
          </svg>
        </button>
      </div>
    </TrashPageHeader>

    <p v-if="messageText" class="page-note" :class="messageType === 'error' ? 'page-note--error' : 'page-note--success'">
      {{ messageText }}
    </p>

    <div ref="pageMain" class="page-main">
      <LoadingSpinner v-if="loading" />

      <div v-else-if="!items.length" class="empty-hint">
        <span class="empty-hint__icon">🗑</span>
        <p>回收站为空。</p>
      </div>

      <div v-else-if="selectionMode && viewMode === 'grid'" ref="itemGrid" class="selection-grid" :style="selectionGridStyle">
        <div
          v-for="entry in visibleSelectionEntries"
          :key="itemKey(entry.item, entry.index)"
          class="selection-wrap"
          :class="{ 'is-selected': isItemSelected(entry.item, entry.index), 'is-disabled': isItemDisabled(entry.item) }"
          :data-index="entry.index"
          :data-select-index="entry.index"
          @pointerdown="onSelectionPointerDown($event, entry.item, entry.index)"
        >
          <MediaItemCard
            :src="resolvedUrl(entry.item)"
            :alt="entry.item.name || ''"
            :info-text="entry.item.name || '未命名'"
            info-title="回收站项目"
            :item-type="entry.item.type"
            :selected="isItemSelected(entry.item, entry.index)"
            :disabled="isItemDisabled(entry.item)"
            @toggle-select="onItemSelectionButtonClick(entry.item, entry.index)"
            @toggle-info="noop"
            @details="openDetailsForItem(entry.item, entry.index)"
          />
        </div>
      </div>

      <div v-else-if="viewMode === 'list'" ref="itemGrid" class="list-view" :style="listViewStyle">
        <div
          v-for="entry in visibleListEntries"
          :key="entry.item.entry_key || entry.item.id || entry.index"
          class="list-row"
          :class="{
            'list-row--selecting': selectionMode,
            'is-selected': isItemSelected(entry.item, entry.index),
            'is-disabled': isItemDisabled(entry.item),
          }"
          :data-index="entry.index"
          :data-select-index="entry.index"
          @pointerdown="onListPointerDown($event, entry.item, entry.index)"
          @click="onListRowClick($event, entry.item, entry.index)"
        >
          <button
            v-if="selectionMode"
            class="list-pick"
            type="button"
            :disabled="isItemDisabled(entry.item)"
            :aria-pressed="isItemSelected(entry.item, entry.index) ? 'true' : 'false'"
            :aria-label="isItemSelected(entry.item, entry.index) ? '取消选择' : '选择项目'"
            @pointerdown.stop
            @click.stop="onItemSelectionButtonClick(entry.item, entry.index)"
          >
            <span v-if="isItemSelected(entry.item, entry.index)" class="list-pick__mark">✓</span>
          </button>
          <div class="list-thumb-wrap">
            <div v-if="!resolvedUrl(entry.item)" class="list-thumb-skeleton" />
            <img
              v-else
              :src="resolvedUrl(entry.item)"
              class="list-thumb-img"
              :alt="entry.item.name || ''"
              @load="onImgLoad(entry.item, $event)"
            />
          </div>
          <div class="list-main">
            <div class="list-title-row">
              <span v-if="entry.item.type === 'album'" class="list-type-pill">ALB</span>
              <span class="list-name">{{ entry.item.name || '未命名' }}</span>
            </div>
          </div>
        </div>
      </div>

      <div
        v-else-if="viewMode === 'grid' && !isPortraitMasonryMode"
        ref="itemGrid"
        class="photo-grid"
        :style="photoGridStyle"
      >
        <div
          v-for="(row, rowIndex) in activePhotoRows"
          :key="rowIndex"
          class="jl-row"
          :style="{ height: row.height + 'px' }"
        >
          <div
            v-for="item in row.items"
            :key="item.entry_key || item.id || item._idx"
            class="photo-wrap"
            :data-index="item._idx"
            :style="{ width: item.computedWidth + 'px' }"
          >
            <div v-if="!resolvedUrl(item)" class="photo-skeleton">
              <span class="skeleton-label">...</span>
            </div>

            <div v-else class="photo-card" @click="openDetailsForItem(item, item._idx)">
              <img
                :src="resolvedUrl(item)"
                class="photo-img"
                loading="lazy"
                :alt="item.name || ''"
                @load="onImgLoad(item, $event)"
              />
              <div v-if="item.type === 'album'" class="album-badge">
                <span class="badge-icon">📁</span>
                <span class="badge-name">{{ item.name }}</span>
                <span class="badge-count">{{ item.photo_count || 0 }} 张</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div
        v-else-if="viewMode === 'grid' && isPortraitMasonryMode && !masonrySkeletonReady"
        ref="itemGrid"
        class="photo-grid photo-grid--masonry-skeleton"
      >
        <div class="masonry-skeleton-col">
          <div v-for="h in [120, 180, 100, 200]" :key="h" class="photo-skeleton masonry-skeleton-item" :style="{ height: h + 'px' }" />
        </div>
        <div class="masonry-skeleton-col">
          <div v-for="h in [160, 100, 220, 140]" :key="h" class="photo-skeleton masonry-skeleton-item" :style="{ height: h + 'px' }" />
        </div>
      </div>

      <div
        v-else
        ref="itemGrid"
        class="photo-grid photo-grid--masonry"
        :style="masonryGridStyle"
      >
        <div
          v-for="item in activeMasonryPlacements"
          :key="item.entry_key || item.id || item._idx"
          class="photo-wrap photo-wrap--masonry"
          :data-index="item._idx"
          :style="{
            left: item.col * (masonryColWidth + 6) + 'px',
            top: item.top + 'px',
            width: item.computedWidth + 'px',
            height: item.computedHeight + 'px',
          }"
          @click="openDetailsForItem(item, item._idx)"
        >
          <div v-if="!resolvedUrl(item)" class="photo-skeleton">
            <span class="skeleton-label">...</span>
          </div>
          <div v-else class="photo-card">
            <img
              :src="resolvedUrl(item)"
              class="photo-img"
              loading="lazy"
              :alt="item.name || ''"
              @load="onImgLoad(item, $event)"
            />
            <div v-if="item.type === 'album'" class="album-badge">
              <span class="badge-icon">📁</span>
              <span class="badge-name">{{ item.name }}</span>
              <span class="badge-count">{{ item.photo_count || 0 }} 张</span>
            </div>
          </div>
        </div>
      </div>

      <div
        v-if="isPagedBrowseMode && items.length"
        ref="paginationHost"
        class="page-pagination-host"
        :class="{ 'page-pagination-host--selection': selectionMode }"
      >
        <PagePaginationBar
          :current-page="activePaginationConfig.currentPage"
          :total-pages="activePaginationConfig.totalPages"
          :page-size="activePaginationConfig.pageSize"
          :page-size-options="activePaginationConfig.pageSizeOptions"
          @update:page="onPaginationPageChange"
          @update:pageSize="onPaginationPageSizeChange"
        />
      </div>
    </div>

    <SelectionIsland
      v-if="selectionMode"
      :floating-style="selectionIslandStyle"
      collapse-label="收起选择操作"
      expand-label="展开选择操作"
      @collapsed-change="onSelectionIslandCollapsedChange"
    >
      <span class="selection-island__count">{{ selectionSummaryText }}</span>
      <button class="selection-island__btn" type="button" :disabled="!selectedCount || actionBusy" @click="openSelectionDetails">详情</button>
      <button class="selection-island__btn" type="button" :disabled="!selectedCount || actionBusy" @click="restoreSelection">还原</button>
      <button class="selection-island__btn selection-island__btn--danger" type="button" :disabled="!selectedCount || actionBusy" @click="hardDeleteSelection">删除</button>
      <div
        ref="selectionIslandMenu"
        class="selection-island__menu-wrap"
        :class="{ 'is-open': selectAllMenuOpen }"
      >
        <button
          class="selection-island__btn"
          type="button"
          :disabled="!items.length || actionBusy"
          :aria-expanded="hasMixedSelectableTypes ? (selectAllMenuOpen ? 'true' : 'false') : 'false'"
          @click="handleSelectAllButtonClick"
        >全选</button>
        <div v-if="hasMixedSelectableTypes" class="selection-island__submenu">
          <button class="selection-island__submenu-btn" type="button" @click="onSelectAllTypeClick('album')">相册</button>
          <button class="selection-island__submenu-btn" type="button" @click="onSelectAllTypeClick('image')">图片</button>
        </div>
      </div>
      <button class="selection-island__btn" type="button" :disabled="actionBusy" @click="clearSelection">取消选择</button>
    </SelectionIsland>

    <SelectionDetailOverlay
      :visible="selectionDetailsOpen"
      :layer-style="selectionDetailsBounds"
      :panel-style="selectionDetailsPanelStyle"
      :preview-items="selectionDetailPreviewItems"
      :is-multi="selectionDetailPreviewItems.length > 1"
      :name-field="selectionDetailNameField"
      :category-field="selectionDetailCategoryField"
      :tags-field="selectionDetailTagsField"
      :size-field="selectionDetailSizeField"
      :size-label="selectionDetailSizeLabel"
      :imported-field="selectionDetailImportedField"
      :created-field="selectionDetailCreatedField"
      primary-action-label="还原"
      :can-open-primary-action="selectedCount > 0 && !actionBusy"
      danger-action-label="删除"
      :danger-action-disabled="actionBusy"
      :can-edit-tags="false"
      @close="closeSelectionDetails"
      @open-primary="restoreSelection"
      @delete="hardDeleteSelection"
    />

    <ConfirmationDialog
      :visible="confirmDialog.visible"
      :title="confirmDialog.title"
      :message="confirmDialog.message"
      :confirm-label="confirmDialog.confirmLabel"
      :cancel-label="confirmDialog.cancelLabel"
      :tone="confirmDialog.tone"
      :show-cancel="confirmDialog.showCancel"
      :busy="confirmDialog.busy"
      :busy-label="confirmDialog.busyLabel"
      @cancel="closeConfirmDialog"
      @confirm="handleConfirmDialogConfirm"
    />

    <ActionProgressOverlay
      :visible="actionBusy"
      :title="actionBusyTitle || '处理中'"
      :message="actionBusyText || '正在处理回收站操作，请稍候…'"
    />
  </section>
</template>

<script>
import ConfirmationDialog from '../components/ConfirmationDialog.vue'
import ActionProgressOverlay from '../components/ActionProgressOverlay.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import MediaItemCard from '../components/MediaItemCard.vue'
import PagePaginationBar from '../components/PagePaginationBar.vue'
import SelectionIsland from '../components/SelectionIsland.vue'
import SelectionDetailOverlay from '../components/SelectionDetailOverlay.vue'
import TrashPageHeader from '../components/TrashPageHeader.vue'
import { normalizeTagColors } from '../utils/tagColors'
import {
  DEFAULT_PAGE_CONFIG,
  PAGE_BROWSE_MODE_PAGED,
  PAGE_BROWSE_MODE_SCROLL,
  PAGE_CONFIG_UPDATED_EVENT,
  fetchPageConfig,
  getCachedPageConfig,
} from '../utils/pageConfig'

const API_BASE = 'http://127.0.0.1:8000'
const FIRST_ROW_TOLERANCE_PX = 12
const RESTORE_ANCHOR_PADDING_PX = 12
const DIMENSION_CORRECTION_BATCH_MS = 60
const SELECTION_INFO_HEIGHT = 56
const SELECTION_OVERSCAN_ROWS = 2
const SELECTION_LANDSCAPE_COLS = 5
const SELECTION_PORTRAIT_COLS = 3
const LANDSCAPE_SELECTION_ROWS = 2
const PORTRAIT_SELECTION_ROWS = 3
const LANDSCAPE_PHOTO_ROWS = 2
const PORTRAIT_MASONRY_COLS = 2
const PORTRAIT_MASONRY_GAP_PX = 6
const MASONRY_SKELETON_MIN_LOADED = 1
const PHOTO_GRID_MIN_TARGET_HEIGHT_PX = 140
const PHOTO_GRID_MAX_TARGET_HEIGHT_PX = 640
const SELECTION_LANDSCAPE_GAP = 16
const SELECTION_PORTRAIT_GAP = 12
const PHOTO_GRID_GAP_PX = 4
const PHOTO_GRID_TARGET_HEIGHT_PX = 440
const MIN_PAGED_PHOTO_ROWS = 2
const MIN_PAGED_SELECTION_ROWS = 2
const PAGED_GRID_BOTTOM_RESERVE_PX = 12
const PAGED_LIST_BOTTOM_RESERVE_PX = 12
const PAGE_SECTION_GAP_PX = 10
const LONG_PRESS_MS = 220
const LIST_ROW_HEIGHT = 62
const LIST_OVERSCAN_ROWS = 12
const DEFAULT_LIST_PAGE_SIZE = 20
const LIST_PAGE_SIZE_OPTIONS = Object.freeze([10, 20, 50, 100])
const JUSTIFIED_LAYOUT_CACHE = new Map()
const JUSTIFIED_LAYOUT_CACHE_LIMIT = 36

function rememberJustifiedLayout(cacheKey, rows) {
  if (JUSTIFIED_LAYOUT_CACHE.has(cacheKey)) {
    JUSTIFIED_LAYOUT_CACHE.delete(cacheKey)
  }
  JUSTIFIED_LAYOUT_CACHE.set(cacheKey, rows)
  while (JUSTIFIED_LAYOUT_CACHE.size > JUSTIFIED_LAYOUT_CACHE_LIMIT) {
    const oldestKey = JUSTIFIED_LAYOUT_CACHE.keys().next().value
    JUSTIFIED_LAYOUT_CACHE.delete(oldestKey)
  }
  return rows
}

function createDialogState() {
  return {
    visible: false,
    title: '请确认操作',
    message: '',
    confirmLabel: '确认',
    cancelLabel: '取消',
    tone: 'danger',
    showCancel: true,
    busy: false,
    busyLabel: '处理中…',
    onConfirm: null,
  }
}

export default {
  name: 'TrashPage',
  components: {
    ActionProgressOverlay,
    ConfirmationDialog,
    LoadingSpinner,
    MediaItemCard,
    PagePaginationBar,
    SelectionIsland,
    SelectionDetailOverlay,
    TrashPageHeader,
  },

  data() {
    const cachedPageConfig = getCachedPageConfig()
    return {
      items: [],
      loading: true,
      sortBy: 'date',
      sortDir: 'desc',
      viewMode: 'grid',
      viewModeBeforeSelection: 'grid',
      listPageIndex: 0,
      listPageSize: DEFAULT_LIST_PAGE_SIZE,
      suppressNextListClick: false,
      pointerSelection: null,
      longPressTimer: null,
      lastScrollDirection: 'none',
      lastObservedScrollTop: typeof window !== 'undefined' ? (window.scrollY || window.pageYOffset || 0) : 0,
      containerWidth: 0,
      itemGridViewportTop: 0,
      paginationHostHeight: 0,
      imgDimensions: {},
      layoutFingerprint: '',
      pendingViewAnchor: null,
      pendingDimensionCorrections: {},
      dimensionFlushTimer: null,
      resizeObserver: null,
      pageBrowseMode: cachedPageConfig.browseMode || DEFAULT_PAGE_CONFIG.browseMode,
      photoPageIndex: 0,
      selectionGridPageIndex: 0,
      selectionMode: false,
      scrollTop: typeof window !== 'undefined' ? (window.scrollY || window.pageYOffset || 0) : 0,
      viewportHeight: typeof window !== 'undefined' ? window.innerHeight : 0,
      viewportWidth: typeof window !== 'undefined' ? window.innerWidth : 0,
      pageMainHeight: 0,
      virtualStartIndex: 0,
      virtualEndIndex: 0,
      virtualAnchorIndex: 0,
      virtualContainerTop: 0,
      selectionRowHeight: 0,
      scrollFrameId: null,
      selectedMap: {},
      selectionTypeLock: null,
      selectionAnchorIndex: null,
      selectionDetailsOpen: false,
      selectionDetailsBounds: {
        top: '0px',
        right: '0px',
        bottom: '0px',
        left: '0px',
      },
      selectionDetailsHostWidth: 0,
      selectionDetailsHostHeight: 0,
      scrollLockState: null,
      messageText: '',
      messageType: 'success',
      actionBusy: false,
      actionBusyTitle: '',
      actionBusyText: '',
      tagLookupMap: {},
      categoryDisplayMap: {},
      selectAllMenuOpen: false,
      confirmDialog: createDialogState(),
    }
  },

  computed: {
    totalCount() {
      return this.items.length
    },

    isPagedBrowseMode() {
      return this.pageBrowseMode === PAGE_BROWSE_MODE_PAGED
    },

    isPhotoGridMode() {
      return this.viewMode === 'grid' && !this.selectionMode
    },

    isSelectionGridMode() {
      return this.selectionMode && this.viewMode === 'grid'
    },

    isVirtualizedMode() {
      return !this.isPagedBrowseMode && (this.isSelectionGridMode || this.viewMode === 'list')
    },

    cacheSortSignature() {
      return `${this.sortBy}:${this.sortDir}:${this.items.length}`
    },

    isPortrait() {
      const width = this.viewportWidth || (typeof window !== 'undefined' ? window.innerWidth : 0)
      const height = this.viewportHeight || (typeof window !== 'undefined' ? window.innerHeight : 0)
      if (!width || !height) return false
      return height > width
    },
    isPortraitMasonryMode() {
      return this.isPhotoGridMode && this.isPortrait
    },
    masonryColWidth() {
      const gap = PORTRAIT_MASONRY_GAP_PX
      const width = this.containerWidth || (typeof window !== 'undefined' ? window.innerWidth : 800)
      return Math.max(60, Math.floor((width - gap * (PORTRAIT_MASONRY_COLS - 1)) / PORTRAIT_MASONRY_COLS))
    },
    masonrySkeletonReady() {
      if (!this.isPortraitMasonryMode) return true
      return Object.keys(this.imgDimensions).length >= MASONRY_SKELETON_MIN_LOADED
    },
    masonryLayout() {
      if (!this.isPortraitMasonryMode || !this.items.length) {
        return { placements: [], totalHeight: 0 }
      }
      const colWidth = this.masonryColWidth
      const gap = PORTRAIT_MASONRY_GAP_PX
      const items = this.items
      const cacheKey = `masonry|trash|${this.cacheSortSignature}|${colWidth}|${this.layoutFingerprint}`
      if (JUSTIFIED_LAYOUT_CACHE.has(cacheKey)) {
        return JUSTIFIED_LAYOUT_CACHE.get(cacheKey)
      }
      const colHeights = Array(PORTRAIT_MASONRY_COLS).fill(0)
      const placements = items.map((item, idx) => {
        const dims = this.dimensionsForItem(item)
        const itemHeight = Math.max(40, Math.round(colWidth * dims.h / dims.w))
        let col = 0
        let minH = colHeights[0]
        for (let c = 1; c < PORTRAIT_MASONRY_COLS; c++) {
          if (colHeights[c] < minH) { minH = colHeights[c]; col = c }
        }
        const top = colHeights[col]
        colHeights[col] += itemHeight + gap
        return { ...item, _idx: idx, col, top, computedWidth: colWidth, computedHeight: itemHeight }
      })
      const totalHeight = Math.max(0, Math.max(...colHeights) - gap)
      const result = { placements, totalHeight }
      return rememberJustifiedLayout(cacheKey, result)
    },
    masonryPages() {
      if (!this.isPagedBrowseMode || !this.isPortraitMasonryMode || !this.items.length) return []
      const budget = this.pagedGridHeightBudget
      const colWidth = this.masonryColWidth
      const gap = PORTRAIT_MASONRY_GAP_PX
      const items = this.items
      const pages = []
      let pageStartIdx = 0
      while (pageStartIdx < items.length) {
        const colHeights = Array(PORTRAIT_MASONRY_COLS).fill(0)
        const pagePlacements = []
        let i = pageStartIdx
        while (i < items.length) {
          const item = items[i]
          const dims = this.dimensionsForItem(item)
          const itemHeight = Math.max(40, Math.round(colWidth * dims.h / dims.w))
          let col = 0
          let minH = colHeights[0]
          for (let c = 1; c < PORTRAIT_MASONRY_COLS; c++) {
            if (colHeights[c] < minH) { minH = colHeights[c]; col = c }
          }
          const prospectiveFill = colHeights[col] + itemHeight
          if (pagePlacements.length > 0 && prospectiveFill > budget) break
          const top = colHeights[col]
          colHeights[col] += itemHeight + gap
          pagePlacements.push({ ...item, _idx: i, col, top, computedWidth: colWidth, computedHeight: itemHeight })
          i++
        }
        const totalHeight = Math.max(0, Math.max(...colHeights) - gap)
        pages.push({
          placements: pagePlacements,
          totalHeight,
          startIndex: pagePlacements[0]?._idx ?? pageStartIdx,
          endIndex: pagePlacements[pagePlacements.length - 1]?._idx ?? pageStartIdx,
        })
        pageStartIdx = i
      }
      return pages
    },
    activeMasonryPlacements() {
      if (!this.isPortraitMasonryMode) return []
      if (!this.isPagedBrowseMode) return this.masonryLayout.placements
      return this.masonryPages[this.normalizedPhotoPageIndex]?.placements || []
    },
    activeMasonryTotalHeight() {
      if (!this.isPortraitMasonryMode) return 0
      if (!this.isPagedBrowseMode) return this.masonryLayout.totalHeight
      return this.masonryPages[this.normalizedPhotoPageIndex]?.totalHeight || 0
    },
    masonryGridStyle() {
      if (!this.isPortraitMasonryMode) return null
      const height = this.isPagedBrowseMode ? this.pagedGridHeightBudget : this.activeMasonryTotalHeight
      return {
        position: 'relative',
        height: `${Math.max(100, height)}px`,
        overflow: this.isPagedBrowseMode ? 'hidden' : 'visible',
      }
    },
    photoGridRowCount() {
      return this.isPhotoGridMode && !this.isPortraitMasonryMode ? this.justifiedRows.length : 0
    },
    selectionColumnCount() {
      return this.isPortrait ? SELECTION_PORTRAIT_COLS : SELECTION_LANDSCAPE_COLS
    },
    selectionRowsPerPageTarget() {
      return this.isPortrait ? PORTRAIT_SELECTION_ROWS : LANDSCAPE_SELECTION_ROWS
    },
    pagedSelectionCardHeight() {
      const rows = this.selectionRowsPerPageTarget
      const gap = this.selectionGridGapPx
      const budget = this.pagedGridHeightBudget
      const totalGap = gap * Math.max(0, rows - 1)
      const height = (budget - totalGap) / rows
      return Math.max(SELECTION_INFO_HEIGHT + 60, Math.floor(height))
    },
    photoGridTargetHeight() {
      if (!this.isPagedBrowseMode) return PHOTO_GRID_TARGET_HEIGHT_PX
      const rows = this.isPortrait ? PORTRAIT_SELECTION_ROWS : LANDSCAPE_PHOTO_ROWS
      const budget = this.pagedGridHeightBudget
      const totalGap = PHOTO_GRID_GAP_PX * Math.max(0, rows - 1)
      const candidate = (budget - totalGap) / rows
      if (!Number.isFinite(candidate) || candidate <= 0) return PHOTO_GRID_TARGET_HEIGHT_PX
      return Math.min(
        PHOTO_GRID_MAX_TARGET_HEIGHT_PX,
        Math.max(PHOTO_GRID_MIN_TARGET_HEIGHT_PX, Math.floor(candidate)),
      )
    },

    selectionGridGapPx() {
      return this.selectionColumnCount === SELECTION_LANDSCAPE_COLS
        ? SELECTION_LANDSCAPE_GAP
        : SELECTION_PORTRAIT_GAP
    },

    effectiveSelectionRowHeight() {
      if (this.isPagedBrowseMode && this.isSelectionGridMode) {
        return this.pagedSelectionCardHeight
      }
      if (this.selectionRowHeight > 0) return this.selectionRowHeight

      const width = this.containerWidth || (typeof window !== 'undefined' ? window.innerWidth - 48 : 800)
      const totalGap = this.selectionGridGapPx * Math.max(0, this.selectionColumnCount - 1)
      const cardWidth = Math.max(0, (width - totalGap) / this.selectionColumnCount)
      return Math.max(SELECTION_INFO_HEIGHT + 80, Math.round(cardWidth + SELECTION_INFO_HEIGHT + 2))
    },

    visibleSelectionEntries() {
      const start = this.isSelectionGridMode
        ? (this.isPagedBrowseMode ? this.selectionGridPageStartIndex : this.virtualStartIndex)
        : 0
      const end = this.isSelectionGridMode
        ? (this.isPagedBrowseMode ? this.selectionGridPageEndIndex : this.virtualEndIndex)
        : this.items.length
      return this.items.slice(start, end).map((item, offset) => ({ item, index: start + offset }))
    },

    isPaginationBarVisible() {
      if (!this.isPagedBrowseMode || !this.items.length || !this.activePaginationConfig) return false
      if (this.activePaginationConfig.pageSize !== null) return true
      return Number(this.activePaginationConfig.totalPages || 0) > 1
    },

    selectionIslandStyle() {
      if (!this.selectionMode || !this.isPagedBrowseMode || !this.isPaginationBarVisible) return null
      const hostHeight = this.paginationHostHeight > 0 ? this.paginationHostHeight : 52
      return {
        bottom: `${hostHeight + 10}px`,
      }
    },

    selectionGridStyle() {
      if (!this.isSelectionGridMode) return null

      if (this.isPagedBrowseMode) {
        const rows = this.selectionRowsPerPageTarget
        const cardHeight = this.pagedSelectionCardHeight
        return {
          minHeight: `${this.pagedGridHeightBudget}px`,
          height: `${this.pagedGridHeightBudget}px`,
          overflow: 'hidden',
          alignContent: 'start',
          gridAutoRows: `${cardHeight}px`,
          gridTemplateRows: `repeat(${rows}, ${cardHeight}px)`,
        }
      }

      const totalRows = Math.ceil(this.items.length / this.selectionColumnCount)
      const startRow = Math.floor(this.virtualStartIndex / this.selectionColumnCount)
      const endRow = Math.ceil(this.virtualEndIndex / this.selectionColumnCount)
      const visibleRows = Math.max(0, endRow - startRow)
      const rowHeight = this.effectiveSelectionRowHeight
      const gap = this.selectionGridGapPx
      const totalHeight = totalRows
        ? totalRows * rowHeight + Math.max(0, totalRows - 1) * gap
        : 0
      const paddingTop = startRow * (rowHeight + gap)
      const renderedHeight = visibleRows
        ? visibleRows * rowHeight + Math.max(0, visibleRows - 1) * gap
        : 0

      return {
        paddingTop: `${paddingTop}px`,
        paddingBottom: `${Math.max(0, totalHeight - paddingTop - renderedHeight)}px`,
      }
    },

    visibleListEntries() {
      const start = this.viewMode === 'list'
        ? (this.isPagedBrowseMode ? this.listPageStartIndex : this.virtualStartIndex)
        : 0
      const end = this.viewMode === 'list'
        ? (this.isPagedBrowseMode ? this.listPageEndIndex : this.virtualEndIndex)
        : this.items.length
      return this.items.slice(start, end).map((item, offset) => ({ item, index: start + offset }))
    },

    listViewStyle() {
      if (this.viewMode !== 'list') return null
      if (this.isPagedBrowseMode) {
        return {
          minHeight: `${this.pagedListHeightBudget}px`,
          height: `${this.pagedListHeightBudget}px`,
          overflow: 'hidden',
        }
      }
      return {
        paddingTop: `${this.virtualStartIndex * LIST_ROW_HEIGHT}px`,
        paddingBottom: `${Math.max(0, (this.items.length - this.virtualEndIndex) * LIST_ROW_HEIGHT)}px`,
      }
    },

    pagedListHeightBudget() {
      const hostHeight = this.pageMainHeight > 0 ? this.pageMainHeight : this.viewportHeight
      return Math.max(
        180,
        hostHeight - this.pagedPaginationHostReservePx - PAGED_LIST_BOTTOM_RESERVE_PX,
      )
    },

    photoGridStyle() {
      if (!this.isPhotoGridMode || !this.isPagedBrowseMode || this.isPortraitMasonryMode) return null
      return {
        minHeight: `${this.pagedGridHeightBudget}px`,
        height: `${this.pagedGridHeightBudget}px`,
        overflow: 'hidden',
      }
    },

    pagedGridHeightBudget() {
      const hostHeight = this.pageMainHeight > 0 ? this.pageMainHeight : this.viewportHeight
      return Math.max(
        220,
        hostHeight - this.pagedPaginationHostReservePx - PAGED_GRID_BOTTOM_RESERVE_PX,
      )
    },

    justifiedRows() {
      const width = this.containerWidth || (typeof window !== 'undefined' ? window.innerWidth - 48 : 800)
      const gap = PHOTO_GRID_GAP_PX
      const targetHeight = this.photoGridTargetHeight
      const items = this.items
      if (!items.length) return []

       const cacheKey = `trash|${this.cacheSortSignature}|${Math.max(1, Math.round(width))}|${this.layoutFingerprint}`
      if (JUSTIFIED_LAYOUT_CACHE.has(cacheKey)) {
        return JUSTIFIED_LAYOUT_CACHE.get(cacheKey)
      }

      const rows = []
      let rowStart = 0
      let rowAspectRatio = 0

      for (let i = 0; i < items.length; i++) {
        const item = items[i]
        const dims = this.dimensionsForItem(item)
        rowAspectRatio += dims.w / dims.h
        const isLast = i === items.length - 1
        const rowLen = i - rowStart + 1
        const neededWidth = rowAspectRatio * targetHeight + gap * (rowLen - 1)

        if (neededWidth >= width || isLast) {
          const totalGap = gap * (rowLen - 1)
          const actualHeight = (isLast && neededWidth < width)
            ? targetHeight
            : Math.round((width - totalGap) / rowAspectRatio)
          const rowItems = []
          for (let j = rowStart; j <= i; j++) {
            const current = items[j]
            const currentDims = this.dimensionsForItem(current)
            rowItems.push({
              ...current,
              _idx: j,
              computedWidth: Math.round((currentDims.w / currentDims.h) * actualHeight),
            })
          }
          rows.push({ items: rowItems, height: actualHeight })
          rowStart = i + 1
          rowAspectRatio = 0
        }
      }

      return rememberJustifiedLayout(cacheKey, rows)
    },

    photoGridPages() {
      if (!this.isPagedBrowseMode || !this.justifiedRows.length) return []

      const pages = []
      const budget = this.pagedGridHeightBudget
      const estimatedRows = Math.max(
        1,
        Math.floor((budget + PHOTO_GRID_GAP_PX) / (PHOTO_GRID_TARGET_HEIGHT_PX + PHOTO_GRID_GAP_PX)),
      )
      const minRowsPerPage = this.justifiedRows.length > 1 && estimatedRows > 1 ? MIN_PAGED_PHOTO_ROWS : 1
      const buildPage = (pageRows) => {
        const firstIndex = pageRows[0]?.items?.[0]?._idx ?? 0
        const lastRow = pageRows[pageRows.length - 1]
        const lastIndex = lastRow?.items?.[lastRow.items.length - 1]?._idx ?? firstIndex
        return { rows: pageRows, startIndex: firstIndex, endIndex: lastIndex }
      }

      let pageRows = []
      let pageHeight = 0

      for (let rowIndex = 0; rowIndex < this.justifiedRows.length; rowIndex += 1) {
        const row = this.justifiedRows[rowIndex]
        const nextRowHeight = row.height + (pageRows.length ? PHOTO_GRID_GAP_PX : 0)
        const remainingRows = this.justifiedRows.length - rowIndex
        const canSplit = pageRows.length >= minRowsPerPage
        const canLeaveFollowingPage = remainingRows > Math.max(0, minRowsPerPage - 1)

        if (pageRows.length && pageHeight + nextRowHeight > budget && canSplit && canLeaveFollowingPage) {
          pages.push(buildPage(pageRows))
          pageRows = []
          pageHeight = 0
        }

        pageRows.push(row)
        pageHeight += row.height + (pageRows.length > 1 ? PHOTO_GRID_GAP_PX : 0)
      }

      if (pageRows.length) {
        pages.push(buildPage(pageRows))
      }

      if (minRowsPerPage > 1 && pages.length > 1) {
        const lastPage = pages[pages.length - 1]
        const previousPage = pages[pages.length - 2]
        if (lastPage.rows.length < minRowsPerPage && previousPage.rows.length > minRowsPerPage) {
          while (lastPage.rows.length < minRowsPerPage && previousPage.rows.length > minRowsPerPage) {
            lastPage.rows.unshift(previousPage.rows.pop())
          }
          pages.splice(pages.length - 2, 2, buildPage(previousPage.rows), buildPage(lastPage.rows))
        }
      }

      return pages
    },

    photoGridTotalPages() {
      if (!this.isPagedBrowseMode) return 1
      if (this.isPortraitMasonryMode) return Math.max(1, this.masonryPages.length)
      return Math.max(1, this.photoGridPages.length)
    },

    normalizedPhotoPageIndex() {
      return Math.min(Math.max(0, this.photoPageIndex), Math.max(0, this.photoGridTotalPages - 1))
    },

    activePhotoRows() {
      if (this.isPortraitMasonryMode) return []
      if (!this.isPagedBrowseMode) return this.justifiedRows
      return this.photoGridPages[this.normalizedPhotoPageIndex]?.rows || []
    },

    selectionGridRowsPerPage() {
      if (!this.isPagedBrowseMode || !this.isSelectionGridMode) return 0

      const totalRows = Math.ceil(this.items.length / this.selectionColumnCount)
      if (!totalRows) return 0

      const rowSpan = this.effectiveSelectionRowHeight + this.selectionGridGapPx
      const estimatedRows = Math.max(1, Math.floor((this.pagedGridHeightBudget + this.selectionGridGapPx) / rowSpan))
      const minRows = totalRows > 1 && estimatedRows > 1 ? MIN_PAGED_SELECTION_ROWS : 1
      return Math.min(totalRows, Math.max(minRows, estimatedRows))
    },

    selectionGridPageSize() {
      if (!this.isPagedBrowseMode || !this.isSelectionGridMode) return this.items.length || 1
      return Math.max(1, this.selectionGridRowsPerPage * this.selectionColumnCount)
    },

    selectionGridTotalPages() {
      if (!this.isPagedBrowseMode || !this.isSelectionGridMode) return 1
      return Math.max(1, Math.ceil(this.items.length / this.selectionGridPageSize))
    },

    normalizedSelectionGridPageIndex() {
      return Math.min(Math.max(0, this.selectionGridPageIndex), Math.max(0, this.selectionGridTotalPages - 1))
    },

    selectionGridPageStartIndex() {
      if (!this.isPagedBrowseMode || !this.isSelectionGridMode) return 0
      return this.normalizedSelectionGridPageIndex * this.selectionGridPageSize
    },

    selectionGridPageEndIndex() {
      if (!this.isPagedBrowseMode || !this.isSelectionGridMode) return this.items.length
      return Math.min(this.items.length, this.selectionGridPageStartIndex + this.selectionGridPageSize)
    },

    listTotalPages() {
      if (!this.isPagedBrowseMode || this.viewMode !== 'list') return 1
      return Math.max(1, Math.ceil(this.items.length / this.listPageSize))
    },
    normalizedListPageIndex() {
      return Math.min(Math.max(0, this.listPageIndex), Math.max(0, this.listTotalPages - 1))
    },
    listPageStartIndex() {
      if (!this.isPagedBrowseMode || this.viewMode !== 'list') return 0
      return this.normalizedListPageIndex * this.listPageSize
    },
    listPageEndIndex() {
      if (!this.isPagedBrowseMode || this.viewMode !== 'list') return this.items.length
      return Math.min(this.items.length, this.listPageStartIndex + this.listPageSize)
    },

    activePaginationConfig() {
      if (!this.isPagedBrowseMode || !this.items.length) return null

      if (this.viewMode === 'list') {
        return {
          kind: 'list',
          currentPage: this.normalizedListPageIndex + 1,
          totalPages: this.listTotalPages,
          pageSize: this.listPageSize,
          pageSizeOptions: LIST_PAGE_SIZE_OPTIONS,
        }
      }

      if (this.isSelectionGridMode) {
        return {
          kind: 'selection-grid',
          currentPage: this.normalizedSelectionGridPageIndex + 1,
          totalPages: this.selectionGridTotalPages,
          pageSize: null,
          pageSizeOptions: [],
        }
      }

      return {
        kind: 'photo-grid',
        currentPage: this.normalizedPhotoPageIndex + 1,
        totalPages: this.photoGridTotalPages,
        pageSize: null,
        pageSizeOptions: [],
      }
    },

    pagedPaginationHostReservePx() {
      if (this.paginationHostHeight <= 0) return 0
      return this.paginationHostHeight + PAGE_SECTION_GAP_PX
    },

    selectedCount() {
      return Object.keys(this.selectedMap).length
    },

    availableSelectionTypes() {
      const types = new Set()
      for (const item of this.items) {
        if (item?.type === 'album' || item?.type === 'image') {
          types.add(item.type)
        }
      }
      return Array.from(types)
    },

    hasMixedSelectableTypes() {
      return this.availableSelectionTypes.includes('album') && this.availableSelectionTypes.includes('image')
    },

    selectedEntries() {
      const entries = []
      for (let index = 0; index < this.items.length; index++) {
        const item = this.items[index]
        if (this.isItemSelected(item, index)) {
          entries.push({ item, index })
        }
      }
      return entries
    },

    selectionSummaryText() {
      if (!this.selectedCount) return '已选 0 项'
      if (this.selectionTypeLock === 'album') return `已选 ${this.selectedCount} 个相册`
      if (this.selectionTypeLock === 'image') return `已选 ${this.selectedCount} 张图片`
      return `已选 ${this.selectedCount} 项`
    },

    selectionDetailPreviewItems() {
      return this.selectedEntries.map(({ item, index }) => ({
        key: this.itemKey(item, index),
        name: item.name || '未命名',
        type: item.type || 'image',
        previewUrl: this.resolvedUrl(item),
        aspectRatio: this.detailAspectRatio(item),
      }))
    },

    selectionDetailsPanelStyle() {
      const hostWidth = this.selectionDetailsHostWidth || (typeof window !== 'undefined' ? window.innerWidth : 0)
      const hostHeight = this.selectionDetailsHostHeight || (typeof window !== 'undefined' ? window.innerHeight : 0)
      if (!hostWidth || !hostHeight) return null

      const availableWidth = Math.max(0, Math.floor(hostWidth - 12))
      const availableHeight = Math.max(0, Math.floor(hostHeight - 12))
      const isPortraitLike = hostWidth <= 960 || hostWidth < hostHeight

      if (isPortraitLike) {
        const panelWidth = Math.min(
          availableWidth,
          Math.max(Math.min(availableWidth, 320), Math.floor(hostWidth * 0.98)),
        )
        const desiredHeight = Math.floor(hostHeight * 0.96)
        const panelHeight = Math.min(
          availableHeight,
          Math.max(Math.min(availableHeight, 360), desiredHeight),
        )
        return {
          width: `${panelWidth}px`,
          maxWidth: `${availableWidth}px`,
          height: `${panelHeight}px`,
          maxHeight: `${availableHeight}px`,
        }
      }

      const panelWidth = Math.min(
        1180,
        availableWidth,
        Math.max(Math.min(availableWidth, 760), Math.floor(hostWidth * 0.8)),
      )
      const panelHeight = Math.min(
        availableHeight,
        Math.max(Math.min(availableHeight, 460), Math.round(panelWidth * 0.58)),
      )
      return {
        width: `${panelWidth}px`,
        height: `${panelHeight}px`,
        maxWidth: `${availableWidth}px`,
        maxHeight: `${availableHeight}px`,
      }
    },

    selectionDetailNameField() {
      return this.buildDetailField(this.selectedEntries.map(({ item }) => item.name || '未命名'))
    },

    selectionDetailCategoryField() {
      return this.buildDetailField(this.selectedEntries.map(({ item }) => this.detailCategoryText(item)))
    },

    selectionDetailTagsField() {
      const imageEntries = this.selectedEntries.filter(({ item }) => item?.type === 'image')
      if (!imageEntries.length) {
        return {
          text: '',
          isVarious: false,
          isEmpty: true,
          items: [],
        }
      }

      const tagIdLists = imageEntries.map(({ item }) => {
        const ids = Array.isArray(item?.tags) ? item.tags.filter(id => Number.isInteger(id)) : []
        return this.sortTagIdsByName([...new Set(ids)])
      })

      const commonTagIds = tagIdLists.reduce((previous, current) => {
        if (!previous.length) return []
        const currentSet = new Set(current)
        return previous.filter(id => currentSet.has(id))
      }, [...(tagIdLists[0] || [])])

      const sortedCommonTagIds = this.sortTagIdsByName([...new Set(commonTagIds)])
      if (sortedCommonTagIds.length) {
        return {
          text: '',
          isVarious: false,
          isEmpty: false,
          items: this.buildTagItemsByIds(sortedCommonTagIds),
        }
      }

      const hasAnyTag = tagIdLists.some(ids => ids.length > 0)
      if (hasAnyTag) {
        return {
          text: 'various',
          isVarious: true,
          isEmpty: false,
          items: [],
        }
      }

      return {
        text: '',
        isVarious: false,
        isEmpty: true,
        items: [],
      }
    },

    selectionDetailSizeField() {
      return this.buildDetailField(this.selectedEntries.map(({ item }) => this.detailSizeText(item)))
    },

    selectionDetailSizeLabel() {
      return this.selectionTypeLock === 'album' ? '图片数量' : '尺寸'
    },

    selectionDetailImportedField() {
      return this.buildDetailField(this.selectedEntries.map(({ item }) => this.formatDateTime(item.imported_at)))
    },

    selectionDetailCreatedField() {
      return this.buildDetailField(this.selectedEntries.map(({ item }) => this.detailCreatedText(item)))
    },
  },

  watch: {
    photoGridRowCount(newVal, oldVal) {
      if (newVal !== oldVal) {
        this.refreshObservedGrid()
      }
    },
    viewMode() {
      if (this.selectionMode) return
      this.refreshObservedGrid()
    },
    selectionMode(nextValue) {
      if (!nextValue) {
        this.closeSelectionDetails()
        this.closeSelectAllMenu()
      }
    },
    selectedCount(nextValue) {
      if (!nextValue) {
        this.closeSelectionDetails()
        this.closeSelectAllMenu()
      }
    },
  },

  created() {
    this.loadData()
    this.fetchPageConfigSetting()
    window.addEventListener('resize', this.onResize)
    window.addEventListener('scroll', this.onWindowScroll, { passive: true })
    window.addEventListener('keydown', this.onWindowKeydown)
    window.addEventListener('pointerdown', this.onWindowPointerDown)
    window.addEventListener(PAGE_CONFIG_UPDATED_EVENT, this.onPageConfigUpdated)
  },

  beforeUnmount() {
    this.unlockPageScroll()
    this.teardownResizeObserver()
    this.clearPointerGesture()
    window.removeEventListener('resize', this.onResize)
    window.removeEventListener('scroll', this.onWindowScroll)
    window.removeEventListener('keydown', this.onWindowKeydown)
    window.removeEventListener('pointerdown', this.onWindowPointerDown)
    window.removeEventListener(PAGE_CONFIG_UPDATED_EVENT, this.onPageConfigUpdated)
    if (this.dimensionFlushTimer) {
      clearTimeout(this.dimensionFlushTimer)
      this.dimensionFlushTimer = null
    }
    if (this.scrollFrameId) {
      cancelAnimationFrame(this.scrollFrameId)
      this.scrollFrameId = null
    }
  },

  methods: {
    logTrashDebug(event, payload = {}) {
      console.debug('[TrashPage]', { event, ...payload })
    },

    async fetchPageConfigSetting() {
      try {
        const config = await fetchPageConfig()
        this.applyPageBrowseMode(config.browseMode, false)
      } catch {
        // keep cached or default page config when settings fetch fails
      }
    },

    onPageConfigUpdated(event) {
      this.applyPageBrowseMode(event?.detail?.browseMode, true)
    },

    applyPageBrowseMode(nextMode, captureAnchor = true) {
      const normalizedMode = nextMode === PAGE_BROWSE_MODE_PAGED
        ? PAGE_BROWSE_MODE_PAGED
        : PAGE_BROWSE_MODE_SCROLL
      if (normalizedMode === this.pageBrowseMode) return

      const anchor = captureAnchor ? this.captureViewportAnchor() : null
      this.pageBrowseMode = normalizedMode
      this.clearPointerGesture()
      this.closeSelectAllMenu()
      this.normalizePaginationState()

      if (anchor) {
        this.pendingViewAnchor = anchor
      }

      this.$nextTick(() => {
        this.refreshObservedGrid()
      })
    },

    itemLayoutKey(item, index = null) {
      return item?.entry_key || item?.id || item?._idx || index || 0
    },

    measureItemGridMetrics() {
      const pageMainRect = this.$refs.pageMain?.getBoundingClientRect?.()
      this.pageMainHeight = pageMainRect ? Math.round(pageMainRect.height) : 0
      if (!this.$refs.itemGrid) return

      const rect = this.$refs.itemGrid.getBoundingClientRect()
      this.containerWidth = this.$refs.itemGrid.offsetWidth || this.containerWidth
      this.itemGridViewportTop = Math.max(0, Math.round(rect.top))
      this.virtualContainerTop = rect.top + (window.scrollY || window.pageYOffset || 0)

      const paginationHostRect = this.$refs.paginationHost?.getBoundingClientRect?.()
      this.paginationHostHeight = paginationHostRect ? Math.round(paginationHostRect.height) : 0
    },

    normalizePaginationState() {
      this.photoPageIndex = Math.min(Math.max(0, this.photoPageIndex), Math.max(0, this.photoGridTotalPages - 1))
      this.selectionGridPageIndex = Math.min(Math.max(0, this.selectionGridPageIndex), Math.max(0, this.selectionGridTotalPages - 1))
      this.listPageIndex = Math.min(Math.max(0, this.listPageIndex), Math.max(0, this.listTotalPages - 1))
    },

    findPhotoPageIndexForItem(targetIndex) {
      const pages = this.isPortraitMasonryMode ? this.masonryPages : this.photoGridPages
      for (let pageIndex = 0; pageIndex < pages.length; pageIndex += 1) {
        const page = pages[pageIndex]
        if (!page) continue
        if (targetIndex >= page.startIndex && targetIndex <= page.endIndex) {
          return pageIndex
        }
      }
      return 0
    },

    restorePagedPageByIndex(targetIndex) {
      if (this.viewMode === 'list') {
        this.listPageIndex = Math.floor(targetIndex / this.listPageSize)
      } else if (this.isSelectionGridMode) {
        const pageSize = Math.max(1, this.selectionGridPageSize)
        this.selectionGridPageIndex = Math.floor(targetIndex / pageSize)
      } else {
        this.photoPageIndex = this.findPhotoPageIndexForItem(targetIndex)
      }

      this.normalizePaginationState()
    },

    scrollItemGridIntoView() {
      if (!this.$refs.itemGrid || typeof window === 'undefined') return
      const rect = this.$refs.itemGrid.getBoundingClientRect()
      const desiredTop = (window.scrollY || window.pageYOffset || 0) + rect.top - RESTORE_ANCHOR_PADDING_PX
      window.scrollTo({ top: Math.max(0, Math.round(desiredTop)), behavior: 'instant' })
    },

    onPaginationPageChange(nextPage) {
      if (!this.isPagedBrowseMode) return

      const targetPageIndex = Math.max(0, Number(nextPage || 1) - 1)
      if (this.viewMode === 'list') {
        this.listPageIndex = targetPageIndex
      } else if (this.isSelectionGridMode) {
        this.selectionGridPageIndex = targetPageIndex
      } else {
        this.photoPageIndex = targetPageIndex
      }

      this.normalizePaginationState()
      this.$nextTick(() => {
        this.scrollItemGridIntoView()
      })
    },

    onPaginationPageSizeChange(nextPageSize) {
      if (this.viewMode !== 'list' || !this.isPagedBrowseMode) return
      const normalizedPageSize = LIST_PAGE_SIZE_OPTIONS.includes(nextPageSize)
        ? nextPageSize
        : DEFAULT_LIST_PAGE_SIZE
      if (normalizedPageSize === this.listPageSize) return
      const anchor = this.captureViewportAnchor()
      this.listPageSize = normalizedPageSize
      this.normalizePaginationState()
      if (anchor) {
        this.pendingViewAnchor = anchor
      }
      this.refreshObservedGrid()
      window.requestAnimationFrame(() => {
        this.scrollItemGridIntoView()
      })
    },

    computeLayoutFingerprint(items, dimensions) {
      let hash = 2166136261
      const updateHash = (value) => {
        const text = String(value)
        for (let idx = 0; idx < text.length; idx++) {
          hash ^= text.charCodeAt(idx)
          hash = Math.imul(hash, 16777619)
        }
      }

      for (let index = 0; index < items.length; index++) {
        const item = items[index]
        const key = this.itemLayoutKey(item, index)
        const dims = dimensions[key] || {}
        updateHash(`${key}:${dims.w || 0}x${dims.h || 0};`)
      }
      return (hash >>> 0).toString(36)
    },

    goBack() {
      if (typeof window !== 'undefined' && window.history.length > 1) {
        this.$router.back()
        return
      }
      this.$router.push('/settings')
    },

    async loadData() {
      this.loading = true
      this.messageText = ''
      this.imgDimensions = {}
      this.layoutFingerprint = ''
      this.lastScrollDirection = 'none'
      this.lastObservedScrollTop = typeof window !== 'undefined' ? (window.scrollY || window.pageYOffset || 0) : 0
      this.pendingViewAnchor = null
      this.pendingDimensionCorrections = {}
      this.selectionRowHeight = 0
      this.closeSelectionDetails()
      this.closeSelectAllMenu()
      this.clearSelection()
      this.clearPointerGesture()
      this.scrollTop = typeof window !== 'undefined' ? (window.scrollY || window.pageYOffset || 0) : 0
      this.viewportHeight = typeof window !== 'undefined' ? window.innerHeight : this.viewportHeight
      this.viewportWidth = typeof window !== 'undefined' ? window.innerWidth : this.viewportWidth
      this.virtualStartIndex = 0
      this.virtualEndIndex = 0
      this.virtualAnchorIndex = 0
      this.virtualContainerTop = 0
      this.photoPageIndex = 0
      this.selectionGridPageIndex = 0
      this.listPageIndex = 0
      if (this.dimensionFlushTimer) {
        clearTimeout(this.dimensionFlushTimer)
        this.dimensionFlushTimer = null
      }
      this.teardownResizeObserver()
      if (!this.selectionMode) {
        this.viewMode = 'grid'
      }
      try {
        const res = await fetch(`${API_BASE}/api/trash/items`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        this.applyFetchedItems(data.items || [])
        this.$nextTick(() => this.refreshObservedGrid())
        this.ensureCategoryLabelsLoaded()
        this.ensureTagLabelsLoaded()
      } catch (err) {
        this.items = []
        this.imgDimensions = {}
        this.layoutFingerprint = ''
        this.showMessage('error', err?.message || '加载回收站失败')
      } finally {
        this.loading = false
      }
    },

    applyFetchedItems(rawItems) {
      const nextItems = this.sortItems(rawItems || [])
      const nextDimensions = {}

      for (const item of nextItems) {
        const key = this.itemLayoutKey(item)
        const width = Number(item?.width)
        const height = Number(item?.height)
        if (Number.isFinite(width) && Number.isFinite(height) && width > 0 && height > 0) {
          nextDimensions[key] = { w: width, h: height }
        }
      }

      this.items = nextItems
      this.virtualStartIndex = 0
      this.virtualEndIndex = nextItems.length
      this.virtualAnchorIndex = nextItems.length ? 0 : -1
      this.imgDimensions = nextDimensions
      this.layoutFingerprint = this.computeLayoutFingerprint(nextItems, nextDimensions)
    },

    showMessage(type, text) {
      this.messageType = type
      this.messageText = text
    },

    refreshContainerWidth() {
      const host = this.$refs.itemGrid || this.$el
      if (host && typeof host.getBoundingClientRect === 'function') {
        this.containerWidth = Math.max(320, Math.floor(host.getBoundingClientRect().width))
      }
    },

    onResize() {
      const anchorBeforeReflow = this.$refs.itemGrid ? this.captureViewportAnchor() : null
      this.viewportHeight = typeof window !== 'undefined' ? window.innerHeight : this.viewportHeight
      this.viewportWidth = typeof window !== 'undefined' ? window.innerWidth : this.viewportWidth
      if (this.$refs.itemGrid) {
        if (this.isPagedBrowseMode) {
          if (anchorBeforeReflow) {
            this.pendingViewAnchor = anchorBeforeReflow
          }
          this.refreshObservedGrid()
        } else {
          this.measureItemGridMetrics()
        }
        if (this.isVirtualizedMode) {
          this.syncVirtualWindow(true)
          if (this.isSelectionGridMode) {
            this.measureSelectionRowHeight()
          }
        }
      }
      if (this.selectionDetailsOpen) {
        this.updateSelectionDetailsBounds()
      }
    },

    onWindowScroll() {
      const nextScrollTop = window.scrollY || window.pageYOffset || 0
      if (nextScrollTop > this.lastObservedScrollTop) {
        this.lastScrollDirection = 'forward'
      } else if (nextScrollTop < this.lastObservedScrollTop) {
        this.lastScrollDirection = 'backward'
      }
      this.lastObservedScrollTop = nextScrollTop

      if (!this.isVirtualizedMode && !this.selectionDetailsOpen) return
      if (this.scrollFrameId) return
      this.scrollFrameId = window.requestAnimationFrame(() => {
        this.scrollFrameId = null
        if (this.isVirtualizedMode) {
          this.scrollTop = window.scrollY || window.pageYOffset || 0
          this.syncVirtualWindow()
        }
        if (this.selectionDetailsOpen) {
          this.updateSelectionDetailsBounds()
        }
      })
    },

    dimensionsForItem(item) {
      const dims = this.imgDimensions[this.itemLayoutKey(item)] || null
      const width = Number(dims?.w ?? item?.width)
      const height = Number(dims?.h ?? item?.height)
      if (!Number.isFinite(width) || width <= 0 || !Number.isFinite(height) || height <= 0) {
        return { w: 4, h: 3 }
      }
      return { w: width, h: height }
    },

    refreshObservedGrid() {
      this.$nextTick(() => {
        this.measureItemGridMetrics()
        this.normalizePaginationState()

        if (this.isVirtualizedMode) {
          this.syncVirtualWindow(true)
        } else {
          this.virtualStartIndex = 0
          this.virtualEndIndex = this.items.length
          this.virtualAnchorIndex = this.items.length ? 0 : -1
        }
        this.setupResizeObserver()
        if (this.isSelectionGridMode) {
          this.measureSelectionRowHeight()
        }
        if (this.pendingViewAnchor) {
          this.restorePendingViewAnchor()
        }
      })
    },

    syncVirtualWindow(force = false) {
      if (!this.$refs.itemGrid) return

      this.scrollTop = window.scrollY || window.pageYOffset || 0
      this.viewportHeight = window.innerHeight || this.viewportHeight
      this.containerWidth = this.$refs.itemGrid.offsetWidth || this.containerWidth
      const rect = this.$refs.itemGrid.getBoundingClientRect()
      this.virtualContainerTop = rect.top + this.scrollTop

      if (!this.isVirtualizedMode) {
        this.virtualStartIndex = 0
        this.virtualEndIndex = this.items.length
        this.virtualAnchorIndex = this.items.length ? 0 : -1
        return
      }

      const viewportTop = Math.max(0, this.scrollTop - this.virtualContainerTop)
      const viewportBottom = viewportTop + this.viewportHeight
      let startIndex = 0
      let endIndex = this.items.length
      let anchorIndex = this.items.length ? 0 : -1

      if (this.viewMode === 'list') {
        const firstVisibleIndex = Math.min(
          this.items.length - 1,
          Math.max(0, Math.floor(viewportTop / LIST_ROW_HEIGHT)),
        )
        anchorIndex = firstVisibleIndex
        startIndex = Math.max(0, firstVisibleIndex - LIST_OVERSCAN_ROWS)
        endIndex = Math.min(
          this.items.length,
          Math.ceil(viewportBottom / LIST_ROW_HEIGHT) + LIST_OVERSCAN_ROWS,
        )
      } else if (this.isSelectionGridMode) {
        const rowSpan = this.effectiveSelectionRowHeight + this.selectionGridGapPx
        const totalRows = Math.ceil(this.items.length / this.selectionColumnCount)
        const firstVisibleRow = Math.min(
          Math.max(0, Math.floor(viewportTop / rowSpan)),
          Math.max(0, totalRows - 1),
        )
        const endVisibleRow = Math.min(
          totalRows,
          Math.ceil(viewportBottom / rowSpan) + SELECTION_OVERSCAN_ROWS,
        )
        anchorIndex = Math.min(this.items.length - 1, firstVisibleRow * this.selectionColumnCount)
        startIndex = Math.max(0, (firstVisibleRow - SELECTION_OVERSCAN_ROWS) * this.selectionColumnCount)
        endIndex = Math.min(this.items.length, endVisibleRow * this.selectionColumnCount)
      }

      const rangeChanged =
        force
        || startIndex !== this.virtualStartIndex
        || endIndex !== this.virtualEndIndex
        || anchorIndex !== this.virtualAnchorIndex

      if (!rangeChanged) return

      this.virtualStartIndex = startIndex
      this.virtualEndIndex = endIndex
      this.virtualAnchorIndex = anchorIndex

      if (this.isSelectionGridMode) {
        this.$nextTick(() => {
          this.measureSelectionRowHeight()
        })
      }
    },

    measureSelectionRowHeight() {
      if (!this.isSelectionGridMode || !this.$refs.itemGrid) return
      const sample = this.$refs.itemGrid.querySelector('.selection-wrap')
      if (!sample) return

      const nextHeight = Math.round(sample.getBoundingClientRect().height)
      if (nextHeight > 0 && Math.abs(nextHeight - this.selectionRowHeight) > 1) {
        this.selectionRowHeight = nextHeight
        if (this.isPagedBrowseMode) {
          this.normalizePaginationState()
        } else {
          this.syncVirtualWindow(true)
        }
      }
    },

    collectVisibleDomEntries() {
      if (!this.$refs.itemGrid || typeof window === 'undefined') return []
      return Array.from(this.$refs.itemGrid.querySelectorAll('[data-index]'))
        .map((element) => {
          const index = Number(element.getAttribute('data-index'))
          if (!Number.isInteger(index)) return null
          const rect = element.getBoundingClientRect()
          if (rect.bottom <= 0 || rect.top >= window.innerHeight) return null
          return {
            index,
            left: rect.left,
            top: rect.top,
          }
        })
        .filter(Boolean)
        .sort((leftEntry, rightEntry) => {
          if (Math.abs(leftEntry.top - rightEntry.top) <= FIRST_ROW_TOLERANCE_PX) {
            return leftEntry.left - rightEntry.left
          }
          return leftEntry.top - rightEntry.top
        })
    },

    captureViewportAnchor() {
      const visibleEntries = this.collectVisibleDomEntries()
      if (visibleEntries.length) {
        const entry = visibleEntries[0]
        const item = this.items[entry.index]
        if (item) {
          const hostRect = this.$refs.itemGrid?.getBoundingClientRect?.() || { left: 0 }
          return {
            index: entry.index,
            itemKey: this.itemKey(item, entry.index),
            anchorOffset: Math.max(0, Math.round(entry.left - hostRect.left)),
          }
        }
      }

      const fallbackIndex = Number.isInteger(this.virtualAnchorIndex) && this.virtualAnchorIndex >= 0
        ? this.virtualAnchorIndex
        : 0
      const item = this.items[fallbackIndex]
      if (!item) return null
      return {
        index: fallbackIndex,
        itemKey: this.itemKey(item, fallbackIndex),
        anchorOffset: 0,
      }
    },

    resolveRestoreAnchorIndex(anchor) {
      if (!anchor || !this.items.length) return -1
      if (Number.isInteger(anchor.index) && anchor.index >= 0 && anchor.index < this.items.length) {
        return anchor.index
      }
      if (anchor.itemKey) {
        const matchedIndex = this.items.findIndex((item, index) => this.itemKey(item, index) === anchor.itemKey)
        if (matchedIndex >= 0) return matchedIndex
      }
      return Math.min(this.items.length - 1, Math.max(0, anchor.index || 0))
    },

    restorePendingViewAnchor() {
      const anchor = this.pendingViewAnchor
      this.pendingViewAnchor = null
      if (!anchor) return

      const targetIndex = this.resolveRestoreAnchorIndex(anchor)
      if (!Number.isInteger(targetIndex) || targetIndex < 0) return

      if (this.isPagedBrowseMode) {
        this.restorePagedPageByIndex(targetIndex)
        return
      }

      if (this.viewMode === 'list') {
        const desiredTop = this.virtualContainerTop + (targetIndex * LIST_ROW_HEIGHT) - RESTORE_ANCHOR_PADDING_PX
        window.scrollTo({ top: Math.max(0, Math.round(desiredTop)), behavior: 'instant' })
        this.logTrashDebug('anchor-restore', { mode: 'list', targetIndex })
        window.requestAnimationFrame(() => {
          this.syncVirtualWindow(true)
        })
        return
      }

      if (this.isSelectionGridMode) {
        const rowIndex = Math.floor(targetIndex / this.selectionColumnCount)
        const desiredTop = this.virtualContainerTop + (rowIndex * (this.effectiveSelectionRowHeight + this.selectionGridGapPx)) - RESTORE_ANCHOR_PADDING_PX
        window.scrollTo({ top: Math.max(0, Math.round(desiredTop)), behavior: 'instant' })
        this.logTrashDebug('anchor-restore', { mode: 'selection-grid', targetIndex, rowIndex })
        window.requestAnimationFrame(() => {
          this.syncVirtualWindow(true)
        })
        return
      }

      this.$nextTick(() => {
        // masonry 滚动模式锚点恢复：按 placement.top 直接定位
        if (this.isPortraitMasonryMode) {
          const placement = this.masonryLayout.placements.find(p => p._idx === targetIndex)
          if (placement) {
            const desiredTop = this.virtualContainerTop + placement.top - RESTORE_ANCHOR_PADDING_PX
            window.scrollTo({ top: Math.max(0, Math.round(desiredTop)), behavior: 'instant' })
            this.logTrashDebug('anchor-restore', { mode: 'masonry', targetIndex, top: placement.top })
            return
          }
        }
        const target = this.$refs.itemGrid?.querySelector?.(`[data-index="${targetIndex}"]`)
        if (!target) return
        const rect = target.getBoundingClientRect()
        const desiredTop = (window.scrollY || window.pageYOffset || 0) + rect.top - RESTORE_ANCHOR_PADDING_PX
        window.scrollTo({ top: Math.max(0, Math.round(desiredTop)), behavior: 'instant' })
        this.logTrashDebug('anchor-restore', { mode: 'photo-grid', targetIndex })
      })
    },

    onImgLoad(item, event) {
      if (!item) return
      const existing = this.imgDimensions[this.itemLayoutKey(item)]
      if (existing?.w > 0 && existing?.h > 0) return

      const width = Number(event?.target?.naturalWidth)
      const height = Number(event?.target?.naturalHeight)
      if (!Number.isFinite(width) || width <= 0 || !Number.isFinite(height) || height <= 0) return

      this.pendingDimensionCorrections = {
        ...this.pendingDimensionCorrections,
        [this.itemLayoutKey(item)]: { w: width, h: height },
      }
      if (this.dimensionFlushTimer) return

      this.dimensionFlushTimer = setTimeout(() => {
        this.dimensionFlushTimer = null
        this.flushDimensionCorrections()
      }, DIMENSION_CORRECTION_BATCH_MS)
    },

    flushDimensionCorrections() {
      const entries = Object.entries(this.pendingDimensionCorrections || {})
      this.pendingDimensionCorrections = {}
      if (!entries.length) return

      const nextDimensions = { ...this.imgDimensions }
      let changed = false
      for (const [key, dims] of entries) {
        if (!dims?.w || !dims?.h) continue
        const prev = nextDimensions[key]
        if (prev?.w === dims.w && prev?.h === dims.h) continue
        nextDimensions[key] = dims
        changed = true
      }

      if (!changed) return

      this.imgDimensions = nextDimensions
      this.layoutFingerprint = this.computeLayoutFingerprint(this.items, nextDimensions)
      this.logTrashDebug('dimension-fallback', { count: entries.length })
    },

    resolvedUrl(item) {
      if (!item) return ''
      if (item.cache_thumb_url) return `${API_BASE}${item.cache_thumb_url}`
      if (item.thumb_url) return `${API_BASE}${item.thumb_url}`
      if (item.trash_media_url) return `${API_BASE}${item.trash_media_url}`
      return ''
    },

    itemDateTs(item) {
      const ts = Number(item?.sort_ts)
      return Number.isFinite(ts) ? ts : 0
    },

    itemAlphaKey(item) {
      return (item?.name || '').toString()
    },

    sortItems(items) {
      const arr = Array.isArray(items) ? [...items] : []
      const dir = this.sortDir === 'desc' ? -1 : 1
      const compare = (a, b) => {
        if (this.sortBy === 'date') {
          const ta = this.itemDateTs(a)
          const tb = this.itemDateTs(b)
          if (ta !== tb) return (ta - tb) * dir
        } else {
          const na = this.itemAlphaKey(a)
          const nb = this.itemAlphaKey(b)
          const nc = na.localeCompare(nb, undefined, { sensitivity: 'base', numeric: true })
          if (nc !== 0) return nc * dir
        }
        const ta = this.itemDateTs(a)
        const tb = this.itemDateTs(b)
        if (ta !== tb) return (ta - tb) * dir
        const na = this.itemAlphaKey(a)
        const nb = this.itemAlphaKey(b)
        return na.localeCompare(nb, undefined, { sensitivity: 'base', numeric: true }) * dir
      }
      const albums = arr.filter(it => it?.type === 'album').sort(compare)
      const images = arr.filter(it => it?.type !== 'album').sort(compare)
      return [...albums, ...images]
    },

    refreshSortResult() {
      const anchor = this.captureViewportAnchor()
      this.items = this.sortItems(this.items)
      this.layoutFingerprint = this.computeLayoutFingerprint(this.items, this.imgDimensions)
      this.clearSelection()
      this.ensureTagLabelsLoaded()
      if (anchor) {
        this.pendingViewAnchor = anchor
      }
      this.refreshObservedGrid()
    },

    onSortModeSelect(mode) {
      if (this.sortBy === mode) return
      this.sortBy = mode
      this.sortDir = 'asc'
      this.refreshSortResult()
    },

    toggleSortDir() {
      this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc'
      this.refreshSortResult()
    },

    toggleSelectionMode(forceValue = null) {
      const nextValue = typeof forceValue === 'boolean' ? forceValue : !this.selectionMode
      if (nextValue === this.selectionMode) return
      const anchor = this.captureViewportAnchor()
      this.closeSelectAllMenu()
      if (nextValue) {
        this.viewModeBeforeSelection = this.viewMode
        this.selectionMode = true
        this.viewMode = 'grid'
      } else {
        this.selectionMode = false
        this.viewMode = this.viewModeBeforeSelection || 'grid'
        this.clearSelection()
        this.clearPointerGesture()
        this.suppressNextListClick = false
      }
      this.normalizePaginationState()
      if (anchor) {
        this.pendingViewAnchor = anchor
      }
      this.refreshObservedGrid()
    },

    itemKey(item, index) {
      if (item?.type === 'album') return `album:${item.entry_key || item.id || index}`
      return `image:${item.entry_key || item.id || index}`
    },

    isItemSelected(item, index) {
      return Boolean(this.selectedMap[this.itemKey(item, index)])
    },

    isItemDisabled(item) {
      return Boolean(this.selectionTypeLock && item?.type !== this.selectionTypeLock)
    },

    clearSelection() {
      this.selectedMap = {}
      this.selectionTypeLock = null
      this.selectionAnchorIndex = null
      this.closeSelectionDetails()
      this.closeSelectAllMenu()
    },

    selectAllOfType(type) {
      if (!type) return
      const next = {}
      let anchorIndex = null
      for (let i = 0; i < this.items.length; i++) {
        const item = this.items[i]
        if (!item || item.type !== type) continue
        next[this.itemKey(item, i)] = true
        if (anchorIndex === null) anchorIndex = i
      }
      this.selectedMap = next
      this.selectionTypeLock = type
      this.selectionAnchorIndex = anchorIndex
      this.closeSelectAllMenu()
    },

    selectAllOfCurrentType() {
      const type = this.selectionTypeLock
        || (this.availableSelectionTypes.length === 1
          ? this.availableSelectionTypes[0]
          : (this.availableSelectionTypes.includes('image') ? 'image' : this.availableSelectionTypes[0]))
      this.selectAllOfType(type)
    },

    handleSelectAllButtonClick() {
      if (!this.hasMixedSelectableTypes) {
        this.selectAllOfCurrentType()
        return
      }
      this.selectAllMenuOpen = !this.selectAllMenuOpen
    },

    onSelectAllTypeClick(type) {
      this.selectAllOfType(type)
    },

    closeSelectAllMenu() {
      this.selectAllMenuOpen = false
    },

    onSelectionIslandCollapsedChange(collapsed) {
      if (!collapsed) return
      this.closeSelectAllMenu()
    },

    selectOnlyIndex(index) {
      const item = this.items[index]
      if (!item) return
      this.selectionTypeLock = item.type
      this.selectedMap = { [this.itemKey(item, index)]: true }
      this.selectionAnchorIndex = index
    },

    addIndexToSelection(index, useAsAnchor = false) {
      const item = this.items[index]
      if (!item) return
      if (this.selectionTypeLock && this.selectionTypeLock !== item.type) return
      const key = this.itemKey(item, index)
      this.selectedMap = { ...this.selectedMap, [key]: true }
      this.selectionTypeLock = item.type
      if (useAsAnchor || this.selectionAnchorIndex === null) {
        this.selectionAnchorIndex = index
      }
    },

    removeIndexFromSelection(index) {
      const item = this.items[index]
      if (!item) return
      const key = this.itemKey(item, index)
      const next = { ...this.selectedMap }
      delete next[key]
      this.selectedMap = next
      if (!Object.keys(next).length) {
        this.selectionTypeLock = null
        this.selectionAnchorIndex = null
      }
    },

    toggleIndexSelection(index) {
      const item = this.items[index]
      if (!item || this.isItemDisabled(item)) return
      if (this.isItemSelected(item, index)) {
        this.removeIndexFromSelection(index)
      } else {
        this.addIndexToSelection(index, true)
      }
    },

    applyRangeSelection(targetIndex, additive = false) {
      const targetItem = this.items[targetIndex]
      if (!targetItem) return
      const anchorIndex = this.selectionAnchorIndex === null ? targetIndex : this.selectionAnchorIndex
      const lockedType = this.selectionTypeLock || targetItem.type
      const next = additive ? { ...this.selectedMap } : {}
      for (let i = Math.min(anchorIndex, targetIndex); i <= Math.max(anchorIndex, targetIndex); i++) {
        const item = this.items[i]
        if (!item || item.type !== lockedType) continue
        next[this.itemKey(item, i)] = true
      }
      this.selectedMap = next
      this.selectionTypeLock = lockedType
      this.selectionAnchorIndex = targetIndex
    },

    onSelectionPointerDown(event, item, index) {
      if (!this.selectionMode) return
      if (event.pointerType === 'mouse' && event.button !== 0) return
      if (this.isItemDisabled(item)) return

      event.preventDefault()

      if (event.shiftKey) {
        this.applyRangeSelection(index, event.ctrlKey || event.metaKey)
        return
      }

      if (event.ctrlKey || event.metaKey) {
        this.toggleIndexSelection(index)
        return
      }

      this.clearPointerGesture()
      this.pointerSelection = {
        pointerId: event.pointerId,
        startIndex: index,
        type: item.type,
        sweeping: false,
        action: null,
        visitedKeys: {},
      }

      this.longPressTimer = window.setTimeout(() => {
        this.beginSweepSelection(index)
      }, LONG_PRESS_MS)

      window.addEventListener('pointermove', this.onGlobalPointerMove)
      window.addEventListener('pointerup', this.onGlobalPointerUp)
      window.addEventListener('pointercancel', this.onGlobalPointerCancel)
    },

    onItemSelectionButtonClick(item, index) {
      if (!item || this.isItemDisabled(item)) return
      if (this.isItemSelected(item, index)) {
        this.removeIndexFromSelection(index)
        return
      }

      if (!this.selectionMode) {
        this.viewModeBeforeSelection = this.viewMode
        this.selectionMode = true
      }

      if (!this.selectedCount) {
        this.selectOnlyIndex(index)
        return
      }

      this.addIndexToSelection(index, true)
    },

    openDetailsForItem(item, index) {
      if (!item) return
      if (!this.isItemSelected(item, index) || this.selectedCount !== 1) {
        this.selectOnlyIndex(index)
      }
      this.openSelectionDetails()
    },

    openSelectionDetails() {
      if (!this.selectedCount) return
      this.ensureCategoryLabelsLoaded()
      this.ensureTagLabelsLoaded()
      this.updateSelectionDetailsBounds()
      this.closeSelectAllMenu()
      this.selectionDetailsOpen = true
      this.lockPageScroll()
    },

    closeSelectionDetails() {
      this.selectionDetailsOpen = false
      this.unlockPageScroll()
    },

    updateSelectionDetailsBounds() {
      if (typeof window === 'undefined') return
      const host = (this.$el && typeof this.$el.closest === 'function')
        ? (this.$el.closest('main') || this.$el)
        : this.$el
      if (!host || typeof host.getBoundingClientRect !== 'function') return

      const rect = host.getBoundingClientRect()
      const visibleTop = Math.max(0, Math.round(rect.top))
      const visibleBottom = Math.max(0, Math.round(window.innerHeight - rect.bottom))
      const visibleLeft = Math.max(0, Math.round(rect.left))
      const visibleRight = Math.max(0, Math.round(window.innerWidth - rect.right))

      this.selectionDetailsHostWidth = Math.max(0, window.innerWidth - visibleLeft - visibleRight)
      this.selectionDetailsHostHeight = Math.max(0, window.innerHeight - visibleTop - visibleBottom)
      this.selectionDetailsBounds = {
        top: `${visibleTop}px`,
        right: `${visibleRight}px`,
        bottom: `${visibleBottom}px`,
        left: `${visibleLeft}px`,
      }
    },

    lockPageScroll() {
      if (typeof window === 'undefined' || this.scrollLockState) return
      const root = document.documentElement
      const body = document.body
      const scrollY = window.scrollY || window.pageYOffset || 0
      const scrollbarWidth = Math.max(0, window.innerWidth - root.clientWidth)
      this.scrollLockState = {
        scrollY,
        bodyOverflow: body.style.overflow,
        bodyPosition: body.style.position,
        bodyTop: body.style.top,
        bodyLeft: body.style.left,
        bodyRight: body.style.right,
        bodyWidth: body.style.width,
        bodyPaddingRight: body.style.paddingRight,
        rootOverflow: root.style.overflow,
        rootOverscrollBehavior: root.style.overscrollBehavior,
      }
      root.style.overflow = 'hidden'
      root.style.overscrollBehavior = 'none'
      body.style.overflow = 'hidden'
      body.style.position = 'fixed'
      body.style.top = `-${scrollY}px`
      body.style.left = '0'
      body.style.right = '0'
      body.style.width = '100%'
      if (scrollbarWidth > 0) {
        body.style.paddingRight = `${scrollbarWidth}px`
      }
    },

    unlockPageScroll() {
      if (typeof window === 'undefined' || !this.scrollLockState) return
      const root = document.documentElement
      const body = document.body
      const state = this.scrollLockState
      root.style.overflow = state.rootOverflow
      root.style.overscrollBehavior = state.rootOverscrollBehavior
      body.style.overflow = state.bodyOverflow
      body.style.position = state.bodyPosition
      body.style.top = state.bodyTop
      body.style.left = state.bodyLeft
      body.style.right = state.bodyRight
      body.style.width = state.bodyWidth
      body.style.paddingRight = state.bodyPaddingRight
      this.scrollLockState = null
      window.scrollTo({ top: state.scrollY, behavior: 'instant' })
    },

    buildDetailField(values, options = {}) {
      const emptyText = Object.prototype.hasOwnProperty.call(options, 'emptyText') ? options.emptyText : '—'
      const normalized = Array.isArray(values) ? values.map(value => (value == null ? '' : String(value).trim())) : []
      if (!normalized.length) {
        return { text: emptyText, isVarious: false, isEmpty: !emptyText }
      }
      const first = normalized[0]
      const allSame = normalized.every(value => value === first)
      if (!allSame) {
        return { text: 'various', isVarious: true, isEmpty: false }
      }
      const isEmpty = first.length === 0
      return { text: isEmpty ? emptyText : first, isVarious: false, isEmpty }
    },

    detailAspectRatio(item) {
      const dims = this.dimensionsForItem(item)
      return `${dims.w} / ${dims.h}`
    },

    buildTagLookupEntry(rawTag) {
      if (!Number.isInteger(rawTag?.id)) return null
      const { color, borderColor, backgroundColor } = normalizeTagColors(rawTag)
      return {
        id: rawTag.id,
        name: String(rawTag?.name || ''),
        displayName: String(rawTag?.display_name || rawTag?.name || `#${rawTag.id}`),
        color: String(color || ''),
        borderColor: String(borderColor || ''),
        backgroundColor: String(backgroundColor || ''),
      }
    },

    sortTagIdsByName(tagIds) {
      return [...tagIds].sort((leftId, rightId) => {
        const leftName = String(this.tagLookupMap[leftId]?.name || '')
        const rightName = String(this.tagLookupMap[rightId]?.name || '')
        if (leftName && rightName && leftName !== rightName) {
          return leftName.localeCompare(rightName)
        }
        if (leftName && !rightName) return -1
        if (!leftName && rightName) return 1
        return leftId - rightId
      })
    },

    buildTagItemsByIds(tagIds) {
      const sortedIds = this.sortTagIdsByName(tagIds)
      return sortedIds.map((id) => {
        const tag = this.tagLookupMap[id]
        if (!tag) {
          return {
            id,
            name: `#${id}`,
            display_name: `#${id}`,
            color: '',
            border_color: '',
            background_color: '',
          }
        }
        return {
          id,
          name: tag.name || `#${id}`,
          display_name: tag.displayName || tag.name || `#${id}`,
          color: tag.color || '',
          border_color: tag.borderColor || '',
          background_color: tag.backgroundColor || '',
        }
      })
    },

    detailTagTextForItem(item) {
      const tags = Array.isArray(item?.tags) ? item.tags : []
      if (!tags.length) return ''
      const sortedIds = this.sortTagIdsByName(tags.filter(id => Number.isInteger(id)))
      return sortedIds
        .map(id => this.tagLookupMap[id]?.displayName || `#${id}`)
        .filter(Boolean)
        .join(', ')
    },

    detailCategoryText(item) {
      if (item?.type !== 'image') return ''
      const categoryId = Number(item?.category_id)
      if (!Number.isInteger(categoryId) || categoryId <= 0) return ''
      return this.categoryDisplayMap[categoryId] || ''
    },

    detailSizeText(item) {
      if (item?.type === 'album') {
        return item?.photo_count != null ? `${item.photo_count} 张` : ''
      }
      const width = Number(item?.width)
      const height = Number(item?.height)
      if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) return ''
      return `${width} × ${height}`
    },

    detailCreatedText(item) {
      if (item?.type === 'album') return this.formatDateTime(item.created_at)
      return this.formatDateTime(item.file_created_at)
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

    async ensureTagLabelsLoaded() {
      const tagIds = []
      for (const { item } of this.selectedEntries) {
        for (const id of (item?.tags || [])) {
          if (Number.isInteger(id) && !tagIds.includes(id)) {
            tagIds.push(id)
          }
        }
      }
      if (!tagIds.length) return
      try {
        const res = await fetch(`${API_BASE}/api/tags?ids=${tagIds.join(',')}&limit=${tagIds.length}`)
        if (!res.ok) return
        const data = await res.json()
        const nextMap = { ...this.tagLookupMap }
        for (const tag of (data.items || [])) {
          const normalizedTag = this.buildTagLookupEntry(tag)
          if (!normalizedTag) continue
          nextMap[normalizedTag.id] = normalizedTag
        }
        this.tagLookupMap = nextMap
      } catch {
        // ignore tag load failure in trash detail view
      }
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
        // ignore category load failure in trash detail view
      }
    },

    noop() {},

    switchViewMode(mode) {
      if (!['grid', 'list'].includes(mode)) return
      const modeChanged = this.viewMode !== mode
      const wasSelecting = this.selectionMode
      const anchor = (modeChanged || wasSelecting) ? this.captureViewportAnchor() : null
      this.closeSelectAllMenu()
      this.viewMode = mode
      if (wasSelecting) {
        this.selectionMode = false
        this.clearSelection()
        this.clearPointerGesture()
        this.suppressNextListClick = false
      }
      if (anchor) {
        this.pendingViewAnchor = anchor
      }
      if (wasSelecting || !modeChanged) {
        this.refreshObservedGrid()
      }
    },

    enterListSelectionMode() {
      this.viewModeBeforeSelection = 'list'
      this.selectionMode = true
      this.viewMode = 'list'
    },

    onListPointerDown(event, item, index) {
      if (event.pointerType === 'mouse' && event.button !== 0) return
      if (this.selectionMode) {
        this.onSelectionPointerDown(event, item, index)
        return
      }
      if (event.shiftKey || event.ctrlKey || event.metaKey) {
        event.preventDefault()
        this.enterListSelectionMode()
        this.suppressNextListClick = true
        if (event.shiftKey) {
          this.applyRangeSelection(index, event.ctrlKey || event.metaKey)
        } else {
          this.toggleIndexSelection(index)
        }
        return
      }
      this.clearPointerGesture()
      this.pointerSelection = {
        pointerId: event.pointerId,
        startIndex: index,
        type: item.type,
        sweeping: false,
        action: null,
        visitedKeys: {},
        origin: 'list-browse',
      }
      this.longPressTimer = window.setTimeout(() => {
        this.activateListLongPressSelection(index)
      }, LONG_PRESS_MS)
      window.addEventListener('pointermove', this.onGlobalPointerMove)
      window.addEventListener('pointerup', this.onGlobalPointerUp)
      window.addEventListener('pointercancel', this.onGlobalPointerCancel)
    },

    activateListLongPressSelection(index) {
      const session = this.pointerSelection
      const item = this.items[index]
      if (!session || !item || session.sweeping) return
      this.enterListSelectionMode()
      this.suppressNextListClick = true
      this.selectOnlyIndex(index)
      session.origin = 'list-selection'
      session.sweeping = true
      session.action = 'add'
      session.type = item.type
      session.visitedKeys = {}
      this.applySweepToIndex(index)
    },

    onListRowClick(_event, item, index) {
      if (this.suppressNextListClick) {
        this.suppressNextListClick = false
        return
      }
      if (this.selectionMode) return
      this.openDetailsForItem(item, index)
    },

    beginSweepSelection(startIndex) {
      const session = this.pointerSelection
      const item = this.items[startIndex]
      if (!session || session.sweeping || !item || this.isItemDisabled(item)) return

      session.sweeping = true
      session.action = this.isItemSelected(item, startIndex) ? 'remove' : 'add'
      session.type = item.type
      this.applySweepToIndex(startIndex)
    },

    applySweepToIndex(index) {
      const session = this.pointerSelection
      const item = this.items[index]
      if (!session || !session.sweeping || !item) return
      if (item.type !== session.type) return
      if (this.selectionTypeLock && this.selectionTypeLock !== item.type) return
      const key = this.itemKey(item, index)
      if (session.visitedKeys[key]) return
      session.visitedKeys[key] = true
      if (session.action === 'remove') {
        this.removeIndexFromSelection(index)
      } else {
        this.addIndexToSelection(index)
      }
    },

    onGlobalPointerMove(event) {
      const session = this.pointerSelection
      if (!session || event.pointerId !== session.pointerId || !session.sweeping) return
      const target = document.elementFromPoint(event.clientX, event.clientY)
      const wrap = target && target.closest('[data-select-index]')
      if (!wrap) return
      const index = Number(wrap.getAttribute('data-select-index'))
      if (Number.isInteger(index)) {
        this.applySweepToIndex(index)
      }
    },

    onGlobalPointerUp(event) {
      const session = this.pointerSelection
      if (!session || event.pointerId !== session.pointerId) return
      const startIndex = session.startIndex
      const sweeping = session.sweeping
      const origin = session.origin
      this.clearPointerGesture()
      if (origin === 'list-browse' && !this.selectionMode) return
      if (!sweeping) {
        this.selectOnlyIndex(startIndex)
      }
    },

    onGlobalPointerCancel(event) {
      const session = this.pointerSelection
      if (!session || event.pointerId !== session.pointerId) return
      this.clearPointerGesture()
    },

    clearPointerGesture() {
      if (this.longPressTimer) {
        clearTimeout(this.longPressTimer)
        this.longPressTimer = null
      }
      window.removeEventListener('pointermove', this.onGlobalPointerMove)
      window.removeEventListener('pointerup', this.onGlobalPointerUp)
      window.removeEventListener('pointercancel', this.onGlobalPointerCancel)
      this.pointerSelection = null
    },

    openConfirmDialog(options = {}) {
      this.confirmDialog = {
        ...createDialogState(),
        ...options,
        visible: true,
      }
    },

    closeConfirmDialog() {
      if (this.confirmDialog.busy) return
      this.confirmDialog = createDialogState()
    },

    async handleConfirmDialogConfirm() {
      if (this.confirmDialog.busy) return
      const onConfirm = this.confirmDialog.onConfirm
      if (typeof onConfirm !== 'function') {
        this.closeConfirmDialog()
        return
      }

      this.confirmDialog = {
        ...this.confirmDialog,
        busy: true,
      }

      try {
        await onConfirm()
      } finally {
        this.confirmDialog = createDialogState()
      }
    },

    restoreSelection() {
      if (!this.selectedCount || this.actionBusy) return
      this.closeSelectAllMenu()
      this.openConfirmDialog({
        title: '确认还原',
        message: `确认还原已选中的 ${this.selectedCount} 项吗？\n若目标位置已存在同名项目，系统会自动补编号避免覆盖。`,
        confirmLabel: '还原',
        cancelLabel: '取消',
        tone: 'accent',
        busyLabel: '还原中…',
        onConfirm: () => this.executeRestoreSelection(),
      })
    },

    async executeRestoreSelection() {
      if (!this.selectedCount || this.actionBusy) return
      this.actionBusy = true
      this.actionBusyTitle = '还原中'
      this.actionBusyText = '正在还原所选内容，请稍候…'
      try {
        const res = await fetch(`${API_BASE}/api/trash/restore`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ entry_ids: this.selectedEntries.map(({ item }) => item.id) }),
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        if (data.errors?.length) {
          this.showMessage('error', data.errors.join('；'))
        } else {
          this.showMessage('success', `已还原 ${data.restored} 项。`)
        }
        await this.loadData()
      } catch (err) {
        this.showMessage('error', err?.message || '还原失败')
      } finally {
        this.actionBusy = false
        this.actionBusyTitle = ''
        this.actionBusyText = ''
      }
    },

    hardDeleteSelection() {
      if (!this.selectedCount || this.actionBusy) return
      this.closeSelectAllMenu()
      this.openConfirmDialog({
        title: '确认彻底删除',
        message: `确认彻底删除已选中的 ${this.selectedCount} 项吗？\n此操作会直接移除 trash 中的文件，且无法恢复。`,
        confirmLabel: '彻底删除',
        cancelLabel: '取消',
        tone: 'danger',
        busyLabel: '删除中…',
        onConfirm: () => this.executeHardDeleteSelection(),
      })
    },

    async executeHardDeleteSelection() {
      if (!this.selectedCount || this.actionBusy) return
      this.actionBusy = true
      this.actionBusyTitle = '删除中'
      this.actionBusyText = '正在彻底删除所选内容，请稍候…'
      try {
        const res = await fetch(`${API_BASE}/api/trash/hard-delete`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ entry_ids: this.selectedEntries.map(({ item }) => item.id) }),
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        if (data.errors?.length) {
          this.showMessage('error', data.errors.join('；'))
        } else {
          this.showMessage('success', `已删除 ${data.deleted} 项。`)
        }
        await this.loadData()
      } catch (err) {
        this.showMessage('error', err?.message || '删除失败')
      } finally {
        this.actionBusy = false
        this.actionBusyTitle = ''
        this.actionBusyText = ''
      }
    },

    clearTrash() {
      if (!this.totalCount || this.actionBusy) return
      this.closeSelectAllMenu()
      this.openConfirmDialog({
        title: '确认清空回收站',
        message: '确认清空回收站吗？\n此操作会物理删除 trash 中的全部文件和目录，且无法恢复。',
        confirmLabel: '清空回收站',
        cancelLabel: '取消',
        tone: 'danger',
        busyLabel: '清空中…',
        onConfirm: () => this.executeClearTrash(),
      })
    },

    async executeClearTrash() {
      if (!this.totalCount || this.actionBusy) return
      this.actionBusy = true
      this.actionBusyTitle = '清空中'
      this.actionBusyText = '正在清空回收站，请稍候…'
      try {
        const res = await fetch(`${API_BASE}/api/trash`, { method: 'DELETE' })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        if (data.errors?.length) {
          this.showMessage('error', data.errors.join('；'))
        } else {
          this.showMessage('success', `已清空回收站，共删除 ${data.deleted} 项。`)
        }
        await this.loadData()
      } catch (err) {
        this.showMessage('error', err?.message || '清空回收站失败')
      } finally {
        this.actionBusy = false
        this.actionBusyTitle = ''
        this.actionBusyText = ''
      }
    },

    onWindowKeydown(event) {
      if (this.selectionDetailsOpen && event.key === 'Escape') {
        event.preventDefault()
        this.closeSelectionDetails()
        return
      }
      if (!this.selectionMode) return
      const key = event.key.toLowerCase()
      if ((event.ctrlKey || event.metaKey) && key === 'a') {
        event.preventDefault()
        this.selectAllOfCurrentType()
      }
      if (event.key === 'Escape') {
        event.preventDefault()
        if (this.selectedCount) {
          this.clearSelection()
        } else {
          this.toggleSelectionMode(false)
        }
      }
    },

    onWindowPointerDown(event) {
      if (!this.selectAllMenuOpen) return
      const menu = this.$refs.selectionIslandMenu
      if (menu && typeof menu.contains === 'function' && menu.contains(event.target)) {
        return
      }
      this.closeSelectAllMenu()
    },

    setupResizeObserver() {
      if (!this.$refs.itemGrid) return
      if (this.resizeObserver) {
        this.resizeObserver.disconnect()
        this.resizeObserver = null
      }

      this.resizeObserver = new ResizeObserver(() => {
        requestAnimationFrame(() => {
          if (!this.$refs.itemGrid) return

          if (this.isPagedBrowseMode) {
            const anchor = this.captureViewportAnchor()
            if (anchor) {
              this.pendingViewAnchor = anchor
            }
            this.refreshObservedGrid()
            return
          }

          this.measureItemGridMetrics()
          if (this.isVirtualizedMode) {
            this.syncVirtualWindow(true)
            if (this.isSelectionGridMode) {
              this.measureSelectionRowHeight()
            }
          }
        })
      })
      this.resizeObserver.observe(this.$refs.itemGrid)
    },

    teardownResizeObserver() {
      if (this.resizeObserver) {
        this.resizeObserver.disconnect()
        this.resizeObserver = null
      }
    },
  },
}
</script>

<style scoped lang="css">
.page {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.page-main {
  display: flex;
  flex: 1 1 auto;
  min-height: 0;
  flex-direction: column;
}

.page--paged {
  height: calc(100dvh - 5rem);
  min-height: calc(100vh - 5rem);
  overflow: hidden;
}

.page--paged .empty-hint,
.page--paged .selection-grid,
.page--paged .photo-grid,
.page--paged .list-view {
  flex: 1 1 auto;
  min-height: 0;
}

.page--paged .list-view {
  overflow-y: auto !important;
}

.page--paged .selection-wrap {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.page--paged .selection-wrap :deep(.media-card) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page--paged .selection-wrap :deep(.media-card__visual) {
  flex: 1 1 0;
  min-height: 0;
  aspect-ratio: auto;
}

.page--paged .selection-island {
  position: absolute;
  right: 1.5rem;
  bottom: 4.25rem;
}

.page--paged .empty-hint {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.page-note {
  margin: 0;
  padding: 0.8rem 1rem;
  border-radius: 12px;
  font-size: 0.9rem;
  font-weight: 600;
}

.page-note--success {
  background: rgba(220, 252, 231, 0.9);
  color: #166534;
}

.page-note--error {
  background: rgba(254, 226, 226, 0.92);
  color: #991b1b;
}

.vm-btns {
  display: flex;
  align-items: center;
  background: #f1f5f9;
  border-radius: 8px;
  padding: 2px;
  gap: 1px;
}

.vm-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  padding: 0;
  transition: background 150ms ease, color 150ms ease, box-shadow 150ms ease, opacity 150ms ease;
}

.vm-btn:hover:not(:disabled) {
  background: #e2e8f0;
  color: #1e293b;
}

.vm-btn.active {
  background: #fff;
  color: #1e293b;
  box-shadow: 0 1px 3px rgba(0,0,0,.12);
}

.empty-hint {
  @apply border-2 border-dashed border-slate-300 bg-slate-50 rounded-xl py-16 text-center text-slate-400 text-sm;
}

.empty-hint__icon {
  @apply text-5xl block mb-3;
}

.selection-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
  align-items: start;
}

.selection-wrap {
  min-width: 0;
  cursor: pointer;
  user-select: none;
  touch-action: pan-y;
}

.selection-wrap.is-disabled {
  cursor: not-allowed;
}

.photo-grid {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-pagination-host {
  padding-top: 0.12rem;
}

.page-pagination-host--selection {
  padding-bottom: 0.08rem;
}

.jl-row {
  display: flex;
  flex-direction: row;
  gap: 4px;
  overflow: hidden;
}

.photo-wrap {
  overflow: hidden;
  flex-shrink: 0;
  height: 100%;
}

.photo-grid--masonry {
  width: 100%;
}

.photo-wrap--masonry {
  position: absolute;
  overflow: hidden;
  border-radius: 10px;
}

.photo-wrap--masonry .photo-card {
  border-radius: 10px;
}

.photo-grid--masonry-skeleton {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  padding: 4px 0;
}

.masonry-skeleton-col {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.masonry-skeleton-item {
  border-radius: 10px;
  width: 100%;
  flex-shrink: 0;
}

.photo-skeleton {
  @apply w-full h-full rounded-xl overflow-hidden flex items-center justify-center;
  background: linear-gradient(90deg, #e2e8f0 25%, #f1f5f9 50%, #e2e8f0 75%);
  background-size: 200% 100%;
  animation: skeleton-wave 1.4s ease-in-out infinite;
}

.skeleton-label {
  @apply text-slate-400 text-xs font-mono tracking-widest select-none;
}

.photo-card {
  @apply relative cursor-pointer rounded-xl overflow-hidden shadow-md;
  width: 100%;
  height: 100%;
  transition: box-shadow 200ms ease, transform 200ms ease;
}

.photo-card:hover {
  @apply shadow-xl -translate-y-0.5;
}

.photo-img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 300ms ease;
}

.photo-card:hover .photo-img {
  transform: scale(1.03);
}

.album-badge {
  @apply absolute top-2 right-2 flex flex-col items-center gap-0.5 px-2 py-1 rounded-lg;
  background: rgba(255, 255, 255, 0.90);
  box-shadow: 0 1px 4px rgba(0,0,0,.15);
  pointer-events: none;
}

.badge-icon {
  font-size: 1rem;
}

.badge-name {
  @apply text-slate-800 text-xs font-semibold text-center select-none;
  max-width: 6rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.badge-count {
  @apply select-none;
  color: rgba(100, 116, 139, 0.8);
  font-size: 0.65rem;
}

@keyframes skeleton-wave {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@media (orientation: landscape) {
  .selection-grid {
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 16px;
  }
}

@media (orientation: portrait) {
  .selection-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }
}

.list-view {
  display: flex;
  flex-direction: column;
}

.list-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 150ms ease, box-shadow 150ms ease, opacity 150ms ease;
}

.list-row:hover { background: #f1f5f9; }

.list-row.is-selected {
  background: #e8eef8;
  box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.08);
}

.list-row.is-disabled {
  opacity: 0.45;
}

.list-pick {
  width: 26px;
  height: 26px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 2px solid rgba(15, 23, 42, 0.85);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.94);
  color: #ffffff;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.12);
  padding: 0;
  cursor: pointer;
  transition: transform 140ms ease, background 140ms ease, border-color 140ms ease;
}

.list-pick:hover:not(:disabled) {
  transform: scale(1.04);
}

.list-pick:disabled {
  cursor: not-allowed;
}

.list-row.is-selected .list-pick {
  border-color: #0f172a;
  background: #0f172a;
}

.list-pick__mark {
  font-size: 0.8rem;
  font-weight: 700;
  line-height: 1;
}

.list-thumb-wrap {
  width: 50px;
  height: 50px;
  flex-shrink: 0;
  border-radius: 6px;
  overflow: hidden;
  background: #e2e8f0;
}

.list-thumb-skeleton {
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, #e2e8f0 25%, #f1f5f9 50%, #e2e8f0 75%);
  background-size: 200% 100%;
  animation: skeleton-wave 1.4s ease-in-out infinite;
}

.list-thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.list-main {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
}

.list-title-row {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  min-width: 0;
  width: 100%;
}

.list-type-pill {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 2.4rem;
  height: 1.55rem;
  padding: 0 0.55rem;
  border-radius: 999px;
  background: #e2e8f0;
  color: #334155;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.list-name {
  flex: 1;
  min-width: 0;
  font-size: 0.875rem;
  color: #334155;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.page--paged .list-view {
  flex: 1 1 auto;
  min-height: 0;
}
</style>