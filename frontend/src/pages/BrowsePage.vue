<template>
  <section class="page">
    <BreadcrumbHeader
      :show-back="true"
      :crumbs="headerCrumbs"
      :item-count="totalCount"
      :show-sort="true"
      :sort-by="sortBy"
      :sort-dir="sortDir"
      @back="goBackOneLevel"
      @update:sortBy="onSortModeSelect"
      @toggle-sort-dir="toggleSortDir"
    >
      <div class="vm-btns" role="group" aria-label="视图模式">
        <button
          class="vm-btn"
          :class="{ active: viewMode === 'grid' }"
          title="大缩略图"
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
    </BreadcrumbHeader>

    <LoadingSpinner v-if="loading" />

    <div v-else-if="!items.length" class="empty-hint">
      <span class="empty-hint__icon">📂</span>
      <p>此页面尚无内容。</p>
    </div>

    <div
      v-else-if="selectionMode && viewMode === 'grid'"
      ref="itemGrid"
      class="selection-grid"
      :style="selectionGridVirtualStyle"
    >
      <div
        v-for="entry in visibleSelectionEntries"
        :key="itemKey(entry.item, entry.index)"
        class="selection-wrap"
        :class="{
          'is-selected': isItemSelected(entry.item, entry.index),
          'is-disabled': isItemDisabled(entry.item),
        }"
        :data-index="entry.index"
        :data-select-index="entry.index"
        @pointerdown="onSelectionPointerDown($event, entry.item, entry.index)"
      >
        <MediaItemCard
          :src="resolvedUrl(entry.item)"
          :alt="entry.item.name || ''"
          :info-text="displayInfoText(entry.item)"
          :info-title="selectionInfoMode === 'tags' ? '当前显示 Tag，点击切换为文件名' : '当前显示文件名，点击切换为 Tag'"
          :item-type="entry.item.type"
          :selected="isItemSelected(entry.item, entry.index)"
          :disabled="isItemDisabled(entry.item)"
          @toggle-select="onItemSelectionButtonClick(entry.item, entry.index)"
          @toggle-info="toggleInfoDisplayMode"
          @details="onReservedDetailsClick(entry.item, entry.index)"
        />
      </div>
    </div>

    <div v-else-if="viewMode === 'grid'" ref="itemGrid" class="photo-grid">
      <div
        v-for="(row, ri) in justifiedRows"
        :key="ri"
        class="jl-row"
        :style="{ height: row.height + 'px' }"
      >
        <div
          v-for="item in row.items"
          :key="item.public_id || item.id || item._idx"
          class="photo-wrap"
          :data-index="item._idx"
          :style="{ width: item.computedWidth + 'px' }"
        >
          <div v-if="!resolvedUrl(item)" class="photo-skeleton">
            <span class="skeleton-label">...</span>
          </div>

          <div v-else class="photo-card" @click="openItem(item)">
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
              <span class="badge-count">{{ item.count }} 张</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else ref="itemGrid" class="list-view" :style="listViewVirtualStyle">
      <div
        v-for="entry in visibleListEntries"
        :key="entry.item.public_id || entry.item.id || entry.index"
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
            <span class="list-name">{{ entry.item.name || entry.item.full_filename || '未知文件' }}</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="selectionMode" class="selection-island">
      <span class="selection-island__count">{{ selectionSummaryText }}</span>
      <button
        class="selection-island__btn"
        type="button"
        :disabled="!selectedCount"
        @click="openSelectionDetailsFromIsland"
      >详情</button>
      <div
        ref="selectionIslandMenu"
        class="selection-island__menu-wrap"
        :class="{ 'is-open': selectAllMenuOpen }"
      >
        <button
          class="selection-island__btn"
          type="button"
          :aria-expanded="hasMixedSelectableTypes ? (selectAllMenuOpen ? 'true' : 'false') : 'false'"
          @click="handleSelectAllButtonClick"
        >全选</button>
        <div v-if="hasMixedSelectableTypes" class="selection-island__submenu">
          <button class="selection-island__submenu-btn" type="button" @click="onSelectAllTypeClick('album')">相册</button>
          <button class="selection-island__submenu-btn" type="button" @click="onSelectAllTypeClick('image')">图片</button>
        </div>
      </div>
      <button class="selection-island__btn" type="button" @click="clearSelection">取消选择</button>
    </div>

    <SelectionDetailOverlay
      :visible="selectionDetailsOpen"
      :layer-style="selectionDetailsLayerStyle"
      :panel-style="selectionDetailsPanelStyle"
      :preview-items="selectionDetailPreviewItems"
      :is-multi="selectionDetailPreviewItems.length > 1"
      :name-field="selectionDetailNameField"
      :tags-field="selectionDetailTagsField"
      :size-field="selectionDetailSizeField"
      :size-label="selectionDetailSizeLabel"
      :imported-field="selectionDetailImportedField"
      :created-field="selectionDetailCreatedField"
      :primary-action-label="selectionDetailPrimaryActionLabel"
      :can-open-primary-action="canOpenPrimaryActionFromDetails"
      @close="closeSelectionDetails"
      @analysis="onReservedAnalysisClick"
      @delete="onReservedDeleteClick"
      @open-primary="openPrimaryFromDetails"
    />
  </section>
</template>

<script>
import LoadingSpinner from '../components/LoadingSpinner.vue'
import BreadcrumbHeader from '../components/BreadcrumbHeader.vue'
import MediaItemCard from '../components/MediaItemCard.vue'
import SelectionDetailOverlay from '../components/SelectionDetailOverlay.vue'

const API_BASE = 'http://127.0.0.1:8000'
const POLL_MS = 80
const RADIUS = 50
const DEBOUNCE_MS = 300
const LONG_PRESS_MS = 220
const TAG_BATCH_SIZE = 120
const LIST_ROW_HEIGHT = 62
const LIST_OVERSCAN_ROWS = 12
const SELECTION_INFO_HEIGHT = 56
const SELECTION_OVERSCAN_ROWS = 2
const SELECTION_LANDSCAPE_COLS = 5
const SELECTION_PORTRAIT_COLS = 3
const SELECTION_LANDSCAPE_GAP = 16
const SELECTION_PORTRAIT_GAP = 12

export default {
  name: 'BrowsePage',
  components: { LoadingSpinner, BreadcrumbHeader, MediaItemCard, SelectionDetailOverlay },

  data() {
    return {
      items: [],
      loading: true,
      cacheUrls: {},
      pollTimer: null,
      taskId: null,
      observer: null,
      debounceTimer: null,
      resizeObserver: null,
      lastCenter: -1,
      imgDimensions: {},
      containerWidth: 0,
      viewMode: 'grid',
      sortBy: 'alpha',
      sortDir: 'asc',
      albumInfo: null,
      selectionMode: false,
      viewModeBeforeSelection: 'grid',
      selectionInfoMode: 'name',
      selectedMap: {},
      selectionTypeLock: null,
      selectionAnchorIndex: null,
      pointerSelection: null,
      longPressTimer: null,
      suppressNextListClick: false,
      tagNameMap: {},
      tagsLoading: false,
      tagFetchSerial: 0,
      scrollTop: typeof window !== 'undefined' ? (window.scrollY || window.pageYOffset || 0) : 0,
      viewportHeight: typeof window !== 'undefined' ? window.innerHeight : 0,
      virtualStartIndex: 0,
      virtualEndIndex: 0,
      virtualAnchorIndex: 0,
      virtualContainerTop: 0,
      selectionRowHeight: 0,
      scrollFrameId: null,
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
      selectionDetailFetchSerial: 0,
      selectAllMenuOpen: false,
    }
  },

  computed: {
    dateGroup() {
      return this.$route.params.group || ''
    },
    albumPath() {
      const raw = this.$route.params.albumPath
      if (!raw) return ''
      return Array.isArray(raw) ? raw.join('/') : raw
    },
    isAlbumMode() {
      return this.albumPath.length > 0
    },
    fullAlbumPath() {
      if (!this.albumPath) return ''
      return `${this.dateGroup}/${this.albumPath}`
    },
    headerCrumbs() {
      const crumbs = [
        { label: '日期视图', title: '日期视图', to: '/calendar' },
      ]

      if (!this.isAlbumMode) {
        crumbs.push({ label: this.dateGroup, current: true })
        return crumbs
      }

      crumbs.push({
        label: this.dateGroup,
        title: this.dateGroup,
        to: `/calendar/${this.dateGroup}`,
      })

      const segments = this.albumPath.split('/').filter(Boolean)
      for (let i = 0; i < segments.length; i++) {
        const isLast = i === segments.length - 1
        const segPath = segments.slice(0, i + 1).join('/')
        const ancestorTitle = this.getAncestorTitle(i, segments[i])
        if (isLast) {
          crumbs.push({
            label: this.bcLabel(this.albumInfo?.title || segments[i]),
            title: this.albumInfo?.title || segments[i],
            current: true,
          })
        } else {
          crumbs.push({
            label: this.bcLabel(ancestorTitle),
            title: ancestorTitle,
            to: `/calendar/${this.dateGroup}/${segPath}`,
          })
        }
      }
      return crumbs
    },
    totalCount() {
      return this.items.length
    },
    isPhotoGridMode() {
      return this.viewMode === 'grid' && !this.selectionMode
    },
    isSelectionGridMode() {
      return this.selectionMode && this.viewMode === 'grid'
    },
    isVirtualizedMode() {
      return this.isSelectionGridMode || this.viewMode === 'list'
    },
    photoGridRowCount() {
      return this.isPhotoGridMode ? this.justifiedRows.length : 0
    },
    selectionColumnCount() {
      if (typeof window === 'undefined') return SELECTION_PORTRAIT_COLS
      return window.matchMedia('(orientation: landscape)').matches
        ? SELECTION_LANDSCAPE_COLS
        : SELECTION_PORTRAIT_COLS
    },
    selectionGridGapPx() {
      return this.selectionColumnCount === SELECTION_LANDSCAPE_COLS
        ? SELECTION_LANDSCAPE_GAP
        : SELECTION_PORTRAIT_GAP
    },
    effectiveSelectionRowHeight() {
      if (this.selectionRowHeight > 0) return this.selectionRowHeight

      const width = this.containerWidth || (typeof window !== 'undefined' ? window.innerWidth - 48 : 800)
      const totalGap = this.selectionGridGapPx * Math.max(0, this.selectionColumnCount - 1)
      const cardWidth = Math.max(0, (width - totalGap) / this.selectionColumnCount)
      return Math.max(SELECTION_INFO_HEIGHT + 80, Math.round(cardWidth + SELECTION_INFO_HEIGHT + 2))
    },
    visibleSelectionEntries() {
      const start = this.isSelectionGridMode ? this.virtualStartIndex : 0
      const end = this.isSelectionGridMode ? this.virtualEndIndex : this.items.length
      return this.items.slice(start, end).map((item, offset) => ({ item, index: start + offset }))
    },
    selectionGridVirtualStyle() {
      if (!this.isSelectionGridMode) return null

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
      const start = this.viewMode === 'list' ? this.virtualStartIndex : 0
      const end = this.viewMode === 'list' ? this.virtualEndIndex : this.items.length
      return this.items.slice(start, end).map((item, offset) => ({ item, index: start + offset }))
    },
    listViewVirtualStyle() {
      if (this.viewMode !== 'list') return null

      return {
        paddingTop: `${this.virtualStartIndex * LIST_ROW_HEIGHT}px`,
        paddingBottom: `${Math.max(0, (this.items.length - this.virtualEndIndex) * LIST_ROW_HEIGHT)}px`,
      }
    },
    justifiedRows() {
      const width = this.containerWidth || (typeof window !== 'undefined' ? window.innerWidth - 48 : 800)
      const gap = 4
      const targetHeight = 440
      const items = this.items
      if (!items.length) return []

      const rows = []
      let rowStart = 0
      let rowAspectRatio = 0

      for (let i = 0; i < items.length; i++) {
        const key = items[i].id || items[i].public_id
        const dims = this.imgDimensions[key] || { w: 4, h: 3 }
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
            const item = items[j]
            const itemKey = item.id || item.public_id
            const dimsForItem = this.imgDimensions[itemKey] || { w: 4, h: 3 }
            rowItems.push({
              ...item,
              _idx: j,
              computedWidth: Math.round((dimsForItem.w / dimsForItem.h) * actualHeight),
            })
          }
          rows.push({ items: rowItems, height: actualHeight })
          rowStart = i + 1
          rowAspectRatio = 0
        }
      }
      return rows
    },
    selectedCount() {
      return Object.keys(this.selectedMap).length
    },
    selectionSummaryText() {
      if (!this.selectedCount) return '已选 0 项'
      if (this.selectionTypeLock === 'album') return `已选 ${this.selectedCount} 个相册`
      if (this.selectionTypeLock === 'image') return `已选 ${this.selectedCount} 张图片`
      return `已选 ${this.selectedCount} 项`
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
    selectionDetailPreviewItems() {
      return this.selectedEntries.map(({ item, index }) => ({
        key: this.itemKey(item, index),
        name: this.detailNameText(item),
        type: item?.type || 'image',
        previewUrl: this.detailPreviewUrl(item),
        aspectRatio: this.detailAspectRatio(item),
      }))
    },
    selectionDetailsLayerStyle() {
      return this.selectionDetailsBounds
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
      return this.buildDetailField(this.selectedEntries.map(({ item }) => this.detailNameText(item)))
    },
    selectionDetailTagsField() {
      return this.buildDetailField(
        this.selectedEntries.map(({ item }) => this.detailTagTextForItem(item)),
        { emptyText: '' },
      )
    },
    selectionDetailSizeField() {
      return this.buildDetailField(this.selectedEntries.map(({ item }) => this.detailSizeText(item)))
    },
    selectionDetailSizeLabel() {
      return this.selectionDetailType === 'album' ? '图片数量' : '尺寸'
    },
    selectionDetailImportedField() {
      return this.buildDetailField(this.selectedEntries.map(({ item }) => this.detailImportedText(item)))
    },
    selectionDetailCreatedField() {
      return this.buildDetailField(this.selectedEntries.map(({ item }) => this.detailCreatedText(item)))
    },
    selectionDetailType() {
      return this.selectedEntries[0]?.item?.type || null
    },
    selectionDetailPrimaryActionLabel() {
      return this.selectionDetailType === 'album' ? '查看相册' : '查看原图'
    },
    canOpenPrimaryActionFromDetails() {
      if (this.selectedEntries.length !== 1) return false
      const entry = this.selectedEntries[0]
      if (entry?.item?.type === 'image') {
        return Number.isInteger(entry?.item?.id)
      }
      return entry?.item?.type === 'album' && typeof entry?.item?.album_path === 'string' && entry.item.album_path.length > 0
    },
  },

  watch: {
    '$route.params': {
      handler() { this.loadData() },
      deep: true,
    },
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
    window.addEventListener('resize', this.onResize)
    window.addEventListener('scroll', this.onWindowScroll, { passive: true })
    window.addEventListener('keydown', this.onWindowKeydown)
    window.addEventListener('pointerdown', this.onWindowPointerDown)
  },

  beforeUnmount() {
    this.teardownObserver()
    this.teardownResizeObserver()
    this.stopPoll()
    this.clearPointerGesture()
    this.unlockPageScroll()
    window.removeEventListener('resize', this.onResize)
    window.removeEventListener('scroll', this.onWindowScroll)
    window.removeEventListener('keydown', this.onWindowKeydown)
    window.removeEventListener('pointerdown', this.onWindowPointerDown)
    if (this.scrollFrameId) {
      cancelAnimationFrame(this.scrollFrameId)
      this.scrollFrameId = null
    }
  },

  methods: {
    async loadData() {
      this.loading = true
      this.sortBy = this.isAlbumMode ? 'alpha' : 'date'
      this.sortDir = 'asc'
      this.cacheUrls = {}
      this.imgDimensions = {}
      this.lastCenter = -1
      this.selectionRowHeight = 0
      this.albumInfo = null
      this.closeSelectionDetails()
      this.closeSelectAllMenu()
      this.clearSelection()
      this.clearPointerGesture()
      this.tagFetchSerial += 1
      this.tagsLoading = false
      this.virtualStartIndex = 0
      this.virtualEndIndex = 0
      this.virtualAnchorIndex = 0
      this.virtualContainerTop = 0
      this.scrollTop = typeof window !== 'undefined' ? (window.scrollY || window.pageYOffset || 0) : 0
      this.viewportHeight = typeof window !== 'undefined' ? window.innerHeight : this.viewportHeight
      this.teardownObserver()
      this.teardownResizeObserver()
      this.stopPoll()

      if (!this.selectionMode) {
        this.viewMode = 'grid'
      }

      try {
        if (this.isAlbumMode) {
          await this.fetchAlbum()
        } else {
          await this.fetchDateGroup()
        }
      } catch {
        this.items = []
        this.albumInfo = null
      } finally {
        this.loading = false
      }

      window.scrollTo({ top: 0, behavior: 'instant' })
      this.refreshObservedGrid()
      if (this.selectionInfoMode === 'tags') {
        this.ensureTagLabelsLoaded()
      }
    },

    async fetchDateGroup() {
      const res = await fetch(`${API_BASE}/api/dates/${this.dateGroup}/items`)
      if (!res.ok) {
        this.items = []
        return
      }
      const data = await res.json()
      this.applyFetchedItems(data.items)
    },

    async fetchAlbum() {
      const res = await fetch(`${API_BASE}/api/albums/by-path/${encodeURI(this.fullAlbumPath)}`)
      if (!res.ok) {
        this.items = []
        return
      }
      const data = await res.json()
      this.albumInfo = data.album || null
      this.applyFetchedItems(data.items)
    },

    applyFetchedItems(rawItems) {
      const nextItems = this.sortItems(rawItems || [])
      const nextCacheUrls = {}
      const nextDimensions = {}

      for (const item of nextItems) {
        if (item.id && item.cache_thumb_url) {
          nextCacheUrls[item.id] = item.cache_thumb_url
        }

        const key = item.id || item.public_id
        const width = Number(item?.width)
        const height = Number(item?.height)
        if (key && Number.isFinite(width) && Number.isFinite(height) && width > 0 && height > 0) {
          nextDimensions[key] = { w: width, h: height }
        }
      }

      this.items = nextItems
      this.virtualStartIndex = 0
      this.virtualEndIndex = nextItems.length
      this.cacheUrls = nextCacheUrls
      this.imgDimensions = nextDimensions
    },

    getAncestorTitle(segIndex, fallback) {
      const ancestors = this.albumInfo?.ancestors || []
      if (segIndex < ancestors.length) return ancestors[segIndex].title
      return fallback
    },

    resolvedUrl(item) {
      if (!item) return ''
      if (item.id) {
        const cached = this.cacheUrls[item.id]
        if (cached) return `${API_BASE}${cached}`
        if (item.cache_thumb_url) return `${API_BASE}${item.cache_thumb_url}`
      }
      if (item.thumb_url) return `${API_BASE}${item.thumb_url}`
      return ''
    },

    openItem(item) {
      if (this.selectionMode) return
      if (item.type === 'album') {
        if (item.album_path) {
          this.$router.push(`/calendar/${item.album_path}`)
        } else if (item.public_id) {
          const base = this.isAlbumMode
            ? `/calendar/${this.dateGroup}/${this.albumPath}`
            : `/calendar/${this.dateGroup}`
          this.$router.push(`${base}/${encodeURIComponent(item.name)}`)
        }
      } else if (item.id) {
        fetch(`${API_BASE}/api/images/${item.id}/open`).catch(() => {})
      }
    },

    openPrimaryFromDetails() {
      if (!this.canOpenPrimaryActionFromDetails) return
      const target = this.selectedEntries[0]?.item
      if (!target) return

      if (target.type === 'album') {
        if (!target.album_path) return
        fetch(`${API_BASE}/api/albums/open-by-path/${encodeURI(target.album_path)}`).catch(() => {})
        return
      }

      if (!target.id) return
      fetch(`${API_BASE}/api/images/${target.id}/open`).catch(() => {})
    },

    openSelectionDetailsFromIsland() {
      if (!this.selectedCount) return
      this.openSelectionDetails()
    },

    openSelectionDetails() {
      if (!this.selectedCount) return
      this.updateSelectionDetailsBounds()
      this.selectionDetailsOpen = true
      this.lockPageScroll()
      this.$nextTick(() => {
        this.updateSelectionDetailsBounds()
      })
      this.ensureTagLabelsLoaded(true)
      this.fetchSelectionDetailMetadata()
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

      const visibleWidth = Math.max(0, window.innerWidth - visibleLeft - visibleRight)
      const visibleHeight = Math.max(0, window.innerHeight - visibleTop - visibleBottom)

      this.selectionDetailsHostWidth = visibleWidth
      this.selectionDetailsHostHeight = visibleHeight
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

    detailNameText(item) {
      return item?.name || item?.full_filename || '未命名'
    },

    detailPreviewUrl(item) {
      return this.resolvedUrl(item)
    },

    detailAspectRatio(item) {
      const width = Number(item?.width)
      const height = Number(item?.height)
      if (!Number.isFinite(width) || width <= 0 || !Number.isFinite(height) || height <= 0) {
        return '4 / 3'
      }
      return `${width} / ${height}`
    },

    itemHasDetailMetadata(item) {
      if (!item || item.type !== 'image') return true
      return ['file_size', 'imported_at', 'file_created_at'].every(field => (
        Object.prototype.hasOwnProperty.call(item, field)
      ))
    },

    async fetchSelectionDetailMetadata() {
      const imageIds = this.selectedEntries
        .map(({ item }) => item)
        .filter(item => item?.type === 'image' && Number.isInteger(item?.id) && !this.itemHasDetailMetadata(item))
        .map(item => item.id)

      if (!imageIds.length) return

      const requestSerial = ++this.selectionDetailFetchSerial

      try {
        const res = await fetch(`${API_BASE}/api/images/meta?ids=${imageIds.join(',')}`)
        if (!res.ok) return

        const data = await res.json()
        if (requestSerial !== this.selectionDetailFetchSerial) return

        const metaMap = new Map(
          (data.items || []).map(meta => [meta.id, meta])
        )
        if (!metaMap.size) return

        this.items = this.items.map(item => {
          if (item?.type !== 'image' || !Number.isInteger(item?.id)) return item
          const meta = metaMap.get(item.id)
          if (!meta) return item
          return {
            ...item,
            ...meta,
            tags: Array.isArray(meta.tags) ? meta.tags : (item.tags || []),
            name: meta.name || item.name,
          }
        })
      } catch {
        // ignore metadata hydration failures and keep current values visible
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
      if (!item) return ''

      if (item.type === 'album') {
        const photoCount = Number(item?.photo_count)
        if (Number.isFinite(photoCount) && photoCount >= 0) {
          return `${photoCount} 张`
        }

        const fallbackCount = Number(item?.count)
        if (Number.isFinite(fallbackCount) && fallbackCount >= 0) {
          return `${fallbackCount} 张`
        }
        return ''
      }

      if (item.type !== 'image') return ''

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
      if (!item || item.type !== 'image') return ''
      return this.formatDateTime(item.imported_at)
    },

    detailCreatedText(item) {
      if (!item) return ''
      if (item.type === 'album') {
        return this.formatDateTime(item.created_at)
      }
      if (item.type !== 'image') return ''
      return this.formatDateTime(item.file_created_at)
    },

    goBackOneLevel() {
      if (this.isAlbumMode) {
        const segments = this.albumPath.split('/').filter(Boolean)
        if (segments.length > 1) {
          const parentPath = segments.slice(0, -1).join('/')
          this.$router.push(`/calendar/${this.dateGroup}/${parentPath}`)
        } else {
          this.$router.push(`/calendar/${this.dateGroup}`)
        }
      } else {
        this.$router.push('/calendar')
      }
    },

    onImgLoad(item, evt) {
      const { naturalWidth: width, naturalHeight: height } = evt.target
      if (!width || !height) return
      const key = item.id || item.public_id
      const existing = this.imgDimensions[key]
      if (!existing || existing.w !== width || existing.h !== height) {
        this.imgDimensions = { ...this.imgDimensions, [key]: { w: width, h: height } }
      }
    },

    onResize() {
      this.viewportHeight = typeof window !== 'undefined' ? window.innerHeight : this.viewportHeight
      if (this.$refs.itemGrid) {
        this.containerWidth = this.$refs.itemGrid.offsetWidth
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

    queueCacheTrigger(centerIdx) {
      if (!Number.isInteger(centerIdx) || centerIdx < 0) return
      clearTimeout(this.debounceTimer)
      this.debounceTimer = setTimeout(() => {
        if (centerIdx !== this.lastCenter) {
          this.lastCenter = centerIdx
          this.triggerCacheAt(centerIdx)
        }
      }, DEBOUNCE_MS)
    },

    syncVirtualWindow(force = false) {
      if (!this.$refs.itemGrid) return

      this.scrollTop = window.scrollY || window.pageYOffset || 0
      this.viewportHeight = window.innerHeight || this.viewportHeight
      this.containerWidth = this.$refs.itemGrid.offsetWidth
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
        force ||
        startIndex !== this.virtualStartIndex ||
        endIndex !== this.virtualEndIndex ||
        anchorIndex !== this.virtualAnchorIndex

      if (!rangeChanged) return

      this.virtualStartIndex = startIndex
      this.virtualEndIndex = endIndex
      this.virtualAnchorIndex = anchorIndex
      this.queueCacheTrigger(anchorIndex)

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
        this.syncVirtualWindow(true)
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

    bcLabel(str) {
      if (!str) return ''
      return str.length > 20 ? str.slice(0, 20) + '…' : str
    },

    itemDateTs(item) {
      const ts = Number(item?.sort_ts)
      if (Number.isFinite(ts)) return ts
      const fallbackId = Number(item?.id)
      return Number.isFinite(fallbackId) ? fallbackId : 0
    },

    itemAlphaKey(item) {
      return (item?.name || item?.full_filename || '').toString()
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
      this.items = this.sortItems(this.items)
      if (this.loading) return
      this.clearSelection()
      this.refreshObservedGrid()
      if (this.selectionInfoMode === 'tags') {
        this.ensureTagLabelsLoaded()
      }
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

    switchViewMode(mode) {
      if (!['grid', 'list'].includes(mode)) return
      const modeChanged = this.viewMode !== mode
      const wasSelecting = this.selectionMode
      this.closeSelectAllMenu()

      this.viewMode = mode

      if (wasSelecting) {
        this.selectionMode = false
        this.clearSelection()
        this.clearPointerGesture()
        this.suppressNextListClick = false
      }

      if (wasSelecting || !modeChanged) {
        this.refreshObservedGrid()
      }
    },

    toggleSelectionMode(forceValue = null) {
      const nextValue = typeof forceValue === 'boolean' ? forceValue : !this.selectionMode
      if (nextValue === this.selectionMode) return
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

      if (this.selectionInfoMode === 'tags') {
        this.ensureTagLabelsLoaded()
      }
      this.refreshObservedGrid()
    },

    itemKey(item, index) {
      if (item?.type === 'album') {
        return `album:${item.public_id || item.album_path || item.id || index}`
      }
      return `image:${item?.id || item?.name || index}`
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
      if (this.selectedMap[key]) {
        if (useAsAnchor) this.selectionAnchorIndex = index
        return
      }
      this.selectionTypeLock = item.type
      this.selectedMap = { ...this.selectedMap, [key]: true }
      if (useAsAnchor || this.selectionAnchorIndex === null) {
        this.selectionAnchorIndex = index
      }
    },

    removeIndexFromSelection(index) {
      const key = this.itemKey(this.items[index], index)
      if (!this.selectedMap[key]) return
      const next = { ...this.selectedMap }
      delete next[key]
      this.selectedMap = next
      if (!Object.keys(next).length) {
        this.selectionTypeLock = null
        this.selectionAnchorIndex = null
      }
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

    toggleIndexSelection(index) {
      const item = this.items[index]
      if (!item || this.isItemDisabled(item)) return
      const key = this.itemKey(item, index)
      if (this.selectedMap[key]) {
        this.removeIndexFromSelection(index)
      } else {
        this.addIndexToSelection(index, true)
      }
    },

    applyRangeSelection(targetIndex, additive = false) {
      const targetItem = this.items[targetIndex]
      if (!targetItem) return
      const anchorIndex = this.selectionAnchorIndex === null ? targetIndex : this.selectionAnchorIndex
      const anchorItem = this.items[anchorIndex]
      const lockedType = this.selectionTypeLock || targetItem.type || anchorItem?.type
      if (!lockedType) return

      const start = Math.min(anchorIndex, targetIndex)
      const end = Math.max(anchorIndex, targetIndex)
      const next = additive ? { ...this.selectedMap } : {}

      this.selectionTypeLock = lockedType
      for (let i = start; i <= end; i++) {
        const item = this.items[i]
        if (!item || item.type !== lockedType) continue
        next[this.itemKey(item, i)] = true
      }

      this.selectedMap = next
      this.selectionAnchorIndex = targetIndex
      if (!Object.keys(next).length) {
        this.selectionTypeLock = null
      }
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

    onWindowPointerDown(event) {
      if (!this.selectAllMenuOpen) return
      const host = this.$refs.selectionIslandMenu
      if (host && typeof host.contains === 'function' && host.contains(event.target)) {
        return
      }
      this.closeSelectAllMenu()
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

    onListRowClick(_event, item) {
      if (this.suppressNextListClick) {
        this.suppressNextListClick = false
        return
      }
      if (this.selectionMode) return
      this.openItem(item)
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
      if (origin === 'list-browse' && !this.selectionMode) {
        return
      }
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

    toggleInfoDisplayMode() {
      this.selectionInfoMode = this.selectionInfoMode === 'name' ? 'tags' : 'name'
      if (this.selectionInfoMode === 'tags') {
        this.ensureTagLabelsLoaded()
      }
    },

    displayInfoText(item) {
      if (this.selectionInfoMode !== 'tags') {
        return item?.name || item?.full_filename || '未命名'
      }
      if (item?.type === 'album') {
        return item?.name || '未命名相册'
      }
      return this.tagTextForItem(item)
    },

    tagTextForItem(item) {
      const ids = Array.isArray(item?.tags)
        ? item.tags.filter(id => Number.isInteger(id))
        : []
      if (!ids.length) return '无标签'

      const names = []
      let allResolved = true
      for (const id of ids) {
        if (!Object.prototype.hasOwnProperty.call(this.tagNameMap, id)) {
          allResolved = false
          continue
        }
        const label = this.tagNameMap[id]
        if (label) names.push(label)
      }

      if (names.length) return names.join(' · ')
      if (!allResolved && this.tagsLoading) return '加载标签中...'
      return '无标签'
    },

    detailTagTextForItem(item) {
      if (item?.type !== 'image') return ''
      const ids = Array.isArray(item?.tags)
        ? item.tags.filter(id => Number.isInteger(id))
        : []
      if (!ids.length) return ''

      const names = []
      let allResolved = true
      for (const id of ids) {
        if (!Object.prototype.hasOwnProperty.call(this.tagNameMap, id)) {
          allResolved = false
          continue
        }
        const label = this.tagNameMap[id]
        if (label) names.push(label)
      }

      if (names.length) return names.join(' · ')
      if (!allResolved && this.tagsLoading) return '加载标签中...'
      return ''
    },

    collectMissingTagIds() {
      const result = []
      const seen = new Set()
      for (const item of this.items) {
        if (item?.type !== 'image' || !Array.isArray(item.tags)) continue
        for (const id of item.tags) {
          if (!Number.isInteger(id)) continue
          if (seen.has(id)) continue
          seen.add(id)
          if (!Object.prototype.hasOwnProperty.call(this.tagNameMap, id)) {
            result.push(id)
          }
        }
      }
      return result
    },

    async ensureTagLabelsLoaded(force = false) {
      if (!force && this.selectionInfoMode !== 'tags') return
      const missingIds = this.collectMissingTagIds()
      if (!missingIds.length) return

      const requestSerial = ++this.tagFetchSerial
      const nextMap = { ...this.tagNameMap }
      this.tagsLoading = true

      try {
        for (let i = 0; i < missingIds.length; i += TAG_BATCH_SIZE) {
          const chunk = missingIds.slice(i, i + TAG_BATCH_SIZE)
          const res = await fetch(`${API_BASE}/api/tags?ids=${chunk.join(',')}&limit=${chunk.length}`)
          if (!res.ok) continue
          const data = await res.json()
          const returnedIds = new Set()
          for (const tag of (data.items || [])) {
            returnedIds.add(tag.id)
            nextMap[tag.id] = tag.display_name || tag.name || `#${tag.id}`
          }
          for (const id of chunk) {
            if (!returnedIds.has(id) && !Object.prototype.hasOwnProperty.call(nextMap, id)) {
              nextMap[id] = ''
            }
          }
        }

        if (requestSerial === this.tagFetchSerial) {
          this.tagNameMap = nextMap
        }
      } catch {
        // ignore tag fetch failures and keep filename mode available
      } finally {
        if (requestSerial === this.tagFetchSerial) {
          this.tagsLoading = false
        }
      }
    },

    onReservedDetailsClick(item, index) {
      if (!item) return
      const alreadySelected = this.isItemSelected(item, index)

      if (!this.selectedCount) {
        this.selectOnlyIndex(index)
      } else if (this.selectedCount === 1) {
        if (!alreadySelected) {
          this.selectOnlyIndex(index)
        }
      } else if (!alreadySelected) {
        this.selectOnlyIndex(index)
      }

      this.openSelectionDetails()
    },

    onReservedAnalysisClick() {
      // reserved for future filename-based tag analysis
    },

    onReservedDeleteClick() {
      // reserved for future delete action
    },

    idsAround(centerIdx) {
      const items = this.items
      const start = Math.max(0, centerIdx - RADIUS)
      const end = Math.min(items.length - 1, centerIdx + RADIUS)
      return items
        .slice(start, end + 1)
        .filter(item => item.id && !this.cacheUrls[item.id] && !item.cache_thumb_url)
        .map(item => item.id)
    },

    async triggerCacheAt(centerIdx) {
      const ids = this.idsAround(centerIdx)
      if (!ids.length) return
      try {
        const res = await fetch(`${API_BASE}/api/thumbnails/cache`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image_ids: ids }),
        })
        if (!res.ok) return
        const { task_id } = await res.json()
        this.taskId = task_id
        this.startPoll()
      } catch {
        // ignore thumbnail trigger failures
      }
    },

    startPoll() {
      this.stopPoll()
      const poll = async () => {
        if (!this.taskId) return
        try {
          const res = await fetch(`${API_BASE}/api/thumbnails/cache/status/${this.taskId}`)
          if (!res.ok) return
          const data = await res.json()
          const newUrls = {}
          for (const item of (data.items || [])) {
            if (item.id && item.cache_thumb_url) newUrls[item.id] = item.cache_thumb_url
          }
          if (Object.keys(newUrls).length > 0) {
            this.cacheUrls = { ...this.cacheUrls, ...newUrls }
          }
          if (data.status === 'running') {
            this.pollTimer = setTimeout(poll, POLL_MS)
          }
        } catch {
          // ignore polling failures
        }
      }
      this.pollTimer = setTimeout(poll, POLL_MS)
    },

    stopPoll() {
      if (this.pollTimer) {
        clearTimeout(this.pollTimer)
        this.pollTimer = null
      }
    },

    refreshObservedGrid() {
      this.$nextTick(() => {
        this.teardownObserver()
        this.teardownResizeObserver()
        if (!this.$refs.itemGrid) return
        this.containerWidth = this.$refs.itemGrid.offsetWidth
        this.syncVirtualWindow(true)
        if (this.isPhotoGridMode) {
          this.triggerCacheAt(0)
          this.setupObserver()
        }
        this.setupResizeObserver()
        if (this.isSelectionGridMode) {
          this.measureSelectionRowHeight()
        }
      })
    },

    setupObserver() {
      if (!this.$refs.itemGrid || !this.isPhotoGridMode) return
      this.observer = new IntersectionObserver(
        (entries) => {
          const visible = entries
            .filter(entry => entry.isIntersecting)
            .map(entry => parseInt(entry.target.dataset.index, 10))
          if (!visible.length) return
          const topIndex = Math.min(...visible)
          clearTimeout(this.debounceTimer)
          this.debounceTimer = setTimeout(() => {
            if (topIndex !== this.lastCenter) {
              this.lastCenter = topIndex
              this.triggerCacheAt(topIndex)
            }
          }, DEBOUNCE_MS)
        },
        { root: null, rootMargin: '0px', threshold: 0.1 },
      )
      for (const el of this.$refs.itemGrid.querySelectorAll('[data-index]')) {
        this.observer.observe(el)
      }
    },

    teardownObserver() {
      if (this.observer) {
        this.observer.disconnect()
        this.observer = null
      }
      if (this.debounceTimer) {
        clearTimeout(this.debounceTimer)
        this.debounceTimer = null
      }
    },

    setupResizeObserver() {
      if (!this.$refs.itemGrid) return
      if (this.resizeObserver) {
        this.resizeObserver.disconnect()
        this.resizeObserver = null
      }
      this.resizeObserver = new ResizeObserver(() => {
        requestAnimationFrame(() => {
          if (this.$refs.itemGrid) {
            this.containerWidth = this.$refs.itemGrid.offsetWidth
            if (this.isVirtualizedMode) {
              this.syncVirtualWindow(true)
              if (this.isSelectionGridMode) {
                this.measureSelectionRowHeight()
              }
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
  @apply flex flex-col gap-6;
  position: relative;
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

.vm-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.empty-hint {
  @apply border-2 border-dashed border-slate-300 bg-slate-50 rounded-xl py-16 text-center text-slate-400 text-sm;
}

.empty-hint__icon { @apply text-5xl block mb-3; }

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

.photo-skeleton {
  @apply w-full h-full rounded-xl overflow-hidden flex items-center justify-center;
  background: linear-gradient(90deg, #e2e8f0 25%, #f1f5f9 50%, #e2e8f0 75%);
  background-size: 200% 100%;
  animation: skeleton-wave 1.4s ease-in-out infinite;
}

.skeleton-label {
  @apply text-slate-400 text-xs font-mono tracking-widest select-none;
  animation: skeleton-fade 1.4s ease-in-out infinite;
}

@keyframes skeleton-wave {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@keyframes skeleton-fade {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.8; }
}

.photo-card {
  @apply relative cursor-pointer rounded-xl overflow-hidden shadow-md;
  width: 100%;
  height: 100%;
  transition: box-shadow 200ms ease, transform 200ms ease;
}

.photo-card:hover { @apply shadow-xl -translate-y-0.5; }

.photo-img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 300ms ease;
}

.photo-card:hover .photo-img { transform: scale(1.03); }

.album-badge {
  @apply absolute top-2 right-2 flex flex-col items-center gap-0.5 px-2 py-1 rounded-lg;
  background: rgba(255, 255, 255, 0.90);
  box-shadow: 0 1px 4px rgba(0,0,0,.15);
  pointer-events: none;
}

.badge-icon { font-size: 1rem; }

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

.selection-island {
  position: fixed;
  right: 1.5rem;
  bottom: 1.5rem;
  z-index: 50;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.65rem 0.75rem;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.14);
  backdrop-filter: blur(14px);
}

.selection-island__count {
  color: #0f172a;
  font-size: 0.82rem;
  font-weight: 700;
  white-space: nowrap;
}

.selection-island__menu-wrap {
  position: relative;
  display: inline-flex;
}

.selection-island__submenu {
  position: absolute;
  left: 0;
  bottom: calc(100% + 0.55rem);
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: 0.42rem;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 18px 34px rgba(15, 23, 42, 0.12);
  opacity: 0;
  pointer-events: none;
  transform: translateY(8px);
  transition: opacity 140ms ease, transform 140ms ease;
}

.selection-island__menu-wrap.is-open .selection-island__submenu {
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0);
}

.selection-island__submenu-btn {
  border: 0;
  border-radius: 10px;
  padding: 0.48rem 0.72rem;
  background: transparent;
  color: #334155;
  font-size: 0.76rem;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  transition: background 140ms ease, color 140ms ease;
}

.selection-island__submenu-btn:hover {
  background: #e2e8f0;
  color: #0f172a;
}

.selection-island__btn {
  border: 0;
  border-radius: 12px;
  padding: 0.45rem 0.75rem;
  background: transparent;
  color: #334155;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 140ms ease, color 140ms ease;
}

.selection-island__btn:hover {
  background: #e2e8f0;
  color: #0f172a;
}

.selection-island__btn:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}

.selection-island__btn:disabled:hover {
  background: transparent;
  color: #334155;
}

@media (orientation: landscape) {
  .selection-grid {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }
}

@media (orientation: portrait) {
  .selection-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.8rem;
  }
}

@media (max-width: 640px) {
  .selection-island {
    right: 0.9rem;
    left: 0.9rem;
    bottom: 0.9rem;
    justify-content: space-between;
    flex-wrap: wrap;
  }

  .selection-island__menu-wrap {
    display: flex;
    flex: 1 1 100%;
  }

  .selection-island__submenu {
    left: 0;
    right: 0;
  }
}
</style>
