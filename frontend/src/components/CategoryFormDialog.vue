<template>
  <Teleport to="body">
    <Transition name="category-form-fade">
      <div v-if="visible" class="category-form-mask" @click.self="$emit('close')">
        <section class="category-form-dialog" role="dialog" aria-modal="true" :aria-label="dialogTitle">
          <header class="category-form-dialog__header">
            <div>
              <h3 class="category-form-dialog__title">{{ dialogTitle }}</h3>
              <p class="category-form-dialog__subtitle">标准名用于系统内部引用，显示名用于界面展示。</p>
            </div>
            <button class="category-form-dialog__close" type="button" @click="$emit('close')">关闭</button>
          </header>

          <form class="category-form" @submit.prevent="submitForm">
            <label class="category-form__field">
              <span class="category-form__label">标准名</span>
              <input
                v-model.trim="form.name"
                class="category-form__input"
                type="text"
                autocomplete="off"
                spellcheck="false"
                placeholder="例如 portrait_people"
              >
              <span v-if="nameEmpty" class="category-form__bubble">标准名不能为空</span>
              <span v-else-if="namePatternInvalid" class="category-form__hint category-form__hint--error">仅支持小写字母、数字和下划线</span>
              <span v-else-if="nameDuplicated" class="category-form__hint category-form__hint--error">该标准名已存在</span>
              <span v-else class="category-form__hint">将自动生成 public_id，例如 category_12</span>
            </label>

            <label class="category-form__field">
              <span class="category-form__label">显示名</span>
              <input
                v-model.trim="form.display_name"
                class="category-form__input"
                type="text"
                autocomplete="off"
                placeholder="例如 人像"
              >
            </label>

            <label class="category-form__field">
              <span class="category-form__label">说明</span>
              <textarea
                v-model.trim="form.description"
                class="category-form__textarea"
                rows="4"
                placeholder="说明这个主分类希望归纳的内容范围"
              ></textarea>
            </label>

            <footer class="category-form__footer">
              <button class="category-form__btn category-form__btn--ghost" type="button" :disabled="saving" @click="$emit('close')">
                取消
              </button>
              <button class="category-form__btn category-form__btn--accent" type="submit" :disabled="saving || !canSubmit">
                {{ saving ? '保存中…' : submitLabel }}
              </button>
            </footer>
          </form>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script>
function createFormState(category = null) {
  return {
    name: category?.name || '',
    display_name: category?.display_name || '',
    description: category?.description || '',
  }
}

export default {
  name: 'CategoryFormDialog',
  props: {
    visible: { type: Boolean, default: false },
    saving: { type: Boolean, default: false },
    mode: { type: String, default: 'create' },
    initialCategory: { type: Object, default: null },
    existingNames: { type: Array, default: () => [] },
  },
  emits: ['close', 'submit'],
  data() {
    return {
      form: createFormState(this.initialCategory),
    }
  },
  computed: {
    dialogTitle() {
      return this.mode === 'edit' ? '编辑主分类' : '新建主分类'
    },
    submitLabel() {
      return this.mode === 'edit' ? '保存修改' : '创建主分类'
    },
    normalizedName() {
      return (this.form.name || '').trim()
    },
    normalizedDisplayName() {
      return (this.form.display_name || '').trim()
    },
    nameEmpty() {
      return this.normalizedName.length === 0
    },
    namePatternInvalid() {
      return !this.nameEmpty && !/^[a-z0-9_]+$/.test(this.normalizedName)
    },
    nameDuplicated() {
      if (this.nameEmpty || this.namePatternInvalid) return false
      const source = Array.isArray(this.existingNames) ? this.existingNames : []
      return source.includes(this.normalizedName) && this.normalizedName !== (this.initialCategory?.name || '')
    },
    canSubmit() {
      return Boolean(this.normalizedDisplayName) && !this.nameEmpty && !this.namePatternInvalid && !this.nameDuplicated
    },
  },
  watch: {
    visible(nextValue) {
      if (nextValue) {
        this.form = createFormState(this.initialCategory)
      }
    },
    initialCategory() {
      if (this.visible) {
        this.form = createFormState(this.initialCategory)
      }
    },
  },
  methods: {
    submitForm() {
      if (!this.canSubmit) return
      this.$emit('submit', {
        name: this.normalizedName,
        display_name: this.normalizedDisplayName,
        description: (this.form.description || '').trim(),
      })
    },
  },
}
</script>

<style scoped lang="css">
.category-form-mask {
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

.category-form-dialog {
  width: min(100%, 620px);
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 28px;
  padding: 1.2rem;
  background:
    radial-gradient(circle at top right, rgba(191, 219, 254, 0.9), transparent 36%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
  box-shadow: 0 30px 80px rgba(15, 23, 42, 0.24);
}

.category-form-dialog__header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.category-form-dialog__title {
  margin: 0;
  color: #0f172a;
  font-size: 1.08rem;
  font-weight: 800;
}

.category-form-dialog__subtitle {
  margin: 0.38rem 0 0;
  color: #64748b;
  font-size: 0.84rem;
  line-height: 1.6;
}

.category-form-dialog__close {
  border: 0;
  background: transparent;
  color: #64748b;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
}

.category-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1.2rem;
}

.category-form__field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.category-form__label {
  color: #334155;
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.category-form__input,
.category-form__textarea {
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.34);
  border-radius: 16px;
  padding: 0.86rem 0.95rem;
  background: rgba(255, 255, 255, 0.9);
  color: #0f172a;
  font-size: 0.9rem;
}

.category-form__textarea {
  resize: vertical;
  min-height: 126px;
}

.category-form__bubble,
.category-form__hint {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  max-width: 100%;
  border-radius: 999px;
  padding: 0.34rem 0.7rem;
  font-size: 0.74rem;
  font-weight: 700;
}

.category-form__bubble,
.category-form__hint--error {
  background: rgba(254, 226, 226, 0.92);
  color: #991b1b;
}

.category-form__hint {
  background: rgba(241, 245, 249, 0.92);
  color: #475569;
}

.category-form__footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.7rem;
  margin-top: 0.2rem;
}

.category-form__btn {
  border: 0;
  border-radius: 16px;
  padding: 0.82rem 1rem;
  font-size: 0.84rem;
  font-weight: 800;
  cursor: pointer;
  transition: transform 150ms ease, opacity 150ms ease;
}

.category-form__btn:hover {
  transform: translateY(-1px);
}

.category-form__btn--ghost {
  background: rgba(226, 232, 240, 0.88);
  color: #334155;
}

.category-form__btn--accent {
  background: linear-gradient(135deg, #0284c7, #0f766e);
  color: #fff;
  box-shadow: 0 14px 28px rgba(8, 145, 178, 0.22);
}

.category-form__btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
}

.category-form-fade-enter-active,
.category-form-fade-leave-active {
  transition: opacity 180ms ease;
}

.category-form-fade-enter-from,
.category-form-fade-leave-to {
  opacity: 0;
}

@media (max-width: 640px) {
  .category-form-dialog {
    padding: 1rem;
    border-radius: 24px;
  }

  .category-form__footer {
    flex-direction: column-reverse;
  }

  .category-form__btn {
    width: 100%;
  }
}
</style>