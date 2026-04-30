<template>
  <div
    v-if="visible"
    class="detail-layer"
    :style="layerStyle"
    @click.self="$emit('close')"
    @mousedown.middle.prevent.stop="$event.preventDefault()"
    @auxclick.prevent.stop="$event.preventDefault()"
  >
    <section
      class="detail-panel"
      :style="panelStyle"
      role="dialog"
      aria-modal="true"
      aria-label="所选项目详情"
      @mousedown.middle.prevent.stop="$event.preventDefault()"
      @auxclick.prevent.stop="$event.preventDefault()"
    >
      <button class="detail-panel__close" type="button" @click="$emit('close')">关闭</button>

      <div class="detail-panel__content">
        <div class="detail-panel__preview">
          <div v-if="isMulti" class="detail-preview-list">
            <article
              v-for="preview in previewItems"
              :key="preview.key"
              class="detail-preview-list__item"
            >
              <div
                class="detail-preview-list__thumb"
                :style="preview.aspectRatio ? { aspectRatio: preview.aspectRatio } : null"
              >
                <img
                  v-if="preview.previewUrl"
                  class="detail-preview-list__img"
                  :src="preview.previewUrl"
                  :alt="preview.name"
                  loading="lazy"
                  draggable="false"
                  @error="$emit('preview-error', preview)"
                />
                <div v-else class="detail-preview-list__skeleton">
                  <span class="detail-preview-list__skeleton-label">...</span>
                </div>
              </div>

              <div class="detail-preview-list__meta">
                <span class="detail-preview-list__name">{{ preview.name }}</span>
                <span class="detail-preview-list__type">
                  {{ preview.type === 'album' ? '相册' : '图片' }}
                </span>
              </div>
            </article>
          </div>

          <div v-else class="detail-preview-stage">
            <img
              v-if="primaryPreview && primaryPreview.previewUrl"
              class="detail-preview-stage__img"
              :src="primaryPreview.previewUrl"
              :alt="primaryPreview.name"
              :style="primaryPreview.aspectRatio ? { aspectRatio: primaryPreview.aspectRatio } : null"
              draggable="false"
              @error="$emit('preview-error', primaryPreview)"
            />
            <div v-else class="detail-preview-stage__skeleton">
              <span class="detail-preview-stage__skeleton-label">
                {{ primaryPreview ? primaryPreview.name : '暂无预览' }}
              </span>
            </div>
          </div>
        </div>

        <div class="detail-panel__aside-shell">
          <div
            class="detail-panel__aside"
            :class="{ 'detail-panel__aside--scrolling': asideScrolling }"
            @scroll.passive="onAsideScroll"
          >
            <p v-if="isMulti" class="detail-panel__summary">已选择 {{ previewItems.length }} 项</p>

            <div class="detail-field">
              <div class="detail-field__head">
                <span class="detail-field__label">名称</span>
              </div>
              <div class="detail-field__value">
                <div v-if="editingField === 'name'" class="detail-inline-editor">
                  <input
                      ref="nameEditorInput"
                      v-model="nameDraft"
                    class="detail-inline-editor__input"
                    type="text"
                    autocomplete="off"
                    spellcheck="false"
                    :disabled="editBusy"
                      @blur="onNameEditBlur"
                      @keydown.enter.prevent="handleNameEditCommitKey"
                    @keydown.esc.prevent="cancelNameEdit"
                  >
                </div>
                <template v-else>
                    <div class="detail-field__display detail-field__display--editable">
                      <em v-if="nameField.isVarious" class="detail-field__various detail-field__various--inline">various</em>
                      <span v-else class="detail-field__text detail-field__text--inline">{{ nameField.text || '—' }}</span>
                      <button
                        v-if="showCategoryField && resolvedCanEditName"
                        class="detail-field__icon-btn"
                        type="button"
                        title="编辑文件名"
                        aria-label="编辑文件名"
                        :disabled="editBusy"
                        @click="startNameEdit"
                      >✎</button>
                    </div>
                </template>
              </div>
            </div>

            <div v-if="showCategoryField" class="detail-field">
              <div class="detail-field__head">
                <span class="detail-field__label">主分类</span>
              </div>
              <div class="detail-field__value">
                <div v-if="editingField === 'category'" class="detail-inline-editor">
                  <select
                    ref="categoryEditorSelect"
                    v-model="categoryDraft"
                    class="detail-inline-editor__input detail-inline-editor__select"
                    :disabled="editBusy"
                    @blur="onCategoryEditBlur"
                    @keydown.enter.prevent="handleCategoryEditCommitKey"
                    @keydown.esc.prevent="cancelCategoryEdit"
                  >
                    <option v-for="option in categoryOptions" :key="option.value" :value="String(option.value)">{{ option.label }}</option>
                  </select>
                </div>
                <template v-else>
                  <div class="detail-field__display detail-field__display--editable">
                    <em v-if="categoryField.isVarious" class="detail-field__various detail-field__various--inline">various</em>
                    <span v-else class="detail-field__text detail-field__text--inline">{{ categoryField.text || '—' }}</span>
                    <button
                      v-if="resolvedCanEditCategory"
                      class="detail-field__icon-btn"
                      type="button"
                      title="编辑主分类"
                      aria-label="编辑主分类"
                      :disabled="editBusy"
                      @click="startCategoryEdit"
                    >✎</button>
                  </div>
                </template>
              </div>
            </div>

            <div class="detail-field detail-field--tags">
              <span class="detail-field__label">标签</span>
              <div class="detail-field__tag-row detail-field__tag-row--single">
                <div class="detail-field__value detail-field__value--tags">
                  <div class="detail-field__tag-stack">
                    <em v-if="tagsField.isVarious" class="detail-field__various">various</em>
                    <span v-else-if="tagsField.isEmpty" class="detail-field__text">无标签</span>
                    <span
                      v-else-if="tagsField.text && !(Array.isArray(tagsField.items) && tagsField.items.length)"
                      class="detail-field__text"
                    >{{ tagsField.text }}</span>
                    <TagChipList
                      :tags="Array.isArray(tagsField.items) ? tagsField.items : []"
                      :compact="true"
                      :show-add-button="resolvedCanEditTags"
                      :add-disabled="tagMenuDisabled"
                      @add-click="$emit('open-tag-menu')"
                    />
                  </div>
                </div>
              </div>
            </div>

            <div class="detail-field">
              <span class="detail-field__label">{{ sizeLabel }}</span>
              <div class="detail-field__value">
                <em v-if="sizeField.isVarious" class="detail-field__various">various</em>
                <span v-else class="detail-field__text">{{ sizeField.text || '—' }}</span>
              </div>
            </div>

            <div class="detail-field">
              <span class="detail-field__label">导入时间</span>
              <div class="detail-field__value">
                <em v-if="importedField.isVarious" class="detail-field__various">various</em>
                <span v-else class="detail-field__text">{{ importedField.text || '—' }}</span>
              </div>
            </div>

            <div class="detail-field">
              <div class="detail-field__head">
                <span class="detail-field__label">创建时间</span>
              </div>
              <div class="detail-field__value">
                <div class="detail-field__display detail-field__display--editable">
                  <em v-if="createdField.isVarious" class="detail-field__various detail-field__various--inline">various</em>
                  <span v-else class="detail-field__text detail-field__text--inline">{{ createdField.text || '—' }}</span>
                  <button
                    v-if="showCategoryField && resolvedCanEditCreatedAt"
                    class="detail-field__icon-btn"
                    type="button"
                    title="编辑创建时间"
                    aria-label="编辑创建时间"
                    :disabled="editBusy"
                    @click="openCreatedEdit"
                  >✎</button>
                </div>
              </div>
            </div>
          </div>

          <div class="detail-panel__actions">
            <button
              class="detail-panel__action"
              :class="primaryActionToneClass"
              type="button"
              :disabled="!canOpenPrimaryAction || primaryActionDisabled"
              @click="$emit('open-primary')"
            >
              {{ primaryActionLabel }}
            </button>
            <button
              class="detail-panel__action"
              :class="secondaryActionToneClass"
              type="button"
              :disabled="secondaryActionDisabledResolved"
              @click="emitSecondaryAction"
            >
              {{ secondaryActionLabelResolved }}
            </button>
            <button
              v-if="canOpenCollectionMenu"
              class="detail-panel__icon-action"
              type="button"
              title="收藏"
              aria-label="收藏"
              :disabled="collectionMenuDisabled"
              @click="$emit('open-collection-menu')"
            >
              <svg class="detail-panel__icon-action-svg" width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M12 3.5L14.74 9.05L20.87 9.95L16.44 14.27L17.49 20.38L12 17.49L6.51 20.38L7.56 14.27L3.13 9.95L9.26 9.05L12 3.5Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </section>
  </div>

  <Teleport to="body">
    <Transition name="detail-subdialog-fade">
      <div v-if="visible && createdDialogVisible" class="detail-subdialog" @click.self="closeCreatedEdit">
        <section class="detail-subdialog__panel" role="dialog" aria-modal="true" aria-label="编辑创建时间">
          <header class="detail-subdialog__header">
            <div>
              <h3 class="detail-subdialog__title">修改创建时间</h3>
              <p class="detail-subdialog__subtitle">
                {{ isMulti ? `将应用到已选 ${previewItems.length} 张图片` : '修改后会同步回写文件系统创建时间。' }}
              </p>
            </div>
            <button class="detail-subdialog__close" type="button" :disabled="editBusy" @click="closeCreatedEdit">关闭</button>
          </header>

          <div class="detail-subdialog__grid">
            <label class="detail-subdialog__field">
              <span class="detail-subdialog__label">日期</span>
              <input v-model="createdDateDraft" class="detail-subdialog__input" type="date" :disabled="editBusy">
            </label>
            <label class="detail-subdialog__field">
              <span class="detail-subdialog__label">时间</span>
              <input v-model="createdTimeDraft" class="detail-subdialog__input" type="time" step="1" :disabled="editBusy">
            </label>
          </div>

          <p class="detail-subdialog__hint">当前文件夹：{{ currentDateGroup || '未分组' }}</p>
          <p v-if="createdMoveWarning" class="detail-subdialog__warning">{{ createdMoveWarning }}</p>

          <footer class="detail-subdialog__actions">
            <button class="detail-subdialog__btn detail-subdialog__btn--ghost" type="button" :disabled="editBusy" @click="closeCreatedEdit">取消</button>
            <button
              class="detail-subdialog__btn detail-subdialog__btn--primary"
              type="button"
              :disabled="editBusy || !createdDateDraft || !createdTimeDraft"
              @click="submitCreatedEdit"
            >{{ editBusy ? '保存中…' : createdConfirmLabel }}</button>
          </footer>
        </section>
      </div>
    </Transition>
  </Teleport>

  <ConfirmationDialog
    :visible="inlineConfirm.visible"
    title="确认更改"
    :message="inlineConfirmMessage"
    confirm-label="确认更改"
    cancel-label="取消"
    tone="accent"
    :busy="editBusy"
    busy-label="保存中…"
    @cancel="handleInlineConfirmCancel"
    @confirm="handleInlineConfirmSubmit"
  />
</template>

<script>
import TagChipList from './TagChipList.vue'
import ConfirmationDialog from './ConfirmationDialog.vue'

function padDatePart(value) {
  return String(value).padStart(2, '0')
}

function splitDateTimeParts(rawValue) {
  const parsed = rawValue ? new Date(rawValue) : new Date()
  const safeDate = Number.isNaN(parsed.getTime()) ? new Date() : parsed
  return {
    date: `${safeDate.getFullYear()}-${padDatePart(safeDate.getMonth() + 1)}-${padDatePart(safeDate.getDate())}`,
    time: `${padDatePart(safeDate.getHours())}:${padDatePart(safeDate.getMinutes())}:${padDatePart(safeDate.getSeconds())}`,
  }
}

function createInlineConfirmState() {
  return {
    visible: false,
    field: '',
    nextValue: '',
  }
}

export default {
  name: 'SelectionDetailOverlay',
  components: {
    TagChipList,
    ConfirmationDialog,
  },
  props: {
    visible: { type: Boolean, default: false },
    layerStyle: { type: Object, default: () => ({}) },
    panelStyle: { type: Object, default: () => ({}) },
    previewItems: { type: Array, default: () => [] },
    isMulti: { type: Boolean, default: false },
    nameField: {
      type: Object,
      default: () => ({ text: '', isVarious: false, isEmpty: false }),
    },
    categoryField: {
      type: Object,
      default: () => ({ text: '', isVarious: false, isEmpty: false }),
    },
    tagsField: {
      type: Object,
      default: () => ({ text: '', isVarious: false, isEmpty: true, items: [] }),
    },
    sizeField: {
      type: Object,
      default: () => ({ text: '', isVarious: false, isEmpty: false }),
    },
    sizeLabel: { type: String, default: '尺寸' },
    importedField: {
      type: Object,
      default: () => ({ text: '', isVarious: false, isEmpty: false }),
    },
    createdField: {
      type: Object,
      default: () => ({ text: '', isVarious: false, isEmpty: false }),
    },
    rawName: { type: String, default: '' },
    rawCategoryId: { type: Number, default: null },
    rawCreatedAt: {
      type: [String, Number, Date],
      default: null,
    },
    primaryActionLabel: { type: String, default: '查看原图' },
    primaryActionTone: { type: String, default: 'accent' },
    canOpenPrimaryAction: { type: Boolean, default: false },
    primaryActionDisabled: { type: Boolean, default: false },
    dangerActionLabel: { type: String, default: '删除' },
    dangerActionDisabled: { type: Boolean, default: false },
    secondaryActionLabel: { type: String, default: '' },
    secondaryActionTone: { type: String, default: '' },
    secondaryActionDisabled: { type: Boolean, default: null },
    canEditTags: { type: Boolean, default: false },
    canOpenCollectionMenu: { type: Boolean, default: false },
    collectionMenuDisabled: { type: Boolean, default: false },
    tagMenuDisabled: { type: Boolean, default: false },
    canEditName: { type: Boolean, default: false },
    canEditCategory: { type: Boolean, default: false },
    canEditCreatedAt: { type: Boolean, default: false },
    metadataPermissions: {
      type: Object,
      default: () => ({}),
    },
    editBusy: { type: Boolean, default: false },
    currentDateGroup: { type: String, default: '' },
    categoryOptions: { type: Array, default: () => [] },
  },
  emits: [
    'close',
    'delete',
    'open-primary',
    'open-collection-menu',
    'open-tag-menu',
    'preview-error',
    'secondary-action',
    'submit-name-edit',
    'submit-category-edit',
    'submit-created-edit',
  ],
  data() {
    const createdParts = splitDateTimeParts(this.rawCreatedAt)
    return {
      asideScrolling: false,
      asideScrollTimer: null,
      editingField: '',
      nameDraft: this.rawName || '',
      categoryDraft: this.rawCategoryId != null ? String(this.rawCategoryId) : '',
      inlineConfirm: createInlineConfirmState(),
      createdDialogVisible: false,
      createdDateDraft: createdParts.date,
      createdTimeDraft: createdParts.time,
    }
  },
  computed: {
    primaryPreview() {
      return this.previewItems[0] || null
    },
    showCategoryField() {
      return this.previewItems.some(item => item?.type === 'image')
    },
    createdTargetDateGroup() {
      if (!this.createdDateDraft || this.createdDateDraft.length < 7) return ''
      return this.createdDateDraft.slice(0, 7)
    },
    createdMoveWarning() {
      if (!this.currentDateGroup || !this.createdTargetDateGroup) return ''
      if (this.createdTargetDateGroup === this.currentDateGroup) return ''
      return `文件将移动到 ${this.createdTargetDateGroup} 文件夹，并同步修改系统创建时间。`
    },
    createdConfirmLabel() {
      return this.createdMoveWarning ? '确认并移动' : '确认修改'
    },
    inlineConfirmMessage() {
      if (this.inlineConfirm.field === 'name') {
        return '文件名已改变，是否确认更改？'
      }
      if (this.inlineConfirm.field === 'category') {
        return '主分类已改变，是否确认更改？'
      }
      return ''
    },
    resolvedCanEditName() {
      if (typeof this.metadataPermissions?.name === 'boolean') {
        return this.metadataPermissions.name
      }
      return this.canEditName
    },
    resolvedCanEditCategory() {
      if (typeof this.metadataPermissions?.category === 'boolean') {
        return this.metadataPermissions.category
      }
      return this.canEditCategory
    },
    resolvedCanEditTags() {
      if (typeof this.metadataPermissions?.tags === 'boolean') {
        return this.metadataPermissions.tags
      }
      return this.canEditTags
    },
    resolvedCanEditCreatedAt() {
      if (typeof this.metadataPermissions?.createdAt === 'boolean') {
        return this.metadataPermissions.createdAt
      }
      return this.canEditCreatedAt
    },
    secondaryActionLabelResolved() {
      return this.secondaryActionLabel || this.dangerActionLabel
    },
    secondaryActionDisabledResolved() {
      if (typeof this.secondaryActionDisabled === 'boolean') {
        return this.secondaryActionDisabled
      }
      return this.dangerActionDisabled
    },
    primaryActionToneClass() {
      return this.actionToneClass(this.primaryActionTone)
    },
    secondaryActionToneClass() {
      return this.actionToneClass(this.secondaryActionTone || 'danger')
    },
  },
  watch: {
    visible(nextVisible) {
      if (!nextVisible) {
        this.clearAsideScrollState()
        this.resetEditState()
      }
    },
    rawName(nextValue) {
      if (this.editingField !== 'name') {
        this.nameDraft = nextValue || ''
      }
    },
    rawCategoryId(nextValue) {
      if (this.editingField !== 'category') {
        this.categoryDraft = nextValue != null ? String(nextValue) : ''
      }
    },
    rawCreatedAt() {
      if (!this.createdDialogVisible) {
        this.seedCreatedDrafts()
      }
    },
  },
  beforeUnmount() {
    this.clearAsideScrollState()
  },
  methods: {
    actionToneClass(tone) {
      switch (tone) {
        case 'danger':
          return 'detail-panel__action--danger'
        case 'neutral':
          return 'detail-panel__action--neutral'
        case 'ghost':
          return 'detail-panel__action--ghost'
        case 'accent':
        default:
          return 'detail-panel__action--accent'
      }
    },
    hasListener(eventName) {
      const vnodeProps = this.$?.vnode?.props || {}
      const propName = `on${String(eventName)
        .split('-')
        .map(segment => segment ? `${segment[0].toUpperCase()}${segment.slice(1)}` : '')
        .join('')}`
      const handler = vnodeProps[propName]
      return typeof handler === 'function' || Array.isArray(handler)
    },
    emitSecondaryAction() {
      if (this.hasListener('secondary-action')) {
        this.$emit('secondary-action')
        return
      }
      this.$emit('delete')
    },
    resetEditState() {
      this.editingField = ''
      this.inlineConfirm = createInlineConfirmState()
      this.createdDialogVisible = false
      this.nameDraft = this.rawName || ''
      this.categoryDraft = this.rawCategoryId != null ? String(this.rawCategoryId) : ''
      this.seedCreatedDrafts()
    },
    focusEditor(refName, shouldSelect = false) {
      const editor = this.$refs[refName]
      if (!editor || typeof editor.focus !== 'function') return
      editor.focus()
      if (shouldSelect && typeof editor.select === 'function') {
        editor.select()
      }
    },
    seedCreatedDrafts() {
      const parts = splitDateTimeParts(this.rawCreatedAt)
      this.createdDateDraft = parts.date
      this.createdTimeDraft = parts.time
    },
    onAsideScroll() {
      this.asideScrolling = true
      if (this.asideScrollTimer) {
        clearTimeout(this.asideScrollTimer)
      }
      this.asideScrollTimer = setTimeout(() => {
        this.asideScrollTimer = null
        this.asideScrolling = false
      }, 620)
    },
    clearAsideScrollState() {
      this.asideScrolling = false
      if (!this.asideScrollTimer) return
      clearTimeout(this.asideScrollTimer)
      this.asideScrollTimer = null
    },
    startNameEdit() {
      if (!this.resolvedCanEditName || this.editBusy || this.inlineConfirm.visible) return
      if (this.editingField && this.editingField !== 'name') return
      this.editingField = 'name'
      this.nameDraft = this.rawName || ''
      this.$nextTick(() => {
        this.focusEditor('nameEditorInput', true)
      })
    },
    cancelNameEdit() {
      if (this.editBusy) return
      this.editingField = ''
      this.nameDraft = this.rawName || ''
      if (this.inlineConfirm.field === 'name') {
        this.inlineConfirm = createInlineConfirmState()
      }
    },
    requestNameEditConfirmation() {
      if (!this.resolvedCanEditName || this.editBusy) return
      const nextName = String(this.nameDraft || '').trim()
      const currentName = String(this.rawName || '').trim()
      if (!nextName || nextName === currentName) {
        this.cancelNameEdit()
        return
      }
      this.inlineConfirm = {
        visible: true,
        field: 'name',
        nextValue: nextName,
      }
    },
    onNameEditBlur() {
      if (this.editingField !== 'name' || this.inlineConfirm.visible) return
      this.requestNameEditConfirmation()
    },
    handleNameEditCommitKey() {
      const input = this.$refs.nameEditorInput
      if (input && typeof input.blur === 'function') {
        input.blur()
        return
      }
      this.requestNameEditConfirmation()
    },
    startCategoryEdit() {
      if (!this.resolvedCanEditCategory || this.editBusy || this.inlineConfirm.visible) return
      if (this.editingField && this.editingField !== 'category') return
      this.editingField = 'category'
      if (this.rawCategoryId != null) {
        this.categoryDraft = String(this.rawCategoryId)
      } else {
        this.categoryDraft = this.categoryOptions[0] ? String(this.categoryOptions[0].value) : ''
      }
      this.$nextTick(() => {
        this.focusEditor('categoryEditorSelect')
      })
    },
    cancelCategoryEdit() {
      if (this.editBusy) return
      this.editingField = ''
      this.categoryDraft = this.rawCategoryId != null ? String(this.rawCategoryId) : ''
      if (this.inlineConfirm.field === 'category') {
        this.inlineConfirm = createInlineConfirmState()
      }
    },
    requestCategoryEditConfirmation() {
      if (!this.resolvedCanEditCategory || this.editBusy) return
      const nextCategoryId = String(this.categoryDraft || '')
      const currentCategoryId = this.rawCategoryId != null ? String(this.rawCategoryId) : ''
      if (!nextCategoryId || nextCategoryId === currentCategoryId) {
        this.cancelCategoryEdit()
        return
      }
      this.inlineConfirm = {
        visible: true,
        field: 'category',
        nextValue: nextCategoryId,
      }
    },
    onCategoryEditBlur() {
      if (this.editingField !== 'category' || this.inlineConfirm.visible) return
      this.requestCategoryEditConfirmation()
    },
    handleCategoryEditCommitKey() {
      const select = this.$refs.categoryEditorSelect
      if (select && typeof select.blur === 'function') {
        select.blur()
        return
      }
      this.requestCategoryEditConfirmation()
    },
    handleInlineConfirmCancel() {
      if (this.editBusy) return
      if (this.inlineConfirm.field === 'name') {
        this.cancelNameEdit()
        return
      }
      if (this.inlineConfirm.field === 'category') {
        this.cancelCategoryEdit()
        return
      }
      this.inlineConfirm = createInlineConfirmState()
    },
    handleInlineConfirmSubmit() {
      if (this.editBusy || !this.inlineConfirm.visible) return
      if (this.inlineConfirm.field === 'name') {
        const nextName = String(this.inlineConfirm.nextValue || '').trim()
        if (!nextName) {
          this.cancelNameEdit()
          return
        }
        this.editingField = ''
        this.nameDraft = nextName
        this.inlineConfirm = createInlineConfirmState()
        this.$emit('submit-name-edit', nextName)
        return
      }

      if (this.inlineConfirm.field === 'category') {
        const categoryId = Number(this.inlineConfirm.nextValue)
        if (!Number.isInteger(categoryId) || categoryId <= 0) {
          this.cancelCategoryEdit()
          return
        }
        this.editingField = ''
        this.categoryDraft = String(categoryId)
        this.inlineConfirm = createInlineConfirmState()
        this.$emit('submit-category-edit', categoryId)
      }
    },
    openCreatedEdit() {
      if (!this.resolvedCanEditCreatedAt || this.editBusy || this.inlineConfirm.visible || this.editingField) return
      this.seedCreatedDrafts()
      this.createdDialogVisible = true
    },
    closeCreatedEdit() {
      if (this.editBusy) return
      this.createdDialogVisible = false
      this.seedCreatedDrafts()
    },
    submitCreatedEdit() {
      if (!this.resolvedCanEditCreatedAt || this.editBusy) return
      if (!this.createdDateDraft || !this.createdTimeDraft) return
      const normalizedTime = this.createdTimeDraft.length === 5
        ? `${this.createdTimeDraft}:00`
        : this.createdTimeDraft
      this.createdDialogVisible = false
      this.$emit('submit-created-edit', `${this.createdDateDraft}T${normalizedTime}`)
    },
  },
}
</script>

<style scoped lang="css">
.detail-layer {
  position: fixed;
  z-index: 70;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(1rem, 2vw, 1.8rem);
  background: rgba(241, 245, 249, 0.72);
  backdrop-filter: blur(12px);
}

.detail-panel {
  position: relative;
  width: min(1100px, 80%);
  max-width: calc(100% - 12px);
  max-height: calc(100% - 12px);
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 32px 72px rgba(15, 23, 42, 0.18);
  overflow: hidden;
}

.detail-panel__close {
  position: absolute;
  top: 1rem;
  right: 1rem;
  z-index: 2;
  border: 0;
  background: transparent;
  color: #64748b;
  font-size: 0.86rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  cursor: pointer;
  transition: color 140ms ease, opacity 140ms ease;
}

.detail-panel__close:hover {
  color: #0f172a;
}

.detail-panel__content {
  display: grid;
  grid-template-columns: minmax(0, 1.58fr) minmax(320px, 1fr);
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.detail-panel__preview {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  padding: clamp(1.1rem, 2.2vw, 1.8rem);
  background:
    radial-gradient(circle at top left, rgba(226, 232, 240, 0.95), rgba(248, 250, 252, 0.72) 50%),
    linear-gradient(180deg, rgba(241, 245, 249, 0.86), rgba(255, 255, 255, 0.78));
}

.detail-preview-stage,
.detail-preview-stage__skeleton {
  width: 100%;
  height: 100%;
  min-height: 0;
  border-radius: 24px;
}

.detail-preview-stage {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(0.6rem, 1.5vw, 1rem);
  overflow: hidden;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.8);
}

.detail-preview-stage__img {
  width: auto;
  height: auto;
  max-width: 100%;
  max-height: 100%;
  display: block;
  object-fit: contain;
  border-radius: 20px;
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.08);
}

.detail-preview-stage__skeleton,
.detail-preview-list__skeleton {
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(90deg, #e2e8f0 25%, #f8fafc 50%, #e2e8f0 75%);
  background-size: 200% 100%;
  animation: detail-wave 1.4s ease-in-out infinite;
}

.detail-preview-stage__skeleton-label,
.detail-preview-list__skeleton-label {
  color: #94a3b8;
  font-size: 0.88rem;
  letter-spacing: 0.08em;
}

.detail-preview-list {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 0.9rem;
  height: 100%;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  touch-action: pan-y;
  padding-right: 0.2rem;
  padding-bottom: 0.4rem;
  scrollbar-width: none;
}

.detail-preview-list::-webkit-scrollbar {
  display: none;
}

.detail-preview-list__item {
  display: grid;
  grid-template-columns: minmax(96px, 132px) minmax(0, 1fr);
  gap: 0.9rem;
  align-items: center;
  padding: 0.7rem;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.76);
  box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.85);
}

.detail-preview-list__thumb {
  width: 100%;
  border-radius: 14px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.88);
  box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.92);
}

.detail-preview-list__img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
}

.detail-preview-list__meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.detail-preview-list__name {
  color: #0f172a;
  font-size: 0.92rem;
  font-weight: 700;
  line-height: 1.45;
  word-break: break-word;
}

.detail-preview-list__type {
  color: #64748b;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.detail-panel__aside-shell {
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  padding: clamp(1.35rem, 2.4vw, 2.1rem);
  border-left: 1px solid rgba(226, 232, 240, 0.9);
  overflow: hidden;
}

.detail-panel__aside {
  display: flex;
  flex-direction: column;
  gap: 1.15rem;
  min-height: 0;
  min-width: 0;
  flex: 1 1 auto;
  --detail-aside-scrollbar-width: 10px;
  --detail-aside-scrollbar-thumb: transparent;
  --detail-aside-scrollbar-border: transparent;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding-right: 0.85rem;
  scrollbar-gutter: stable;
  scrollbar-width: thin;
  scrollbar-color: transparent transparent;
}

.detail-panel__aside::-webkit-scrollbar {
  width: var(--detail-aside-scrollbar-width);
  height: var(--detail-aside-scrollbar-width);
}

.detail-panel__aside::-webkit-scrollbar-track {
  background: transparent;
}

.detail-panel__aside::-webkit-scrollbar-thumb {
  border-radius: 999px;
  border: 2px solid var(--detail-aside-scrollbar-border);
  background: var(--detail-aside-scrollbar-thumb);
  background-clip: padding-box;
}

.detail-panel__aside--scrolling {
  scrollbar-color: rgba(203, 213, 225, 0.92) transparent;
  --detail-aside-scrollbar-thumb: rgba(203, 213, 225, 0.96);
  --detail-aside-scrollbar-border: rgba(255, 255, 255, 0.92);
}

.detail-panel__aside--scrolling::-webkit-scrollbar-thumb {
  background: var(--detail-aside-scrollbar-thumb);
}

.detail-panel__aside > :last-child {
  padding-bottom: 0.1rem;
}

.detail-panel__summary {
  color: #475569;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.detail-field {
  display: flex;
  flex-direction: column;
  gap: 0.42rem;
}

.detail-field__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.detail-field__label {
  color: #64748b;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.detail-field__edit {
  border: 0;
  padding: 0;
  background: transparent;
  color: #2563eb;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
  transition: color 140ms ease, opacity 140ms ease;
}

.detail-field__edit:hover:not(:disabled) {
  color: #1d4ed8;
}

.detail-field__edit:disabled {
  color: #94a3b8;
  opacity: 0.6;
  cursor: not-allowed;
}

.detail-field__value {
  min-height: 2.4rem;
  display: flex;
  align-items: center;
  color: #0f172a;
  font-size: 0.95rem;
  line-height: 1.6;
  word-break: break-word;
}

.detail-field__value--tags {
  min-height: 3.4rem;
  align-items: flex-start;
}

.detail-field__tag-stack {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.detail-field__text {
  display: block;
  width: 100%;
}

.detail-field__display {
  width: 100%;
  min-width: 0;
  display: inline-flex;
  align-items: center;
  gap: 0.38rem;
}

.detail-field__display--editable {
  align-items: flex-start;
}

.detail-field__text--inline,
.detail-field__various--inline {
  flex: 1 1 auto;
  min-width: 0;
  width: auto;
}

.detail-field__icon-btn {
  width: 1.62rem;
  height: 1.62rem;
  flex: 0 0 auto;
  border: 1px solid rgba(148, 163, 184, 0.45);
  border-radius: 8px;
  padding: 0;
  background: #f8fafc;
  color: #334155;
  font-size: 0.84rem;
  font-weight: 700;
  line-height: 1;
  cursor: pointer;
  transition: background 140ms ease, border-color 140ms ease, color 140ms ease, opacity 140ms ease;
}

.detail-field__icon-btn:hover:not(:disabled) {
  background: #e2e8f0;
  border-color: rgba(100, 116, 139, 0.55);
  color: #0f172a;
}

.detail-field__icon-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.detail-inline-editor {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.28rem;
}

.detail-inline-editor__input {
  width: 100%;
  min-height: 2.16rem;
  border: 1px solid rgba(148, 163, 184, 0.32);
  border-radius: 10px;
  padding: 0.42rem 0.58rem;
  background: rgba(248, 250, 252, 0.96);
  color: #0f172a;
  font-size: 0.84rem;
  line-height: 1.4;
}

.detail-inline-editor__input:focus {
  outline: none;
  border-color: rgba(37, 99, 235, 0.46);
  box-shadow: 0 0 0 2px rgba(191, 219, 254, 0.72);
}

.detail-inline-editor__select {
  appearance: none;
}

.detail-field__placeholder {
  width: 100%;
  min-height: 3.4rem;
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.72), rgba(241, 245, 249, 0.88));
  box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.92);
}

.detail-field__various {
  color: #475569;
  font-style: italic;
}

.detail-field__tag-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.75rem;
  align-items: end;
}

.detail-field__tag-row--single {
  grid-template-columns: minmax(0, 1fr);
}

.detail-panel__actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 0.8rem;
  margin-top: 0.95rem;
  padding-top: 0.8rem;
  padding-bottom: 0.2rem;
  padding-right: 0.85rem;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0), rgba(255, 255, 255, 0.98) 38%);
}

.detail-panel__action {
  min-width: 112px;
  border: 1px solid rgba(148, 163, 184, 0.32);
  border-radius: 16px;
  padding: 0.72rem 1rem;
  font-size: 0.88rem;
  font-weight: 700;
  cursor: pointer;
  transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease, opacity 140ms ease;
}

.detail-panel__action:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(100, 116, 139, 0.36);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
}

.detail-panel__action:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  box-shadow: none;
}

.detail-panel__action--accent {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  border-color: rgba(37, 99, 235, 0.25);
  color: #ffffff;
  box-shadow: 0 16px 26px rgba(37, 99, 235, 0.22);
}

.detail-panel__action--accent:hover:not(:disabled) {
  border-color: rgba(29, 78, 216, 0.36);
  box-shadow: 0 18px 30px rgba(37, 99, 235, 0.28);
}

.detail-panel__action--danger {
  border-color: rgba(234, 88, 12, 0.22);
  background: rgba(255, 237, 213, 0.86);
  color: #b45309;
}

.detail-panel__action--danger:hover:not(:disabled) {
  border-color: rgba(234, 88, 12, 0.3);
}

.detail-panel__action--neutral {
  background: rgba(226, 232, 240, 0.92);
  border-color: rgba(148, 163, 184, 0.3);
  color: #0f172a;
}

.detail-panel__action--ghost {
  background: rgba(255, 255, 255, 0.76);
  border-color: rgba(148, 163, 184, 0.34);
  color: #334155;
}

.detail-panel__icon-action {
  width: 3.35rem;
  min-width: 3.35rem;
  height: 3.35rem;
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(148, 163, 184, 0.32);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.86);
  color: #475569;
  cursor: pointer;
  transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease, opacity 140ms ease, color 140ms ease;
}

.detail-panel__icon-action:hover:not(:disabled) {
  transform: translateY(-1px);
  color: #0f172a;
  border-color: rgba(100, 116, 139, 0.36);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
}

.detail-panel__icon-action:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.detail-panel__icon-action-svg {
  display: block;
}

.detail-subdialog {
  position: fixed;
  inset: 0;
  z-index: 82;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: rgba(15, 23, 42, 0.28);
  backdrop-filter: blur(6px);
}

.detail-subdialog__panel {
  width: min(100%, 460px);
  border: 1px solid rgba(203, 213, 225, 0.9);
  border-radius: 24px;
  padding: 1.1rem 1.1rem 1rem;
  background:
    radial-gradient(circle at top right, rgba(255, 255, 255, 0.98), transparent 42%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
  box-shadow: 0 24px 72px rgba(15, 23, 42, 0.24);
}

.detail-subdialog__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.detail-subdialog__title {
  margin: 0;
  color: #0f172a;
  font-size: 1rem;
  font-weight: 800;
}

.detail-subdialog__subtitle {
  margin: 0.4rem 0 0;
  color: #64748b;
  font-size: 0.84rem;
  line-height: 1.6;
}

.detail-subdialog__close {
  border: 0;
  background: transparent;
  color: #64748b;
  font-size: 0.84rem;
  font-weight: 700;
  cursor: pointer;
}

.detail-subdialog__grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  margin-top: 1rem;
}

.detail-subdialog__field {
  display: flex;
  flex-direction: column;
  gap: 0.42rem;
}

.detail-subdialog__label {
  color: #475569;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.detail-subdialog__input {
  width: 100%;
  min-height: 2.9rem;
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 14px;
  padding: 0.72rem 0.86rem;
  background: rgba(248, 250, 252, 0.96);
  color: #0f172a;
  font-size: 0.92rem;
}

.detail-subdialog__input:focus {
  outline: none;
  border-color: rgba(37, 99, 235, 0.46);
  box-shadow: 0 0 0 3px rgba(191, 219, 254, 0.7);
}

.detail-subdialog__hint {
  margin: 0.9rem 0 0;
  color: #64748b;
  font-size: 0.82rem;
}

.detail-subdialog__warning {
  margin: 0.75rem 0 0;
  border-radius: 16px;
  padding: 0.78rem 0.88rem;
  background: rgba(255, 237, 213, 0.9);
  color: #b45309;
  font-size: 0.84rem;
  line-height: 1.65;
}

.detail-subdialog__actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.65rem;
  margin-top: 1rem;
}

.detail-subdialog__btn {
  border: 0;
  border-radius: 14px;
  padding: 0.68rem 1rem;
  font-size: 0.84rem;
  font-weight: 800;
  cursor: pointer;
  transition: transform 160ms ease, opacity 160ms ease;
}

.detail-subdialog__btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.detail-subdialog__btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.detail-subdialog__btn--ghost {
  background: rgba(226, 232, 240, 0.82);
  color: #334155;
}

.detail-subdialog__btn--primary {
  background: linear-gradient(135deg, #2563eb, #0f766e);
  color: #fff;
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.22);
}

.detail-subdialog-fade-enter-active,
.detail-subdialog-fade-leave-active {
  transition: opacity 180ms ease;
}

.detail-subdialog-fade-enter-from,
.detail-subdialog-fade-leave-to {
  opacity: 0;
}

@keyframes detail-wave {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@media (max-width: 960px) {
  .detail-panel {
    width: calc(100% - 12px);
  }

  .detail-panel__content {
    grid-template-columns: 1fr;
    height: auto;
    overflow: visible;
  }

  .detail-panel__aside-shell {
    border-left: 0;
    border-top: 1px solid rgba(226, 232, 240, 0.9);
    padding-top: clamp(1.35rem, 2.4vw, 2.1rem);
    padding-right: clamp(1.35rem, 2.4vw, 2.1rem);
    padding-bottom: clamp(1.35rem, 2.4vw, 2.1rem);
    padding-left: clamp(1.35rem, 2.4vw, 2.1rem);
  }

  .detail-panel__aside {
    overflow-y: visible;
    padding-right: 0;
    scrollbar-gutter: auto;
  }

  .detail-panel__actions {
    margin-top: 1rem;
    padding-right: 0;
  }

  .detail-preview-stage,
  .detail-preview-stage__skeleton,
  .detail-preview-list {
    min-height: 260px;
  }
}

@media (max-width: 640px) {
  .detail-layer {
    padding: 0.6rem;
  }

  .detail-panel {
    border-radius: 22px;
  }

  .detail-preview-list__item {
    grid-template-columns: 92px minmax(0, 1fr);
  }

  .detail-inline-editor__actions,
  .detail-subdialog__actions,
  .detail-field__tag-row,
  .detail-panel__actions {
    grid-template-columns: 1fr;
    display: grid;
  }

  .detail-subdialog__grid {
    grid-template-columns: 1fr;
  }

  .detail-inline-editor__btn,
  .detail-subdialog__btn,
  .detail-panel__action,
  .detail-panel__icon-action {
    width: 100%;
  }
}
</style>