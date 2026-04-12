<template>
  <div class="min-h-screen bg-slate-50 text-slate-900 [overflow-x:clip]">
    <div class="flex min-h-screen">
      <AppSidebar />
      <main class="flex-1 min-w-0 p-10">
        <router-view v-slot="{ Component, route }">
          <keep-alive include="GalleryPage">
            <component :is="Component" :key="route.path" />
          </keep-alive>
        </router-view>
      </main>
    </div>
  </div>
</template>

<script>
import AppSidebar from './components/Sidebar.vue'

export default {
  name: 'App',
  components: {
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
</style>