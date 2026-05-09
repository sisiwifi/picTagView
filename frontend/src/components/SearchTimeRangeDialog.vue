<template>
  <Teleport to="body">
    <Transition name="search-time-dialog-fade">
      <div v-if="visible" class="search-time-dialog__mask" @click.self="$emit('close')">
        <section class="search-time-dialog" role="dialog" aria-modal="true" aria-label="搜索时间范围">
          <header class="search-time-dialog__header">
            <div>
              <h3 class="search-time-dialog__title">时间范围搜索</h3>
              <p class="search-time-dialog__subtitle">选择导入时间或创建时间范围，确认后会自动写回搜索框。</p>
            </div>
            <button class="search-time-dialog__close" type="button" @click="$emit('close')">关闭</button>
          </header>

          <form class="search-time-dialog__form" @submit.prevent="submitForm">
            <div class="search-time-dialog__mode-row" role="group" aria-label="时间字段类型">
              <button
                type="button"
                class="search-time-dialog__mode-btn"
                :class="{ 'search-time-dialog__mode-btn--active': fieldType === 'imported_at' }"
                @click="fieldType = 'imported_at'"
              >
                导入时间
              </button>
              <button
                type="button"
                class="search-time-dialog__mode-btn"
                :class="{ 'search-time-dialog__mode-btn--active': fieldType === 'file_created_at' }"
                @click="fieldType = 'file_created_at'"
              >
                创建时间
              </button>
            </div>

            <div class="search-time-dialog__grid">
              <section class="search-time-dialog__field-group">
                <h4 class="search-time-dialog__field-title">开始时间</h4>
                <label class="search-time-dialog__field">
                  <span class="search-time-dialog__label">日期</span>
                  <input v-model="startDate" class="search-time-dialog__input" type="date">
                </label>
                <label class="search-time-dialog__field">
                  <span class="search-time-dialog__label">时间</span>
                  <input v-model="startTime" class="search-time-dialog__input" type="time" step="1">
                </label>
              </section>

              <section class="search-time-dialog__field-group">
                <h4 class="search-time-dialog__field-title">结束时间</h4>
                <label class="search-time-dialog__field">
                  <span class="search-time-dialog__label">日期</span>
                  <input v-model="endDate" class="search-time-dialog__input" type="date">
                </label>
                <label class="search-time-dialog__field">
                  <span class="search-time-dialog__label">时间</span>
                  <input v-model="endTime" class="search-time-dialog__input" type="time" step="1">
                </label>
              </section>
            </div>

            <div class="search-time-dialog__preview-shell">
              <span class="search-time-dialog__preview-label">搜索框写回预览</span>
              <code class="search-time-dialog__preview-text">{{ previewQueryText || '请选择完整的开始与结束时间' }}</code>
            </div>

            <p v-if="validationMessage || errorMessage" class="search-time-dialog__error">
              {{ validationMessage || errorMessage }}
            </p>

            <footer class="search-time-dialog__footer">
              <button class="search-time-dialog__action search-time-dialog__action--ghost" type="button" @click="$emit('close')">
                取消
              </button>
              <button class="search-time-dialog__action search-time-dialog__action--accent" type="submit" :disabled="!canSubmit">
                应用到搜索框
              </button>
            </footer>
          </form>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script>
function splitDateTimeText(rawValue) {
  const normalized = String(rawValue || '').trim()
  const matched = /^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})$/.exec(normalized)
  if (!matched) {
    return {
      date: '',
      time: '',
    }
  }
  return {
    date: matched[1],
    time: matched[2],
  }
}

function combineDateTimeText(datePart, timePart) {
  const dateText = String(datePart || '').trim()
  const timeText = String(timePart || '').trim()
  if (!dateText || !timeText) return ''
  const normalizedTime = timeText.length === 5 ? `${timeText}:00` : timeText
  return `${dateText} ${normalizedTime}`
}

export default {
  name: 'SearchTimeRangeDialog',
  props: {
    visible: { type: Boolean, default: false },
    initialField: { type: String, default: 'imported_at' },
    initialStartText: { type: String, default: '' },
    initialEndText: { type: String, default: '' },
    errorMessage: { type: String, default: '' },
  },
  emits: ['close', 'apply'],
  data() {
    return {
      fieldType: 'imported_at',
      startDate: '',
      startTime: '',
      endDate: '',
      endTime: '',
    }
  },
  computed: {
    startText() {
      return combineDateTimeText(this.startDate, this.startTime)
    },
    endText() {
      return combineDateTimeText(this.endDate, this.endTime)
    },
    previewQueryText() {
      if (!this.startText || !this.endText) return ''
      const prefix = this.fieldType === 'file_created_at' ? 'create:' : 'import:'
      return `${prefix}${this.startText}~${this.endText}`
    },
    validationMessage() {
      if (!this.startText || !this.endText) {
        return '请完整选择开始和结束时间。'
      }
      const startDate = new Date(this.startText.replace(' ', 'T'))
      const endDate = new Date(this.endText.replace(' ', 'T'))
      if (Number.isNaN(startDate.getTime()) || Number.isNaN(endDate.getTime())) {
        return '时间格式无效。'
      }
      if (startDate.getTime() > endDate.getTime()) {
        return '开始时间不能晚于结束时间。'
      }
      return ''
    },
    canSubmit() {
      return !this.validationMessage
    },
  },
  watch: {
    visible(nextValue) {
      if (nextValue) {
        this.seedFromProps()
      }
    },
    initialField() {
      if (this.visible) {
        this.seedFromProps()
      }
    },
    initialStartText() {
      if (this.visible) {
        this.seedFromProps()
      }
    },
    initialEndText() {
      if (this.visible) {
        this.seedFromProps()
      }
    },
  },
  methods: {
    seedFromProps() {
      this.fieldType = this.initialField === 'file_created_at' ? 'file_created_at' : 'imported_at'
      const startParts = splitDateTimeText(this.initialStartText)
      const endParts = splitDateTimeText(this.initialEndText)
      this.startDate = startParts.date
      this.startTime = startParts.time
      this.endDate = endParts.date
      this.endTime = endParts.time
    },
    submitForm() {
      if (!this.canSubmit) return
      this.$emit('apply', {
        fieldType: this.fieldType,
        startText: this.startText,
        endText: this.endText,
        queryText: this.previewQueryText,
      })
    },
  },
}
</script>

<style scoped lang="css">
.search-time-dialog__mask {
  position: fixed;
  inset: 0;
  z-index: 120;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: rgba(15, 23, 42, 0.34);
  backdrop-filter: blur(8px);
}

.search-time-dialog {
  width: min(100%, 720px);
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 28px;
  padding: 1.2rem;
  background:
    radial-gradient(circle at top right, rgba(167, 243, 208, 0.88), transparent 34%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
  box-shadow: 0 30px 80px rgba(15, 23, 42, 0.24);
}

.search-time-dialog__header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.search-time-dialog__title {
  margin: 0;
  color: #0f172a;
  font-size: 1.08rem;
  font-weight: 800;
}

.search-time-dialog__subtitle {
  margin: 0.38rem 0 0;
  color: #64748b;
  font-size: 0.84rem;
  line-height: 1.6;
}

.search-time-dialog__close {
  border: 0;
  background: transparent;
  color: #64748b;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
}

.search-time-dialog__form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1.2rem;
}

.search-time-dialog__mode-row {
  display: inline-flex;
  width: fit-content;
  gap: 0.55rem;
  padding: 0.34rem;
  border-radius: 999px;
  background: rgba(241, 245, 249, 0.94);
}

.search-time-dialog__mode-btn {
  border: 0;
  border-radius: 999px;
  padding: 0.55rem 0.95rem;
  background: transparent;
  color: #475569;
  font-size: 0.82rem;
  font-weight: 800;
  cursor: pointer;
}

.search-time-dialog__mode-btn--active {
  background: linear-gradient(135deg, #059669, #0f766e);
  color: #ffffff;
  box-shadow: 0 12px 24px rgba(5, 150, 105, 0.22);
}

.search-time-dialog__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.search-time-dialog__field-group {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.9);
}

.search-time-dialog__field-title {
  margin: 0;
  color: #0f172a;
  font-size: 0.9rem;
  font-weight: 800;
}

.search-time-dialog__field {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.search-time-dialog__label {
  color: #334155;
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.search-time-dialog__input {
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.34);
  border-radius: 16px;
  padding: 0.82rem 0.9rem;
  background: rgba(255, 255, 255, 0.92);
  color: #0f172a;
  font-size: 0.88rem;
}

.search-time-dialog__preview-shell {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  padding: 0.9rem 1rem;
  border-radius: 18px;
  background: rgba(240, 253, 250, 0.92);
  border: 1px solid rgba(167, 243, 208, 0.85);
}

.search-time-dialog__preview-label {
  color: #0f766e;
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.search-time-dialog__preview-text {
  color: #134e4a;
  font-size: 0.8rem;
  word-break: break-all;
}

.search-time-dialog__error {
  margin: 0;
  color: #991b1b;
  font-size: 0.78rem;
  font-weight: 700;
}

.search-time-dialog__footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.7rem;
}

.search-time-dialog__action {
  border: 0;
  border-radius: 16px;
  padding: 0.82rem 1rem;
  font-size: 0.84rem;
  font-weight: 800;
  cursor: pointer;
  transition: transform 150ms ease, opacity 150ms ease;
}

.search-time-dialog__action:hover {
  transform: translateY(-1px);
}

.search-time-dialog__action--ghost {
  background: rgba(226, 232, 240, 0.88);
  color: #334155;
}

.search-time-dialog__action--accent {
  background: linear-gradient(135deg, #059669, #0f766e);
  color: #ffffff;
  box-shadow: 0 14px 28px rgba(5, 150, 105, 0.22);
}

.search-time-dialog__action:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
}

.search-time-dialog-fade-enter-active,
.search-time-dialog-fade-leave-active {
  transition: opacity 180ms ease;
}

.search-time-dialog-fade-enter-from,
.search-time-dialog-fade-leave-to {
  opacity: 0;
}

@media (max-width: 720px) {
  .search-time-dialog {
    border-radius: 24px;
    padding: 1rem;
  }

  .search-time-dialog__grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .search-time-dialog__footer {
    flex-direction: column-reverse;
  }

  .search-time-dialog__action {
    width: 100%;
  }
}
</style>