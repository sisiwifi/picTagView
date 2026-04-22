<template>
  <Teleport to="body">
    <Transition name="action-progress-fade">
      <div v-if="visible" class="action-progress-mask" aria-live="polite" aria-busy="true">
        <section class="action-progress-panel" role="status" aria-label="处理中">
          <span class="action-progress-spinner"></span>
          <div class="action-progress-copy">
            <h3 class="action-progress-title">{{ title }}</h3>
            <p v-if="message" class="action-progress-message">{{ message }}</p>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script>
export default {
  name: 'ActionProgressOverlay',
  props: {
    visible: { type: Boolean, default: false },
    title: { type: String, default: '处理中' },
    message: { type: String, default: '' },
  },
}
</script>

<style scoped lang="css">
.action-progress-mask {
  position: fixed;
  inset: 0;
  z-index: 110;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: rgba(15, 23, 42, 0.22);
  backdrop-filter: blur(6px);
}

.action-progress-panel {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  width: min(100%, 420px);
  border: 1px solid rgba(203, 213, 225, 0.92);
  border-radius: 22px;
  padding: 1rem 1.1rem;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 22px 60px rgba(15, 23, 42, 0.18);
}

.action-progress-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(148, 163, 184, 0.4);
  border-top-color: #0f172a;
  border-radius: 999px;
  animation: action-progress-spin 0.8s linear infinite;
  flex: 0 0 auto;
}

.action-progress-copy {
  min-width: 0;
}

.action-progress-title {
  margin: 0;
  color: #0f172a;
  font-size: 0.96rem;
  font-weight: 800;
}

.action-progress-message {
  margin: 0.25rem 0 0;
  color: #475569;
  font-size: 0.84rem;
  line-height: 1.55;
}

.action-progress-fade-enter-active,
.action-progress-fade-leave-active {
  transition: opacity 180ms ease;
}

.action-progress-fade-enter-from,
.action-progress-fade-leave-to {
  opacity: 0;
}

@keyframes action-progress-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>