<template>
  <div class="min-h-screen bg-slate-50 text-slate-900 [overflow-x:clip]">
    <div class="flex min-h-screen">
      <AppSidebar />
      <main class="flex-1 min-w-0 p-10">
        <router-view v-slot="{ Component, route }">
          <Transition name="page" mode="out-in">
            <KeepAlive v-if="route.meta?.keepAlive">
              <component :is="Component" :key="route.meta?.reuseKey || route.name" />
            </KeepAlive>
            <component v-else :is="Component" :key="route.meta?.reuseKey || route.name" />
          </Transition>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script>
import { KeepAlive } from 'vue'
import AppSidebar from './components/Sidebar.vue'

export default {
  name: 'App',
  components: {
    KeepAlive,
    AppSidebar
  },
  created() {
    const saved = localStorage.getItem('theme')
    if (saved === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  },
}
</script>

<style>
#app {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* 路由页面切换淡入淡出 */
.page-enter-active { transition: opacity 160ms ease; }
.page-enter-from   { opacity: 0; }
.page-leave-active { transition: opacity 110ms ease; }
.page-leave-to     { opacity: 0; }
</style>