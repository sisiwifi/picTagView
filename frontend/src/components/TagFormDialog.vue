<template>
  <Teleport to="body">
    <Transition name="tag-form-fade">
      <div v-if="visible" class="tag-form-mask" @click.self="$emit('close')">
        <section class="tag-form-dialog" role="dialog" aria-modal="true" :aria-label="dialogTitle">
          <header class="tag-form-dialog__header">
            <div>
              <h3 class="tag-form-dialog__title">{{ dialogTitle }}</h3>
              <p class="tag-form-dialog__subtitle">统一使用 HEX8 存储颜色，边框颜色同时作为文字颜色。</p>
            </div>
            <button class="tag-form-dialog__close" type="button" :disabled="saving" @click="$emit('close')">关闭</button>
          </header>

          <form class="tag-form" @submit.prevent="submitForm">
            <div class="tag-form__grid">
              <div class="tag-form__column tag-form__column--fields">
                <label class="tag-form__field">
                  <span class="tag-form__label">public id</span>
                  <input :value="form.public_id || '预留中…'" class="tag-form__input tag-form__input--readonly" type="text" readonly>
                </label>

                <label class="tag-form__field">
                  <span class="tag-form__label">name</span>
                  <input
                    v-model.trim="form.name"
                    class="tag-form__input"
                    type="text"
                    autocomplete="off"
                    spellcheck="false"
                    placeholder="例如 asuna_yuuki"
                    :disabled="saving"
                  >
                  <span v-if="nameEmpty" class="tag-form__bubble">name 不能为空</span>
                  <span v-else-if="namePatternInvalid" class="tag-form__hint tag-form__hint--error">仅支持小写字母、数字和下划线</span>
                  <span v-else-if="nameDuplicated" class="tag-form__hint tag-form__hint--error">该 name 已被占用</span>
                  <span v-else class="tag-form__hint">将作为标签的唯一标准名写入数据库</span>
                </label>

                <label class="tag-form__field">
                  <span class="tag-form__label">display name</span>
                  <input
                    v-model.trim="form.display_name"
                    class="tag-form__input"
                    type="text"
                    autocomplete="off"
                    spellcheck="false"
                    placeholder="例如 结城明日奈"
                    :disabled="saving"
                  >
                  <span class="tag-form__hint">留空时默认使用 name</span>
                </label>

                <label class="tag-form__field">
                  <span class="tag-form__label">type</span>
                  <select v-model="form.type" class="tag-form__input tag-form__select" :disabled="saving">
                    <option v-for="option in tagTypeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                  </select>
                </label>

                <label class="tag-form__field tag-form__field--grow">
                  <span class="tag-form__label">description</span>
                  <textarea
                    v-model.trim="form.description"
                    class="tag-form__textarea"
                    rows="6"
                    placeholder="填写标签说明，可留空"
                    :disabled="saving"
                  ></textarea>
                </label>
              </div>

              <div class="tag-form__column tag-form__column--design">
                <section class="tag-form__panel">
                  <div class="tag-form__panel-head">
                    <span class="tag-form__panel-label">标签预览</span>
                    <span class="tag-form__panel-note">边框与文字颜色保持一致</span>
                  </div>
                  <div class="tag-form__preview-card">
                    <TagChipList :tags="[previewTag]" :compact="false" />
                  </div>
                </section>

                <section class="tag-form__panel">
                  <div class="tag-form__panel-head">
                    <span class="tag-form__panel-label">颜色编辑</span>
                    <button class="tag-form__sync-btn" type="button" :disabled="saving" @click="syncBackgroundToBorder">背景跟随边框</button>
                  </div>

                  <div class="tag-form__target-list">
                    <button
                      class="tag-form__target"
                      :class="{ 'tag-form__target--active': activeTarget === 'border' }"
                      type="button"
                      :disabled="saving"
                      @click="selectColorTarget('border')"
                    >
                      <span class="tag-form__target-meta">
                        <span class="tag-form__target-label">边框 / 文字</span>
                        <strong class="tag-form__target-value">{{ form.border_color }}</strong>
                      </span>
                      <span class="tag-form__target-swatch" :style="{ background: form.border_color, borderColor: form.border_color }"></span>
                    </button>

                    <button
                      class="tag-form__target"
                      :class="{ 'tag-form__target--active': activeTarget === 'background' }"
                      type="button"
                      :disabled="saving"
                      @click="selectColorTarget('background')"
                    >
                      <span class="tag-form__target-meta">
                        <span class="tag-form__target-label">背景</span>
                        <strong class="tag-form__target-value">{{ form.background_color }}</strong>
                      </span>
                      <span class="tag-form__target-swatch tag-form__target-swatch--checker" :style="{ background: form.background_color, borderColor: form.border_color }"></span>
                    </button>
                  </div>

                  <div class="tag-form__preset-list" role="list" aria-label="预设标签样式">
                    <button
                      v-for="preset in tagStylePresets"
                      :key="preset.id"
                      class="tag-form__preset"
                      type="button"
                      :title="preset.label"
                      :disabled="saving"
                      @click="applyPreset(preset)"
                    >
                      <span
                        class="tag-form__preset-pill"
                        :style="{ '--preset-border': preset.borderColor, '--preset-background': preset.backgroundColor }"
                      ></span>
                    </button>
                  </div>

                  <TagColorPicker
                    :model-value="currentPickerValue"
                    :alpha-enabled="activeTarget === 'background'"
                    :disabled="saving"
                    :fallback-color="currentPickerValue"
                    @update:modelValue="applyColorToActiveTarget"
                  />
                </section>
              </div>
            </div>

            <p v-if="errorMessage" class="tag-form__feedback tag-form__feedback--error">{{ errorMessage }}</p>

            <footer class="tag-form__footer">
              <button class="tag-form__btn tag-form__btn--ghost" type="button" :disabled="saving" @click="$emit('close')">取消</button>
              <button class="tag-form__btn tag-form__btn--accent" type="submit" :disabled="saving || !canSubmit">{{ saving ? '保存中…' : submitLabel }}</button>
            </footer>
          </form>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script>
import TagChipList from './TagChipList.vue'
import TagColorPicker from './TagColorPicker.vue'
import { isSameRgb, normalizeHex8, normalizeTagColors, withAlpha } from '../utils/tagColors'

const TAG_TYPE_OPTIONS = [
  { value: 'normal', label: 'normal / 普通标签' },
  { value: 'artist', label: 'artist / 作者标签' },
  { value: 'copyright', label: 'copyright / 作品标签' },
  { value: 'character', label: 'character / 角色标签' },
  { value: 'series', label: 'series / 系列标签' },
]

const TAG_STYLE_PRESETS = [
  { id: 'preset-red', label: '红色', borderColor: '#FF0000FF', backgroundColor: '#FF000066' },
  { id: 'preset-orange', label: '橙色', borderColor: '#FF6600FF', backgroundColor: '#FF660066' },
  { id: 'preset-yellow', label: '金黄', borderColor: '#C9A600FF', backgroundColor: '#FFFF0024' },
  { id: 'preset-green', label: '绿色', borderColor: '#00B84AFF', backgroundColor: '#00FF0029' },
  { id: 'preset-blue', label: '蓝色', borderColor: '#1E90FFFF', backgroundColor: '#1E90FF66' },
  { id: 'preset-purple', label: '紫色', borderColor: '#8A2BE2FF', backgroundColor: '#8A2BE266' },
  { id: 'preset-pink', label: '粉色', borderColor: '#FF1493FF', backgroundColor: '#FF149366' },
]

function createMetadataBase(metadata = null) {
  return {
    schema_version: Number.isInteger(metadata?.schema_version) ? metadata.schema_version : 1,
    created_via: typeof metadata?.created_via === 'string' && metadata.created_via.trim() ? metadata.created_via.trim() : 'manual',
    ui_hint: metadata?.ui_hint && typeof metadata.ui_hint === 'object' && !Array.isArray(metadata.ui_hint) ? { ...metadata.ui_hint } : {},
    notes: typeof metadata?.notes === 'string' ? metadata.notes : '',
  }
}

function createFormState(tag = null) {
  const metadata = tag?.metadata && typeof tag.metadata === 'object' ? tag.metadata : {}
  const preset = TAG_STYLE_PRESETS[0]
  const { borderColor, backgroundColor } = normalizeTagColors(tag || { metadata }, {
    fallbackColor: preset.borderColor,
    fallbackBackgroundAlpha: preset.backgroundColor.slice(7, 9),
  })

  return {
    id: Number.isInteger(tag?.id) ? tag.id : null,
    public_id: String(tag?.public_id || ''),
    name: String(tag?.name || ''),
    display_name: String(tag?.display_name || ''),
    type: TAG_TYPE_OPTIONS.some(option => option.value === tag?.type) ? tag.type : 'normal',
    description: String(tag?.description || ''),
    border_color: normalizeHex8(borderColor, { defaultAlpha: 'FF' }) || preset.borderColor,
    background_color: normalizeHex8(backgroundColor, { defaultAlpha: '66' }) || preset.backgroundColor,
    metadata_base: createMetadataBase(metadata),
  }
}

function shouldAutoSyncBackground(tag = null) {
  if (!tag) return true
  const { borderColor, backgroundColor } = normalizeTagColors(tag)
  return isSameRgb(borderColor, backgroundColor)
}

export default {
  name: 'TagFormDialog',
  components: {
    TagChipList,
    TagColorPicker,
  },
  props: {
    visible: { type: Boolean, default: false },
    saving: { type: Boolean, default: false },
    mode: { type: String, default: 'create' },
    initialTag: { type: Object, default: null },
    existingNames: { type: Array, default: () => [] },
    errorMessage: { type: String, default: '' },
  },
  emits: ['close', 'submit'],
  data() {
    return {
      form: createFormState(this.initialTag),
      activeTarget: 'border',
      autoSyncBackground: shouldAutoSyncBackground(this.initialTag),
    }
  },
  computed: {
    tagTypeOptions() {
      return TAG_TYPE_OPTIONS
    },
    tagStylePresets() {
      return TAG_STYLE_PRESETS
    },
    dialogTitle() {
      return this.mode === 'edit' ? '编辑标签' : '新增标签'
    },
    submitLabel() {
      return this.mode === 'edit' ? '确认修改' : '确认创建'
    },
    normalizedName() {
      return String(this.form.name || '').trim()
    },
    normalizedDisplayName() {
      return String(this.form.display_name || '').trim()
    },
    nameEmpty() {
      return this.normalizedName.length === 0
    },
    namePatternInvalid() {
      return !this.nameEmpty && !/^[a-z0-9_]+$/.test(this.normalizedName)
    },
    nameDuplicated() {
      if (this.nameEmpty || this.namePatternInvalid) return false
      const currentName = String(this.initialTag?.name || '').trim()
      return (Array.isArray(this.existingNames) ? this.existingNames : [])
        .some(name => name === this.normalizedName && name !== currentName)
    },
    canSubmit() {
      return Boolean(this.form.public_id) && !this.nameEmpty && !this.namePatternInvalid && !this.nameDuplicated
    },
    currentPickerValue() {
      return this.activeTarget === 'background' ? this.form.background_color : this.form.border_color
    },
    previewTag() {
      const displayName = this.normalizedDisplayName || this.normalizedName || 'tag'
      return {
        id: this.form.id || 'preview',
        name: this.normalizedName || 'tag',
        display_name: displayName,
        color: this.form.border_color,
        border_color: this.form.border_color,
        background_color: this.form.background_color,
      }
    },
    backgroundAlphaHex() {
      return this.form.background_color ? this.form.background_color.slice(7, 9) : '66'
    },
  },
  watch: {
    visible(nextValue) {
      if (nextValue) {
        this.resetForm(this.initialTag)
      }
    },
    initialTag() {
      if (this.visible) {
        this.resetForm(this.initialTag)
      }
    },
  },
  methods: {
    resetForm(tag = null) {
      this.form = createFormState(tag)
      this.activeTarget = 'border'
      this.autoSyncBackground = shouldAutoSyncBackground(tag)
    },
    selectColorTarget(target) {
      this.activeTarget = target
    },
    applyPreset(preset) {
      this.form.border_color = preset.borderColor
      this.form.background_color = preset.backgroundColor
      this.autoSyncBackground = isSameRgb(preset.borderColor, preset.backgroundColor)
      this.activeTarget = 'border'
    },
    syncBackgroundToBorder() {
      this.form.background_color = withAlpha(this.form.border_color, '66')
      this.autoSyncBackground = true
      this.activeTarget = 'background'
    },
    applyColorToActiveTarget(nextHex) {
      const normalized = normalizeHex8(nextHex, { defaultAlpha: this.activeTarget === 'background' ? this.backgroundAlphaHex : 'FF' })
      if (!normalized) return

      if (this.activeTarget === 'background') {
        this.form.background_color = normalized
        this.autoSyncBackground = false
        return
      }

      const nextBorder = withAlpha(normalized, 'FF')
      this.form.border_color = nextBorder

      if (this.autoSyncBackground) {
        const alphaHex = this.backgroundAlphaHex || '66'
        this.form.background_color = withAlpha(nextBorder, alphaHex)
      }
    },
    submitForm() {
      if (!this.canSubmit) return

      const metadataBase = this.form.metadata_base || {}
      this.$emit('submit', {
        id: this.form.id,
        public_id: this.form.public_id,
        name: this.normalizedName,
        display_name: this.normalizedDisplayName || this.normalizedName,
        type: this.form.type,
        description: String(this.form.description || '').trim(),
        metadata: {
          schema_version: Number.isInteger(metadataBase.schema_version) ? metadataBase.schema_version : 1,
          created_via: metadataBase.created_via || 'manual',
          ui_hint: metadataBase.ui_hint || {},
          notes: metadataBase.notes || '',
          color: this.form.border_color,
          border_color: this.form.border_color,
          background_color: this.form.background_color,
        },
      })
    },
  },
}
</script>

<style scoped lang="css">
.tag-form-mask {
  position: fixed;
  inset: 0;
  z-index: 130;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: rgba(15, 23, 42, 0.34);
  backdrop-filter: blur(8px);
}

.tag-form-dialog {
  width: min(1120px, 96vw);
  max-height: min(92vh, 980px);
  overflow: hidden;
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 30px;
  padding: 1.28rem;
  background:
    radial-gradient(circle at top left, rgba(253, 224, 71, 0.18), transparent 26%),
    radial-gradient(circle at bottom right, rgba(148, 163, 184, 0.18), transparent 32%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.99), rgba(248, 250, 252, 0.98));
  box-shadow: 0 34px 90px rgba(15, 23, 42, 0.24);
  display: flex;
  flex-direction: column;
}

.tag-form-dialog__header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.tag-form-dialog__title {
  margin: 0;
  color: #0f172a;
  font-size: 1.12rem;
  font-weight: 800;
}

.tag-form-dialog__subtitle {
  margin: 0.38rem 0 0;
  color: #64748b;
  font-size: 0.84rem;
  line-height: 1.65;
}

.tag-form-dialog__close {
  border: 0;
  background: transparent;
  color: #64748b;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
}

.tag-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1.15rem;
  min-height: 0;
}

.tag-form__grid {
  display: grid;
  grid-template-columns: minmax(0, 0.92fr) minmax(0, 1.08fr);
  gap: 1rem;
  min-height: 0;
}

.tag-form__column {
  min-height: 0;
}

.tag-form__column--fields,
.tag-form__column--design {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

.tag-form__field {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.tag-form__field--grow {
  flex: 1;
}

.tag-form__label,
.tag-form__panel-label,
.tag-form__target-label {
  color: #334155;
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.tag-form__input,
.tag-form__textarea,
.tag-form__select {
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.34);
  border-radius: 16px;
  padding: 0.84rem 0.95rem;
  background: rgba(255, 255, 255, 0.92);
  color: #0f172a;
  font-size: 0.9rem;
}

.tag-form__input--readonly {
  background: rgba(241, 245, 249, 0.92);
  color: #475569;
}

.tag-form__textarea {
  min-height: 170px;
  resize: vertical;
}

.tag-form__bubble,
.tag-form__hint,
.tag-form__feedback {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  max-width: 100%;
  border-radius: 999px;
  padding: 0.34rem 0.7rem;
  font-size: 0.74rem;
  font-weight: 700;
}

.tag-form__bubble,
.tag-form__hint--error,
.tag-form__feedback--error {
  background: rgba(254, 226, 226, 0.92);
  color: #991b1b;
}

.tag-form__hint {
  background: rgba(241, 245, 249, 0.92);
  color: #475569;
}

.tag-form__panel {
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 24px;
  padding: 0.95rem;
  background: rgba(248, 250, 252, 0.78);
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

.tag-form__panel-head {
  display: flex;
  justify-content: space-between;
  gap: 0.8rem;
  align-items: center;
}

.tag-form__panel-note {
  color: #64748b;
  font-size: 0.76rem;
}

.tag-form__preview-card {
  min-height: 96px;
  border-radius: 22px;
  border: 1px dashed rgba(148, 163, 184, 0.4);
  background:
    radial-gradient(circle at center, rgba(255, 255, 255, 0.95), rgba(241, 245, 249, 0.92));
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.tag-form__target-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem;
}

.tag-form__target {
  border: 1px solid rgba(203, 213, 225, 0.9);
  border-radius: 18px;
  padding: 0.8rem 0.9rem;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  text-align: left;
  cursor: pointer;
  transition: border-color 150ms ease, box-shadow 150ms ease, transform 150ms ease;
}

.tag-form__target:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(100, 116, 139, 0.45);
}

.tag-form__target--active {
  border-color: rgba(15, 23, 42, 0.88);
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.08);
}

.tag-form__target-meta {
  display: flex;
  flex-direction: column;
  gap: 0.28rem;
}

.tag-form__target-value {
  color: #0f172a;
  font-size: 0.8rem;
}

.tag-form__target-swatch {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  border: 2px solid rgba(15, 23, 42, 0.12);
  flex: 0 0 auto;
}

.tag-form__target-swatch--checker {
  background-image:
    linear-gradient(45deg, rgba(148, 163, 184, 0.16) 25%, transparent 25%, transparent 50%, rgba(148, 163, 184, 0.16) 50%, rgba(148, 163, 184, 0.16) 75%, transparent 75%, transparent 100%);
  background-size: 10px 10px;
}

.tag-form__preset-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.48rem;
}

.tag-form__preset {
  border: 0;
  background: transparent;
  padding: 0;
  cursor: pointer;
}

.tag-form__preset-pill {
  display: inline-flex;
  width: 34px;
  height: 22px;
  border-radius: 999px;
  border: 2px solid var(--preset-border, #334155);
  background: var(--preset-background, rgba(51, 65, 85, 0.4));
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.45);
}

.tag-form__sync-btn {
  border: 0;
  border-radius: 999px;
  padding: 0.4rem 0.74rem;
  background: rgba(226, 232, 240, 0.92);
  color: #334155;
  font-size: 0.74rem;
  font-weight: 700;
  cursor: pointer;
}

.tag-form__footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.7rem;
}

.tag-form__btn {
  border: 0;
  border-radius: 16px;
  padding: 0.84rem 1.14rem;
  font-size: 0.84rem;
  font-weight: 800;
  cursor: pointer;
}

.tag-form__btn--ghost {
  background: rgba(226, 232, 240, 0.88);
  color: #334155;
}

.tag-form__btn--accent {
  background: linear-gradient(135deg, #0f172a, #334155);
  color: #fff;
}

.tag-form-dialog__close:disabled,
.tag-form__btn:disabled,
.tag-form__sync-btn:disabled,
.tag-form__target:disabled,
.tag-form__preset:disabled,
.tag-form__input:disabled,
.tag-form__textarea:disabled,
.tag-form__select:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.tag-form-fade-enter-active,
.tag-form-fade-leave-active {
  transition: opacity 180ms ease;
}

.tag-form-fade-enter-from,
.tag-form-fade-leave-to {
  opacity: 0;
}

@media (max-width: 900px) {
  .tag-form-dialog {
    width: min(96vw, 760px);
  }

  .tag-form__grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .tag-form-dialog {
    padding: 1rem;
    border-radius: 24px;
  }

  .tag-form__target-list {
    grid-template-columns: 1fr;
  }

  .tag-form__panel-head,
  .tag-form__footer {
    flex-direction: column;
    align-items: stretch;
  }

  .tag-form__btn,
  .tag-form__sync-btn {
    width: 100%;
  }
}
</style>