<template>
  <Teleport to="body">
    <Transition name="confirm-dialog-fade">
      <div v-if="visible" class="confirm-dialog" @click.self="handleCancel">
        <div
          class="confirm-dialog__panel"
          role="alertdialog"
          aria-modal="true"
          :aria-labelledby="titleId"
          :aria-describedby="messageId"
        >
          <div class="confirm-dialog__badge" :class="`confirm-dialog__badge--${tone}`">
            <span v-if="tone === 'danger'">!</span>
            <span v-else>↺</span>
          </div>

          <div class="confirm-dialog__content">
            <h3 :id="titleId" class="confirm-dialog__title">{{ title }}</h3>
            <p :id="messageId" class="confirm-dialog__message">{{ message }}</p>
          </div>

          <div class="confirm-dialog__actions">
            <button
              v-if="showCancel"
              class="confirm-dialog__btn confirm-dialog__btn--cancel"
              type="button"
              :disabled="busy"
              @click="handleCancel"
            >
              {{ cancelLabel }}
            </button>
            <button
              class="confirm-dialog__btn"
              :class="`confirm-dialog__btn--${tone}`"
              type="button"
              :disabled="busy"
              @click="handleConfirm"
            >
              {{ busy ? busyLabel : confirmLabel }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script>
export default {
  name: 'ConfirmationDialog',
  props: {
    visible: { type: Boolean, default: false },
    title: { type: String, default: '请确认操作' },
    message: { type: String, default: '' },
    confirmLabel: { type: String, default: '确认' },
    cancelLabel: { type: String, default: '取消' },
    tone: {
      type: String,
      default: 'danger',
      validator: value => ['danger', 'accent'].includes(value),
    },
    showCancel: { type: Boolean, default: true },
    busy: { type: Boolean, default: false },
    busyLabel: { type: String, default: '处理中…' },
  },
  emits: ['confirm', 'cancel'],
  data() {
    return {
      dialogIdBase: `confirm-dialog-${Math.random().toString(36).slice(2, 10)}`,
    }
  },
  computed: {
    titleId() {
      return `${this.dialogIdBase}-title`
    },
    messageId() {
      return `${this.dialogIdBase}-message`
    },
  },
  methods: {
    handleCancel() {
      if (this.busy) return
      this.$emit('cancel')
    },
    handleConfirm() {
      if (this.busy) return
      this.$emit('confirm')
    },
  },
}
</script>

<style scoped lang="css">
.confirm-dialog {
  position: fixed;
  inset: 0;
  z-index: 120;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.25rem;
  background: rgba(15, 23, 42, 0.28);
  backdrop-filter: blur(6px);
}

.confirm-dialog__panel {
  width: min(100%, 430px);
  border: 1px solid rgba(203, 213, 225, 0.9);
  border-radius: 24px;
  padding: 1.15rem 1.15rem 1rem;
  background:
    radial-gradient(circle at top right, rgba(255, 255, 255, 0.98), transparent 44%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
  box-shadow: 0 26px 80px rgba(15, 23, 42, 0.22);
}

.confirm-dialog__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 14px;
  font-size: 1rem;
  font-weight: 800;
}

.confirm-dialog__badge--danger {
  background: rgba(254, 226, 226, 0.92);
  color: #b91c1c;
}

.confirm-dialog__badge--accent {
  background: rgba(219, 234, 254, 0.92);
  color: #1d4ed8;
}

.confirm-dialog__content {
  margin-top: 0.85rem;
}

.confirm-dialog__title {
  margin: 0;
  color: #0f172a;
  font-size: 1.02rem;
  font-weight: 800;
  letter-spacing: 0.01em;
}

.confirm-dialog__message {
  margin: 0.52rem 0 0;
  color: #475569;
  font-size: 0.9rem;
  line-height: 1.65;
  white-space: pre-line;
}

.confirm-dialog__actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.65rem;
  margin-top: 1rem;
}

.confirm-dialog__btn {
  border: 0;
  border-radius: 14px;
  padding: 0.68rem 1rem;
  font-size: 0.84rem;
  font-weight: 800;
  cursor: pointer;
  transition: transform 160ms ease, box-shadow 160ms ease, background 160ms ease, color 160ms ease;
}

.confirm-dialog__btn:hover {
  transform: translateY(-1px);
}

.confirm-dialog__btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
}

.confirm-dialog__btn--cancel {
  background: rgba(226, 232, 240, 0.8);
  color: #334155;
}

.confirm-dialog__btn--cancel:hover {
  background: rgba(226, 232, 240, 1);
}

.confirm-dialog__btn--danger {
  background: linear-gradient(135deg, #dc2626, #ea580c);
  color: #fff;
  box-shadow: 0 10px 24px rgba(220, 38, 38, 0.24);
}

.confirm-dialog__btn--accent {
  background: linear-gradient(135deg, #2563eb, #0f766e);
  color: #fff;
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.2);
}

.confirm-dialog-fade-enter-active,
.confirm-dialog-fade-leave-active {
  transition: opacity 180ms ease;
}

.confirm-dialog-fade-enter-from,
.confirm-dialog-fade-leave-to {
  opacity: 0;
}

@media (max-width: 640px) {
  .confirm-dialog {
    padding: 0.9rem;
  }

  .confirm-dialog__panel {
    border-radius: 20px;
    padding: 1rem 1rem 0.95rem;
  }

  .confirm-dialog__actions {
    flex-direction: column-reverse;
  }

  .confirm-dialog__btn {
    width: 100%;
  }
}
</style>