<template>
  <section class="page">
    <TopLevelPageHeader
      title="主页"
      subtitle="欢迎使用 picTagView 图片管理系统。"
    />

    <!-- Stats row -->
    <div class="stats-row">
      <div class="stat-card">
        <span class="stat-card__icon">🖼️</span>
        <div class="stat-card__body">
          <span class="stat-card__num">{{ fileCount }}</span>
          <span class="stat-card__label">已导入图片</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script>
import TopLevelPageHeader from './TopLevelPageHeader.vue'

const API_BASE = 'http://127.0.0.1:8000'

export default {
  components: {
    TopLevelPageHeader,
  },
  data() {
    return { fileCount: 0 }
  },
  methods: {
    refreshFileCount() {
      fetch(`${API_BASE}/api/images/count`)
        .then(r => r.json())
        .then(d => { if (d.count != null) this.fileCount = d.count })
        .catch(() => {})
    },
    onLibraryRefreshed(e) {
      if (e.detail && e.detail.total_images != null) {
        this.fileCount = e.detail.total_images
      }
    },
  },
  created() {
    this.refreshFileCount()
    window.addEventListener('library-refreshed', this.onLibraryRefreshed)
  },
  activated() {
    this.refreshFileCount()
  },
  beforeUnmount() {
    window.removeEventListener('library-refreshed', this.onLibraryRefreshed)
  },
  beforeRouteEnter(to, from, next) {
    next(vm => vm.refreshFileCount())
  },
  beforeRouteUpdate(to, from, next) {
    this.refreshFileCount()
    next()
  }
}
</script>

<style scoped lang="css">
.page { @apply flex flex-col gap-8; }

.stats-row { @apply flex flex-wrap gap-4; }
.stat-card {
  @apply flex items-center gap-4 bg-white border border-slate-200
         rounded-xl px-6 py-5 shadow-sm;
  min-width: 10rem;
}
.stat-card__icon { @apply text-4xl leading-none; }
.stat-card__body { @apply flex flex-col; }
.stat-card__num  { @apply text-4xl font-bold text-slate-800 leading-none; }
.stat-card__label {
  @apply mt-1 text-slate-400;
  font-size: 0.8rem;
}
</style>
