<template>
  <div v-if="visible" class="collection-menu-layer" @click.self="$emit('close')">
    <section class="collection-menu" role="dialog" aria-modal="true" aria-label="收藏菜单">
      <header class="collection-menu__header">
        <div>
          <h3 class="collection-menu__title">收藏菜单</h3>
          <p class="collection-menu__subtitle">
            {{ isMulti ? `将处理已选 ${selectionCount} 张图片` : '选择已有收藏，或输入名称创建新收藏。' }}
          </p>
        </div>
        <button class="collection-menu__close" type="button" :disabled="busy" @click="$emit('close')">关闭</button>
      </header>

      <div class="collection-menu__body">
        <aside class="collection-menu__sidebar">
          <p class="collection-menu__label">所选图片</p>
          <div class="collection-menu__preview-list">
            <article
              v-for="item in normalizedSelectionItems"
              :key="item.key"
              class="collection-menu__preview-item"
            >
              <div
                class="collection-menu__preview-thumb"
                :style="item.aspectRatio ? { aspectRatio: item.aspectRatio } : null"
              >
                <img
                  v-if="item.previewUrl"
                  class="collection-menu__preview-img"
                  :src="item.previewUrl"
                  :alt="item.name"
                  draggable="false"
                >
                <div v-else class="collection-menu__preview-skeleton">...</div>
              </div>
              <span class="collection-menu__preview-name">{{ item.name }}</span>
            </article>
          </div>
        </aside>

        <div class="collection-menu__main">
          <section class="collection-menu__block">
            <p class="collection-menu__label">收藏夹</p>
            <input
              :value="query"
              class="collection-menu__input"
              type="text"
              maxlength="120"
              placeholder="输入收藏名称，搜索或新建"
              :disabled="busy"
              @input="$emit('query-change', $event.target.value)"
            >

            <div class="collection-menu__suggestion-container">
              <ul v-if="displayItems.length" class="collection-menu__suggestions" role="listbox" aria-label="收藏候选">
                <li v-for="item in displayItems" :key="candidateKey(item)" class="collection-menu__suggestion">
                  <button
                    class="collection-menu__suggestion-btn"
                    :class="{ 'is-active': isSelectedCollection(item), 'is-create': item.isNew }"
                    type="button"
                    :disabled="busy"
                    @click="$emit('select-collection', item)"
                  >
                    <span class="collection-menu__suggestion-title">{{ item.title }}</span>
                    <span class="collection-menu__suggestion-meta">
                      <template v-if="item.isNew">新建收藏并加入当前图片</template>
                      <template v-else>已包含 {{ item.selected_match_count || 0 }} / {{ selectionCount }} 张，现有 {{ item.photo_count || 0 }} 张</template>
                    </span>
                  </button>
                </li>
              </ul>
              <p v-else-if="!searchBusy" class="collection-menu__empty">{{ trimmedQuery ? '暂无匹配收藏' : '暂无收藏' }}</p>
              <p v-if="searchBusy" class="collection-menu__hint">搜索中...</p>
            </div>
          </section>

          <section v-if="selectedCollection" class="collection-menu__block">
            <p class="collection-menu__label">目标收藏</p>
            <div class="collection-menu__selection-card" :class="{ 'collection-menu__selection-card--create': selectedCollection.isNew }">
              <span class="collection-menu__selection-title">{{ selectedCollection.title }}</span>
              <span class="collection-menu__selection-meta">
                {{ selectedCollection.isNew ? '将创建新收藏' : `当前已收录 ${selectedCollection.photo_count || 0} 张图片` }}
              </span>
            </div>

            <p v-if="!isMulti" class="collection-menu__single-hint">
              {{ singleActionHint }}
            </p>

            <div v-else class="collection-menu__action-list">
              <article v-for="item in normalizedItemActions" :key="item.key" class="collection-menu__action-item">
                <div class="collection-menu__action-main">
                  <div
                    class="collection-menu__action-thumb"
                    :style="item.aspectRatio ? { aspectRatio: item.aspectRatio } : null"
                  >
                    <img
                      v-if="item.previewUrl"
                      class="collection-menu__action-img"
                      :src="item.previewUrl"
                      :alt="item.name"
                      draggable="false"
                    >
                    <div v-else class="collection-menu__action-skeleton">...</div>
                  </div>
                  <div class="collection-menu__action-texts">
                    <span class="collection-menu__action-name">{{ item.name }}</span>
                    <span class="collection-menu__action-state">{{ item.existsInCollection ? '已在该收藏中' : '将加入该收藏' }}</span>
                  </div>
                </div>

                <div class="collection-menu__action-control">
                  <select
                    v-if="item.canChangeAction"
                    class="collection-menu__select"
                    :value="item.action"
                    :disabled="busy"
                    @change="$emit('item-action-change', { imageId: item.imageId, action: $event.target.value })"
                  >
                    <option value="keep">保留</option>
                    <option value="remove">移除</option>
                  </select>
                  <span v-else class="collection-menu__action-fixed">添加</span>
                </div>
              </article>
            </div>
          </section>

          <p v-if="errorMessage" class="collection-menu__error">{{ errorMessage }}</p>
        </div>
      </div>

      <footer class="collection-menu__footer">
        <button class="collection-menu__btn" type="button" :disabled="busy" @click="$emit('cancel')">取消</button>
        <button class="collection-menu__btn collection-menu__btn--confirm" type="button" :disabled="busy || confirmDisabled" @click="$emit('confirm')">{{ confirmLabel }}</button>
      </footer>
    </section>
  </div>
</template>

<script>
export default {
  name: 'CollectionMenuDialog',
  props: {
    visible: { type: Boolean, default: false },
    busy: { type: Boolean, default: false },
    searchBusy: { type: Boolean, default: false },
    errorMessage: { type: String, default: '' },
    query: { type: String, default: '' },
    selectionItems: { type: Array, default: () => [] },
    suggestions: { type: Array, default: () => [] },
    selectedCollection: { type: Object, default: null },
    itemActions: { type: Array, default: () => [] },
    confirmDisabled: { type: Boolean, default: true },
    confirmLabel: { type: String, default: '确定' },
  },
  emits: ['close', 'cancel', 'confirm', 'query-change', 'select-collection', 'item-action-change'],
  computed: {
    trimmedQuery() {
      return String(this.query || '').trim()
    },
    normalizedSelectionItems() {
      return Array.isArray(this.selectionItems) ? this.selectionItems : []
    },
    normalizedItemActions() {
      return Array.isArray(this.itemActions) ? this.itemActions : []
    },
    normalizedSuggestions() {
      return Array.isArray(this.suggestions) ? this.suggestions : []
    },
    selectionCount() {
      return this.normalizedSelectionItems.length
    },
    isMulti() {
      return this.selectionCount > 1
    },
    hasExactTitleMatch() {
      const target = this.trimmedQuery.toLocaleLowerCase()
      if (!target) return false
      return this.normalizedSuggestions.some(item => String(item?.title || '').trim().toLocaleLowerCase() === target)
    },
    createOption() {
      if (!this.trimmedQuery || this.hasExactTitleMatch) return null
      return {
        id: null,
        isNew: true,
        title: this.trimmedQuery,
        photo_count: 0,
        matched_image_ids: [],
        selected_match_count: 0,
      }
    },
    displayItems() {
      return this.createOption ? [this.createOption, ...this.normalizedSuggestions] : this.normalizedSuggestions
    },
    singleActionHint() {
      if (!this.selectedCollection) return ''
      if (this.selectedCollection.isNew) {
        return '确定后会创建新收藏，并将当前图片加入其中。'
      }
      const matchedCount = Number(this.selectedCollection.selected_match_count || 0)
      return matchedCount > 0
        ? '当前图片已在该收藏中，确定后将从该收藏移除。'
        : '当前图片尚未加入该收藏，确定后将加入其中。'
    },
  },
  methods: {
    candidateKey(item) {
      return item?.id != null ? `collection-${item.id}` : `create-${String(item?.title || '').trim()}`
    },
    isSelectedCollection(item) {
      if (!item || !this.selectedCollection) return false
      if (item.id != null && this.selectedCollection.id != null) {
        return Number(item.id) === Number(this.selectedCollection.id)
      }
      return Boolean(item.isNew) && Boolean(this.selectedCollection.isNew) && String(item.title || '').trim() === String(this.selectedCollection.title || '').trim()
    },
  },
}
</script>

<style scoped lang="css">
.collection-menu-layer {
  position: fixed;
  inset: 0;
  z-index: 90;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: rgba(15, 23, 42, 0.28);
  backdrop-filter: blur(6px);
}

.collection-menu {
  width: min(940px, 94vw);
  max-height: min(88vh, 860px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 22px;
  border: 1px solid rgba(203, 213, 225, 0.92);
  background: #ffffff;
  box-shadow: 0 26px 56px rgba(15, 23, 42, 0.24);
}

.collection-menu__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.8rem;
  padding: 1rem 1.05rem;
  border-bottom: 1px solid rgba(226, 232, 240, 0.9);
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.86), rgba(255, 255, 255, 0.98));
}

.collection-menu__title {
  margin: 0;
  color: #0f172a;
  font-size: 1rem;
  font-weight: 800;
}

.collection-menu__subtitle {
  margin: 0.38rem 0 0;
  color: #64748b;
  font-size: 0.82rem;
  line-height: 1.6;
}

.collection-menu__close {
  border: 0;
  background: transparent;
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
}

.collection-menu__body {
  display: grid;
  grid-template-columns: minmax(220px, 0.76fr) minmax(0, 1.24fr);
  gap: 1rem;
  min-height: 0;
  overflow: hidden;
  padding: 1rem;
}

.collection-menu__sidebar,
.collection-menu__main {
  min-height: 0;
}

.collection-menu__sidebar {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  padding: 0.8rem;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.76);
}

.collection-menu__preview-list {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  overflow-y: auto;
}

.collection-menu__preview-item {
  display: grid;
  grid-template-columns: 64px minmax(0, 1fr);
  gap: 0.6rem;
  align-items: center;
}

.collection-menu__preview-thumb,
.collection-menu__action-thumb {
  width: 100%;
  border-radius: 14px;
  overflow: hidden;
  background: rgba(226, 232, 240, 0.84);
}

.collection-menu__preview-img,
.collection-menu__action-img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.collection-menu__preview-skeleton,
.collection-menu__action-skeleton {
  min-height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #94a3b8;
  background: linear-gradient(90deg, #e2e8f0 25%, #f8fafc 50%, #e2e8f0 75%);
  background-size: 200% 100%;
  animation: collection-menu-wave 1.4s ease-in-out infinite;
}

.collection-menu__preview-name,
.collection-menu__action-name,
.collection-menu__selection-title,
.collection-menu__suggestion-title {
  color: #0f172a;
  font-size: 0.82rem;
  font-weight: 700;
  line-height: 1.5;
  word-break: break-word;
}

.collection-menu__main {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  overflow-y: auto;
}

.collection-menu__block {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 16px;
  padding: 0.8rem;
  background: rgba(248, 250, 252, 0.7);
}

.collection-menu__label {
  margin: 0;
  color: #475569;
  font-size: 0.74rem;
  font-weight: 800;
  letter-spacing: 0.06em;
}

.collection-menu__input,
.collection-menu__select {
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.42);
  border-radius: 12px;
  padding: 0.58rem 0.72rem;
  background: #ffffff;
  color: #0f172a;
  font-size: 0.84rem;
}

.collection-menu__input:focus,
.collection-menu__select:focus {
  outline: none;
  border-color: rgba(37, 99, 235, 0.44);
  box-shadow: 0 0 0 2px rgba(191, 219, 254, 0.64);
}

.collection-menu__suggestion-container,
.collection-menu__action-list {
  min-height: 0;
  max-height: 260px;
  overflow-y: auto;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 12px;
  background: #ffffff;
  padding: 0.4rem;
}

.collection-menu__suggestions {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.42rem;
}

.collection-menu__suggestion-btn {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  align-items: flex-start;
  padding: 0.68rem 0.74rem;
  border: 1px solid rgba(226, 232, 240, 0.96);
  border-radius: 12px;
  background: #ffffff;
  text-align: left;
  cursor: pointer;
  transition: border-color 140ms ease, background 140ms ease, box-shadow 140ms ease;
}

.collection-menu__suggestion-btn:hover:not(:disabled),
.collection-menu__suggestion-btn.is-active {
  border-color: rgba(59, 130, 246, 0.36);
  background: rgba(239, 246, 255, 0.88);
  box-shadow: 0 10px 22px rgba(59, 130, 246, 0.1);
}

.collection-menu__suggestion-btn.is-create {
  border-style: dashed;
}

.collection-menu__suggestion-meta,
.collection-menu__selection-meta,
.collection-menu__action-state,
.collection-menu__single-hint,
.collection-menu__hint,
.collection-menu__empty {
  color: #64748b;
  font-size: 0.76rem;
  line-height: 1.55;
}

.collection-menu__selection-card {
  display: flex;
  flex-direction: column;
  gap: 0.28rem;
  padding: 0.72rem 0.82rem;
  border: 1px solid rgba(191, 219, 254, 0.9);
  border-radius: 14px;
  background: rgba(239, 246, 255, 0.84);
}

.collection-menu__selection-card--create {
  border-style: dashed;
  background: rgba(240, 253, 244, 0.82);
  border-color: rgba(134, 239, 172, 0.92);
}

.collection-menu__action-list {
  display: flex;
  flex-direction: column;
  gap: 0.46rem;
}

.collection-menu__action-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.65rem;
  align-items: center;
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 12px;
  padding: 0.48rem 0.56rem;
}

.collection-menu__action-main {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr);
  gap: 0.55rem;
  align-items: center;
  min-width: 0;
}

.collection-menu__action-texts {
  display: flex;
  flex-direction: column;
  gap: 0.16rem;
  min-width: 0;
}

.collection-menu__action-fixed {
  color: #0f766e;
  font-size: 0.78rem;
  font-weight: 700;
}

.collection-menu__error {
  margin: 0;
  color: #b91c1c;
  font-size: 0.78rem;
}

.collection-menu__footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.65rem;
  padding: 0 1rem 1rem;
}

.collection-menu__btn {
  border: 1px solid rgba(148, 163, 184, 0.4);
  border-radius: 12px;
  background: #ffffff;
  color: #334155;
  padding: 0.58rem 0.92rem;
  font-size: 0.82rem;
  font-weight: 800;
  cursor: pointer;
}

.collection-menu__btn:disabled,
.collection-menu__close:disabled,
.collection-menu__suggestion-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.collection-menu__btn--confirm {
  border-color: rgba(37, 99, 235, 0.36);
  background: linear-gradient(135deg, #2563eb, #0f766e);
  color: #ffffff;
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.2);
}

@keyframes collection-menu-wave {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@media (max-width: 840px) {
  .collection-menu__body {
    grid-template-columns: 1fr;
  }

  .collection-menu__preview-list {
    max-height: 180px;
  }
}

@media (max-width: 640px) {
  .collection-menu-layer {
    padding: 0.7rem;
  }

  .collection-menu {
    width: 100%;
    max-height: calc(100vh - 1.4rem);
  }

  .collection-menu__action-item {
    grid-template-columns: 1fr;
  }

  .collection-menu__footer {
    flex-direction: column-reverse;
  }

  .collection-menu__btn {
    width: 100%;
  }
}
</style>