<template>
  <section class="page">
    <TopLevelPageHeader
      title="标签总览"
      subtitle="这里会承接标签检索、分类统计和批量管理能力，当前先提供统一的一级页占位。"
    />

    <div class="placeholder-card">
      <span class="placeholder-card__icon">🏷️</span>
      <p class="placeholder-card__title">标签总览正在整理中</p>
      <p class="placeholder-card__text">下一步可以在这里接入标签搜索、使用频率排序、颜色视图和批量编辑入口。</p>
    </div>
  </section>
</template>

<script>
import TopLevelPageHeader from './TopLevelPageHeader.vue'

export default {
  name: 'TagOverviewPlaceholderPage',
  components: {
    TopLevelPageHeader,
  },
}
</script>

<style scoped lang="css">
.page {
  @apply flex flex-col gap-8;
}

.placeholder-card {
  @apply rounded-2xl border border-dashed border-sky-200 bg-sky-50 px-6 py-20 text-center text-sky-900;
}

.placeholder-card__icon {
  @apply mb-4 block text-6xl leading-none;
}

.placeholder-card__title {
  @apply m-0 text-lg font-semibold;
}

.placeholder-card__text {
  @apply mx-auto mt-3 max-w-2xl text-sm leading-6 text-sky-800/80;
}
</style>