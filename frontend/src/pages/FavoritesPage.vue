<template>
  <section class="top-level-page favorites-page" :style="pageVars">
    <TopLevelPageHeader
      title="收藏"
      subtitle="这一页先作为一级入口占位，后续会接入收藏夹、分组与筛选能力。"
    />

    <div class="favorites-page__empty">
      <span class="favorites-page__icon">☆</span>
      <p>收藏功能尚未开始实现。</p>
      <span class="favorites-page__note">页面结构与缩略图规范已预留，后续可以直接补业务交互。</span>
    </div>
  </section>
</template>

<script>
import TopLevelPageHeader from './TopLevelPageHeader.vue'
import { topLevelPageVars } from './topLevelPageConvention'

export default {
  name: 'FavoritesPage',
  components: {
    TopLevelPageHeader,
  },
  computed: {
    pageVars() {
      return topLevelPageVars()
    },
  },
}
</script>

<style scoped lang="css">
.top-level-page {
  @apply flex flex-col gap-6;
}

.favorites-page__empty {
  @apply rounded-2xl border border-dashed border-amber-200 bg-amber-50 px-6 py-20 text-center text-amber-800;
}

.favorites-page__icon {
  @apply mb-4 block text-6xl leading-none;
}

.favorites-page__note {
  @apply mt-2 block text-sm text-amber-700/80;
}
</style>