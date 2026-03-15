<template>
  <section class="page">
    <header class="page-header">
      <h2 class="page-title">主页</h2>
      <p class="page-subtitle">欢迎使用 picTagView 图片管理系统。</p>
    </header>

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
const API_BASE = 'http://127.0.0.1:8000'

export default {
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
.page-header { @apply flex flex-col gap-1; }
.page-title  { @apply text-2xl font-semibold text-slate-900 m-0; }
.page-subtitle { @apply text-sm text-slate-500 m-0; }

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
