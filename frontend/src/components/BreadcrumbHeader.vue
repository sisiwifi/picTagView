<template>
  <header class="page-header">
    <button
      v-if="showBack"
      class="back-btn"
      type="button"
      @click="$emit('back')"
    >
      ← {{ backText }}
    </button>

    <div
      class="breadcrumb-wrap"
      ref="breadcrumbWrap"
      :class="{ 'bc-dragging': bcDragging }"
      @mousedown="onBcMousedown"
      @mouseleave="onBcMouseup"
      @mouseup="onBcMouseup"
      @mousemove="onBcMousemove"
    >
      <nav class="breadcrumb" aria-label="页面路径">
        <template v-for="(crumb, idx) in crumbs" :key="`${idx}-${crumb.label}`">
          <span v-if="idx > 0" class="bc-sep" aria-hidden="true">›</span>

          <router-link
            v-if="crumb.to && !crumb.current"
            :to="crumb.to"
            class="bc-item bc-link"
            :title="crumb.title || crumb.label"
          >
            {{ crumb.label }}
          </router-link>

          <span
            v-else
            class="bc-item"
            :class="{ 'bc-current': crumb.current || idx === crumbs.length - 1 }"
            :title="crumb.title || crumb.label"
          >
            {{ crumb.label }}
          </span>
        </template>
      </nav>
    </div>

    <div v-if="showRight" class="header-right">
      <span v-if="itemCount !== null" class="header-count">{{ itemCount }} {{ countSuffix }}</span>

      <div v-if="showSort" class="sort-controls" role="group" aria-label="排序设置">
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
  name: 'BreadcrumbHeader',
  props: {
    showBack: { type: Boolean, default: false },
    backText: { type: String, default: '返回' },
    crumbs: {
      type: Array,
      default: () => [],
    },
    itemCount: { type: Number, default: null },
    countSuffix: { type: String, default: '项' },
    showSort: { type: Boolean, default: false },
    sortBy: { type: String, default: 'date' },
    sortDir: { type: String, default: 'asc' },
    sortOptions: {
      type: Array,
      default: () => ([
        { value: 'date', label: 'Date' },
        { value: 'alpha', label: 'Alpha' },
      ]),
    },
  },
  emits: ['back', 'update:sortBy', 'toggle-sort-dir'],
  data() {
    return {
      bcDragging: false,
      bcStartX: 0,
      bcScrollLeft: 0,
    }
  },
  computed: {
    showRight() {
      return this.itemCount !== null || this.showSort || Boolean(this.$slots.default)
    },
  },
  methods: {
    onBcMousedown(e) {
      const el = this.$refs.breadcrumbWrap
      if (!el) return
      this.bcDragging = true
      this.bcStartX = e.pageX
      this.bcScrollLeft = el.scrollLeft
    },
    onBcMouseup() {
      this.bcDragging = false
    },
    onBcMousemove(e) {
      if (!this.bcDragging) return
      e.preventDefault()
      const el = this.$refs.breadcrumbWrap
      if (!el) return
      el.scrollLeft = this.bcScrollLeft - (e.pageX - this.bcStartX)
    },
  },
}
</script>

<style scoped lang="css">
.page-header {
  @apply sticky top-0 z-40 flex items-center gap-3 bg-white bg-opacity-95 py-3 backdrop-blur-sm shadow-sm;
  min-width: 0;
}

.back-btn {
  @apply flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm text-slate-500 bg-transparent border-0 cursor-pointer transition-colors duration-150;
  flex-shrink: 0;
}
.back-btn:hover { @apply bg-slate-100 text-slate-800; }

.breadcrumb-wrap {
  flex: 1 1 0;
  min-width: 0;
  overflow-x: auto;
  cursor: grab;
  scrollbar-width: none;
  -ms-overflow-style: none;
  user-select: none;
}
.breadcrumb-wrap::-webkit-scrollbar { display: none; }
.breadcrumb-wrap.bc-dragging { cursor: grabbing; }

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
  text-decoration: none;
}
.bc-link {
  @apply rounded-md px-2 py-1 transition-colors duration-150;
}
.bc-link:hover {
  color: #0f172a;
  background: #f1f5f9;
}
.bc-current {
  color: #0f172a;
  font-weight: 600;
}
.bc-sep {
  color: #94a3b8;
  font-size: 0.75rem;
  flex-shrink: 0;
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
</style>
