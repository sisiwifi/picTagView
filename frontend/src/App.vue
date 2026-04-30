<template>
  <div class="h-screen overflow-x-clip overflow-y-hidden bg-slate-50 text-slate-900">
    <div class="flex h-screen">
      <AppSidebar />
      <main class="flex-1 min-w-0 overflow-y-auto">
        <div class="min-h-full p-10">
          <router-view v-slot="{ Component, route }">
            <KeepAlive>
              <component
                v-if="route.meta?.keepAlive"
                :is="Component"
                :key="route.meta?.reuseKey || route.name"
              />
            </KeepAlive>
            <Transition name="page" mode="out-in">
              <component v-if="!route.meta?.keepAlive" :is="Component" :key="route.meta?.reuseKey || route.name" />
            </Transition>
          </router-view>
        </div>
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