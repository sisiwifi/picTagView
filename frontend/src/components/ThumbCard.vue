<template>
  <div class="thumb-card" :style="{ borderRadius: rounded }" @click="$emit('click', $event)">
    <img class="thumb-card__img" :src="src" :alt="alt" loading="lazy" />
    <div class="thumb-card__overlay" :style="{ background: `rgba(0,0,0,${overlayOpacity})` }"></div>
    <div class="thumb-card__body">
      <slot />
    </div>
  </div>
</template>

<script>
export default {
  name: 'ThumbCard',
  emits: ['click'],
  props: {
    src:            { type: String, required: true },
    alt:            { type: String, default: '' },
    overlayOpacity: { type: Number, default: 0.40 },
    rounded:        { type: String, default: '1rem' },
  },
}
</script>

<style scoped lang="postcss">
.thumb-card {
  @apply relative overflow-hidden cursor-pointer shadow-md;
  transition: box-shadow 200ms ease, transform 200ms ease;
}
.thumb-card:hover {
  @apply shadow-xl -translate-y-0.5;
}
.thumb-card__img {
  @apply absolute inset-0 w-full h-full object-cover;
  transition: transform 300ms ease;
}
.thumb-card:hover .thumb-card__img {
  @apply scale-105;
}
.thumb-card__overlay {
  @apply absolute inset-0;
}
.thumb-card__body {
  @apply absolute inset-0 flex flex-col items-center justify-center;
}
</style>
