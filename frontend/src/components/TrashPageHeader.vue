<template>
  <header class="page-header">
    <button class="back-btn" type="button" @click="$emit('back')">
      ← 返回
    </button>

    <div class="breadcrumb-wrap">
      <nav class="breadcrumb" aria-label="页面路径">
        <span class="bc-item bc-current">回收站</span>
      </nav>
    </div>

    <div class="header-right">
      <button
        class="clear-btn"
        type="button"
        :disabled="clearDisabled"
        @click="$emit('clear-trash')"
      >
        清空回收站
      </button>

      <span v-if="itemCount !== null" class="header-count">{{ itemCount }} {{ countSuffix }}</span>

      <div class="sort-controls" role="group" aria-label="排序设置">
        <select
          class="sort-select"
          :value="sortBy"
          aria-label="排序字段"
          @change="$emit('update:sortBy', $event.target.value)"
        >
          <option v-for="opt in sortOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>

        <button
          class="sort-order-btn"
          type="button"
          :title="sortDir === 'asc' ? '当前升序，点击切换降序' : '当前降序，点击切换升序'"
          aria-label="切换升降序"
          @click="$emit('toggle-sort-dir')"
        >
          {{ sortDir === 'asc' ? '↑' : '↓' }}
        </button>
      </div>

      <slot></slot>
    </div>
  </header>
</template>

<script>
export default {
  name: 'TrashPageHeader',
  props: {
    itemCount: { type: Number, default: null },
    countSuffix: { type: String, default: '项' },
    sortBy: { type: String, default: 'date' },
    sortDir: { type: String, default: 'desc' },
    clearDisabled: { type: Boolean, default: false },
    sortOptions: {
      type: Array,
      default: () => ([
        { value: 'date', label: 'Date' },
        { value: 'alpha', label: 'Alpha' },
      ]),
    },
  },
  emits: ['back', 'clear-trash', 'update:sortBy', 'toggle-sort-dir'],
}
</script>

<style scoped lang="css">
.page-header {
  @apply sticky top-0 z-40 flex items-center gap-3 bg-white bg-opacity-95 py-3 backdrop-blur-sm shadow-sm;
  min-width: 0;
  flex-wrap: wrap;
}

.back-btn {
  @apply flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm text-slate-500 bg-transparent border-0 cursor-pointer transition-colors duration-150;
  flex-shrink: 0;
}

.back-btn:hover {
  @apply bg-slate-100 text-slate-800;
}

.breadcrumb-wrap {
  flex: 1 1 0;
  min-width: 0;
}

.breadcrumb {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  white-space: nowrap;
  padding: 0.125rem 0;
}

.bc-item {
  font-size: 0.875rem;
  color: #64748b;
  max-width: 14rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.bc-current {
  color: #0f172a;
  font-weight: 600;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-shrink: 0;
}

.header-count {
  @apply text-sm text-slate-400;
}

.sort-controls {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.sort-select {
  height: 30px;
  min-width: 92px;
  padding: 0 0.6rem;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #334155;
  font-size: 0.78rem;
  font-weight: 600;
  outline: none;
}

.sort-select:focus {
  border-color: #94a3b8;
  box-shadow: 0 0 0 3px rgba(148, 163, 184, 0.22);
}

.sort-order-btn {
  width: 30px;
  height: 30px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #334155;
  font-size: 0.9rem;
  font-weight: 700;
  line-height: 1;
  cursor: pointer;
  transition: background 140ms ease, color 140ms ease, border-color 140ms ease;
}

.sort-order-btn:hover {
  background: #f8fafc;
  color: #0f172a;
  border-color: #94a3b8;
}

.clear-btn {
  height: 30px;
  border: 1px solid rgba(234, 88, 12, 0.22);
  border-radius: 8px;
  padding: 0 0.8rem;
  background: rgba(255, 237, 213, 0.86);
  color: #b45309;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 140ms ease, border-color 140ms ease, color 140ms ease, opacity 140ms ease;
}

.clear-btn:hover:not(:disabled) {
  border-color: rgba(234, 88, 12, 0.3);
  background: rgba(255, 237, 213, 1);
}

.clear-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

@media (max-width: 640px) {
  .header-right {
    width: 100%;
    flex-wrap: wrap;
  }
}
</style>