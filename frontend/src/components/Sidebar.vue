<template>
  <aside class="sidebar" :class="isSidebarCollapsed ? 'sidebar--collapsed' : 'sidebar--expanded'">
    <div class="sidebar__header">
      <img alt="Vue 标志" src="../assets/logo.png" class="sidebar__logo">
      <div
        class="sidebar__title"
        :class="isTextVisible ? 'sidebar__title--visible' : 'sidebar__title--hidden'"
      >
        <h1 class="text-lg font-semibold">图片标签管理</h1>
        <p class="text-sm text-slate-500">导航面板</p>
      </div>
    </div>
    <nav class="sidebar__nav">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="sidebar__nav-item"
        :class="{ 'sidebar__nav-item--active': isActive(item.path) }"
      >
        <span>{{ item.icon }}</span>
        <span
          class="sidebar__nav-text"
          :class="isTextVisible ? 'sidebar__nav-text--visible' : 'sidebar__nav-text--hidden'"
        >{{ item.label }}</span>
      </router-link>
    </nav>
    <div class="sidebar__footer">
      <button
        class="sidebar__toggle"
        @click="toggleSidebar"
        :aria-label="isSidebarCollapsed ? '展开侧边栏' : '收起侧边栏'"
      >
        <span v-if="isSidebarCollapsed">&gt;</span>
        <span v-else>&lt;</span>
      </button>
    </div>
  </aside>
</template>

<script>
export default {
  name: 'AppSidebar',
  data() {
    return {
      isSidebarCollapsed: false,
      isTextVisible: true,
      navItems: [
        { path: '/', label: '主页', icon: '🏠' },
        { path: '/tags', label: '标签总览', icon: '🏷️' },
        { path: '/gallery', label: '图库管理', icon: '🖼️' },
        { path: '/calendar', label: '日期视图', icon: '📅' },
        { path: '/settings', label: '设置', icon: '⚙️' }
      ]
    }
  },
  methods: {
    isActive(path) {
      return this.$route.path === path
    },
    toggleSidebar() {
      if (this.isSidebarCollapsed) {
        this.isSidebarCollapsed = false
        window.setTimeout(() => {
          this.isTextVisible = true
        }, 180)
        return
      }

      this.isTextVisible = false
      window.setTimeout(() => {
        this.isSidebarCollapsed = true
      }, 200)
    }
  }
}
</script>

<style scoped lang="css">
.sidebar {
  @apply sticky top-0 h-screen flex-shrink-0 z-50 overflow-y-auto flex flex-col border-r border-slate-200 bg-white transition-all duration-300;
}

.sidebar--collapsed {
  @apply w-20;
}

.sidebar--expanded {
  @apply w-64;
}

.sidebar__header {
  @apply flex items-center gap-3 p-6;
}

.sidebar__logo {
  @apply h-7 w-7;
}

.sidebar__title {
  @apply overflow-hidden whitespace-nowrap transition-all duration-200;
}

.sidebar__title--visible {
  @apply max-w-[200px] opacity-100;
}

.sidebar__title--hidden {
  @apply max-w-0 opacity-0;
}

.sidebar__nav {
  @apply mt-2 space-y-2 px-4 text-sm;
}

.sidebar__nav-item {
  @apply flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-slate-600 hover:bg-slate-100;
}

.sidebar__nav-item--active {
  @apply bg-slate-100 font-medium text-slate-900;
}

.sidebar__nav-text {
  @apply inline-block overflow-hidden whitespace-nowrap transition-all duration-200;
}

.sidebar__nav-text--visible {
  @apply max-w-[140px] opacity-100;
}

.sidebar__nav-text--hidden {
  @apply max-w-0 opacity-0;
}

.sidebar__footer {
  @apply mt-auto p-4;
}

.sidebar__toggle {
  @apply flex h-9 w-full items-center justify-center rounded-full border border-slate-200 text-sm text-slate-500 hover:bg-slate-100;
}
</style>