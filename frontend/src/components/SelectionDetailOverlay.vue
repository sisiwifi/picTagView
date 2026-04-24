<template>
  <div
    v-if="visible"
    class="detail-layer"
    :style="layerStyle"
    @click.self="$emit('close')"
    @mousedown.middle.prevent.stop="$event.preventDefault()"
    @auxclick.prevent.stop="$event.preventDefault()"
  >
    <section
      class="detail-panel"
      :style="panelStyle"
      role="dialog"
      aria-modal="true"
      aria-label="所选项目详情"
      @mousedown.middle.prevent.stop="$event.preventDefault()"
      @auxclick.prevent.stop="$event.preventDefault()"
    >
      <button class="detail-panel__close" type="button" @click="$emit('close')">关闭</button>

      <div class="detail-panel__content">
        <div class="detail-panel__preview">
          <div v-if="isMulti" class="detail-preview-list">
            <article
              v-for="preview in previewItems"
              :key="preview.key"
              class="detail-preview-list__item"
            >
              <div
                class="detail-preview-list__thumb"
                :style="preview.aspectRatio ? { aspectRatio: preview.aspectRatio } : null"
              >
                <img
                  v-if="preview.previewUrl"
                  class="detail-preview-list__img"
                  :src="preview.previewUrl"
                  :alt="preview.name"
                  loading="lazy"
                  draggable="false"
                />
                <div v-else class="detail-preview-list__skeleton">
                  <span class="detail-preview-list__skeleton-label">...</span>
                </div>
              </div>

              <div class="detail-preview-list__meta">
                <span class="detail-preview-list__name">{{ preview.name }}</span>
                <span class="detail-preview-list__type">
                  {{ preview.type === 'album' ? '相册' : '图片' }}
                </span>
              </div>
            </article>
          </div>

          <div v-else class="detail-preview-stage">
            <img
              v-if="primaryPreview && primaryPreview.previewUrl"
              class="detail-preview-stage__img"
              :src="primaryPreview.previewUrl"
              :alt="primaryPreview.name"
              :style="primaryPreview.aspectRatio ? { aspectRatio: primaryPreview.aspectRatio } : null"
              draggable="false"
            />
            <div v-else class="detail-preview-stage__skeleton">
              <span class="detail-preview-stage__skeleton-label">
                {{ primaryPreview ? primaryPreview.name : '暂无预览' }}
              </span>
            </div>
          </div>
        </div>

        <div class="detail-panel__aside">
          <p v-if="isMulti" class="detail-panel__summary">已选择 {{ previewItems.length }} 项</p>

          <div class="detail-field">
            <span class="detail-field__label">名称</span>
            <div class="detail-field__value">
              <em v-if="nameField.isVarious" class="detail-field__various">various</em>
              <span v-else class="detail-field__text">{{ nameField.text || '—' }}</span>
            </div>
          </div>

          <div v-if="showCategoryField" class="detail-field">
            <span class="detail-field__label">主分类（图片）</span>
            <div class="detail-field__value">
              <em v-if="categoryField.isVarious" class="detail-field__various">various</em>
              <span v-else class="detail-field__text">{{ categoryField.text || '—' }}</span>
            </div>
          </div>

          <div class="detail-field detail-field--tags">
            <span class="detail-field__label">标签</span>
            <div class="detail-field__tag-row" :class="{ 'detail-field__tag-row--single': !showAnalysisButton }">
              <div class="detail-field__value detail-field__value--tags">
                <em v-if="tagsField.isVarious" class="detail-field__various">various</em>
                <span v-else-if="tagsField.isEmpty" class="detail-field__placeholder"></span>
                <span v-else class="detail-field__text">{{ tagsField.text }}</span>
              </div>

              <button v-if="showAnalysisButton" class="detail-field__ghost" type="button" @click="$emit('analysis')">分析</button>
            </div>
          </div>

          <div class="detail-field">
            <span class="detail-field__label">{{ sizeLabel }}</span>
            <div class="detail-field__value">
              <em v-if="sizeField.isVarious" class="detail-field__various">various</em>
              <span v-else class="detail-field__text">{{ sizeField.text || '—' }}</span>
            </div>
          </div>

          <div class="detail-field">
            <span class="detail-field__label">导入时间</span>
            <div class="detail-field__value">
              <em v-if="importedField.isVarious" class="detail-field__various">various</em>
              <span v-else class="detail-field__text">{{ importedField.text || '—' }}</span>
            </div>
          </div>

          <div class="detail-field">
            <span class="detail-field__label">创建时间</span>
            <div class="detail-field__value">
              <em v-if="createdField.isVarious" class="detail-field__various">various</em>
              <span v-else class="detail-field__text">{{ createdField.text || '—' }}</span>
            </div>
          </div>

          <div class="detail-panel__actions">
            <button
              class="detail-panel__action"
              type="button"
              :disabled="!canOpenPrimaryAction || primaryActionDisabled"
              @click="$emit('open-primary')"
            >
              {{ primaryActionLabel }}
            </button>
            <button
              class="detail-panel__action detail-panel__action--danger"
              type="button"
              :disabled="dangerActionDisabled"
              @click="$emit('delete')"
            >
              {{ dangerActionLabel }}
            </button>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script>
export default {
  name: 'SelectionDetailOverlay',
  props: {
    visible: { type: Boolean, default: false },
    layerStyle: { type: Object, default: () => ({}) },
    panelStyle: { type: Object, default: () => ({}) },
    previewItems: { type: Array, default: () => [] },
    isMulti: { type: Boolean, default: false },
    nameField: {
      type: Object,
      default: () => ({ text: '', isVarious: false, isEmpty: false }),
    },
    categoryField: {
      type: Object,
      default: () => ({ text: '', isVarious: false, isEmpty: false }),
    },
    tagsField: {
      type: Object,
      default: () => ({ text: '', isVarious: false, isEmpty: true }),
    },
    sizeField: {
      type: Object,
      default: () => ({ text: '', isVarious: false, isEmpty: false }),
    },
    sizeLabel: { type: String, default: '尺寸' },
    importedField: {
      type: Object,
      default: () => ({ text: '', isVarious: false, isEmpty: false }),
    },
    createdField: {
      type: Object,
      default: () => ({ text: '', isVarious: false, isEmpty: false }),
    },
    primaryActionLabel: { type: String, default: '查看原图' },
    canOpenPrimaryAction: { type: Boolean, default: false },
    primaryActionDisabled: { type: Boolean, default: false },
    dangerActionLabel: { type: String, default: '删除' },
    dangerActionDisabled: { type: Boolean, default: false },
    showAnalysisButton: { type: Boolean, default: true },
  },
  emits: ['analysis', 'close', 'delete', 'open-primary'],
  computed: {
    primaryPreview() {
      return this.previewItems[0] || null
    },
    showCategoryField() {
      return this.previewItems.some(item => item?.type === 'image')
    },
  },
}
</script>

<style scoped lang="css">
.detail-layer {
  position: fixed;
  z-index: 70;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(1rem, 2vw, 1.8rem);
  background: rgba(241, 245, 249, 0.72);
  backdrop-filter: blur(12px);
}

.detail-panel {
  position: relative;
  width: min(1100px, 80%);
  max-width: calc(100% - 12px);
  max-height: calc(100% - 12px);
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 32px 72px rgba(15, 23, 42, 0.18);
  overflow: hidden;
}

.detail-panel__close {
  position: absolute;
  top: 1rem;
  right: 1rem;
  z-index: 2;
  border: 0;
  background: transparent;
  color: #64748b;
  font-size: 0.86rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  cursor: pointer;
  transition: color 140ms ease, opacity 140ms ease;
}

.detail-panel__close:hover {
  color: #0f172a;
}

.detail-panel__content {
  display: grid;
  grid-template-columns: minmax(0, 1.58fr) minmax(320px, 1fr);
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.detail-panel__preview {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  padding: clamp(1.1rem, 2.2vw, 1.8rem);
  background:
    radial-gradient(circle at top left, rgba(226, 232, 240, 0.95), rgba(248, 250, 252, 0.72) 50%),
    linear-gradient(180deg, rgba(241, 245, 249, 0.86), rgba(255, 255, 255, 0.78));
}

.detail-preview-stage,
.detail-preview-stage__skeleton {
  width: 100%;
  height: 100%;
  min-height: 0;
  border-radius: 24px;
}

.detail-preview-stage {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(0.6rem, 1.5vw, 1rem);
  overflow: hidden;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.8);
}

.detail-preview-stage__img {
  width: auto;
  height: auto;
  max-width: 100%;
  max-height: 100%;
  display: block;
  object-fit: contain;
  border-radius: 20px;
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.08);
}

.detail-preview-stage__skeleton,
.detail-preview-list__skeleton {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(90deg, #e2e8f0 25%, #f8fafc 50%, #e2e8f0 75%);
  background-size: 200% 100%;
  animation: detail-wave 1.4s ease-in-out infinite;
}

.detail-preview-stage__skeleton-label,
.detail-preview-list__skeleton-label {
  color: #94a3b8;
  font-size: 0.88rem;
  letter-spacing: 0.08em;
}

.detail-preview-list {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 0.9rem;
  height: 100%;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  touch-action: pan-y;
  padding-right: 0.2rem;
  padding-bottom: 0.4rem;
  scrollbar-width: none;
}

.detail-preview-list::-webkit-scrollbar {
  display: none;
}

.detail-preview-list__item {
  display: grid;
  grid-template-columns: minmax(96px, 132px) minmax(0, 1fr);
  gap: 0.9rem;
  align-items: center;
  padding: 0.7rem;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.76);
  box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.85);
}

.detail-preview-list__thumb {
  width: 100%;
  border-radius: 14px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.92);
}

.detail-preview-list__img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
}

.detail-preview-list__meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.detail-preview-list__name {
  color: #0f172a;
  font-size: 0.92rem;
  font-weight: 700;
  line-height: 1.45;
  word-break: break-word;
}

.detail-preview-list__type {
  color: #64748b;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.detail-panel__aside {
  display: flex;
  flex-direction: column;
  gap: 1.15rem;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: clamp(1.35rem, 2.4vw, 2.1rem);
  border-left: 1px solid rgba(226, 232, 240, 0.9);
}

.detail-panel__summary {
  color: #475569;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.detail-field {
  display: flex;
  flex-direction: column;
  gap: 0.42rem;
}

.detail-field__label {
  color: #64748b;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.detail-field__value {
  min-height: 2.4rem;
  display: flex;
  align-items: center;
  color: #0f172a;
  font-size: 0.95rem;
  line-height: 1.6;
  word-break: break-word;
}

.detail-field__value--tags {
  min-height: 3.4rem;
  align-items: flex-start;
}

.detail-field__text {
  display: block;
  width: 100%;
}

.detail-field__placeholder {
  width: 100%;
  min-height: 3.4rem;
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.72), rgba(241, 245, 249, 0.88));
  box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.92);
}

.detail-field__various {
  color: #475569;
  font-style: italic;
}

.detail-field__tag-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.75rem;
  align-items: end;
}

.detail-field__tag-row--single {
  grid-template-columns: minmax(0, 1fr);
}

.detail-field__ghost {
  flex-shrink: 0;
  border: 1px solid rgba(148, 163, 184, 0.34);
  border-radius: 14px;
  padding: 0.55rem 0.95rem;
  background: transparent;
  color: #334155;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 140ms ease, border-color 140ms ease, color 140ms ease;
}

.detail-field__ghost:hover {
  background: #f8fafc;
  border-color: rgba(100, 116, 139, 0.4);
  color: #0f172a;
}

.detail-panel__actions {
  position: sticky;
  bottom: 0;
  margin-top: auto;
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding-top: 0.8rem;
  padding-bottom: 0.2rem;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0), rgba(255, 255, 255, 0.98) 38%);
}

.detail-panel__action {
  min-width: 112px;
  border: 1px solid rgba(148, 163, 184, 0.32);
  border-radius: 16px;
  padding: 0.72rem 1rem;
  background: #ffffff;
  color: #0f172a;
  font-size: 0.88rem;
  font-weight: 700;
  cursor: pointer;
  transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease, opacity 140ms ease;
}

.detail-panel__action:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(100, 116, 139, 0.36);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
}

.detail-panel__action:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  box-shadow: none;
}

.detail-panel__action--danger {
  border-color: rgba(234, 88, 12, 0.22);
  background: rgba(255, 237, 213, 0.86);
  color: #b45309;
}

.detail-panel__action--danger:hover {
  border-color: rgba(234, 88, 12, 0.3);
}

@keyframes detail-wave {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@media (max-width: 960px) {
  .detail-panel {
    width: calc(100% - 12px);
  }

  .detail-panel__content {
    grid-template-columns: 1fr;
    height: auto;
    overflow: visible;
  }

  .detail-panel__aside {
    border-left: 0;
    border-top: 1px solid rgba(226, 232, 240, 0.9);
    overflow-y: visible;
  }

  .detail-preview-stage,
  .detail-preview-stage__skeleton,
  .detail-preview-list {
    min-height: 260px;
  }
}

@media (max-width: 640px) {
  .detail-layer {
    padding: 0.6rem;
  }

  .detail-panel {
    border-radius: 22px;
  }

  .detail-preview-list__item {
    grid-template-columns: 92px minmax(0, 1fr);
  }

  .detail-field__tag-row,
  .detail-panel__actions {
    grid-template-columns: 1fr;
    display: grid;
  }

  .detail-panel__action,
  .detail-field__ghost {
    width: 100%;
  }
}
</style>