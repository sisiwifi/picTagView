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

    <div v-else-if="selectionMode && viewMode === 'grid'" ref="itemGrid" class="selection-grid">
      <div
        v-for="(item, idx) in items"
        :key="itemKey(item, idx)"
        class="selection-wrap"
        :class="{
          'is-selected': isItemSelected(item, idx),
          'is-disabled': isItemDisabled(item),
        }"
        :data-index="idx"
        :data-select-index="idx"
        @pointerdown="onSelectionPointerDown($event, item, idx)"
      >
        <MediaItemCard
          :src="resolvedUrl(item)"
          :alt="item.name || ''"
          :info-text="displayInfoText(item)"
          :info-title="selectionInfoMode === 'tags' ? '当前显示 Tag，点击切换为文件名' : '当前显示文件名，点击切换为 Tag'"
          :item-type="item.type"
          :selected="isItemSelected(item, idx)"
          :disabled="isItemDisabled(item)"
          @toggle-select="onItemSelectionButtonClick(item, idx)"
          @toggle-info="toggleInfoDisplayMode"
          @details="onReservedDetailsClick(item)"
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

    <div v-else ref="itemGrid" class="list-view">
      <div
        v-for="(item, idx) in items"
        :key="item.public_id || item.id || idx"
        class="list-row"
        :class="{
          'list-row--selecting': selectionMode,
          'is-selected': isItemSelected(item, idx),
          'is-disabled': isItemDisabled(item),
        }"
        :data-index="idx"
        :data-select-index="idx"
        @pointerdown="onListPointerDown($event, item, idx)"
        @click="onListRowClick($event, item, idx)"
      >
        <button
          v-if="selectionMode"
          class="list-pick"
          type="button"
          :disabled="isItemDisabled(item)"
          :aria-pressed="isItemSelected(item, idx) ? 'true' : 'false'"
          :aria-label="isItemSelected(item, idx) ? '取消选择' : '选择项目'"
          @pointerdown.stop
          @click.stop="onItemSelectionButtonClick(item, idx)"
        >
          <span v-if="isItemSelected(item, idx)" class="list-pick__mark">✓</span>
        </button>
        <div class="list-thumb-wrap">
          <div v-if="!resolvedUrl(item)" class="list-thumb-skeleton" />
          <img
            v-else
            :src="resolvedUrl(item)"
            class="list-thumb-img"
            :alt="item.name || ''"
            @load="onImgLoad(item, $event)"
          />
        </div>
        <div class="list-main">
          <div class="list-title-row">
            <span v-if="item.type === 'album'" class="list-type-pill">ALB</span>
            <span class="list-name">{{ item.name || item.full_filename || '未知文件' }}</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="selectionMode" class="selection-island">
      <span class="selection-island__count">{{ selectionSummaryText }}</span>
      <button class="selection-island__btn" type="button" @click="selectAllOfCurrentType">全选</button>
      <button class="selection-island__btn" type="button" @click="clearSelection">取消选择</button>
    </div>
  </section>
</template>

<script>
import LoadingSpinner from '../components/LoadingSpinner.vue'
import BreadcrumbHeader from '../components/BreadcrumbHeader.vue'
import MediaItemCard from '../components/MediaItemCard.vue'

const API_BASE = 'http://127.0.0.1:8000'
const POLL_MS = 80
const RADIUS = 50
const DEBOUNCE_MS = 300
const LONG_PRESS_MS = 220
const TAG_BATCH_SIZE = 120

export default {
  name: 'BrowsePage',
  components: { LoadingSpinner, BreadcrumbHeader, MediaItemCard },

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
  },

  watch: {
    '$route.params': {
      handler() { this.loadData() },
      deep: true,
    },
    justifiedRows(newVal, oldVal) {
      if (this.selectionMode) return
      if (newVal.length !== oldVal.length) {
        this.refreshObservedGrid()
      }
    },
    viewMode() {
      if (this.selectionMode) return
      this.refreshObservedGrid()
    },
  },

  created() {
    this.loadData()
    window.addEventListener('resize', this.onResize)
    window.addEventListener('keydown', this.onWindowKeydown)
  },

  beforeUnmount() {
    this.teardownObserver()
    this.teardownResizeObserver()
    this.stopPoll()
    this.clearPointerGesture()
    window.removeEventListener('resize', this.onResize)
    window.removeEventListener('keydown', this.onWindowKeydown)
  },

  methods: {
    async loadData() {
      this.loading = true
      this.sortBy = this.isAlbumMode ? 'alpha' : 'date'
      this.sortDir = 'asc'
      this.cacheUrls = {}
      this.imgDimensions = {}
      this.lastCenter = -1
      this.albumInfo = null
      this.clearSelection()
      this.clearPointerGesture()
      this.tagFetchSerial += 1
      this.tagsLoading = false
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
      if (this.$refs.itemGrid) {
        this.containerWidth = this.$refs.itemGrid.offsetWidth
      }
    },

    onWindowKeydown(event) {
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

    selectAllOfCurrentType() {
      const type = this.selectionTypeLock || this.items[0]?.type
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

    async ensureTagLabelsLoaded() {
      if (this.selectionInfoMode !== 'tags') return
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

    onReservedDetailsClick() {
      // reserved for future menu
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
        this.triggerCacheAt(0)
        this.setupObserver()
        this.setupResizeObserver()
      })
    },

    setupObserver() {
      if (!this.$refs.itemGrid) return
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
.page { @apply flex flex-col gap-6; }

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
}
</style>
