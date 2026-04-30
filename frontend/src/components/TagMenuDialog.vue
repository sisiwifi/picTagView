<template>
  <div v-if="visible" class="tag-menu-layer" @click.self="$emit('close')">
    <section class="tag-menu" role="dialog" aria-modal="true" aria-label="标签菜单">
      <header class="tag-menu__header">
        <h3 class="tag-menu__title">Tag 标签菜单</h3>
        <button class="tag-menu__close" type="button" :disabled="busy" @click="$emit('close')">关闭</button>
      </header>

      <div class="tag-menu__body">
        <div class="tag-menu__block">
          <p class="tag-menu__label">现有标签</p>
          <ul class="tag-menu__existing-list">
            <li
              v-for="item in existingTags"
              :key="`existing-${item.id}`"
              class="tag-menu__existing-item"
              :style="chipStyle(item)"
            >
              <span class="tag-menu__existing-text">{{ item.display_name || item.name || `#${item.id}` }}</span>
              <button
                class="tag-menu__existing-remove"
                type="button"
                :disabled="busy"
                @click="$emit('remove-tag', item)"
              >x</button>
            </li>
          </ul>
          <p v-if="!existingTags.length" class="tag-menu__empty">当前选择没有公共标签</p>
        </div>

        <div class="tag-menu__block">
          <p class="tag-menu__label">添加已有标签</p>
          <div class="tag-menu__search-row">
            <input
              :value="query"
              class="tag-menu__input"
              type="text"
              maxlength="60"
              placeholder="输入 name 或 display name"
              :disabled="busy"
              @input="$emit('query-change', $event.target.value)"
            >
          </div>

          <p class="tag-menu__hint">{{ query.trim() ? '标签建议' : '最近使用（last_used_at 最新 5 条）' }}</p>

          <div class="tag-menu__suggestion-container">
            <ul v-if="displayItems.length" class="tag-menu__suggestions" role="listbox" aria-label="标签建议">
              <li v-for="item in displayItems" :key="`suggest-${item.id}`" class="tag-menu__suggestion">
                <div class="tag-menu__suggestion-main">
                  <span class="tag-menu__suggestion-name">{{ item.display_name || item.name || `#${item.id}` }}</span>
                  <span class="tag-menu__suggestion-meta">{{ item.description || '' }}</span>
                </div>
                <div class="tag-menu__suggestion-actions">
                  <button
                    class="tag-menu__icon-btn"
                    type="button"
                    title="添加此标签"
                    :disabled="busy"
                    @click="$emit('add-tag', item)"
                  >+</button>
                  <button
                    class="tag-menu__icon-btn"
                    type="button"
                    title="编辑标签元数据"
                    :disabled="busy"
                    @click="$emit('edit-tag', item)"
                  >✎</button>
                </div>
              </li>
            </ul>
            <p v-else-if="!searchBusy" class="tag-menu__empty">{{ query.trim() ? '暂无匹配标签' : '暂无最近使用标签' }}</p>
            <p v-if="searchBusy" class="tag-menu__hint">搜索中...</p>
          </div>

          <div class="tag-menu__entry-actions">
            <button class="tag-menu__btn" type="button" :disabled="busy" @click="$emit('add-new-tag')">添加新标签</button>
            <button class="tag-menu__btn" type="button" :disabled="busy" @click="$emit('auto-tag')">自动标签</button>
          </div>
        </div>

        <p v-if="errorMessage" class="tag-menu__error">{{ errorMessage }}</p>
      </div>

      <footer class="tag-menu__footer">
        <button class="tag-menu__btn" type="button" :disabled="busy" @click="$emit('cancel')">取消</button>
        <button class="tag-menu__btn tag-menu__btn--confirm" type="button" :disabled="busy || confirmDisabled" @click="$emit('confirm')">确定</button>
      </footer>
    </section>
  </div>
</template>

<script>
import { normalizeTagColors } from '../utils/tagColors'

export default {
  name: 'TagMenuDialog',
  props: {
    visible: { type: Boolean, default: false },
    busy: { type: Boolean, default: false },
    searchBusy: { type: Boolean, default: false },
    errorMessage: { type: String, default: '' },
    query: { type: String, default: '' },
    existingTags: { type: Array, default: () => [] },
    suggestions: { type: Array, default: () => [] },
    recentTags: { type: Array, default: () => [] },
    confirmDisabled: { type: Boolean, default: false },
  },
  emits: ['close', 'cancel', 'confirm', 'query-change', 'add-tag', 'remove-tag', 'edit-tag', 'add-new-tag', 'auto-tag'],
  computed: {
    displayItems() {
      const source = String(this.query || '').trim() ? this.suggestions : this.recentTags
      return Array.isArray(source) ? source : []
    },
  },
  methods: {
    chipStyle(tag) {
      const { color, borderColor, backgroundColor } = normalizeTagColors(tag)
      return {
        '--tag-chip-color': color,
        '--tag-chip-border-color': borderColor,
        '--tag-chip-bg': backgroundColor,
      }
    },
  },
}
</script>

<style scoped lang="css">
.tag-menu-layer {
  position: fixed;
  inset: 0;
  z-index: 85;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: rgba(15, 23, 42, 0.24);
  backdrop-filter: blur(4px);
}

.tag-menu {
  width: min(620px, 92vw);
  max-height: min(86vh, 760px);
  overflow: hidden;
  border-radius: 18px;
  border: 1px solid rgba(203, 213, 225, 0.92);
  background: #ffffff;
  box-shadow: 0 26px 56px rgba(15, 23, 42, 0.24);
  display: flex;
  flex-direction: column;
}

.tag-menu__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.8rem;
  padding: 0.95rem 1rem;
  border-bottom: 1px solid rgba(226, 232, 240, 0.9);
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.86), rgba(255, 255, 255, 0.98));
}

.tag-menu__title {
  color: #0f172a;
  font-size: 0.98rem;
  font-weight: 700;
  margin: 0;
}

.tag-menu__close {
  border: 0;
  background: transparent;
  color: #64748b;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
}

.tag-menu__close:hover:not(:disabled) {
  color: #0f172a;
}

.tag-menu__close:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.tag-menu__body {
  overflow-y: auto;
  padding: 0.95rem 1rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.95rem;
}

.tag-menu__block {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 12px;
  padding: 0.72rem;
  background: rgba(248, 250, 252, 0.7);
}

.tag-menu__label {
  margin: 0;
  color: #475569;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.tag-menu__existing-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0.38rem;
}

.tag-menu__existing-item {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  min-height: 1.36rem;
  padding: 0.14rem 0.5rem;
  border-radius: 999px;
  border: 1px solid var(--tag-chip-border-color, var(--tag-chip-color, #64748b));
  color: var(--tag-chip-color, #334155);
  background: var(--tag-chip-bg, rgba(100, 116, 139, 0.4));
  font-size: 0.72rem;
  font-weight: 700;
  line-height: 1.2;
}

.tag-menu__existing-text {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tag-menu__existing-remove {
  border: 0;
  background: transparent;
  color: inherit;
  font-size: 0.76rem;
  font-weight: 700;
  line-height: 1;
  cursor: pointer;
  padding: 0;
}

.tag-menu__existing-remove:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.tag-menu__search-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 0.45rem;
  align-items: center;
}

.tag-menu__entry-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.tag-menu__input {
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.42);
  border-radius: 10px;
  padding: 0.46rem 0.58rem;
  font-size: 0.82rem;
  color: #0f172a;
  background: #ffffff;
}

.tag-menu__input:focus {
  outline: none;
  border-color: rgba(59, 130, 246, 0.48);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.12);
}

.tag-menu__btn {
  border: 1px solid rgba(148, 163, 184, 0.4);
  border-radius: 10px;
  background: #ffffff;
  color: #334155;
  padding: 0.42rem 0.7rem;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 140ms ease, border-color 140ms ease, color 140ms ease, opacity 140ms ease;
}

.tag-menu__btn:hover:not(:disabled) {
  background: #f8fafc;
  border-color: rgba(100, 116, 139, 0.5);
  color: #0f172a;
}

.tag-menu__btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.tag-menu__btn--confirm {
  border-color: rgba(37, 99, 235, 0.38);
  background: rgba(219, 234, 254, 0.78);
  color: #1d4ed8;
}

.tag-menu__btn--confirm:hover:not(:disabled) {
  border-color: rgba(37, 99, 235, 0.56);
  background: rgba(191, 219, 254, 0.9);
  color: #1e3a8a;
}

.tag-menu__hint {
  margin: 0;
  color: #64748b;
  font-size: 0.76rem;
}

.tag-menu__suggestion-container {
  min-height: 240px;
  max-height: 240px;
  overflow-y: auto;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 10px;
  background: #ffffff;
  padding: 0.4rem;
}

.tag-menu__suggestions {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.38rem;
}

.tag-menu__suggestion {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 10px;
  padding: 0.46rem 0.56rem;
}

.tag-menu__suggestion-main {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.14rem;
}

.tag-menu__suggestion-name {
  color: #0f172a;
  font-size: 0.81rem;
  font-weight: 700;
  line-height: 1.2;
}

.tag-menu__suggestion-meta {
  color: #64748b;
  font-size: 0.72rem;
  line-height: 1.2;
}

.tag-menu__suggestion-actions {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  flex-shrink: 0;
}

.tag-menu__icon-btn {
  width: 1.62rem;
  height: 1.62rem;
  border: 1px solid rgba(148, 163, 184, 0.45);
  border-radius: 8px;
  background: #f8fafc;
  color: #334155;
  font-size: 0.84rem;
  font-weight: 700;
  line-height: 1;
  cursor: pointer;
  transition: background 140ms ease, border-color 140ms ease, color 140ms ease, opacity 140ms ease;
}

.tag-menu__icon-btn:hover:not(:disabled) {
  background: #e2e8f0;
  border-color: rgba(100, 116, 139, 0.55);
  color: #0f172a;
}

.tag-menu__icon-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.tag-menu__empty {
  margin: 0;
  color: #64748b;
  font-size: 0.76rem;
}

.tag-menu__error {
  margin: 0;
  color: #dc2626;
  font-size: 0.78rem;
  font-weight: 600;
}

.tag-menu__footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 0.72rem 1rem 0.95rem;
  border-top: 1px solid rgba(226, 232, 240, 0.9);
  background: linear-gradient(0deg, rgba(248, 250, 252, 0.9), rgba(255, 255, 255, 0.96));
}

@media (max-width: 640px) {
  .tag-menu {
    width: 96vw;
  }

  .tag-menu__search-row {
    grid-template-columns: 1fr;
  }

  .tag-menu__suggestion-container {
    min-height: 200px;
    max-height: 200px;
  }
}
</style>
