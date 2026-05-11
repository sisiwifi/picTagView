<template>
  <Teleport to="body">
    <Transition name="browse-filter-menu-fade">
      <div v-if="visible" class="browse-filter-menu__mask" @click.self="$emit('close')">
        <section
          class="browse-filter-menu"
          :style="panelStyle"
          role="dialog"
          aria-modal="true"
          aria-label="浏览筛选"
        >
          <header class="browse-filter-menu__header">
            <div>
              <h3 class="browse-filter-menu__title">筛选</h3>
              <p class="browse-filter-menu__subtitle">优先按标签筛选，再叠加文件名、类型、时间和大小条件。</p>
            </div>
            <button class="browse-filter-menu__close" type="button" @click="$emit('close')">关闭</button>
          </header>

          <div class="browse-filter-menu__body">
            <section class="browse-filter-menu__section browse-filter-menu__section--tags">
              <div class="browse-filter-menu__section-head">
                <div>
                  <h4 class="browse-filter-menu__section-title">标签</h4>
                  <p class="browse-filter-menu__section-subtitle">标签优先展示。可多选，命中任一标签即可。</p>
                </div>
                <button class="browse-filter-menu__clear-link" type="button" @click="clearTagSelection">清空</button>
              </div>

              <div class="browse-filter-menu__chip-toolbar">
                <button
                  class="browse-filter-menu__choice-chip"
                  :class="{ 'browse-filter-menu__choice-chip--active': allTagsSelected && tags.length }"
                  type="button"
                  @click="selectAllTags"
                >
                  全选
                </button>
                <button
                  class="browse-filter-menu__choice-chip"
                  :class="{ 'browse-filter-menu__choice-chip--active': localFilter.includeUntagged }"
                  type="button"
                  @click="toggleIncludeUntagged"
                >
                  无标签
                </button>
              </div>

              <div v-if="tags.length" class="browse-filter-menu__tag-list">
                <button
                  v-for="tag in tags"
                  :key="tag.id"
                  class="tag-chip tag-chip--interactive browse-filter-menu__tag-chip"
                  :class="{ 'browse-filter-menu__tag-chip--muted': !isTagSelected(tag.id) }"
                  :style="tagChipStyle(tag, isTagSelected(tag.id))"
                  :title="tag.description || ''"
                  type="button"
                  @click="toggleTag(tag.id)"
                >
                  {{ tag.display_name || tag.name || `#${tag.id}` }}
                </button>
              </div>
              <p v-else class="browse-filter-menu__empty">当前视图没有可用标签。</p>
            </section>

            <section class="browse-filter-menu__section">
              <div class="browse-filter-menu__section-head">
                <div>
                  <h4 class="browse-filter-menu__section-title">主分类</h4>
                  <p class="browse-filter-menu__section-subtitle">按当前页面出现过的主分类多选筛选。</p>
                </div>
                <button class="browse-filter-menu__clear-link" type="button" @click="toggleAllCategories">
                  {{ allCategoriesSelected && categories.length ? '取消全选' : '全选' }}
                </button>
              </div>

              <div v-if="categories.length" class="browse-filter-menu__choice-grid">
                <button
                  v-for="category in categories"
                  :key="category.id"
                  class="browse-filter-menu__choice-chip"
                  :class="{ 'browse-filter-menu__choice-chip--active': isCategorySelected(category.id) }"
                  type="button"
                  @click="toggleCategory(category.id)"
                >
                  {{ category.label }}
                </button>
              </div>
              <p v-else class="browse-filter-menu__empty">当前视图没有可用的主分类。</p>
            </section>

            <section class="browse-filter-menu__section">
              <div class="browse-filter-menu__section-head">
                <div>
                  <h4 class="browse-filter-menu__section-title">文件名</h4>
                  <p class="browse-filter-menu__section-subtitle">支持包含匹配或完整文件名精确匹配。</p>
                </div>
              </div>

              <div class="browse-filter-menu__field-row browse-filter-menu__field-row--stack-on-mobile">
                <label class="browse-filter-menu__field browse-filter-menu__field--compact">
                  <span class="browse-filter-menu__label">匹配方式</span>
                  <select v-model="localFilter.filenameMode" class="browse-filter-menu__select">
                    <option value="contains">包含</option>
                    <option value="exact">完全</option>
                  </select>
                </label>

                <label class="browse-filter-menu__field browse-filter-menu__field--grow">
                  <span class="browse-filter-menu__label">输入</span>
                  <input
                    v-model="localFilter.filenameQuery"
                    class="browse-filter-menu__input"
                    type="text"
                    maxlength="160"
                    placeholder="输入文件名或完整文件名"
                  >
                </label>
              </div>
            </section>

            <section class="browse-filter-menu__section">
              <div class="browse-filter-menu__section-head">
                <div>
                  <h4 class="browse-filter-menu__section-title">文件类型</h4>
                  <p class="browse-filter-menu__section-subtitle">按当前视图里出现过的扩展名多选。</p>
                </div>
                <button class="browse-filter-menu__clear-link" type="button" @click="toggleAllFileTypes">
                  {{ allFileTypesSelected && fileTypes.length ? '取消全选' : '全选' }}
                </button>
              </div>

              <div v-if="fileTypes.length" class="browse-filter-menu__choice-grid">
                <button
                  v-for="fileType in fileTypes"
                  :key="fileType"
                  class="browse-filter-menu__choice-chip"
                  :class="{ 'browse-filter-menu__choice-chip--active': isFileTypeSelected(fileType) }"
                  type="button"
                  @click="toggleFileType(fileType)"
                >
                  {{ fileType.toUpperCase() }}
                </button>
              </div>
              <p v-else class="browse-filter-menu__empty">当前视图没有可用的文件类型。</p>
            </section>

            <section class="browse-filter-menu__section">
              <div class="browse-filter-menu__section-head">
                <div>
                  <h4 class="browse-filter-menu__section-title">导入时间</h4>
                  <p class="browse-filter-menu__section-subtitle">支持只填开始或结束时间，未填时表示开区间。</p>
                </div>
                <button class="browse-filter-menu__clear-link" type="button" @click="clearTimeField('imported')">清空</button>
              </div>

              <div class="browse-filter-menu__time-grid">
                <div class="browse-filter-menu__time-block">
                  <span class="browse-filter-menu__label">开始</span>
                  <div class="browse-filter-menu__field-row browse-filter-menu__time-input-row">
                    <input
                      :value="dateValue('importedStart')"
                      class="browse-filter-menu__input"
                      type="date"
                      @input="updateDatePart('importedStart', $event.target.value)"
                    >
                    <input
                      :value="timeValue('importedStart')"
                      class="browse-filter-menu__input"
                      type="time"
                      step="1"
                      @input="updateTimePart('importedStart', $event.target.value)"
                    >
                  </div>
                </div>

                <div class="browse-filter-menu__time-block">
                  <span class="browse-filter-menu__label">结束</span>
                  <div class="browse-filter-menu__field-row browse-filter-menu__time-input-row">
                    <input
                      :value="dateValue('importedEnd')"
                      class="browse-filter-menu__input"
                      type="date"
                      @input="updateDatePart('importedEnd', $event.target.value)"
                    >
                    <input
                      :value="timeValue('importedEnd')"
                      class="browse-filter-menu__input"
                      type="time"
                      step="1"
                      @input="updateTimePart('importedEnd', $event.target.value)"
                    >
                  </div>
                </div>
              </div>
            </section>

            <section class="browse-filter-menu__section">
              <div class="browse-filter-menu__section-head">
                <div>
                  <h4 class="browse-filter-menu__section-title">创建时间</h4>
                  <p class="browse-filter-menu__section-subtitle">同样支持开区间，适合只限定起始或截止时间。</p>
                </div>
                <button class="browse-filter-menu__clear-link" type="button" @click="clearTimeField('created')">清空</button>
              </div>

              <div class="browse-filter-menu__time-grid">
                <div class="browse-filter-menu__time-block">
                  <span class="browse-filter-menu__label">开始</span>
                  <div class="browse-filter-menu__field-row browse-filter-menu__time-input-row">
                    <input
                      :value="dateValue('createdStart')"
                      class="browse-filter-menu__input"
                      type="date"
                      @input="updateDatePart('createdStart', $event.target.value)"
                    >
                    <input
                      :value="timeValue('createdStart')"
                      class="browse-filter-menu__input"
                      type="time"
                      step="1"
                      @input="updateTimePart('createdStart', $event.target.value)"
                    >
                  </div>
                </div>

                <div class="browse-filter-menu__time-block">
                  <span class="browse-filter-menu__label">结束</span>
                  <div class="browse-filter-menu__field-row browse-filter-menu__time-input-row">
                    <input
                      :value="dateValue('createdEnd')"
                      class="browse-filter-menu__input"
                      type="date"
                      @input="updateDatePart('createdEnd', $event.target.value)"
                    >
                    <input
                      :value="timeValue('createdEnd')"
                      class="browse-filter-menu__input"
                      type="time"
                      step="1"
                      @input="updateTimePart('createdEnd', $event.target.value)"
                    >
                  </div>
                </div>
              </div>
            </section>

            <section class="browse-filter-menu__section">
              <div class="browse-filter-menu__section-head">
                <div>
                  <h4 class="browse-filter-menu__section-title">文件大小</h4>
                  <p class="browse-filter-menu__section-subtitle">单位 MB，可只填最小值或最大值。</p>
                </div>
              </div>

              <div class="browse-filter-menu__field-row browse-filter-menu__field-row--stack-on-mobile">
                <label class="browse-filter-menu__field">
                  <span class="browse-filter-menu__label">最小值</span>
                  <div class="browse-filter-menu__unit-field">
                    <input
                      v-model="localFilter.sizeMinMb"
                      class="browse-filter-menu__input"
                      type="number"
                      min="0"
                      step="0.1"
                      placeholder="0"
                    >
                    <span class="browse-filter-menu__unit">MB</span>
                  </div>
                </label>

                <label class="browse-filter-menu__field">
                  <span class="browse-filter-menu__label">最大值</span>
                  <div class="browse-filter-menu__unit-field">
                    <input
                      v-model="localFilter.sizeMaxMb"
                      class="browse-filter-menu__input"
                      type="number"
                      min="0"
                      step="0.1"
                      placeholder="不限"
                    >
                    <span class="browse-filter-menu__unit">MB</span>
                  </div>
                </label>
              </div>
            </section>
          </div>

          <footer class="browse-filter-menu__footer">
            <button class="browse-filter-menu__action browse-filter-menu__action--ghost" type="button" @click="$emit('close')">
              取消
            </button>
            <button class="browse-filter-menu__action browse-filter-menu__action--accent" type="button" @click="submitFilter">
              确定
            </button>
          </footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script>
import { normalizeTagColors } from '../utils/tagColors'

function createEmptyFilter() {
  return {
    filenameMode: 'contains',
    filenameQuery: '',
    categoryIds: [],
    fileTypes: [],
    tagIds: [],
    includeUntagged: false,
    importedStartDate: '',
    importedStartTime: '',
    importedEndDate: '',
    importedEndTime: '',
    createdStartDate: '',
    createdStartTime: '',
    createdEndDate: '',
    createdEndTime: '',
    sizeMinMb: '',
    sizeMaxMb: '',
  }
}

function normalizeStringArray(values) {
  const normalized = []
  const seen = new Set()
  for (const value of Array.isArray(values) ? values : []) {
    const text = String(value || '').trim().toLowerCase()
    if (!text || seen.has(text)) continue
    seen.add(text)
    normalized.push(text)
  }
  return normalized
}

function normalizeIntArray(values) {
  const normalized = []
  const seen = new Set()
  for (const value of Array.isArray(values) ? values : []) {
    const parsed = Number.parseInt(value, 10)
    if (!Number.isInteger(parsed) || parsed <= 0 || seen.has(parsed)) continue
    seen.add(parsed)
    normalized.push(parsed)
  }
  return normalized
}

function normalizeFilter(rawFilter) {
  const nextFilter = createEmptyFilter()
  const source = rawFilter && typeof rawFilter === 'object' ? rawFilter : {}

  nextFilter.filenameMode = source.filenameMode === 'exact' ? 'exact' : 'contains'
  nextFilter.filenameQuery = String(source.filenameQuery || '').trim()
  nextFilter.categoryIds = normalizeIntArray(source.categoryIds)
  nextFilter.fileTypes = normalizeStringArray(source.fileTypes)
  nextFilter.tagIds = normalizeIntArray(source.tagIds)
  nextFilter.includeUntagged = Boolean(source.includeUntagged)

  for (const field of [
    'importedStartDate',
    'importedStartTime',
    'importedEndDate',
    'importedEndTime',
    'createdStartDate',
    'createdStartTime',
    'createdEndDate',
    'createdEndTime',
    'sizeMinMb',
    'sizeMaxMb',
  ]) {
    nextFilter[field] = String(source[field] || '').trim()
  }

  return nextFilter
}

function viewportWidth() {
  return typeof window !== 'undefined' ? window.innerWidth : 1280
}

function viewportHeight() {
  return typeof window !== 'undefined' ? window.innerHeight : 900
}

export default {
  name: 'BrowseFilterMenu',
  props: {
    visible: { type: Boolean, default: false },
    anchorRect: {
      type: Object,
      default: null,
    },
    filter: {
      type: Object,
      default: () => createEmptyFilter(),
    },
    tags: {
      type: Array,
      default: () => [],
    },
    categories: {
      type: Array,
      default: () => [],
    },
    fileTypes: {
      type: Array,
      default: () => [],
    },
    viewportWidth: { type: Number, default: 0 },
    viewportHeight: { type: Number, default: 0 },
  },
  emits: ['close', 'apply'],
  data() {
    return {
      localFilter: createEmptyFilter(),
    }
  },
  computed: {
    panelStyle() {
      const width = Math.max(320, Number(this.viewportWidth) || viewportWidth())
      const height = Math.max(420, Number(this.viewportHeight) || viewportHeight())
      const availableWidth = Math.max(288, width - 32)
      const panelWidth = Math.min(680, Math.max(560, width - 160), availableWidth)
      const rect = this.anchorRect && typeof this.anchorRect === 'object' ? this.anchorRect : null
      const desiredTop = rect ? rect.bottom + 12 : 88
      const top = Math.max(16, Math.min(desiredTop, Math.max(16, height - 380)))
      const desiredLeft = rect ? rect.right - panelWidth : width - panelWidth - 16
      const left = Math.max(16, Math.min(desiredLeft, Math.max(16, width - panelWidth - 16)))
      const maxHeight = Math.max(320, height - top - 16)
      return {
        top: `${top}px`,
        left: `${left}px`,
        width: `${panelWidth}px`,
        maxHeight: `${maxHeight}px`,
      }
    },
    allTagsSelected() {
      if (!this.tags.length) return false
      const selectedSet = new Set(this.localFilter.tagIds)
      return this.tags.every(tag => selectedSet.has(tag.id))
    },
    allCategoriesSelected() {
      if (!this.categories.length) return false
      const selectedSet = new Set(this.localFilter.categoryIds)
      return this.categories.every(category => selectedSet.has(category.id))
    },
    allFileTypesSelected() {
      if (!this.fileTypes.length) return false
      const selectedSet = new Set(this.localFilter.fileTypes)
      return this.fileTypes.every(fileType => selectedSet.has(fileType))
    },
  },
  watch: {
    visible(nextValue) {
      if (nextValue) {
        this.seedFromProps()
      }
    },
    filter: {
      handler() {
        if (this.visible) {
          this.seedFromProps()
        }
      },
      deep: true,
    },
  },
  methods: {
    seedFromProps() {
      this.localFilter = normalizeFilter(this.filter)
    },
    isCategorySelected(categoryId) {
      return this.localFilter.categoryIds.includes(Number(categoryId))
    },
    toggleCategory(categoryId) {
      const normalizedId = Number.parseInt(categoryId, 10)
      if (!Number.isInteger(normalizedId) || normalizedId <= 0) return
      const nextCategoryIds = new Set(this.localFilter.categoryIds)
      if (nextCategoryIds.has(normalizedId)) {
        nextCategoryIds.delete(normalizedId)
      } else {
        nextCategoryIds.add(normalizedId)
      }
      this.localFilter.categoryIds = Array.from(nextCategoryIds).sort((left, right) => left - right)
    },
    toggleAllCategories() {
      if (!this.categories.length) {
        this.localFilter.categoryIds = []
        return
      }
      if (this.allCategoriesSelected) {
        this.localFilter.categoryIds = []
        return
      }
      this.localFilter.categoryIds = this.categories
        .map(category => Number.parseInt(category?.id, 10))
        .filter(id => Number.isInteger(id) && id > 0)
        .sort((left, right) => left - right)
    },
    isTagSelected(tagId) {
      return this.localFilter.tagIds.includes(Number(tagId))
    },
    toggleTag(tagId) {
      const normalizedId = Number.parseInt(tagId, 10)
      if (!Number.isInteger(normalizedId) || normalizedId <= 0) return
      const nextTagIds = new Set(this.localFilter.tagIds)
      if (nextTagIds.has(normalizedId)) {
        nextTagIds.delete(normalizedId)
      } else {
        nextTagIds.add(normalizedId)
      }
      this.localFilter.tagIds = Array.from(nextTagIds).sort((left, right) => left - right)
    },
    selectAllTags() {
      if (!this.tags.length) {
        this.localFilter.tagIds = []
        return
      }
      if (this.allTagsSelected) {
        this.localFilter.tagIds = []
        return
      }
      this.localFilter.tagIds = this.tags
        .map(tag => Number.parseInt(tag?.id, 10))
        .filter(id => Number.isInteger(id) && id > 0)
        .sort((left, right) => left - right)
    },
    clearTagSelection() {
      this.localFilter.tagIds = []
      this.localFilter.includeUntagged = false
    },
    toggleIncludeUntagged() {
      this.localFilter.includeUntagged = !this.localFilter.includeUntagged
    },
    isFileTypeSelected(fileType) {
      return this.localFilter.fileTypes.includes(String(fileType || '').trim().toLowerCase())
    },
    toggleFileType(fileType) {
      const normalizedType = String(fileType || '').trim().toLowerCase()
      if (!normalizedType) return
      const nextTypes = new Set(this.localFilter.fileTypes)
      if (nextTypes.has(normalizedType)) {
        nextTypes.delete(normalizedType)
      } else {
        nextTypes.add(normalizedType)
      }
      this.localFilter.fileTypes = Array.from(nextTypes).sort((left, right) => left.localeCompare(right))
    },
    toggleAllFileTypes() {
      if (!this.fileTypes.length) {
        this.localFilter.fileTypes = []
        return
      }
      if (this.allFileTypesSelected) {
        this.localFilter.fileTypes = []
        return
      }
      this.localFilter.fileTypes = [...this.fileTypes].map(item => String(item || '').trim().toLowerCase())
    },
    dateValue(prefix) {
      return this.localFilter[`${prefix}Date`] || ''
    },
    timeValue(prefix) {
      return this.localFilter[`${prefix}Time`] || ''
    },
    updateDatePart(prefix, nextValue) {
      this.localFilter = {
        ...this.localFilter,
        [`${prefix}Date`]: String(nextValue || '').trim(),
      }
    },
    updateTimePart(prefix, nextValue) {
      this.localFilter = {
        ...this.localFilter,
        [`${prefix}Time`]: String(nextValue || '').trim(),
      }
    },
    clearTimeField(scope) {
      if (scope === 'created') {
        this.localFilter = {
          ...this.localFilter,
          createdStartDate: '',
          createdStartTime: '',
          createdEndDate: '',
          createdEndTime: '',
        }
        return
      }
      this.localFilter = {
        ...this.localFilter,
        importedStartDate: '',
        importedStartTime: '',
        importedEndDate: '',
        importedEndTime: '',
      }
    },
    tagChipStyle(tag, isSelected) {
      if (!isSelected) {
        return {
          '--tag-chip-color': '#94A3B8',
          '--tag-chip-border-color': 'rgba(148, 163, 184, 0.42)',
          '--tag-chip-bg': 'rgba(226, 232, 240, 0.72)',
        }
      }

      const { color, borderColor, backgroundColor } = normalizeTagColors(tag)
      return {
        '--tag-chip-color': color,
        '--tag-chip-border-color': borderColor,
        '--tag-chip-bg': backgroundColor,
      }
    },
    submitFilter() {
      this.$emit('apply', normalizeFilter(this.localFilter))
    },
  },
}
</script>

<style scoped lang="css">
.browse-filter-menu__mask {
  position: fixed;
  inset: 0;
  z-index: 95;
  background: rgba(15, 23, 42, 0.26);
  backdrop-filter: blur(6px);
}

.browse-filter-menu {
  position: fixed;
  z-index: 96;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid rgba(203, 213, 225, 0.9);
  border-radius: 24px;
  background:
    radial-gradient(circle at top right, rgba(191, 219, 254, 0.78), transparent 32%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
  box-shadow: 0 32px 72px rgba(15, 23, 42, 0.26);
}

.browse-filter-menu__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem 1rem 0.85rem;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
}

.browse-filter-menu__title {
  margin: 0;
  color: #0f172a;
  font-size: 1rem;
  font-weight: 800;
}

.browse-filter-menu__subtitle {
  margin: 0.32rem 0 0;
  color: #64748b;
  font-size: 0.82rem;
  line-height: 1.5;
}

.browse-filter-menu__close,
.browse-filter-menu__clear-link {
  border: 0;
  background: transparent;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
}

.browse-filter-menu__close:hover,
.browse-filter-menu__clear-link:hover {
  color: #0f172a;
}

.browse-filter-menu__body {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  padding: 1rem;
  overflow-y: auto;
}

.browse-filter-menu__section {
  display: flex;
  flex-direction: column;
  gap: 0.72rem;
  padding: 0.9rem;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.78);
}

.browse-filter-menu__section--tags {
  background:
    radial-gradient(circle at top left, rgba(220, 252, 231, 0.84), transparent 44%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.98));
  border-color: rgba(134, 239, 172, 0.42);
}

.browse-filter-menu__section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.8rem;
}

.browse-filter-menu__section-title {
  margin: 0;
  color: #0f172a;
  font-size: 0.92rem;
  font-weight: 800;
}

.browse-filter-menu__section-subtitle {
  margin: 0.2rem 0 0;
  color: #64748b;
  font-size: 0.78rem;
  line-height: 1.45;
}

.browse-filter-menu__chip-toolbar,
.browse-filter-menu__choice-grid,
.browse-filter-menu__tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.browse-filter-menu__choice-chip {
  min-height: 2rem;
  padding: 0.32rem 0.72rem;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: #475569;
  font-size: 0.76rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 140ms ease, border-color 140ms ease, color 140ms ease, transform 140ms ease;
}

.browse-filter-menu__choice-chip:hover {
  border-color: rgba(100, 116, 139, 0.4);
  color: #0f172a;
}

.browse-filter-menu__choice-chip--active {
  border-color: rgba(14, 116, 144, 0.62);
  background: rgba(224, 242, 254, 0.98);
  color: #0c4a6e;
}

.browse-filter-menu__tag-chip {
  min-height: 1.68rem;
  padding-inline: 0.7rem;
  font-size: 0.78rem;
}

.browse-filter-menu__tag-chip--muted {
  filter: grayscale(0.3);
}

.browse-filter-menu__field-row {
  display: flex;
  gap: 0.7rem;
}

.browse-filter-menu__field-row > .browse-filter-menu__input,
.browse-filter-menu__field-row > .browse-filter-menu__select {
  min-width: 0;
  flex: 1 1 0;
  width: auto;
}

.browse-filter-menu__field {
  display: flex;
  min-width: 0;
  flex: 1 1 0;
  flex-direction: column;
  gap: 0.34rem;
}

.browse-filter-menu__field--compact {
  flex: 0 0 120px;
}

.browse-filter-menu__field--grow {
  flex: 1 1 auto;
}

.browse-filter-menu__label {
  color: #475569;
  font-size: 0.74rem;
  font-weight: 700;
}

.browse-filter-menu__input,
.browse-filter-menu__select {
  width: 100%;
  min-height: 2.25rem;
  padding: 0.48rem 0.72rem;
  border: 1px solid rgba(203, 213, 225, 0.92);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.96);
  color: #0f172a;
  font-size: 0.82rem;
  outline: none;
  transition: border-color 140ms ease, box-shadow 140ms ease;
}

.browse-filter-menu__input:focus,
.browse-filter-menu__select:focus {
  border-color: rgba(14, 116, 144, 0.5);
  box-shadow: 0 0 0 3px rgba(186, 230, 253, 0.72);
}

.browse-filter-menu__time-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 0.7rem;
}

.browse-filter-menu__time-block {
  display: flex;
  flex-direction: column;
  gap: 0.34rem;
}

.browse-filter-menu__time-input-row {
  display: grid;
  grid-template-columns: minmax(0, 1.28fr) minmax(0, 1fr);
}

.browse-filter-menu__unit-field {
  display: flex;
  align-items: center;
  gap: 0.55rem;
}

.browse-filter-menu__unit {
  flex: 0 0 auto;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 700;
}

.browse-filter-menu__empty {
  margin: 0;
  color: #94a3b8;
  font-size: 0.8rem;
}

.browse-filter-menu__footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.65rem;
  padding: 0.9rem 1rem 1rem;
  border-top: 1px solid rgba(226, 232, 240, 0.92);
}

.browse-filter-menu__action {
  min-height: 2.3rem;
  padding: 0.45rem 1rem;
  border-radius: 999px;
  border: 1px solid transparent;
  font-size: 0.82rem;
  font-weight: 800;
  cursor: pointer;
}

.browse-filter-menu__action--ghost {
  border-color: rgba(203, 213, 225, 0.92);
  background: rgba(255, 255, 255, 0.96);
  color: #334155;
}

.browse-filter-menu__action--accent {
  border-color: rgba(14, 116, 144, 0.24);
  background: #0f172a;
  color: #ffffff;
}

.browse-filter-menu-fade-enter-active,
.browse-filter-menu-fade-leave-active {
  transition: opacity 180ms ease;
}

.browse-filter-menu-fade-enter-from,
.browse-filter-menu-fade-leave-to {
  opacity: 0;
}

@media (max-width: 760px) {
  .browse-filter-menu__field-row--stack-on-mobile,
  .browse-filter-menu__time-grid {
    grid-template-columns: 1fr;
    display: grid;
  }

  .browse-filter-menu__time-input-row {
    grid-template-columns: 1fr;
  }

  .browse-filter-menu__field--compact {
    flex-basis: auto;
  }
}
</style>