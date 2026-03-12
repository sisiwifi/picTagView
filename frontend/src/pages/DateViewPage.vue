<template>
  <section class="page">
    <!-- ── Header ──────────────────────────────────────────────── -->
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

    <!-- ── Grid view ───────────────────────────────────────────── -->
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

    <!-- ── Detail view ─────────────────────────────────────────── -->
    <Transition :name="transitionName">
      <div
        v-if="detailVisible"
        class="detail-wrapper"
        :style="originStyle"
      >
        <LoadingSpinner v-if="loadingItems" />

        <div v-else class="card-grid">
          <ThumbCard
            v-for="(item, i) in selectedItems"
            :key="i"
            :src="api(item.thumb_url)"
            class="item-card"
            :overlay-opacity="item.type === 'album' ? 0.50 : 0.15"
            :rounded="'0.75rem'"
          >
            <!-- Album badge -->
            <template v-if="item.type === 'album'">
              <span class="album-icon">🗂️</span>
              <span class="album-name">{{ item.name }}</span>
              <span class="album-count">相册 · {{ item.count }} 张</span>
            </template>
          </ThumbCard>
        </div>
      </div>
    </Transition>
  </section>
</template>

<script>
import ThumbCard      from '../components/ThumbCard.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'

const API_BASE = 'http://127.0.0.1:8000'

export default {
  name: 'DateViewPage',
  components: { ThumbCard, LoadingSpinner },

  data() {
    return {
      years:         [],
      loadingDates:  true,
      view:          'grid',    // 'grid' | 'animating' | 'detail' | 'returning'
      navDir:        'forward', // 'forward' | 'back'
      detailVisible: false,     // v-if source for the detail panel (controls Transition)
      selectedGroup: '',
      selectedItems: [],
      loadingItems:  false,
      originX: '50%',
      originY: '50%',
    }
  },

  computed: {
    transitionName() {
      return this.navDir === 'back' ? 't-back' : 't-forward'
    },
    originStyle() {
      return { '--tx': this.originX, '--ty': this.originY }
    },
  },

  created()   { this.fetchDates() },
  activated() {
    this.view          = 'grid'
    this.detailVisible = false
    this.selectedGroup = ''
    this.selectedItems = []
    this.fetchDates()
  },

  methods: {
    api(path) { return `${API_BASE}${path}` },

    async fetchDates() {
      this.loadingDates = true
      try {
        const r = await fetch(`${API_BASE}/api/dates`)
        const d = await r.json()
        this.years = d.years || []
      } catch { this.years = [] }
      finally  { this.loadingDates = false }
    },

    async openGroup(mg, ev) {
      // Record click-centre for transform-origin
      const rect = ev.currentTarget.getBoundingClientRect()
      this.originX = `${Math.round(((rect.left + rect.width  / 2) / window.innerWidth)  * 100)}%`
      this.originY = `${Math.round(((rect.top  + rect.height / 2) / window.innerHeight) * 100)}%`

      this.navDir = 'forward'
      this.view   = 'animating'   // grid fades out (160ms CSS transition)
      this.selectedGroup = mg.group
      this.loadingItems  = true
      this.selectedItems = []

      const [data] = await Promise.all([
        fetch(`${API_BASE}/api/dates/${mg.group}/items`)
          .then(r => r.json()).catch(() => ({ items: [] })),
        new Promise(r => setTimeout(r, 170)),
      ])

      this.selectedItems = data.items || []
      this.loadingItems  = false
      this.detailVisible = true  // ← triggers t-forward-enter (220ms)
      this.view = 'detail'
    },

    closeDetail() {
      this.navDir = 'back'
      // 'returning': grid becomes visible at opacity-0 while detail plays its leave animation
      this.view = 'returning'
      this.detailVisible = false   // ← triggers t-back-leave (220ms scale + fade)
      this.selectedGroup = ''
      // After detail has mostly gone (~190ms), lift the opacity so grid fades in (180ms CSS)
      setTimeout(() => { this.view = 'grid' }, 190)
      // Clean up detail data after both animations finish
      setTimeout(() => { this.selectedItems = [] }, 430)
    },
  },
}
</script>

<style scoped lang="postcss">
/* ── Page layout ──────────────────────────────────────────────── */
.page { @apply flex flex-col gap-6; }

/* ── Header ──────────────────────────────────────────────────── */
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

/* ── Grid wrapper ────────────────────────────────────────────── */
.grid-wrapper {
  @apply flex flex-col gap-10;
  transition: opacity 180ms ease;   /* used for both forward-out and back-in */
}
.grid-wrapper--fading { @apply opacity-0 pointer-events-none; }

/* ── Empty hint ──────────────────────────────────────────────── */
.empty-hint {
  @apply border-2 border-dashed border-slate-300 bg-slate-50 rounded-xl
         py-16 text-center text-slate-400 text-sm;
}
.empty-hint__icon { @apply text-5xl block mb-3; }

/* ── Year section ────────────────────────────────────────────── */
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

/* ── Card grid ───────────────────────────────────────────────── */
.card-grid { @apply grid grid-cols-2 gap-5; }
@media (min-width: 640px)  { .card-grid { @apply grid-cols-3; } }
@media (min-width: 768px)  { .card-grid { @apply grid-cols-4; } }
@media (min-width: 1024px) { .card-grid { @apply grid-cols-5; } }

/* ── Month card content ──────────────────────────────────────── */
.month-card { @apply h-44; }
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

/* ── Item card content ───────────────────────────────────────── */
.item-card { aspect-ratio: 3/2; }
.album-icon  { @apply text-2xl mb-1; }
.album-name  {
  @apply text-white text-xs font-semibold text-center select-none;
  max-width: 90%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-shadow: 0 1px 6px rgba(0,0,0,.8);
}
.album-count {
  @apply mt-1 select-none;
  color: rgba(255,255,255,.60);
  font-size: 0.72rem;
}

/* ══════════════════════════════════════════════════════════════
   PANEL TRANSITIONS
   CSS custom properties (--tx / --ty) and transform-origin
   cannot use @apply, so these stay as plain CSS.

   Animation timing overview
   ─────────────────────────
   Forward (open):
     grid fades OUT  →  160ms CSS opacity
     detail enters   →  220ms scale-up from card position
   Back (close):
     detail leaves   →  220ms scale-down to card position  (symmetric!)
     grid fades IN   →  180ms CSS opacity (starts at ~190ms, slight overlap)
══════════════════════════════════════════════════════════════ */

/* ── Forward: detail opens ──────────────────────────────────── */
.t-forward-enter-active {
  transition: opacity 220ms ease, transform 220ms cubic-bezier(0.20, 0, 0.30, 1);
  transform-origin: var(--tx, 50%) var(--ty, 50%);
}
.t-forward-enter-from { opacity: 0; transform: scale(0.92) translateY(14px); }
.t-forward-enter-to   { opacity: 1; transform: scale(1)    translateY(0); }

.t-forward-leave-active { transition: opacity 160ms ease; }
.t-forward-leave-from   { opacity: 1; }
.t-forward-leave-to     { opacity: 0; }

/* ── Back: detail closes — symmetric with forward enter ─────── */
.t-back-leave-active {
  transition: opacity 220ms ease, transform 220ms cubic-bezier(0.40, 0, 0.80, 1);
  transform-origin: var(--tx, 50%) var(--ty, 50%);
}
.t-back-leave-from { opacity: 1; transform: scale(1)    translateY(0); }
.t-back-leave-to   { opacity: 0; transform: scale(0.92) translateY(14px); }

/* grid fades in via the CSS transition on .grid-wrapper (180ms);
   no t-back-enter needed since the grid uses v-show + CSS class */
</style>
