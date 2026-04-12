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
          @click="viewMode = 'grid'"
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
          @click="viewMode = 'list'"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <rect x="1" y="2" width="12" height="2" rx="1" fill="currentColor"/>
            <rect x="1" y="6" width="12" height="2" rx="1" fill="currentColor"/>
            <rect x="1" y="10" width="12" height="2" rx="1" fill="currentColor"/>
          </svg>
        </button>
        <button class="vm-btn vm-btn--disabled" title="选择（即将推出）" disabled>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M3 1L3 11L6 8.5L8 13L9.5 12.3L7.5 7.8L11 7.8Z" fill="currentColor"/>
          </svg>
        </button>
      </div>
    </BreadcrumbHeader>

    <LoadingSpinner v-if="loading" />

    <div v-else-if="!items.length" class="empty-hint">
      <span class="empty-hint__icon">📂</span>
      <p>此相册尚无内容。</p>
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
            <span class="skeleton-label">···</span>
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
        :data-index="idx"
        @click="openItem(item)"
      >
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
        <span class="list-name">{{ item.name || item.full_filename || '未知文件' }}</span>
        <span v-if="item.type === 'album'" class="list-album-badge">📁 {{ item.count }} 张</span>
      </div>
    </div>
  </section>
</template>

<script>
import LoadingSpinner from '../components/LoadingSpinner.vue'
import BreadcrumbHeader from '../components/BreadcrumbHeader.vue'

const API_BASE = 'http://127.0.0.1:8000'
const POLL_MS = 80
const RADIUS = 50
const DEBOUNCE_MS = 300

export default {
  name: 'AlbumViewPage',
  components: { LoadingSpinner, BreadcrumbHeader },
  props: { id: { type: String, required: true } },

  data() {
    return {
      album: {},
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
      // 导航时预先传入的相册名，避免数据加载前显示占位符"相册"
      pendingTitle: sessionStorage.getItem('pendingAlbumTitle') || '',
    }
  },

  computed: {
    currentGroup() {
      const fromQuery = this.$route?.query?.group
      if (typeof fromQuery === 'string' && /^\d{4}-\d{2}$/.test(fromQuery)) {
        return fromQuery
      }
      const fromAlbum = this.album?.date_group
      if (typeof fromAlbum === 'string' && /^\d{4}-\d{2}$/.test(fromAlbum)) {
        return fromAlbum
      }
      const fromPath = this.album?.path
      if (typeof fromPath === 'string') {
        const m = fromPath.match(/(^|\/)(\d{4}-\d{2})(\/|$)/)
        if (m?.[2]) return m[2]
      }
      return ''
    },
    headerCrumbs() {
      const crumbs = [{ label: this.bcLabel('日期视图'), title: '日期视图', to: '/calendar' }]

      if (this.currentGroup) {
        crumbs.push({
          label: this.currentGroup,
          title: this.currentGroup,
          to: { name: 'calendar', query: { group: this.currentGroup } },
        })
      }

      for (const anc of (this.album.ancestors || [])) {
        crumbs.push({
          label: this.bcLabel(anc.title),
          title: anc.title,
          to: {
            name: 'album',
            params: { id: anc.public_id },
            query: this.currentGroup ? { group: this.currentGroup } : {},
          },
        })
      }
      crumbs.push({
        label: this.bcLabel(this.album.title || this.pendingTitle || '\u76f8\u518c'),
        title: this.album.title || this.pendingTitle || '\u76f8\u518c',
        current: true,
      })
      return crumbs
    },
    totalCount() {
      return this.items.length
    },
    justifiedRows() {
      const W = this.containerWidth || (typeof window !== 'undefined' ? window.innerWidth - 48 : 800)
      const GAP = 4
      const TARGET_H = 440
      const items = this.items
      if (!items.length) return []

      const rows = []
      let rowStart = 0
      let rowAR = 0

      for (let i = 0; i < items.length; i++) {
        const dims = this.imgDimensions[items[i].id || items[i].public_id] || { w: 4, h: 3 }
        rowAR += dims.w / dims.h
        const isLast = i === items.length - 1
        const rowLen = i - rowStart + 1
        const neededW = rowAR * TARGET_H + GAP * (rowLen - 1)

        if (neededW >= W || isLast) {
          const totalGap = GAP * (rowLen - 1)
          const actualH = (isLast && neededW < W) ? TARGET_H : Math.round((W - totalGap) / rowAR)
          const rowItems = []
          for (let j = rowStart; j <= i; j++) {
            const it = items[j]
            const key = it.id || it.public_id
            const d = this.imgDimensions[key] || { w: 4, h: 3 }
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
    justifiedRows(newVal, oldVal) {
      if (newVal.length !== oldVal.length) {
        this.$nextTick(() => {
          this.teardownObserver()
          this.setupObserver()
        })
      }
    },
    viewMode() {
      this.$nextTick(() => {
        this.teardownObserver()
        this.setupObserver()
      })
    },
  },

  created() {
    sessionStorage.removeItem('pendingAlbumTitle')
    this.fetchAlbum()
    window.addEventListener('resize', this.onResize)
  },

  beforeUnmount() {
    this.teardownObserver()
    this.teardownResizeObserver()
    this.stopPoll()
    window.removeEventListener('resize', this.onResize)
  },

  methods: {
    goBackOneLevel() {
      const currentId = String(this.id || this.$route?.params?.id || '')
      const ancestors = Array.isArray(this.album?.ancestors) ? this.album.ancestors : []
      const parent = [...ancestors]
        .reverse()
        .find((anc) => anc?.public_id && String(anc.public_id) !== currentId)

      if (parent?.public_id) {
        const query = { ...this.$route.query }
        if (this.currentGroup) query.group = this.currentGroup
        this.$router.push({
          name: 'album',
          params: { id: parent.public_id },
          query,
        })
        return
      }

      const group = this.currentGroup
      if (group) {
        this.$router.push({ name: 'calendar', query: { group } })
        return
      }
      this.$router.push('/calendar')
    },

    async fetchAlbum() {
      this.loading = true
      this.viewMode = 'grid'
      this.sortBy = 'alpha'
      this.sortDir = 'asc'
      this.cacheUrls = {}
      this.imgDimensions = {}
      this.lastCenter = -1
      this.teardownObserver()
      this.teardownResizeObserver()
      this.stopPoll()

      try {
        const res = await fetch(`${API_BASE}/api/albums/${this.id}`)
        if (!res.ok) { this.items = []; this.album = {}; return }
        const data = await res.json()
        this.album = data.album || {}
        this.items = this.sortItems(data.items || [])

        for (const item of this.items) {
          if (item.id && item.cache_thumb_url) {
            this.cacheUrls = { ...this.cacheUrls, [item.id]: item.cache_thumb_url }
          }
        }
      } catch { this.items = []; this.album = {} }
      finally { this.loading = false }

      this.$nextTick(() => {
        window.scrollTo({ top: 0, behavior: 'instant' })
        if (this.$refs.itemGrid) {
          this.containerWidth = this.$refs.itemGrid.offsetWidth
        }
        this.triggerCacheAt(0)
        this.setupObserver()
        this.setupResizeObserver()
      })
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
      if (item.type === 'album' && item.public_id) {
        const query = { ...this.$route.query }
        if (this.currentGroup) query.group = this.currentGroup
        // 将相册名存入 sessionStorage，避免占位符闪烁
        sessionStorage.setItem('pendingAlbumTitle', item.name || '')
        this.$router.push({
          name: 'album',
          params: { id: item.public_id },
          query,
        })
      } else if (item.id) {
        fetch(`${API_BASE}/api/images/${item.id}/open`).catch(() => {})
      }
    },
    onImgLoad(item, evt) {
      const { naturalWidth: w, naturalHeight: h } = evt.target
      if (!w || !h) return
      const key = item.id || item.public_id
      const ex = this.imgDimensions[key]
      if (!ex || ex.w !== w || ex.h !== h) {
        this.imgDimensions = { ...this.imgDimensions, [key]: { w, h } }
      }
    },

    onResize() {
      if (this.$refs.itemGrid) {
        this.containerWidth = this.$refs.itemGrid.offsetWidth
      }
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
      this.$nextTick(() => {
        this.teardownObserver()
        this.setupObserver()
        this.triggerCacheAt(0)
      })
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

    // ── Cache thumbnail polling (same pattern as DateViewPage) ──────────
    idsAround(centerIdx) {
      const items = this.items
      const start = Math.max(0, centerIdx - RADIUS)
      const end = Math.min(items.length - 1, centerIdx + RADIUS)
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

    setupResizeObserver() {
      if (!this.$refs.itemGrid) return
      if (this.resizeObserver) { this.resizeObserver.disconnect(); this.resizeObserver = null }
      this.resizeObserver = new ResizeObserver(() => {
        requestAnimationFrame(() => {
          if (this.$refs.itemGrid) {
            this.containerWidth = this.$refs.itemGrid.offsetWidth
          }
        })
      })
      this.resizeObserver.observe(this.$refs.itemGrid)
    },

    bcLabel(str) {
      if (!str) return ''
      return str.length > 20 ? str.slice(0, 20) + '…' : str
    },
    teardownResizeObserver() {
      if (this.resizeObserver) { this.resizeObserver.disconnect(); this.resizeObserver = null }
    },
  },
}
</script>

<style scoped lang="css">
.page { @apply flex flex-col gap-6; }

/* View mode buttons */
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
  transition: background 150ms ease, color 150ms ease, box-shadow 150ms ease;
}
.vm-btn:hover {
  background: #e2e8f0;
  color: #1e293b;
}
.vm-btn.active {
  background: #fff;
  color: #1e293b;
  box-shadow: 0 1px 3px rgba(0,0,0,.12);
}
.vm-btn--disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.vm-btn--disabled:hover {
  background: transparent;
  color: #64748b;
  box-shadow: none;
}

.empty-hint {
  @apply border-2 border-dashed border-slate-300 bg-slate-50 rounded-xl
         py-16 text-center text-slate-400 text-sm;
}
.empty-hint__icon { @apply text-5xl block mb-3; }

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

/* List view */
.list-view {
  display: flex;
  flex-direction: column;
}
.list-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 6px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 150ms ease;
}
.list-row:hover { background: #f1f5f9; }
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
.list-name {
  flex: 1;
  min-width: 0;
  font-size: 0.875rem;
  color: #334155;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.list-album-badge {
  flex-shrink: 0;
  font-size: 0.7rem;
  color: #64748b;
  background: #f1f5f9;
  border-radius: 4px;
  padding: 1px 5px;
}
</style>
