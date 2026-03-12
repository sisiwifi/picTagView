<template>
  <div class="min-h-screen bg-slate-50 text-slate-900">
    <div class="flex min-h-screen">
      <AppSidebar />
      <main class="flex-1 p-10">
        <router-view />
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
  }
}
</script>

<style>
#app {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
</style>