<template>
  <Teleport to="body">
    <Transition name="tag-import-fade">
      <div v-if="visible" class="tag-import-mask" @click.self="$emit('close')">
        <section class="tag-import-dialog" role="dialog" aria-modal="true" aria-label="导入标签 JSON">
          <header class="tag-import-dialog__header">
            <div>
              <h3 class="tag-import-dialog__title">导入标签 JSON</h3>
              <p class="tag-import-dialog__subtitle">选择文件后导入，可决定同名标签的冲突处理方式。</p>
            </div>
            <button class="tag-import-dialog__close" type="button" @click="$emit('close')">关闭</button>
          </header>

          <div class="tag-import-grid">
            <label class="tag-import-field">
              <span class="tag-import-field__label">文件路径</span>
              <div class="tag-import-file-picker">
                <input
                  class="tag-import-file-picker__input"
                  type="text"
                  :value="fileLabel || '尚未选择文件'"
                  readonly
                >
                <button class="tag-import-file-picker__btn" type="button" :disabled="busy" @click="$emit('choose-file')">
                  选择文件
                </button>
              </div>
            </label>

            <label class="tag-import-field">
              <span class="tag-import-field__label">冲突处理</span>
              <select
                class="tag-import-select"
                :value="conflict"
                :disabled="busy"
                @change="$emit('update:conflict', $event.target.value)"
              >
                <option value="skip">跳过已存在</option>
                <option value="overwrite">覆盖已存在</option>
              </select>
            </label>
          </div>

          <p v-if="result" class="tag-import-feedback tag-import-feedback--success">
            已导入 {{ result.imported }}，更新 {{ result.updated }}，跳过 {{ result.skipped }}。
          </p>
          <p v-if="error" class="tag-import-feedback tag-import-feedback--error">{{ error }}</p>

          <footer class="tag-import-dialog__footer">
            <button class="tag-import-dialog__btn tag-import-dialog__btn--ghost" type="button" :disabled="busy" @click="$emit('close')">
              取消
            </button>
            <button class="tag-import-dialog__btn tag-import-dialog__btn--accent" type="button" :disabled="busy || !hasFile" @click="$emit('confirm')">
              {{ busy ? '导入中…' : '开始导入' }}
            </button>
          </footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script>
export default {
  name: 'TagImportDialog',
  props: {
    visible: { type: Boolean, default: false },
    busy: { type: Boolean, default: false },
    conflict: { type: String, default: 'skip' },
    fileLabel: { type: String, default: '' },
    hasFile: { type: Boolean, default: false },
    result: { type: Object, default: null },
    error: { type: String, default: '' },
  },
  emits: ['choose-file', 'close', 'confirm', 'update:conflict'],
}
</script>

<style scoped lang="css">
.tag-import-mask {
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

.tag-import-dialog {
  width: min(100%, 720px);
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 28px;
  padding: 1.25rem;
  background:
    radial-gradient(circle at top left, rgba(254, 249, 195, 0.9), transparent 40%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
  box-shadow: 0 28px 80px rgba(15, 23, 42, 0.24);
}

.tag-import-dialog__header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.tag-import-dialog__title {
  margin: 0;
  color: #0f172a;
  font-size: 1.1rem;
  font-weight: 800;
}

.tag-import-dialog__subtitle {
  margin: 0.4rem 0 0;
  color: #64748b;
  font-size: 0.85rem;
  line-height: 1.6;
}

.tag-import-dialog__close {
  border: 0;
  background: transparent;
  color: #64748b;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
}

.tag-import-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(220px, 1fr);
  gap: 1rem;
  margin-top: 1.25rem;
}

.tag-import-field {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.tag-import-field__label {
  color: #334155;
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.tag-import-file-picker {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.65rem;
}

.tag-import-file-picker__input,
.tag-import-select {
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.34);
  border-radius: 16px;
  padding: 0.85rem 0.95rem;
  background: rgba(255, 255, 255, 0.88);
  color: #0f172a;
  font-size: 0.88rem;
}

.tag-import-file-picker__btn,
.tag-import-dialog__btn {
  border: 0;
  border-radius: 16px;
  padding: 0.82rem 1rem;
  font-size: 0.84rem;
  font-weight: 800;
  cursor: pointer;
  transition: transform 150ms ease, opacity 150ms ease, box-shadow 150ms ease;
}

.tag-import-file-picker__btn:hover,
.tag-import-dialog__btn:hover {
  transform: translateY(-1px);
}

.tag-import-file-picker__btn,
.tag-import-dialog__btn--ghost {
  background: rgba(226, 232, 240, 0.88);
  color: #334155;
}

.tag-import-dialog__btn--accent {
  background: linear-gradient(135deg, #f97316, #ea580c);
  color: #fff;
  box-shadow: 0 14px 28px rgba(234, 88, 12, 0.24);
}

.tag-import-dialog__footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.7rem;
  margin-top: 1.15rem;
}

.tag-import-feedback {
  margin: 1rem 0 0;
  border-radius: 16px;
  padding: 0.8rem 0.95rem;
  font-size: 0.82rem;
  font-weight: 700;
}

.tag-import-feedback--success {
  background: rgba(220, 252, 231, 0.82);
  color: #166534;
}

.tag-import-feedback--error {
  background: rgba(254, 226, 226, 0.9);
  color: #991b1b;
}

.tag-import-file-picker__btn:disabled,
.tag-import-dialog__btn:disabled,
.tag-import-select:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
}

.tag-import-fade-enter-active,
.tag-import-fade-leave-active {
  transition: opacity 180ms ease;
}

.tag-import-fade-enter-from,
.tag-import-fade-leave-to {
  opacity: 0;
}

@media (max-width: 640px) {
  .tag-import-dialog {
    padding: 1rem;
    border-radius: 24px;
  }

  .tag-import-dialog__header,
  .tag-import-dialog__footer,
  .tag-import-grid,
  .tag-import-file-picker {
    grid-template-columns: 1fr;
    display: grid;
  }

  .tag-import-dialog__footer {
    justify-content: stretch;
  }

  .tag-import-dialog__btn,
  .tag-import-file-picker__btn {
    width: 100%;
  }
}
</style>