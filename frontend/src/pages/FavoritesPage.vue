<template>
  <section class="page favorites-page" :style="pageVars">
    <TopLevelPageHeader
      title="收藏"
      subtitle="按收藏夹浏览跨月份整理的图片。"
    />

    <LoadingSpinner v-if="loadingCollections" />

    <div v-else-if="!collections.length" class="empty-hint">
      <span class="empty-hint__icon">☆</span>
      <p>暂无可见收藏夹。</p>
    </div>

    <div v-else class="card-grid">
      <ThumbCard
        v-for="collection in collections"
        :key="collection.public_id || collection.id"
        :src="resolvedUrl(collection)"
        class="favorites-card"
        :overlay-opacity="0.42"
        :rounded="'1.25rem'"
        @click="openCollection(collection)"
      >
        <span class="favorites-card__label">{{ collection.title }}</span>
        <span class="favorites-card__count">{{ collection.photo_count }} 张</span>
      </ThumbCard>
    </div>
  </section>
</template>

<script>
import ThumbCard from '../components/ThumbCard.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import TopLevelPageHeader from './TopLevelPageHeader.vue'
import { API_BASE, topLevelPageVars } from './topLevelPageConvention'

export default {
  name: 'FavoritesPage',
  components: {
    ThumbCard,
    LoadingSpinner,
    TopLevelPageHeader,
  },
  data() {
    return {
      collections: [],
      loadingCollections: true,
      cacheUrls: {},
      pollTimer: null,
      taskId: null,
      cacheGeneration: 0,
      cacheStatusCursor: 0,
    }
  },
  computed: {
    pageVars() {
      return topLevelPageVars()
    },
  },
  created() {
    this.fetchCollections()
  },
  beforeUnmount() {
    this.stopPoll()
  },
  methods: {
    resolvedUrl(item) {
      if (!item) return ''
      const cacheKey = item.cover_photo_id
      if (cacheKey && this.cacheUrls[cacheKey]) return `${API_BASE}${this.cacheUrls[cacheKey]}`
      if (item.cache_thumb_url) return `${API_BASE}${item.cache_thumb_url}`
      if (item.thumb_url) return `${API_BASE}${item.thumb_url}`
      return ''
    },

    async fetchCollections() {
      this.loadingCollections = true
      try {
        const response = await fetch(`${API_BASE}/api/collections`)
        const payload = await response.json().catch(() => ({}))
        this.collections = Array.isArray(payload?.items) ? payload.items : []

        const missingIds = this.collections
          .filter(item => item.cover_photo_id && !item.thumb_url && !this.cacheUrls[item.cover_photo_id])
          .map(item => item.cover_photo_id)

        for (const item of this.collections) {
          if (item.cover_photo_id && item.cache_thumb_url) {
            this.cacheUrls = {
              ...this.cacheUrls,
              [item.cover_photo_id]: item.cache_thumb_url,
            }
          }
        }

        if (missingIds.length > 0) {
          try {
            const generation = this.cacheGeneration + 1
            const cacheRes = await fetch(`${API_BASE}/api/thumbnails/cache`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                ordered_image_ids: missingIds,
                generation,
                page_token: 'favorites-overview',
                sort_signature: `collections:${missingIds.length}`,
                direction: 'none',
              }),
            })
            if (cacheRes.ok) {
              const { task_id } = await cacheRes.json()
              this.cacheGeneration = generation
              this.cacheStatusCursor = 0
              this.taskId = task_id
              this.startPoll(generation)
            }
          } catch {
            // ignore cache warming failures
          }
        }
      } catch {
        this.collections = []
      } finally {
        this.loadingCollections = false
      }
    },

    openCollection(collection) {
      if (!collection?.public_id) return
      this.$router.push(`/favorites/${encodeURIComponent(collection.public_id)}`)
    },

    startPoll(expectedGeneration = this.cacheGeneration) {
      this.stopPoll(false)
      const poll = async () => {
        if (!this.taskId || expectedGeneration !== this.cacheGeneration) return
        try {
          const res = await fetch(`${API_BASE}/api/thumbnails/cache/status/${this.taskId}?cursor=${this.cacheStatusCursor}`)
          if (!res.ok) return
          const data = await res.json()
          if (expectedGeneration !== this.cacheGeneration) return
          const newUrls = {}
          for (const item of (data.items || [])) {
            if (item.id && item.cache_thumb_url) newUrls[item.id] = item.cache_thumb_url
          }
          if (Object.keys(newUrls).length > 0) {
            this.cacheUrls = { ...this.cacheUrls, ...newUrls }
          }
          if (Number.isInteger(data.next_cursor)) {
            this.cacheStatusCursor = data.next_cursor
          } else {
            this.cacheStatusCursor += (data.items || []).length
          }
          if (data.status === 'running') {
            this.pollTimer = setTimeout(poll, 180)
          }
        } catch {
          // ignore polling failures
        }
      }
      this.pollTimer = setTimeout(poll, 180)
    },

    stopPoll(resetTask = true) {
      if (this.pollTimer) {
        clearTimeout(this.pollTimer)
        this.pollTimer = null
      }
      if (resetTask) {
        this.taskId = null
      }
      this.cacheStatusCursor = 0
    },
  },
}
</script>

<style scoped lang="css">
.page {
  @apply flex flex-col gap-6;
}

.empty-hint {
  @apply border-2 border-dashed border-slate-300 bg-slate-50 rounded-xl py-16 text-center text-slate-400 text-sm;
}

.empty-hint__icon {
  @apply text-5xl block mb-3;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.25rem;
}

@media (orientation: landscape) {
  .card-grid {
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }
}

@media (orientation: portrait) {
  .card-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

.favorites-card {
  aspect-ratio: 1 / 1;
}

.favorites-card__label {
  @apply text-white font-bold leading-none select-none text-center px-3;
  font-family: 'Georgia', 'Times New Roman', serif;
  font-size: clamp(1.05rem, 2.7vw, 1.45rem);
  letter-spacing: 0.08em;
  text-shadow: 0 2px 12px rgba(0, 0, 0, 0.72);
}

.favorites-card__count {
  @apply mt-1 select-none;
  color: rgba(255, 255, 255, 0.7);
  font-size: 0.72rem;
  letter-spacing: 0.06em;
}
</style>