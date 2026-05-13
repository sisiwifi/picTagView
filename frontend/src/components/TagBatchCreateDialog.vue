<template>
  <Teleport to="body">
    <Transition name="tag-batch-create-fade">
      <div v-if="visible" class="tag-batch-create-mask" @click.self="handleClose">
        <section class="tag-batch-create-dialog" role="dialog" aria-modal="true" aria-label="批量新增标签">
          <header class="tag-batch-create-dialog__header">
            <div>
              <h3 class="tag-batch-create-dialog__title">批量新增标签</h3>
              <p class="tag-batch-create-dialog__subtitle">填写标准名、显示名、说明、类型，并为每行选择一种 chip 样式。默认样式会按 7 组预设自动循环。</p>
            </div>
            <button class="tag-batch-create-dialog__close" type="button" :disabled="busy" @click="handleClose">关闭</button>
          </header>

          <div class="tag-batch-create-dialog__toolbar">
            <p class="tag-batch-create-dialog__toolbar-note">当前共 {{ rows.length }} 行，可继续追加或删减。</p>
            <button class="tag-batch-create-dialog__add-btn" type="button" :disabled="busy" @click="addRow">增加一行</button>
          </div>

          <div class="tag-batch-create-dialog__sheet" role="table" aria-label="批量新增标签表格">
            <div class="tag-batch-create-dialog__sheet-head" role="rowgroup">
              <div class="tag-batch-create-dialog__sheet-row tag-batch-create-dialog__sheet-row--head" role="row">
                <span class="tag-batch-create-dialog__cell tag-batch-create-dialog__cell--index" role="columnheader">序号</span>
                <span class="tag-batch-create-dialog__cell tag-batch-create-dialog__cell--name" role="columnheader">标准名</span>
                <span class="tag-batch-create-dialog__cell tag-batch-create-dialog__cell--display" role="columnheader">显示名</span>
                <span class="tag-batch-create-dialog__cell tag-batch-create-dialog__cell--description" role="columnheader">说明</span>
                <span class="tag-batch-create-dialog__cell tag-batch-create-dialog__cell--type" role="columnheader">类型</span>
                <span class="tag-batch-create-dialog__cell tag-batch-create-dialog__cell--style" role="columnheader">样式</span>
                <span class="tag-batch-create-dialog__cell tag-batch-create-dialog__cell--preview" role="columnheader">预览</span>
                <span class="tag-batch-create-dialog__cell tag-batch-create-dialog__cell--actions" role="columnheader">操作</span>
              </div>
            </div>

            <div class="tag-batch-create-dialog__sheet-body" role="rowgroup">
              <div
                v-for="(row, index) in rows"
                :key="row.localId"
                class="tag-batch-create-dialog__sheet-row"
                :class="{ 'tag-batch-create-dialog__sheet-row--error': hasRowError(index) }"
                role="row"
              >
                <div class="tag-batch-create-dialog__cell tag-batch-create-dialog__cell--index" role="cell">
                  <span class="tag-batch-create-dialog__row-number">{{ index + 1 }}</span>
                </div>

                <div class="tag-batch-create-dialog__cell tag-batch-create-dialog__cell--name" role="cell">
                  <input
                    v-model.trim="row.name"
                    :class="['tag-batch-create-dialog__input', { 'tag-batch-create-dialog__input--invalid': Boolean(fieldError(index, 'name')) }]"
                    type="text"
                    autocomplete="off"
                    spellcheck="false"
                    placeholder="例如 asuna_yuuki"
                    :disabled="busy"
                  >
                  <p v-if="fieldError(index, 'name')" class="tag-batch-create-dialog__field-error">{{ fieldError(index, 'name') }}</p>
                </div>

                <div class="tag-batch-create-dialog__cell tag-batch-create-dialog__cell--display" role="cell">
                  <input
                    v-model.trim="row.display_name"
                    class="tag-batch-create-dialog__input"
                    type="text"
                    autocomplete="off"
                    spellcheck="false"
                    placeholder="例如 结城明日奈"
                    :disabled="busy"
                  >
                </div>

                <div class="tag-batch-create-dialog__cell tag-batch-create-dialog__cell--description" role="cell">
                  <input
                    v-model.trim="row.description"
                    class="tag-batch-create-dialog__input"
                    type="text"
                    autocomplete="off"
                    spellcheck="false"
                    placeholder="可选说明"
                    :disabled="busy"
                  >
                </div>

                <div class="tag-batch-create-dialog__cell tag-batch-create-dialog__cell--type" role="cell">
                  <select
                    v-model="row.type"
                    :class="['tag-batch-create-dialog__select', { 'tag-batch-create-dialog__select--invalid': Boolean(fieldError(index, 'type')) }]"
                    :disabled="busy"
                  >
                    <option v-for="option in tagTypeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                  </select>
                  <p v-if="fieldError(index, 'type')" class="tag-batch-create-dialog__field-error">{{ fieldError(index, 'type') }}</p>
                </div>

                <div class="tag-batch-create-dialog__cell tag-batch-create-dialog__cell--style" role="cell">
                  <select
                    v-model="row.presetId"
                    :class="['tag-batch-create-dialog__select', { 'tag-batch-create-dialog__select--invalid': Boolean(fieldError(index, 'style')) }]"
                    :disabled="busy"
                  >
                    <option v-for="preset in tagStylePresets" :key="preset.id" :value="preset.id">{{ preset.label }}</option>
                  </select>
                  <p v-if="fieldError(index, 'style')" class="tag-batch-create-dialog__field-error">{{ fieldError(index, 'style') }}</p>
                </div>

                <div class="tag-batch-create-dialog__cell tag-batch-create-dialog__cell--preview" role="cell">
                  <span class="tag-batch-create-dialog__preview-chip" :style="previewStyle(row)">{{ previewLabel(row) }}</span>
                </div>

                <div class="tag-batch-create-dialog__cell tag-batch-create-dialog__cell--actions" role="cell">
                  <button
                    class="tag-batch-create-dialog__remove-btn"
                    type="button"
                    :disabled="busy || rows.length <= 1"
                    @click="removeRow(row.localId)"
                  >删除</button>
                </div>
              </div>
            </div>
          </div>

          <p v-if="errorMessage" class="tag-batch-create-dialog__feedback tag-batch-create-dialog__feedback--error">{{ errorMessage }}</p>

          <footer class="tag-batch-create-dialog__footer">
            <button class="tag-batch-create-dialog__footer-btn tag-batch-create-dialog__footer-btn--ghost" type="button" :disabled="busy" @click="handleClose">取消</button>
            <button class="tag-batch-create-dialog__footer-btn tag-batch-create-dialog__footer-btn--accent" type="button" :disabled="busy || !rows.length" @click="submitForm">{{ busy ? '提交中…' : '确认批量新增' }}</button>
          </footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script>
import {
  buildTagStyleMetadata,
  getCycledTagStylePreset,
  getTagStylePresetById,
  TAG_STYLE_PRESETS,
} from '../utils/tagStylePresets'
import { TAG_TYPE_OPTIONS } from '../utils/tagTypes'

export default {
  name: 'TagBatchCreateDialog',
  props: {
    visible: { type: Boolean, default: false },
    busy: { type: Boolean, default: false },
    rowErrors: { type: Array, default: () => [] },
    errorMessage: { type: String, default: '' },
  },
  emits: ['close', 'submit'],
  data() {
    return {
      rows: [],
      nextRowLocalId: 1,
    }
  },
  computed: {
    tagStylePresets() {
      return TAG_STYLE_PRESETS
    },
    tagTypeOptions() {
      return TAG_TYPE_OPTIONS
    },
    rowErrorsByIndex() {
      const grouped = {}
      for (const item of Array.isArray(this.rowErrors) ? this.rowErrors : []) {
        const rowIndex = Number(item?.row_index)
        if (!Number.isInteger(rowIndex) || rowIndex < 0) continue
        if (!grouped[rowIndex]) {
          grouped[rowIndex] = []
        }
        grouped[rowIndex].push(item)
      }
      return grouped
    },
  },
  watch: {
    visible(nextValue, previousValue) {
      if (nextValue && !previousValue) {
        this.resetRows()
      }
    },
  },
  methods: {
    createEmptyRow(orderIndex) {
      const preset = getCycledTagStylePreset(orderIndex) || TAG_STYLE_PRESETS[0]
      const row = {
        localId: `row-${this.nextRowLocalId}`,
        name: '',
        display_name: '',
        description: '',
        type: TAG_TYPE_OPTIONS[0].value,
        presetId: preset?.id || TAG_STYLE_PRESETS[0].id,
      }
      this.nextRowLocalId += 1
      return row
    },
    resetRows() {
      this.nextRowLocalId = 1
      this.rows = [this.createEmptyRow(0)]
    },
    handleClose() {
      if (this.busy) return
      this.$emit('close')
    },
    addRow() {
      this.rows = [...this.rows, this.createEmptyRow(this.rows.length)]
    },
    removeRow(localId) {
      if (this.busy || this.rows.length <= 1) return
      this.rows = this.rows.filter(row => row.localId !== localId)
    },
    rowErrorList(rowIndex) {
      return this.rowErrorsByIndex[rowIndex] || []
    },
    hasRowError(rowIndex) {
      return this.rowErrorList(rowIndex).length > 0
    },
    fieldError(rowIndex, field) {
      const matched = this.rowErrorList(rowIndex).find(item => String(item?.field || '') === field)
      return matched ? String(matched.message || '') : ''
    },
    previewLabel(row) {
      return String(row?.display_name || row?.name || '预览标签').trim() || '预览标签'
    },
    previewStyle(row) {
      const preset = getTagStylePresetById(row?.presetId)
      return {
        color: preset.borderColor,
        borderColor: preset.borderColor,
        backgroundColor: preset.backgroundColor,
      }
    },
    submitForm() {
      if (this.busy || !this.rows.length) return
      this.$emit('submit', {
        tags: this.rows.map(row => ({
          name: String(row.name || '').trim(),
          display_name: String(row.display_name || '').trim(),
          description: String(row.description || '').trim(),
          type: String(row.type || TAG_TYPE_OPTIONS[0].value),
          metadata: buildTagStyleMetadata(row.presetId),
        })),
      })
    },
  },
}
</script>

<style scoped lang="css">
.tag-batch-create-mask {
  position: fixed;
  inset: 0;
  z-index: 140;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: rgba(15, 23, 42, 0.36);
  backdrop-filter: blur(10px);
}

.tag-batch-create-dialog {
  width: min(1420px, 96vw);
  height: min(86vh, 840px);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 0.95rem;
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 28px;
  padding: 1.2rem;
  background:
    radial-gradient(circle at top left, rgba(191, 219, 254, 0.3), transparent 26%),
    radial-gradient(circle at bottom right, rgba(167, 243, 208, 0.24), transparent 30%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.99), rgba(248, 250, 252, 0.98));
  box-shadow: 0 34px 90px rgba(15, 23, 42, 0.26);
}

.tag-batch-create-dialog__header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.tag-batch-create-dialog__title {
  margin: 0;
  color: #0f172a;
  font-size: 1.08rem;
  font-weight: 800;
}

.tag-batch-create-dialog__subtitle {
  margin: 0.35rem 0 0;
  color: #64748b;
  font-size: 0.84rem;
  line-height: 1.65;
}

.tag-batch-create-dialog__close {
  border: 0;
  background: transparent;
  color: #64748b;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
}

.tag-batch-create-dialog__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.tag-batch-create-dialog__toolbar-note {
  margin: 0;
  color: #475569;
  font-size: 0.82rem;
  font-weight: 600;
}

.tag-batch-create-dialog__add-btn,
.tag-batch-create-dialog__remove-btn,
.tag-batch-create-dialog__footer-btn {
  border: 0;
  border-radius: 14px;
  cursor: pointer;
  transition: transform 160ms ease, box-shadow 160ms ease, opacity 160ms ease, background 160ms ease;
}

.tag-batch-create-dialog__add-btn:hover:not(:disabled),
.tag-batch-create-dialog__remove-btn:hover:not(:disabled),
.tag-batch-create-dialog__footer-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.tag-batch-create-dialog__add-btn,
.tag-batch-create-dialog__remove-btn {
  padding: 0.62rem 0.9rem;
  font-size: 0.78rem;
  font-weight: 800;
}

.tag-batch-create-dialog__add-btn {
  background: linear-gradient(135deg, #2563eb, #0f766e);
  color: #ffffff;
  box-shadow: 0 12px 26px rgba(37, 99, 235, 0.2);
}

.tag-batch-create-dialog__remove-btn {
  background: rgba(254, 242, 242, 0.96);
  color: #b91c1c;
}

.tag-batch-create-dialog__add-btn:disabled,
.tag-batch-create-dialog__remove-btn:disabled,
.tag-batch-create-dialog__footer-btn:disabled,
.tag-batch-create-dialog__close:disabled {
  opacity: 0.48;
  cursor: not-allowed;
  transform: none;
}

.tag-batch-create-dialog__sheet {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 22px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.82);
}

.tag-batch-create-dialog__sheet-head {
  flex: 0 0 auto;
  background: rgba(241, 245, 249, 0.92);
  border-bottom: 1px solid rgba(226, 232, 240, 0.9);
}

.tag-batch-create-dialog__sheet-body {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
}

.tag-batch-create-dialog__sheet-row {
  display: grid;
  grid-template-columns: 72px minmax(180px, 1.1fr) minmax(180px, 1fr) minmax(170px, 1fr) 150px 150px 180px 92px;
  align-items: stretch;
  border-bottom: 1px solid rgba(226, 232, 240, 0.85);
}

.tag-batch-create-dialog__sheet-row--head {
  border-bottom: 0;
}

.tag-batch-create-dialog__sheet-row--error {
  background: rgba(254, 242, 242, 0.72);
  box-shadow: inset 0 0 0 2px rgba(239, 68, 68, 0.32), 0 0 18px rgba(239, 68, 68, 0.12);
}

.tag-batch-create-dialog__sheet-row:last-child {
  border-bottom: 0;
}

.tag-batch-create-dialog__cell {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 0.42rem;
  min-width: 0;
  padding: 0.82rem 0.78rem;
  border-right: 1px solid rgba(226, 232, 240, 0.88);
}

.tag-batch-create-dialog__sheet-row--head .tag-batch-create-dialog__cell {
  color: #334155;
  font-family: 'Microsoft YaHei UI', 'PingFang SC', 'Noto Sans SC', sans-serif;
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.03em;
  text-transform: none;
}

.tag-batch-create-dialog__cell:last-child {
  border-right: 0;
}

.tag-batch-create-dialog__row-number {
  color: #0f172a;
  font-size: 0.88rem;
  font-weight: 800;
}

.tag-batch-create-dialog__input,
.tag-batch-create-dialog__select {
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.34);
  border-radius: 14px;
  padding: 0.68rem 0.78rem;
  background: rgba(255, 255, 255, 0.96);
  color: #0f172a;
  font-size: 0.84rem;
}

.tag-batch-create-dialog__input--invalid,
.tag-batch-create-dialog__select--invalid {
  border-color: rgba(220, 38, 38, 0.62);
  box-shadow: 0 0 0 3px rgba(254, 226, 226, 0.72);
  background: rgba(255, 255, 255, 0.98);
}

.tag-batch-create-dialog__field-error,
.tag-batch-create-dialog__feedback--error {
  margin: 0;
  color: #b91c1c;
  font-size: 0.74rem;
  font-weight: 700;
  line-height: 1.5;
}

.tag-batch-create-dialog__preview-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 36px;
  max-width: 100%;
  border: 1px solid currentColor;
  border-radius: 999px;
  padding: 0.46rem 0.8rem;
  font-size: 0.78rem;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tag-batch-create-dialog__footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.68rem;
}

.tag-batch-create-dialog__footer-btn {
  padding: 0.72rem 1.08rem;
  font-size: 0.82rem;
  font-weight: 800;
}

.tag-batch-create-dialog__footer-btn--ghost {
  background: rgba(226, 232, 240, 0.86);
  color: #334155;
}

.tag-batch-create-dialog__footer-btn--accent {
  background: linear-gradient(135deg, #1d4ed8, #0f766e);
  color: #ffffff;
  box-shadow: 0 12px 26px rgba(29, 78, 216, 0.18);
}

.tag-batch-create-fade-enter-active,
.tag-batch-create-fade-leave-active {
  transition: opacity 180ms ease, transform 180ms ease;
}

.tag-batch-create-fade-enter-from,
.tag-batch-create-fade-leave-to {
  opacity: 0;
  transform: translateY(12px);
}

@media (max-width: 1080px) {
  .tag-batch-create-dialog {
    width: min(98vw, 1420px);
    height: min(90vh, 840px);
  }

  .tag-batch-create-dialog__sheet-row {
    min-width: 1220px;
  }

  .tag-batch-create-dialog__sheet-head,
  .tag-batch-create-dialog__sheet-body {
    overflow-x: auto;
  }
}

@media (max-width: 780px) {
  .tag-batch-create-dialog {
    padding: 1rem;
  }

  .tag-batch-create-dialog__toolbar,
  .tag-batch-create-dialog__header,
  .tag-batch-create-dialog__footer {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>