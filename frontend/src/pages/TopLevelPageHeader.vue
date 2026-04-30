<template>
  <header class="top-level-header">
    <div class="top-level-header__main">
      <h2 class="top-level-header__title">{{ title }}</h2>
      <p v-if="subtitle" class="top-level-header__subtitle">{{ subtitle }}</p>
    </div>

    <div v-if="$slots.default" class="top-level-header__extra">
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
.top-level-header {
  @apply flex flex-wrap items-end justify-between gap-3;
}

.top-level-header__main {
  @apply flex min-w-0 flex-col gap-1;
}

.top-level-header__extra {
  @apply flex flex-wrap items-center gap-3;
}

.top-level-header__title {
  @apply m-0 text-2xl font-semibold text-slate-900;
}

.top-level-header__subtitle {
  @apply m-0 text-sm text-slate-500;
}

@media (max-width: 640px) {
  .top-level-header {
    @apply flex-col items-stretch;
  }

  .top-level-header__extra {
    @apply justify-start;
  }
}
</style>