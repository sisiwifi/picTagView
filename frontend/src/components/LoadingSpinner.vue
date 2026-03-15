<template>
  <div class="spinner-wrap">
    <span class="spinner"></span>
    <span><slot>加载中…</slot></span>
  </div>
</template>

<script>
export default { name: 'LoadingSpinner' }
</script>

<style scoped lang="css">
.spinner-wrap {
  @apply flex items-center gap-2 text-slate-400 text-sm;
}
.spinner {
  @apply flex-shrink-0 inline-block w-4 h-4 border-2 border-slate-300 rounded-full;
  border-top-color: #64748b;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
