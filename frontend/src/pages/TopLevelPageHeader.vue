<template>
  <header class="page-header">
    <div class="page-header__main">
      <h2 class="page-title">{{ title }}</h2>
      <p v-if="subtitle" class="page-subtitle">{{ subtitle }}</p>
    </div>

    <div v-if="$slots.default" class="page-header__extra">
      <slot />
    </div>
  </header>
</template>

<script>
export default {
  name: 'TopLevelPageHeader',
  props: {
    title: {
      type: String,
      required: true,
    },
    subtitle: {
      type: String,
      default: '',
    },
  },
}
</script>

<style scoped lang="css">
.page-header {
  @apply flex flex-wrap items-end justify-between gap-3;
}

.page-header__main {
  @apply flex min-w-0 flex-col gap-1;
}

.page-header__extra {
  @apply flex flex-wrap items-center gap-3;
}

.page-title {
  @apply m-0 text-2xl font-semibold text-slate-900;
}

.page-subtitle {
  @apply m-0 text-sm text-slate-500;
}
</style>