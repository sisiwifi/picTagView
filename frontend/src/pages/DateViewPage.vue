<template>
  <section class="page">
    <!-- Header -->
    <header class="page-header">
      <button
        v-if="view === 'detail' || view === 'returning'"
        class="back-btn"
        @click="closeDetail"
      >
        ← 返回
      </button>

      <!-- Detail mode: breadcrumb + view-mode toggle -->
      <template v-if="view === 'detail' || view === 'returning'">
        <div
          class="breadcrumb-wrap"
          ref="breadcrumbWrap"
          :class="{ 'bc-dragging': bcDragging }"
          @mousedown="onBcMousedown"
          @mouseleave="onBcMouseleave"
          @mouseup="onBcMouseup"
          @mousemove="onBcMousemove"
        >
          <nav class="breadcrumb">
            <span class="bc-item" title="日期视图">日期视图</span>
            <span class="bc-sep">›</span>
            <span class="bc-item bc-item--cur" :title="selectedGroup">{{ truncate(selectedGroup, 20) }}</span>
          </nav>
        </div>
        <div class="header-actions">
          <span class="header-count">{{ selectedItems.length }} 项</span>
          <div class="sort-controls" role="group" aria-label="排序设置">
            <div class="sort-switch" role="group" aria-label="排序字段">
              <span class="sort-thumb" :class="{ 'is-alpha': sortBy === 'alpha' }" aria-hidden="true"></span>
              <button
                class="sort-mode-btn"
                :class="{ active: sortBy === 'date' }"
                title="按日期排序"
                aria-label="按日期排序"
                @click="onSortModeClick('date')"
              >
                Date <span v-if="sortBy === 'date'" class="sort-dir-mark">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
              </button>
              <button
                class="sort-mode-btn"
                :class="{ active: sortBy === 'alpha' }"
                title="按字符顺序排序"
                aria-label="按字符顺序排序"
                @click="onSortModeClick('alpha')"
              >
                Alpha <span v-if="sortBy === 'alpha'" class="sort-dir-mark">{{ sortDir === 'asc' ? '↑' : '↓' }}</span>
              </button>
            </div>
          </div>
          <div class="view-toggle" role="group" aria-label="显示方式">
            <button
              class="vt-btn"
              :class="{ active: viewMode === 'grid' }"
              title="大缩略图显示"
              aria-label="大缩略图显示"
              @click="viewMode = 'grid'"
            >
              <svg width="15" height="15" viewBox="0 0 15 15" fill="currentColor" aria-hidden="true">
                <rect x="1"   y="1"   width="5.5" height="5.5" rx="1"/>
                <rect x="8.5" y="1"   width="5.5" height="5.5" rx="1"/>
                <rect x="1"   y="8.5" width="5.5" height="5.5" rx="1"/>
                <rect x="8.5" y="8.5" width="5.5" height="5.5" rx="1"/>
              </svg>
            </button>
            <button
              class="vt-btn"
              :class="{ active: viewMode === 'list' }"
              title="列表显示"
              aria-label="列表显示"
              @click="viewMode = 'list'"
            >
              <svg width="15" height="15" viewBox="0 0 15 15" fill="currentColor" aria-hidden="true">
                <rect x="1"   y="1.5" width="4"   height="4"   rx="0.75"/>
                <rect x="6.5" y="3"   width="7.5" height="1.5" rx="0.75"/>
                <rect x="1"   y="7.5" width="4"   height="4"   rx="0.75"/>
                <rect x="6.5" y="9"   width="7.5" height="1.5" rx="0.75"/>
                <rect x="1"   y="13"  width="4"   height="1.5" rx="0.75"/>
                <rect x="6.5" y="13"  width="7.5" height="1.5" rx="0.75"/>
              </svg>
            </button>
            <button
              class="vt-btn vt-btn--placeholder"
              title="选择（即将推出）"
              aria-label="选择"
              disabled
            >
              <svg width="15" height="15" viewBox="0 0 15 15" fill="currentColor" aria-hidden="true">
                <path d="M3.5 1 L3.5 12 L6.3 9.2 L8.7 14 L10.5 13.2 L8.1 8.4 L12 8.4 Z"/>
              </svg>
            </button>
          </div>
        </div>
      </template>

      <!-- Grid mode: plain title -->
      <template v-else>
        <h2 class="page-title flex-1">日期视图</h2>
        <span class="page-subtitle">按年份与月份浏览已导入的图片。</span>
      </template>
    </header>

    <!-- Grid view -->
    <div
      v-show="view === 'grid' || view === 'animating' || view === 'returning'"
      class="grid-wrapper"
      :class="{ 'grid-wrapper--fading': view === 'animating' || view === 'returning' }"
    >
      <LoadingSpinner v-if="loadingDates" />

      <div v-else-if="!years.length" class="empty-hint">
        <span class="empty-hint__icon">📅</span>
        <p>暂无图片，请先在「图库管理」导入。</p>
      </div>

      <template v-else>
        <div v-for="yg in years" :key="yg.year" class="year-section">
          <div class="year-heading">
            <span class="year-heading__num">{{ yg.year }}</span>
            <span class="year-heading__count">
              {{ yg.months.reduce((s, m) => s + m.count, 0) }} 张
            </span>
          </div>
          <div class="year-divider"></div>

          <div class="card-grid">
            <ThumbCard
              v-for="mg in yg.months"
              :key="mg.group"
              :src="resolvedUrl(mg)"
              class="month-card"
              :overlay-opacity="0.40"
              :rounded="'1.25rem'"
              @click="openGroup(mg, $event)"
            >
              <span class="month-label">{{ mg.group }}</span>
              <span class="month-count">{{ mg.count }} 张</span>
            </ThumbCard>
          </div>
        </div>
      </template>
    </div>

    <!-- Detail view -->
    <Transition :name="transitionName">
      <div
        v-if="detailVisible"
        class="detail-wrapper"
        :style="originStyle"
      >
        <LoadingSpinner v-if="loadingItems" />

        <template v-else>
          <!-- Grid mode: justified-layout large thumbnails -->
          <div v-if="viewMode === 'grid'" ref="itemGrid" class="photo-grid">
            <div
              v-for="(row, ri) in justifiedRows"
              :key="ri"
              class="jl-row"
              :style="{ height: row.height + 'px' }"
            >
              <div
                v-for="item in row.items"
                :key="item.id || item._idx"
                class="photo-wrap"
                :data-index="item._idx"
                :style="{ width: item.computedWidth + 'px' }"
              >
                <!-- Skeleton while no thumbnail available -->
                <div v-if="!resolvedUrl(item)" class="photo-skeleton">
                  <span class="skeleton-label">···</span>
                </div>

                <!-- Image -->
                <div
                  v-else
                  class="photo-card"
                  @click="openImage(item)"
                >
                  <img
                    :src="resolvedUrl(item)"
                    class="photo-img"
                    loading="lazy"
                    :alt="item.name || ''"
                    @load="onImgLoad(item, $event)"
                    @error="onImgError(item, $event)"
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

          <!-- List mode: 50 px thumbnail + filename -->
          <div v-else ref="listView" class="list-view">
            <div
              v-for="(item, idx) in selectedItems"
              :key="item.id || idx"
              class="list-item"
              :data-index="idx"
              @click="openImage(item)"
            >
              <div class="list-thumb-wrap">
                <div v-if="!resolvedUrl(item)" class="list-thumb-skeleton"></div>
                <img
                  v-else
                  :src="resolvedUrl(item)"
                  class="list-thumb"
                  loading="lazy"
                  :alt="item.name || ''"
                  :style="listThumbStyle(item)"
                  @load="onImgLoad(item, $event)"
                  @error="onImgError(item, $event)"
                />
              </div>
              <span class="list-filename">{{ item.name || '—' }}</span>
              <span v-if="item.type === 'album'" class="list-album-badge">📁 {{ item.count }} 张</span>
            </div>
          </div>
        </template>
      </div>
    </Transition>
  </section>
</template>

<script>
import ThumbCard      from '../components/ThumbCard.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'

const API_BASE = 'http://127.0.0.1:8000'
const DEBOUNCE_MS = 300
const POLL_MS = 80
const RADIUS = 50

export default {
  name: 'DateViewPage',
  components: { ThumbCard, LoadingSpinner },

  data() {
    return {
      years:          [],
      loadingDates:   true,
      view:           'grid',
      navDir:         'forward',
      detailVisible:  false,
      selectedGroup:  '',
      selectedItems:  [],
      loadingItems:   false,
      originX:        '50%',
      originY:        '50%',
      cacheUrls:     {},
      pollTimer:     null,
      taskId:        null,
      observer:      null,
      debounceTimer: null,
      resizeObserver: null,
      lastCenter:    -1,
      imgDimensions: {},      // id -> { w, h }  tracked from img.onload
      containerWidth: 0,      // width of the photo-grid container
      refreshingThumbs: false,
      cacheBustById: {},
      thumbErrorRetries: {},
      failedThumbIds: {},
      viewMode:       'grid',   // 'grid' | 'list'
      sortBy:         'date',   // 'date' | 'alpha'
      sortDir:        'asc',    // 'asc' | 'desc'
      bcDragging:     false,
      bcStartX:       0,
      bcScrollLeft:   0,
    }
  },

  computed: {
    transitionName() {
      return this.navDir === 'back' ? 't-back' : 't-forward'
    },
    originStyle() {
      return { '--tx': this.originX, '--ty': this.originY }
    },

    // Justified-layout: groups selectedItems into rows of equal height
    // where each row fills the container width proportionally.
    justifiedRows() {
      const W = this.containerWidth || (typeof window !== 'undefined' ? window.innerWidth - 48 : 800)
      const GAP = 4
      const TARGET_H = 440
      const items = this.selectedItems
      if (!items.length) return []

      const rows = []
      let rowStart = 0
      let rowAR = 0  // cumulative aspect-ratio sum for current row

      for (let i = 0; i < items.length; i++) {
        const dims = this.imgDimensions[items[i].id] || { w: 4, h: 3 }
        rowAR += dims.w / dims.h
        const isLast = i === items.length - 1
        const rowLen = i - rowStart + 1
        const neededW = rowAR * TARGET_H + GAP * (rowLen - 1)

        if (neededW >= W || isLast) {
          const totalGap = GAP * (rowLen - 1)
          // Last partial row keeps target height; full rows scale to fill width.
          const actualH = (isLast && neededW < W)
            ? TARGET_H
            : Math.round((W - totalGap) / rowAR)
          const rowItems = []
          for (let j = rowStart; j <= i; j++) {
            const it = items[j]
            const d = this.imgDimensions[it.id] || { w: 4, h: 3 }
            rowItems.push({ ...it, _idx: j, computedWidth: Math.round((d.w / d.h) * actualH) })
          }
          rows.push({ items: rowItems, height: actualH })
          rowStart = i + 1
          rowAR = 0
        }
      }
      return rows
    },
  },

  watch: {
    // Re-initialize IntersectionObserver when row structure changes (new DOM nodes)
    justifiedRows(newVal, oldVal) {
      if (newVal.length !== oldVal.length) {
        this.$nextTick(() => {
          this.teardownObserver()
          this.setupObserver()
        })
      }
    },
    // Re-connect observer when switching between grid and list
    viewMode() {
      this.$nextTick(() => {
        this.teardownObserver()
        this.teardownResizeObserver()
        this.setupObserver()
        this.setupResizeObserver()
        if (this.$refs.itemGrid) {
          this.containerWidth = this.$refs.itemGrid.offsetWidth
        }
      })
    },
  },

  created() {
    this.fetchDates()
    window.addEventListener('resize', this.onResize)
  },
  activated() {
    this.view          = 'grid'
    this.detailVisible = false
    this.selectedGroup = ''
    this.selectedItems = []
    this.fetchDates()
  },

  beforeUnmount() {
    this.teardownObserver()
    this.teardownResizeObserver()
    this.stopPoll()
    window.removeEventListener('resize', this.onResize)
  },

  methods: {
    api(path) { return path ? `${API_BASE}${path}` : '' },

    resolvedUrl(item) {
      if (!item) return ''
      const cached = this.cacheUrls[item.id]
      let urlPath = ''
      if (cached) {
        urlPath = cached
      } else if (item.cache_thumb_url) {
        urlPath = item.cache_thumb_url
      } else if (item.thumb_url) {
        urlPath = item.thumb_url
      }
      if (!urlPath) return ''

      const nonce = item.id ? this.cacheBustById[item.id] : null
      return nonce ? `${API_BASE}${urlPath}?v=${nonce}` : `${API_BASE}${urlPath}`
    },

    bumpCacheBust(id) {
      if (!id) return
      this.cacheBustById = { ...this.cacheBustById, [id]: Date.now() }
    },

    async triggerCacheForIds(ids) {
      const uniq = Array.from(new Set((ids || []).filter(Boolean)))
      if (!uniq.length) return
      const cacheRes = await fetch(`${API_BASE}/api/thumbnails/cache`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image_ids: uniq }),
      })
      if (!cacheRes.ok) return
      const { task_id } = await cacheRes.json()
      this.taskId = task_id
      this.startPoll()
    },

    async onImgError(item) {
      const id = item?.id
      if (!id) return

      const retries = this.thumbErrorRetries[id] || 0
      if (retries >= 2) return
      this.thumbErrorRetries = { ...this.thumbErrorRetries, [id]: retries + 1 }
      this.failedThumbIds = { ...this.failedThumbIds, [id]: true }
      this.bumpCacheBust(id)

      try {
        await this.triggerCacheForIds([id])
      } catch { /* ignore */ }

      // Fallback: force refresh even when URLs exist but actual files were stale/missing.
      this._checkAndRefreshItems(true)
    },

    async fetchDates() {
      this.loadingDates = true
      try {
        const r = await fetch(`${API_BASE}/api/dates`)
        const d = await r.json()
        this.years = d.years || []
        
        // Populate existing cache URLs
        const allMonths = (d.years || []).flatMap(y => y.months || [])
        for (const m of allMonths) {
          if (m.id && m.cache_thumb_url) {
            this.cacheUrls = { ...this.cacheUrls, [m.id]: m.cache_thumb_url }
          }
        }

        // Trigger cache generation for missing covers
        const missingIds = allMonths
          .filter(m => m.id && !m.thumb_url && !this.cacheUrls[m.id])
          .map(m => m.id)
        
        if (missingIds.length > 0) {
          try {
            const cacheRes = await fetch(`${API_BASE}/api/thumbnails/cache`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ image_ids: missingIds }),
            })
            if (cacheRes.ok) {
              const { task_id } = await cacheRes.json()
              this.taskId = task_id
              this.startPoll()
            }
          } catch (e) { /* ignore cache trigger error */ }
        }
      } catch (e) { this.years = [] }
      finally  { this.loadingDates = false }
    },

    async openGroup(mg, ev) {
      const rect = ev.currentTarget.getBoundingClientRect()
      this.originX = `${Math.round(((rect.left + rect.width  / 2) / window.innerWidth)  * 100)}%`
      this.originY = `${Math.round(((rect.top  + rect.height / 2) / window.innerHeight) * 100)}%`

      this.viewMode  = 'grid'
      this.sortBy    = 'date'
      this.sortDir   = 'asc'
      this.navDir = 'forward'
      this.view   = 'animating'
      this.selectedGroup = mg.group
      this.loadingItems  = true
      this.selectedItems = []
      this.cacheUrls    = {}
      this.lastCenter   = -1
      this.teardownObserver()
      this.stopPoll()

      const [data] = await Promise.all([
        fetch(`${API_BASE}/api/dates/${mg.group}/items`)
          .then(r => r.json()).catch(() => ({ items: [] })),
        new Promise(r => setTimeout(r, 170)),
      ])

      this.selectedItems = this.sortItems(data.items || [])
      for (const item of this.selectedItems) {
        if (item.id && item.cache_thumb_url) {
          this.cacheUrls = { ...this.cacheUrls, [item.id]: item.cache_thumb_url }
        }
      }

      this.loadingItems  = false
      this.detailVisible = true
      this.view = 'detail'

      this.$nextTick(() => {
        // Scroll to top so the detail view starts at the first image
        window.scrollTo({ top: 0, behavior: 'instant' })
        // Capture container width for justified-layout computation
        if (this.$refs.itemGrid) {
          this.containerWidth = this.$refs.itemGrid.offsetWidth
        }
        this.triggerCacheAt(0)
        this.setupObserver()
        this.setupResizeObserver()
      })
      // Detect missing item thumbnails and trigger an immediate background refresh
      this._checkAndRefreshItems()
    },

    closeDetail() {
      this.teardownObserver()
      this.teardownResizeObserver()
      this.stopPoll()
      this.navDir = 'back'
      this.view = 'returning'
      this.detailVisible = false
      this.selectedGroup = ''
      setTimeout(() => { this.view = 'grid' }, 190)
      setTimeout(() => {
        this.selectedItems  = []
        this.cacheUrls      = {}
        this.taskId         = null
        this.imgDimensions  = {}
        this.containerWidth = 0
        this.cacheBustById = {}
        this.thumbErrorRetries = {}
        this.failedThumbIds = {}
      }, 430)
    },

    idsAround(centerIdx) {
      const items = this.selectedItems
      const start = Math.max(0, centerIdx - RADIUS)
      const end   = Math.min(items.length - 1, centerIdx + RADIUS)
      return items
        .slice(start, end + 1)
        .filter(it => it.id && !this.cacheUrls[it.id] && !it.cache_thumb_url)
        .map(it => it.id)
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
      } catch { /* ignore */ }
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
          for (const it of (data.items || [])) {
            if (it.id && it.cache_thumb_url) {
              newUrls[it.id] = it.cache_thumb_url
              this.bumpCacheBust(it.id)
            }
          }
          if (Object.keys(newUrls).length > 0) {
            this.cacheUrls = { ...this.cacheUrls, ...newUrls }
          }
          if (data.status === 'running') {
            this.pollTimer = setTimeout(poll, POLL_MS)
          }
        } catch { /* ignore */ }
      }
      this.pollTimer = setTimeout(poll, POLL_MS)
    },

    stopPoll() {
      if (this.pollTimer) { clearTimeout(this.pollTimer); this.pollTimer = null }
    },

    setupObserver() {
      const container = this.$refs.itemGrid || this.$refs.listView
      if (!container) return
      this.observer = new IntersectionObserver(
        (entries) => {
          const visible = entries
            .filter(e => e.isIntersecting)
            .map(e => parseInt(e.target.dataset.index, 10))
          if (!visible.length) return
          const topIdx = Math.min(...visible)
          clearTimeout(this.debounceTimer)
          this.debounceTimer = setTimeout(() => {
            if (topIdx !== this.lastCenter) {
              this.lastCenter = topIdx
              this.triggerCacheAt(topIdx)
            }
          }, DEBOUNCE_MS)
        },
        { root: null, rootMargin: '0px', threshold: 0.1 },
      )
      for (const el of container.querySelectorAll('[data-index]')) {
        this.observer.observe(el)
      }
    },

    teardownObserver() {
      if (this.observer) { this.observer.disconnect(); this.observer = null }
      if (this.debounceTimer) { clearTimeout(this.debounceTimer); this.debounceTimer = null }
    },

    setupResizeObserver() {
      const container = this.$refs.itemGrid || this.$refs.listView
      if (!container) return
      if (this.resizeObserver) { this.resizeObserver.disconnect(); this.resizeObserver = null }
      this.resizeObserver = new ResizeObserver(() => {
        requestAnimationFrame(() => {
          if (this.$refs.itemGrid) {
            this.containerWidth = this.$refs.itemGrid.offsetWidth
          }
        })
      })
      this.resizeObserver.observe(container)
    },

    teardownResizeObserver() {
      if (this.resizeObserver) { this.resizeObserver.disconnect(); this.resizeObserver = null }
    },

    onImgLoad(item, evt) {
      const { naturalWidth: w, naturalHeight: h } = evt.target
      if (!w || !h) return
      const ex = this.imgDimensions[item.id]
      if (!ex || ex.w !== w || ex.h !== h) {
        this.imgDimensions = { ...this.imgDimensions, [item.id]: { w, h } }
      }
      if (item?.id && this.failedThumbIds[item.id]) {
        const next = { ...this.failedThumbIds }
        delete next[item.id]
        this.failedThumbIds = next
      }
    },

    onResize() {
      if (this.$refs.itemGrid) {
        this.containerWidth = this.$refs.itemGrid.offsetWidth
      }
    },

    // Re-fetch dates after a background refresh so month-cover thumbnails
    // appear without requiring the user to manually reload.
    async _refreshAndUpdateDates() {
      if (this.refreshingThumbs) return
      this.refreshingThumbs = true
      try {
        const refreshRes = await fetch(`${API_BASE}/api/admin/refresh`, { method: 'POST' })
        if (refreshRes.ok) {
          const refreshData = await refreshRes.json()
          window.dispatchEvent(new CustomEvent('library-refreshed', { detail: refreshData }))
        }
        const r = await fetch(`${API_BASE}/api/dates`)
        if (r.ok) {
          const d = await r.json()
          this.years = d.years || []
        }
      } catch { /* ignore */ }
      finally { this.refreshingThumbs = false }
    },

    // Check if any visible items are missing thumbnails. If so, trigger an
    // immediate refresh and re-fetch to update the detail view automatically.
    async _checkAndRefreshItems(force = false) {
      if (this.refreshingThumbs) return
      const hasMissing = this.selectedItems.some(
        item => !item.thumb_url && !item.cache_thumb_url
      )
      const hasFailed = this.selectedItems.some(item => item.id && this.failedThumbIds[item.id])
      if (!force && !hasMissing && !hasFailed) return
      this.refreshingThumbs = true
      try {
        const refreshRes = await fetch(`${API_BASE}/api/admin/refresh`, { method: 'POST' })
        if (refreshRes.ok) {
          const refreshData = await refreshRes.json()
          window.dispatchEvent(new CustomEvent('library-refreshed', { detail: refreshData }))
        }
        if (!this.detailVisible || !this.selectedGroup) return
        const r = await fetch(`${API_BASE}/api/dates/${this.selectedGroup}/items`)
        if (!r.ok) return
        const data = await r.json()
        this.selectedItems = this.sortItems(data.items || [])
        for (const item of this.selectedItems) {
          if (item.id && item.cache_thumb_url) {
            this.cacheUrls = { ...this.cacheUrls, [item.id]: item.cache_thumb_url }
          }
        }
      } catch { /* ignore */ }
      finally { this.refreshingThumbs = false }
    },

    truncate(str, max = 20) {
      if (!str) return ''
      return str.length > max ? str.slice(0, max) + '\u2026' : str
    },

    listThumbStyle(item) {
      const dims = this.imgDimensions[item?.id]
      if (!dims || !dims.w || !dims.h) return { width: '50px', height: '50px', objectFit: 'contain' }
      const { w, h } = dims
      if (w >= h) return { width: '50px', height: Math.round(h / w * 50) + 'px', objectFit: 'contain' }
      return { width: Math.round(w / h * 50) + 'px', height: '50px', objectFit: 'contain' }
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
      this.selectedItems = this.sortItems(this.selectedItems)
      if (!this.detailVisible) return
      this.$nextTick(() => {
        this.teardownObserver()
        this.setupObserver()
        this.triggerCacheAt(0)
      })
    },

    onSortModeClick(mode) {
      if (this.sortBy === mode) {
        this.toggleSortDir()
        return
      }
      this.sortBy = mode
      this.sortDir = 'asc'
      this.refreshSortResult()
    },

    toggleSortDir() {
      this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc'
      this.refreshSortResult()
    },

    onBcMousedown(e) {
      const el = this.$refs.breadcrumbWrap
      if (!el) return
      this.bcDragging   = true
      this.bcStartX     = e.pageX
      this.bcScrollLeft = el.scrollLeft
    },
    onBcMouseup()    { this.bcDragging = false },
    onBcMouseleave() { this.bcDragging = false },
    onBcMousemove(e) {
      if (!this.bcDragging) return
      e.preventDefault()
      const el = this.$refs.breadcrumbWrap
      if (!el) return
      el.scrollLeft = this.bcScrollLeft - (e.pageX - this.bcStartX)
    },

    async openImage(item) {
      if (item.type === 'album' && item.public_id) {
        this.$router.push({ name: 'album', params: { id: item.public_id } })
        return
      }
      if (!item.id) return
      try {
        await fetch(`${API_BASE}/api/images/${item.id}/open`)
      } catch { /* silently ignore */ }
    },
  },
}
</script>

<style scoped lang="css">
.page { @apply flex flex-col gap-6; }

.page-header {
  @apply sticky top-0 z-40 flex items-center gap-3 bg-white bg-opacity-95 py-3 backdrop-blur-sm shadow-sm;
}
.page-title  { @apply text-xl font-semibold text-slate-900 m-0 min-w-0; }
.page-subtitle { @apply text-sm text-slate-400 m-0; }
.header-count { @apply text-sm text-slate-400; }
.back-btn {
  @apply flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm text-slate-500
         bg-transparent border-0 cursor-pointer transition-colors duration-150;
}
.back-btn:hover { @apply bg-slate-100 text-slate-800; }

.grid-wrapper {
  @apply flex flex-col gap-10;
  transition: opacity 180ms ease;
}
.grid-wrapper--fading { @apply opacity-0 pointer-events-none; }

.empty-hint {
  @apply border-2 border-dashed border-slate-300 bg-slate-50 rounded-xl
         py-16 text-center text-slate-400 text-sm;
}
.empty-hint__icon { @apply text-5xl block mb-3; }

.year-section { @apply flex flex-col gap-4; }
.year-heading  { @apply flex items-baseline gap-3; }
.year-heading__num {
  @apply text-5xl font-extrabold text-slate-800 leading-none;
  letter-spacing: -0.02em;
}
.year-heading__count { @apply text-sm text-slate-400; }
.year-divider {
  @apply h-px;
  background: linear-gradient(to right, #cbd5e1, transparent);
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.25rem;
}
@media (min-width: 768px) {
  .card-grid { grid-template-columns: repeat(6, 1fr); }
}

.month-card { aspect-ratio: 1 / 1; }
.month-label {
  @apply text-white font-bold leading-none select-none;
  font-family: 'Georgia', 'Times New Roman', serif;
  font-size: clamp(1.2rem, 3vw, 1.6rem);
  letter-spacing: 0.1em;
  text-shadow: 0 2px 12px rgba(0,0,0,.7);
}
.month-count {
  @apply mt-1 select-none;
  color: rgba(255,255,255,.65);
  font-size: 0.72rem;
  letter-spacing: 0.06em;
}

/* ── Detail photo grid: justified-layout (equal-height rows, natural aspect) ──── */
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
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
@keyframes skeleton-fade {
  0%, 100% { opacity: 0.4; }
  50%       { opacity: 0.8; }
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
.badge-icon  { font-size: 1rem; }
.badge-name  {
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

.t-forward-enter-active {
  transition: opacity 220ms ease, transform 220ms cubic-bezier(0.20, 0, 0.30, 1);
  transform-origin: var(--tx, 50%) var(--ty, 50%);
}
.t-forward-enter-from { opacity: 0; transform: scale(0.92) translateY(14px); }
.t-forward-enter-to   { opacity: 1; transform: scale(1)    translateY(0); }
.t-forward-leave-active { transition: opacity 160ms ease; }
.t-forward-leave-from   { opacity: 1; }
.t-forward-leave-to     { opacity: 0; }

.t-back-leave-active {
  transition: opacity 220ms ease, transform 220ms cubic-bezier(0.40, 0, 0.80, 1);
  transform-origin: var(--tx, 50%) var(--ty, 50%);
}
.t-back-leave-from { opacity: 1; transform: scale(1)    translateY(0); }
.t-back-leave-to   { opacity: 0; transform: scale(0.92) translateY(14px); }

/* ── Breadcrumb ─────────────────────────────────────────── */
.breadcrumb-wrap {
  flex: 1 1 0;
  min-width: 0;
  overflow-x: auto;
  cursor: grab;
  scrollbar-width: none;
  -ms-overflow-style: none;
  user-select: none;
}
.breadcrumb-wrap::-webkit-scrollbar { display: none; }
.breadcrumb-wrap.bc-dragging { cursor: grabbing; }

.breadcrumb {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  white-space: nowrap;
  padding: 0.125rem 0;
}
.bc-item {
  font-size: 0.875rem;
  color: #64748b;
  max-width: 12rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bc-item--cur {
  color: #1e293b;
  font-weight: 600;
}
.bc-sep {
  color: #94a3b8;
  font-size: 0.75rem;
  flex-shrink: 0;
}

/* ── View-mode toggle ───────────────────────────────────── */
.header-actions {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  flex-shrink: 0;
}

.sort-controls {
  display: flex;
  align-items: center;
  gap: 0;
}

.sort-switch {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 1fr;
  align-items: center;
  min-width: 132px;
  height: 30px;
  padding: 2px;
  border-radius: 999px;
  background: #dbe6f0;
}

.sort-thumb {
  position: absolute;
  left: 2px;
  top: 2px;
  width: calc(50% - 2px);
  height: 26px;
  border-radius: 999px;
  background: #22c55e;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.16);
  transition: transform 160ms ease;
  pointer-events: none;
}

.sort-thumb.is-alpha {
  transform: translateX(100%);
}

.sort-mode-btn {
  position: relative;
  z-index: 1;
  border: none;
  background: transparent;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  line-height: 1;
  padding: 0;
  height: 100%;
}

.sort-mode-btn.active {
  color: #0f172a;
}

.sort-dir-mark {
  display: inline-block;
  margin-left: 1px;
  color: #0f172a;
  font-weight: 700;
}

.view-toggle {
  display: flex;
  align-items: center;
  gap: 2px;
  background: #f1f5f9;
  border-radius: 8px;
  padding: 3px;
}
.vt-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  transition: background 140ms ease, color 140ms ease;
}
.vt-btn:hover:not(:disabled) {
  background: #e2e8f0;
  color: #475569;
}
.vt-btn.active {
  background: #ffffff;
  color: #0f172a;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12), 0 0 0 1px rgba(0,0,0,.04);
}
.vt-btn--placeholder {
  opacity: 0.35;
  cursor: not-allowed;
}

/* ── List view ──────────────────────────────────────────── */
.list-view {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.list-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 5px 6px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 130ms ease;
}
.list-item:hover { background: #f8fafc; }
.list-thumb-wrap {
  flex-shrink: 0;
  width: 50px;
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  overflow: hidden;
  background: #f1f5f9;
}
.list-thumb {
  display: block;
  border-radius: 3px;
}
.list-thumb-skeleton {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  background: linear-gradient(90deg, #e2e8f0 25%, #f1f5f9 50%, #e2e8f0 75%);
  background-size: 200% 100%;
  animation: skeleton-wave 1.4s ease-in-out infinite;
}
.list-filename {
  font-size: 0.8125rem;
  color: #334155;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
  flex: 1;
}
.list-album-badge {
  flex-shrink: 0;
  font-size: 0.75rem;
  color: #94a3b8;
}
</style>
