<template>
  <section class="page">
    <header class="page-header">
      <button class="back-btn" @click="goBack">← 返回</button>
      <div>
        <h2 class="page-title">{{ album.title || '相册' }}</h2>
        <p class="page-subtitle">{{ totalCount }} 项</p>
      </div>
    </header>

    <LoadingSpinner v-if="loading" />

    <div v-else-if="!items.length" class="empty-hint">
      <span class="empty-hint__icon">📂</span>
      <p>此相册尚无内容。</p>
    </div>

    <div v-else ref="itemGrid" class="photo-grid">
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
  </section>
</template>

<script>
import LoadingSpinner from '../components/LoadingSpinner.vue'

const API_BASE = 'http://127.0.0.1:8000'
const POLL_MS = 80
const RADIUS = 50
const DEBOUNCE_MS = 300

export default {
  name: 'AlbumViewPage',
  components: { LoadingSpinner },
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
      lastCenter: -1,
      imgDimensions: {},
      containerWidth: 0,
    }
  },

  computed: {
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
    id() { this.fetchAlbum() },
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
    this.fetchAlbum()
    window.addEventListener('resize', this.onResize)
  },

  beforeUnmount() {
    this.teardownObserver()
    this.stopPoll()
    window.removeEventListener('resize', this.onResize)
  },

  methods: {
    async fetchAlbum() {
      this.loading = true
      this.cacheUrls = {}
      this.imgDimensions = {}
      this.lastCenter = -1
      this.teardownObserver()
      this.stopPoll()

      try {
        const res = await fetch(`${API_BASE}/api/albums/${this.id}`)
        if (!res.ok) { this.items = []; this.album = {}; return }
        const data = await res.json()
        this.album = data.album || {}
        this.items = data.items || []

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
        this.$router.push({ name: 'album', params: { id: item.public_id } })
      } else if (item.id) {
        fetch(`${API_BASE}/api/images/${item.id}/open`).catch(() => {})
      }
    },

    goBack() {
      if (this.album.parent_public_id) {
        this.$router.push({ name: 'album', params: { id: this.album.parent_public_id } })
      } else {
        this.$router.back()
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
</style>
