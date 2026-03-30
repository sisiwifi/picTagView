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
      <div>
        <h2 class="page-title">{{ (view === 'detail' || view === 'returning') ? selectedGroup : '日期视图' }}</h2>
        <p class="page-subtitle">
          {{ (view === 'detail' || view === 'returning')
            ? `${selectedItems.length} 项`
            : '按年份与月份浏览已导入的图片。' }}
        </p>
      </div>
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
              :src="api(mg.thumb_url)"
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

        <div v-else ref="itemGrid" class="photo-grid">
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
      lastCenter:    -1,
      imgDimensions: {},      // id -> { w, h }  tracked from img.onload
      containerWidth: 0,      // width of the photo-grid container
      refreshingThumbs: false,
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
    this.stopPoll()
    window.removeEventListener('resize', this.onResize)
  },

  methods: {
    api(path) { return path ? `${API_BASE}${path}` : '' },

    resolvedUrl(item) {
      if (!item) return ''
      const cached = this.cacheUrls[item.id]
      if (cached) return `${API_BASE}${cached}`
      if (item.cache_thumb_url) return `${API_BASE}${item.cache_thumb_url}`
      if (item.thumb_url)       return `${API_BASE}${item.thumb_url}`
      return ''
    },

    async fetchDates() {
      this.loadingDates = true
      try {
        const r = await fetch(`${API_BASE}/api/dates`)
        const d = await r.json()
        this.years = d.years || []
        // Detect missing month-cover thumbnails and refresh immediately if needed
        const allMonths = (d.years || []).flatMap(y => y.months || [])
        if (allMonths.some(m => !m.thumb_url)) {
          this._refreshAndUpdateDates()
        }
      } catch { this.years = [] }
      finally  { this.loadingDates = false }
    },

    async openGroup(mg, ev) {
      const rect = ev.currentTarget.getBoundingClientRect()
      this.originX = `${Math.round(((rect.left + rect.width  / 2) / window.innerWidth)  * 100)}%`
      this.originY = `${Math.round(((rect.top  + rect.height / 2) / window.innerHeight) * 100)}%`

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

      this.selectedItems = data.items || []
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
      })
      // Detect missing item thumbnails and trigger an immediate background refresh
      this._checkAndRefreshItems()
    },

    closeDetail() {
      this.teardownObserver()
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
            if (it.id && it.cache_thumb_url) newUrls[it.id] = it.cache_thumb_url
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
      if (!this.$refs.itemGrid) return
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
      for (const el of this.$refs.itemGrid.querySelectorAll('[data-index]')) {
        this.observer.observe(el)
      }
    },

    teardownObserver() {
      if (this.observer) { this.observer.disconnect(); this.observer = null }
      if (this.debounceTimer) { clearTimeout(this.debounceTimer); this.debounceTimer = null }
    },

    onImgLoad(item, evt) {
      const { naturalWidth: w, naturalHeight: h } = evt.target
      if (!w || !h) return
      const ex = this.imgDimensions[item.id]
      if (!ex || ex.w !== w || ex.h !== h) {
        this.imgDimensions = { ...this.imgDimensions, [item.id]: { w, h } }
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
    async _checkAndRefreshItems() {
      if (this.refreshingThumbs) return
      const hasMissing = this.selectedItems.some(
        item => !item.thumb_url && !item.cache_thumb_url
      )
      if (!hasMissing) return
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
        this.selectedItems = data.items || []
        for (const item of this.selectedItems) {
          if (item.id && item.cache_thumb_url) {
            this.cacheUrls = { ...this.cacheUrls, [item.id]: item.cache_thumb_url }
          }
        }
      } catch { /* ignore */ }
      finally { this.refreshingThumbs = false }
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
  @apply sticky top-0 z-40 flex items-center gap-4 bg-white bg-opacity-95 py-2 backdrop-blur-sm shadow-sm;
}
.page-title  { @apply text-2xl font-semibold text-slate-900 m-0; }
.page-subtitle { @apply text-sm text-slate-500 m-0; }
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

.card-grid { @apply grid grid-cols-2 gap-5; }
@media (min-width: 640px)  { .card-grid { @apply grid-cols-3; } }
@media (min-width: 768px)  { .card-grid { @apply grid-cols-4; } }
@media (min-width: 1024px) { .card-grid { @apply grid-cols-5; } }

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
</style>
