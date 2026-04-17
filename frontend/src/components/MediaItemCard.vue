<template>
  <article class="media-card" :class="cardClasses">
    <div class="media-card__visual">
      <img
        v-if="src"
        class="media-card__img"
        :src="src"
        :alt="alt"
        loading="lazy"
        draggable="false"
      />
      <div v-else class="media-card__skeleton">
        <span class="media-card__skeleton-label">...</span>
      </div>

      <button
        class="media-card__pick"
        type="button"
        :disabled="disabled"
        :aria-pressed="selected ? 'true' : 'false'"
        :aria-label="selected ? '取消选择' : '选择项目'"
        @pointerdown.stop
        @click.stop="$emit('toggle-select')"
      >
        <span v-if="selected" class="media-card__pick-mark">✓</span>
      </button>

      <span v-if="itemType === 'album'" class="media-card__type-flag">ALB</span>
    </div>

    <div class="media-card__info">
      <button
        class="media-card__info-toggle"
        type="button"
        :title="infoTitle"
        @pointerdown.stop
        @click.stop="$emit('toggle-info')"
      >
        <span class="media-card__info-text">{{ infoText }}</span>
      </button>

      <button
        class="media-card__details"
        type="button"
        title="查看详情"
        aria-label="查看详情"
        @pointerdown.stop
        @click.stop="$emit('details')"
      >...</button>
    </div>
  </article>
</template>

<script>
export default {
  name: 'MediaItemCard',
  props: {
    src: { type: String, default: '' },
    alt: { type: String, default: '' },
    infoText: { type: String, default: '' },
    infoTitle: { type: String, default: '' },
    itemType: { type: String, default: 'image' },
    selected: { type: Boolean, default: false },
    disabled: { type: Boolean, default: false },
  },
  emits: ['toggle-info', 'details', 'toggle-select'],
  computed: {
    cardClasses() {
      return {
        'is-selected': this.selected,
        'is-disabled': this.disabled,
        'is-album': this.itemType === 'album',
      }
    },
  },
}
</script>

<style scoped lang="css">
.media-card {
  display: flex;
  flex-direction: column;
  min-width: 0;
  border: 1px solid #dbe3ec;
  border-radius: 20px;
  overflow: hidden;
  background: #ffffff;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
  transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease, opacity 180ms ease;
}

.media-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.10);
  border-color: #c7d2de;
}

.media-card.is-selected {
  border-color: #0f172a;
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.16);
}

.media-card.is-disabled {
  opacity: 0.48;
  filter: grayscale(0.45);
}

.media-card__visual {
  position: relative;
  aspect-ratio: 1 / 1;
  overflow: hidden;
  background: linear-gradient(160deg, #e2e8f0 0%, #f8fafc 100%);
}

.media-card__img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
  user-select: none;
}

.media-card__skeleton {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(90deg, #e2e8f0 25%, #f8fafc 50%, #e2e8f0 75%);
  background-size: 200% 100%;
  animation: media-card-wave 1.4s ease-in-out infinite;
}

.media-card__skeleton-label {
  color: #94a3b8;
  font-size: 0.95rem;
  letter-spacing: 0.12em;
  user-select: none;
}

.media-card__pick {
  position: absolute;
  top: 10px;
  left: 10px;
  width: 26px;
  height: 26px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 2px solid rgba(15, 23, 42, 0.85);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.12);
  padding: 0;
  cursor: pointer;
  transition: transform 140ms ease, background 140ms ease, border-color 140ms ease;
}

.media-card__pick:hover:not(:disabled) {
  transform: scale(1.04);
}

.media-card__pick:disabled {
  cursor: not-allowed;
}

.media-card__pick-mark {
  color: #ffffff;
  font-size: 0.85rem;
  font-weight: 700;
  line-height: 1;
}

.media-card.is-selected .media-card__pick {
  border-color: #0f172a;
  background: #0f172a;
}

.media-card__type-flag {
  position: absolute;
  top: 12px;
  right: 12px;
  min-width: 38px;
  height: 24px;
  padding: 0 0.45rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(15, 23, 42, 0.16);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.92);
  color: #334155;
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.media-card__info {
  height: 56px;
  display: flex;
  align-items: stretch;
  gap: 0.2rem;
  padding: 0 0.25rem 0 0.45rem;
  border-top: 1px solid #e2e8f0;
  background: rgba(255, 255, 255, 0.96);
}

.media-card__info-toggle {
  flex: 1 1 auto;
  min-width: 0;
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  padding: 0 0.45rem;
  border: 0;
  background: transparent;
  color: #334155;
  cursor: pointer;
  text-align: left;
  transition: color 140ms ease;
}

.media-card__info-toggle:hover {
  color: #0f172a;
}

.media-card__info-text {
  display: block;
  width: 100%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-size: 0.84rem;
  font-weight: 600;
}

.media-card__details {
  width: 40px;
  flex-shrink: 0;
  border: 0;
  border-radius: 12px;
  margin: 8px 0;
  background: transparent;
  color: #64748b;
  font-size: 1.15rem;
  font-weight: 700;
  line-height: 1;
  letter-spacing: 0.08em;
  cursor: pointer;
  transition: background 140ms ease, color 140ms ease, transform 140ms ease;
}

.media-card__details:hover {
  background: #e2e8f0;
  color: #0f172a;
  transform: translateY(-1px);
}

@keyframes media-card-wave {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>