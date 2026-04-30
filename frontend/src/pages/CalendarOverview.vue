<template>
  <section class="page">
    <TopLevelPageHeader
      title="日期视图"
      subtitle="按年份与月份浏览已导入的图片。"
    />

    <LoadingSpinner v-if="loadingDates" />

    <div v-else-if="!years.length" class="empty-hint">
      <span class="empty-hint__icon">📅</span>
      <p>暂无图片，请先在「图库管理」导入。</p>
    </div>

    <div v-else class="grid-wrapper">
      <div v-for="yg in years" :key="yg.year" class="year-section">
        <div class="year-heading">
          <span class="year-heading__num">{{ yg.year }}</span>
          <span class="year-heading__count">{{ yg.months.reduce((s, m) => s + m.count, 0) }} 张</span>
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
            @click="openGroup(mg)"
          >
            <span class="month-label">{{ mg.group }}</span>
            <span class="month-count">{{ mg.count }} 张</span>
          </ThumbCard>
        </div>
      </div>
    </div>
  </section>
</template>

<script>
import ThumbCard from '../components/ThumbCard.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import TopLevelPageHeader from './TopLevelPageHeader.vue'

const API_BASE = 'http://127.0.0.1:8000'

export default {
  name: 'CalendarOverview',
  components: { ThumbCard, LoadingSpinner, TopLevelPageHeader },

  data() {
    return {
      years: [],
      loadingDates: true,
      cacheUrls: {},
      pollTimer: null,
      taskId: null,
      cacheGeneration: 0,
      cacheStatusCursor: 0,
    }
  },

  created() {
    this.fetchDates()
  },

  beforeUnmount() {
    this.stopPoll()
  },

  methods: {
    resolvedUrl(item) {
      if (!item) return ''
      const cached = this.cacheUrls[item.id]
      if (cached) return `${API_BASE}${cached}`
      if (item.cache_thumb_url) return `${API_BASE}${item.cache_thumb_url}`
      if (item.thumb_url) return `${API_BASE}${item.thumb_url}`
      return ''
    },

    async fetchDates() {
      this.loadingDates = true
      try {
        const r = await fetch(`${API_BASE}/api/dates`)
        const d = await r.json()
        this.years = d.years || []

        const allMonths = (d.years || []).flatMap(y => y.months || [])
        for (const m of allMonths) {
          if (m.id && m.cache_thumb_url) {
            this.cacheUrls = { ...this.cacheUrls, [m.id]: m.cache_thumb_url }
          }
        }

        const missingIds = allMonths
          .filter(m => m.id && !m.thumb_url && !this.cacheUrls[m.id])
          .map(m => m.id)

        if (missingIds.length > 0) {
          try {
            const generation = this.cacheGeneration + 1
            const cacheRes = await fetch(`${API_BASE}/api/thumbnails/cache`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                ordered_image_ids: missingIds,
                generation,
                page_token: 'calendar-overview',
                sort_signature: `months:${missingIds.length}`,
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
          } catch { /* ignore */ }
        }
      } catch { this.years = [] }
      finally { this.loadingDates = false }
    },

    openGroup(mg) {
      this.$router.push(`/calendar/${mg.group}`)
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
          for (const it of (data.items || [])) {
            if (it.id && it.cache_thumb_url) newUrls[it.id] = it.cache_thumb_url
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
        } catch { /* ignore */ }
      }
      this.pollTimer = setTimeout(poll, 180)
    },

    stopPoll(resetTask = true) {
      if (this.pollTimer) { clearTimeout(this.pollTimer); this.pollTimer = null }
      if (resetTask) {
        this.taskId = null
      }
      this.cacheStatusCursor = 0
    },
  },
}
</script>

<style scoped lang="css">
.page { @apply flex flex-col gap-6; }

.grid-wrapper { @apply flex flex-col gap-10; }

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
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1.25rem;
}

@media (orientation: landscape) {
  .card-grid { grid-template-columns: repeat(6, minmax(0, 1fr)); }
}

@media (orientation: portrait) {
  .card-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
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
</style>
