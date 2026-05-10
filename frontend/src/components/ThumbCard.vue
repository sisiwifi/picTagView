<template>
  <div class="thumb-card" :style="{ borderRadius: rounded }" @click="$emit('click', $event)">
    <img v-if="activeSrc" class="thumb-card__img" :src="activeSrc" :alt="alt" loading="lazy" @error="onImgError" />
    <div v-else-if="shouldShowUnavailable" class="thumb-card__unavailable">
      <span class="thumb-card__unavailable-label">{{ unavailableLabel }}</span>
    </div>
    <div v-else class="thumb-card__skeleton">
      <span class="skeleton-label">···</span>
    </div>
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
    src:            { type: String, default: '' },
    fallbackSrc:    { type: String, default: '' },
    unavailable:    { type: Boolean, default: false },
    unavailableLabel: { type: String, default: '预览不可用' },
    alt:            { type: String, default: '' },
    overlayOpacity: { type: Number, default: 0.40 },
    rounded:        { type: String, default: '1rem' },
  },
  data() {
    return {
      sourceStage: 'primary',
    }
  },
  computed: {
    sourceStateToken() {
      return `${this.src || ''}|${this.fallbackSrc || ''}`
    },
    activeSrc() {
      if (this.sourceStage === 'done') return ''
      if (this.sourceStage === 'fallback') return this.fallbackSrc || ''
      return this.src || ''
    },
    shouldShowUnavailable() {
      return this.unavailable || this.sourceStage === 'done'
    },
  },
  watch: {
    sourceStateToken() {
      this.sourceStage = 'primary'
    },
  },
  methods: {
    onImgError() {
      if (this.sourceStage === 'primary' && this.fallbackSrc && this.fallbackSrc !== this.src) {
        this.sourceStage = 'fallback'
        return
      }
      this.sourceStage = 'done'
    },
  },
}
</script>

<style scoped lang="css">
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

.thumb-card__skeleton {
  @apply absolute inset-0 flex items-center justify-center;
  background: linear-gradient(90deg, #e2e8f0 25%, #f1f5f9 50%, #e2e8f0 75%);
  background-size: 200% 100%;
  animation: skeleton-wave 1.4s ease-in-out infinite;
}

.thumb-card__unavailable {
  @apply absolute inset-0 flex items-center justify-center;
  background: linear-gradient(180deg, #cbd5e1 0%, #e2e8f0 100%);
}

.thumb-card__unavailable-label {
  @apply text-slate-600 text-xs font-semibold tracking-wide select-none;
}
.skeleton-label {
  @apply text-slate-400 text-sm font-mono tracking-widest select-none;
}
</style>
