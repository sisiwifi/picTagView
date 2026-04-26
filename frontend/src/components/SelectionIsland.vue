<template>
  <div
    class="selection-island"
    :class="{ 'selection-island--collapsed': collapsed }"
    :style="floatingStyle"
  >
    <button
      class="selection-island__toggle"
      type="button"
      :aria-expanded="collapsed ? 'false' : 'true'"
      :aria-label="collapsed ? expandLabel : collapseLabel"
      @click="toggleCollapsed"
    >
      <svg class="selection-island__toggle-icon" width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
        <path d="M8.75 2.25L4 7L8.75 11.75" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>

    <div class="selection-island__body">
      <slot />
    </div>
  </div>
</template>

<script>
export default {
  name: 'SelectionIsland',
  emits: ['collapsed-change'],
  props: {
    floatingStyle: {
      type: [Object, Array, String],
      default: null,
    },
    collapseLabel: {
      type: String,
      default: 'Collapse actions',
    },
    expandLabel: {
      type: String,
      default: 'Expand actions',
    },
  },
  data() {
    return {
      collapsed: false,
    }
  },
  methods: {
    toggleCollapsed() {
      const nextValue = !this.collapsed
      this.collapsed = nextValue
      this.$emit('collapsed-change', nextValue)
    },
  },
}
</script>

<style scoped lang="css">
.selection-island {
  --selection-island-collapse-shift: 0.7rem;
  position: fixed;
  right: 1.5rem;
  bottom: 1.5rem;
  z-index: 50;
  display: inline-flex;
  align-items: center;
  width: fit-content;
  gap: 0.45rem;
  max-width: calc(100vw - 3rem);
  padding: 0.5rem;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.14);
  backdrop-filter: blur(14px);
  overflow: hidden;
  transform-origin: right center;
  transition: transform 220ms ease, padding 220ms ease, gap 220ms ease, box-shadow 220ms ease, border-radius 220ms ease;
}

.selection-island--collapsed {
  gap: 0;
  padding: 0.28rem 0.22rem 0.28rem 0.28rem;
  border-radius: 999px;
  transform: translateX(var(--selection-island-collapse-shift));
}

.selection-island__toggle {
  width: 1.9rem;
  height: 1.9rem;
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: 999px;
  background: rgba(226, 232, 240, 0.9);
  color: #0f172a;
  cursor: pointer;
  padding: 0;
  transition: background 140ms ease, color 140ms ease, transform 140ms ease;
}

.selection-island__toggle:hover {
  background: #cbd5e1;
}

.selection-island__toggle-icon {
  display: block;
  transition: transform 220ms ease;
}

.selection-island--collapsed .selection-island__toggle-icon {
  transform: rotate(180deg);
}

.selection-island__body {
  min-width: 0;
  display: inline-flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: 0.5rem;
  flex: 0 1 auto;
  overflow: hidden;
  white-space: nowrap;
  max-width: calc(100vw - 5.5rem);
  transition: max-width 220ms ease, opacity 180ms ease, transform 220ms ease, visibility 0s linear 0s;
}

.selection-island--collapsed .selection-island__body {
  max-width: 0;
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transform: translateX(0.35rem);
  transition: max-width 220ms ease, opacity 180ms ease, transform 220ms ease, visibility 0s linear 220ms;
}

:deep(.selection-island__count) {
  color: #0f172a;
  font-size: 0.82rem;
  font-weight: 700;
  white-space: nowrap;
}

:deep(.selection-island__menu-wrap) {
  position: relative;
  display: inline-flex;
}

:deep(.selection-island__submenu) {
  position: absolute;
  left: 0;
  bottom: calc(100% + 0.55rem);
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: 0.42rem;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 18px 34px rgba(15, 23, 42, 0.12);
  opacity: 0;
  pointer-events: none;
  transform: translateY(8px);
  transition: opacity 140ms ease, transform 140ms ease;
}

:deep(.selection-island__menu-wrap.is-open .selection-island__submenu) {
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0);
}

:deep(.selection-island__submenu-btn) {
  border: 0;
  border-radius: 10px;
  padding: 0.48rem 0.72rem;
  background: transparent;
  color: #334155;
  font-size: 0.76rem;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
  transition: background 140ms ease, color 140ms ease;
}

:deep(.selection-island__submenu-btn:hover) {
  background: #e2e8f0;
  color: #0f172a;
}

:deep(.selection-island__btn) {
  border: 0;
  border-radius: 12px;
  padding: 0.45rem 0.75rem;
  background: transparent;
  color: #334155;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 140ms ease, color 140ms ease, opacity 140ms ease;
}

:deep(.selection-island__btn:hover) {
  background: #e2e8f0;
  color: #0f172a;
}

:deep(.selection-island__btn--danger) {
  color: #b45309;
}

:deep(.selection-island__btn:disabled) {
  opacity: 0.42;
  cursor: not-allowed;
}

:deep(.selection-island__btn:disabled:hover) {
  background: transparent;
  color: #334155;
}

@media (max-width: 720px) {
  .selection-island {
    --selection-island-collapse-shift: 0.55rem;
    right: 0.9rem;
    bottom: 0.9rem;
    max-width: calc(100vw - 1.8rem);
    gap: 0.28rem;
    padding: 0.38rem 0.42rem;
  }

  .selection-island--collapsed {
    padding: 0.22rem 0.16rem 0.22rem 0.22rem;
  }

  .selection-island__toggle {
    width: 1.7rem;
    height: 1.7rem;
  }

  .selection-island__body {
    max-width: calc(100vw - 3.7rem);
    gap: 0.24rem;
  }

  :deep(.selection-island__count) {
    flex: 0 0 auto;
    font-size: 0.76rem;
  }

  :deep(.selection-island__menu-wrap) {
    display: inline-flex;
    flex: 0 0 auto;
  }

  :deep(.selection-island__btn) {
    border-radius: 10px;
    padding: 0.32rem 0.52rem;
    font-size: 0.72rem;
  }

  :deep(.selection-island__submenu) {
    left: auto;
    right: 0;
  }
}
</style>