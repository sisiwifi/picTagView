<template>
  <section class="tag-manager-page">
    <BreadcrumbHeader
      :show-back="true"
      :crumbs="headerCrumbs"
      :item-count="totalCount"
      count-suffix="个标签"
      @back="$emit('back')"
    >
      <div class="tag-manager-page__header-actions">
        <label class="tag-manager-page__mode-toggle">
          <input
            class="tag-manager-page__mode-checkbox"
            type="checkbox"
            :checked="paginationEnabled"
            :disabled="headerBusy"
            @change="togglePaginationMode($event.target.checked)"
          >
          <span>分页</span>
        </label>

        <button
          class="tag-manager-page__header-btn tag-manager-page__header-btn--primary"
          type="button"
          :disabled="headerBusy"
          @click="openBatchCreateDialog"
        >批量新增</button>
      </div>
    </BreadcrumbHeader>

    <Transition name="tag-manager-message">
      <p v-if="messageText" class="floating-message" :class="messageType === 'error' ? 'floating-message--error' : 'floating-message--success'">
        {{ messageText }}
      </p>
    </Transition>

    <div class="tag-manager-page__body">
      <div class="tag-manager-page__intro">
        <p class="tag-manager-page__summary">{{ viewModeSummary }}</p>
        <p class="tag-manager-page__hint">单击行或复选框可切换勾选；Shift 连选当前视图范围，Shift + Ctrl/Cmd 追加范围，Ctrl/Cmd + A 会全选当前视图，编辑按钮不会触发行选择。</p>
      </div>

      <LoadingSpinner v-if="loading">正在读取标签列表…</LoadingSpinner>

      <p v-else-if="loadError" class="tag-manager-page__error">{{ loadError }}</p>

      <div v-else-if="!loadedTags.length" class="tag-manager-page__empty">
        <span class="tag-manager-page__empty-icon">#</span>
        <p class="tag-manager-page__empty-title">当前没有可管理的标签。</p>
        <p class="tag-manager-page__empty-desc">可以先从设定页导入 JSON，或直接点击“批量新增”创建新的标签条目。</p>
      </div>

      <template v-else>
        <div class="tag-manager-page__table-wrap">
          <table class="tag-manager-table">
            <thead>
              <tr class="tag-manager-table__head-row">
                <th class="tag-manager-table__select-col">
                  <input
                    ref="selectAllCheckbox"
                    class="tag-manager-table__checkbox"
                    type="checkbox"
                    :checked="allVisibleSelected"
                    :aria-label="allVisibleSelected ? '取消全选当前视图' : '全选当前视图'"
                    :disabled="tableBusy || !filteredTags.length"
                    @click.stop
                    @change="toggleSelectAllVisible"
                  >
                </th>
                <th class="tag-manager-table__sequence-col">序号</th>
                <th class="tag-manager-table__id-col">
                  <div class="tag-manager-table__head-inline">
                    <input
                      v-if="isFilterVisible('id')"
                      ref="filter-id"
                      v-model.trim="columnFilters.id"
                      class="tag-manager-table__filter-input tag-manager-table__filter-input--header"
                      type="text"
                      placeholder="ID"
                      :disabled="tableBusy"
                      data-stop-row-select="true"
                      @click.stop
                      @mousedown.stop
                      @blur="hideFilterField('id')"
                      @keydown.enter.prevent="hideFilterField('id')"
                      @keydown.esc.prevent="hideFilterField('id')"
                    >
                    <span v-else class="tag-manager-table__head-label" :class="{ 'tag-manager-table__head-label--active': isFilterActive('id') }">
                      <span>标签 ID</span>
                      <span v-if="isFilterActive('id')" class="tag-manager-table__filter-state-dot" aria-label="标签 ID 已筛选"></span>
                    </span>
                    <button
                      class="tag-manager-table__filter-toggle"
                      :class="{ 'tag-manager-table__filter-toggle--active': isFilterActive('id') || isFilterVisible('id') }"
                      type="button"
                      :disabled="tableBusy"
                      aria-label="筛选标签 ID"
                      @mousedown.stop.prevent
                      @click.stop="toggleFilterField('id')"
                    >🔍</button>
                  </div>
                </th>
                <th class="tag-manager-table__name-col">
                  <div class="tag-manager-table__head-inline">
                    <input
                      v-if="isFilterVisible('name')"
                      ref="filter-name"
                      v-model.trim="columnFilters.name"
                      class="tag-manager-table__filter-input tag-manager-table__filter-input--header"
                      type="text"
                      placeholder="筛选标准名"
                      :disabled="tableBusy"
                      data-stop-row-select="true"
                      @click.stop
                      @mousedown.stop
                      @blur="hideFilterField('name')"
                      @keydown.enter.prevent="hideFilterField('name')"
                      @keydown.esc.prevent="hideFilterField('name')"
                    >
                    <span v-else class="tag-manager-table__head-label" :class="{ 'tag-manager-table__head-label--active': isFilterActive('name') }">
                      <span>标准名</span>
                      <span v-if="isFilterActive('name')" class="tag-manager-table__filter-state-dot" aria-label="标准名已筛选"></span>
                    </span>
                    <button
                      class="tag-manager-table__filter-toggle"
                      :class="{ 'tag-manager-table__filter-toggle--active': isFilterActive('name') || isFilterVisible('name') }"
                      type="button"
                      :disabled="tableBusy"
                      aria-label="筛选标准名"
                      @mousedown.stop.prevent
                      @click.stop="toggleFilterField('name')"
                    >🔍</button>
                  </div>
                </th>
                <th class="tag-manager-table__display-col">
                  <div class="tag-manager-table__head-inline">
                    <input
                      v-if="isFilterVisible('display_name')"
                      ref="filter-display_name"
                      v-model.trim="columnFilters.display_name"
                      class="tag-manager-table__filter-input tag-manager-table__filter-input--header"
                      type="text"
                      placeholder="筛选显示名"
                      :disabled="tableBusy"
                      data-stop-row-select="true"
                      @click.stop
                      @mousedown.stop
                      @blur="hideFilterField('display_name')"
                      @keydown.enter.prevent="hideFilterField('display_name')"
                      @keydown.esc.prevent="hideFilterField('display_name')"
                    >
                    <span v-else class="tag-manager-table__head-label" :class="{ 'tag-manager-table__head-label--active': isFilterActive('display_name') }">
                      <span>显示名</span>
                      <span v-if="isFilterActive('display_name')" class="tag-manager-table__filter-state-dot" aria-label="显示名已筛选"></span>
                    </span>
                    <button
                      class="tag-manager-table__filter-toggle"
                      :class="{ 'tag-manager-table__filter-toggle--active': isFilterActive('display_name') || isFilterVisible('display_name') }"
                      type="button"
                      :disabled="tableBusy"
                      aria-label="筛选显示名"
                      @mousedown.stop.prevent
                      @click.stop="toggleFilterField('display_name')"
                    >🔍</button>
                  </div>
                </th>
                <th class="tag-manager-table__description-col">
                  <div class="tag-manager-table__head-inline">
                    <input
                      v-if="isFilterVisible('description')"
                      ref="filter-description"
                      v-model.trim="columnFilters.description"
                      class="tag-manager-table__filter-input tag-manager-table__filter-input--header"
                      type="text"
                      placeholder="筛选说明"
                      :disabled="tableBusy"
                      data-stop-row-select="true"
                      @click.stop
                      @mousedown.stop
                      @blur="hideFilterField('description')"
                      @keydown.enter.prevent="hideFilterField('description')"
                      @keydown.esc.prevent="hideFilterField('description')"
                    >
                    <span v-else class="tag-manager-table__head-label" :class="{ 'tag-manager-table__head-label--active': isFilterActive('description') }">
                      <span>说明</span>
                      <span v-if="isFilterActive('description')" class="tag-manager-table__filter-state-dot" aria-label="说明已筛选"></span>
                    </span>
                    <button
                      class="tag-manager-table__filter-toggle"
                      :class="{ 'tag-manager-table__filter-toggle--active': isFilterActive('description') || isFilterVisible('description') }"
                      type="button"
                      :disabled="tableBusy"
                      aria-label="筛选说明"
                      @mousedown.stop.prevent
                      @click.stop="toggleFilterField('description')"
                    >🔍</button>
                  </div>
                </th>
                <th class="tag-manager-table__type-col">
                  <div class="tag-manager-table__head-inline">
                    <select
                      v-if="isFilterVisible('type')"
                      ref="filter-type"
                      v-model="columnFilters.type"
                      class="tag-manager-table__filter-input tag-manager-table__filter-select tag-manager-table__filter-input--header"
                      :disabled="tableBusy"
                      data-stop-row-select="true"
                      @click.stop
                      @mousedown.stop
                      @blur="hideFilterField('type')"
                      @keydown.esc.prevent="hideFilterField('type')"
                    >
                      <option value="">全部类型</option>
                      <option v-for="option in tagTypeOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                    </select>
                    <span v-else class="tag-manager-table__head-label" :class="{ 'tag-manager-table__head-label--active': isFilterActive('type') }">
                      <span>类型</span>
                      <span v-if="isFilterActive('type')" class="tag-manager-table__filter-state-dot" aria-label="类型已筛选"></span>
                    </span>
                    <button
                      class="tag-manager-table__filter-toggle"
                      :class="{ 'tag-manager-table__filter-toggle--active': isFilterActive('type') || isFilterVisible('type') }"
                      type="button"
                      :disabled="tableBusy"
                      aria-label="筛选类型"
                      @mousedown.stop.prevent
                      @click.stop="toggleFilterField('type')"
                    >🔍</button>
                  </div>
                </th>
                <th class="tag-manager-table__preview-col">样式预览</th>
                <th class="tag-manager-table__actions-col">编辑</th>
              </tr>
            </thead>

            <tbody>
              <tr v-if="!filteredTags.length">
                <td colspan="9" class="tag-manager-table__empty-cell">当前筛选条件下没有匹配的标签。</td>
              </tr>

              <tr
                v-for="(tag, index) in filteredTags"
                v-else
                :key="tag.id"
                :class="{ 'tag-manager-table__row--selected': isSelected(tag.id) }"
                @mousedown="handleRowMouseDown($event)"
                @click="handleRowSelection(tag.id, index, $event)"
              >
                <td class="tag-manager-table__select-col">
                  <input
                    class="tag-manager-table__checkbox"
                    type="checkbox"
                    :checked="isSelected(tag.id)"
                    :aria-label="isSelected(tag.id) ? '取消选择标签' : '选择标签'"
                    :disabled="tableBusy"
                    data-stop-row-select="true"
                    @click.stop
                    @mousedown.stop
                    @change="handleCheckboxSelection(tag.id, index, $event)"
                  >
                </td>
                <td class="tag-manager-table__sequence-col">{{ displayRowNumber(index) }}</td>
                <td class="tag-manager-table__id-col">{{ tag.id }}</td>
                <td class="tag-manager-table__mono tag-manager-table__name-col">{{ tag.name || '—' }}</td>
                <td class="tag-manager-table__display-col">{{ tag.display_name || '—' }}</td>
                <td class="tag-manager-table__description-col">{{ tag.description || '—' }}</td>
                <td class="tag-manager-table__type-col">
                  <span class="tag-manager-table__type-badge">{{ getTagTypeLabel(tag.type) }}</span>
                </td>
                <td class="tag-manager-table__preview-col">
                  <span class="tag-manager-table__preview-chip" :style="chipStyle(tag)">{{ previewLabel(tag) }}</span>
                </td>
                <td class="tag-manager-table__actions-col">
                  <button
                    class="tag-manager-table__edit-btn"
                    type="button"
                    :disabled="tableBusy"
                    title="编辑标签"
                    data-stop-row-select="true"
                    @click.stop="openEditTagForm(tag)"
                    @mousedown.stop
                  >
                    <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
                      <path d="M13.9 3.1a1.8 1.8 0 0 1 2.546 0l.454.454a1.8 1.8 0 0 1 0 2.546l-8.182 8.182-3.47.924.924-3.47L13.9 3.1Z" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" />
                      <path d="M12.5 4.5l3 3" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" />
                    </svg>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="paginationEnabled" class="tag-manager-page__pagination">
          <PagePaginationBar
            :current-page="currentPage"
            :total-pages="paginationTotalPages"
            :page-size="pageSize"
            :page-size-options="pageSizeOptions"
            @update:page="onPaginationPageChange"
            @update:pageSize="onPaginationPageSizeChange"
          />
        </div>
      </template>
    </div>

    <SelectionIsland collapse-label="收起标签操作" expand-label="展开标签操作">
      <span class="selection-island__count">已选 {{ selectedIds.length }} 个标签</span>
      <button class="selection-island__btn" type="button" :disabled="!filteredTags.length || islandBusy" @click="selectAllCurrentView">{{ selectAllButtonLabel }}</button>
      <button class="selection-island__btn" type="button" :disabled="!selectedIds.length || islandBusy" @click="clearSelection">取消选择</button>
      <button class="selection-island__btn" type="button" :disabled="islandBusy" @click="openBatchCreateDialog">批量新增</button>
      <button class="selection-island__btn selection-island__btn--danger" type="button" :disabled="!selectedIds.length || islandBusy" @click="openDeleteConfirm">删除已选</button>
    </SelectionIsland>

    <ConfirmationDialog
      :visible="deleteConfirmVisible"
      title="批量删除标签"
      :message="deleteConfirmMessage"
      confirm-label="确认删除"
      cancel-label="取消"
      tone="danger"
      :busy="deleteConfirmBusy"
      busy-label="删除中…"
      :model-value="deleteConfirmInput"
      :input-visible="true"
      input-label="请输入 8 位确认码"
      :input-placeholder="deleteConfirmCode"
      :input-hint="deleteConfirmHint"
      @update:modelValue="deleteConfirmInput = $event"
      @cancel="closeDeleteConfirm"
      @confirm="confirmDeleteSelected"
    />

    <TagBatchCreateDialog
      :visible="batchCreateVisible"
      :busy="batchCreateBusy"
      :row-errors="batchCreateRowErrors"
      :error-message="batchCreateError"
      @close="closeBatchCreateDialog"
      @submit="submitBatchCreate"
    />

    <TagFormDialog
      :visible="tagFormVisible"
      :saving="tagFormSaving"
      mode="edit"
      :initial-tag="tagFormTag"
      :existing-names="tagFormExistingNames"
      :error-message="tagFormError"
      @close="closeTagForm"
      @submit="submitTagForm"
    />
  </section>
</template>

<script>
import BreadcrumbHeader from './BreadcrumbHeader.vue'
import ConfirmationDialog from './ConfirmationDialog.vue'
import LoadingSpinner from './LoadingSpinner.vue'
import PagePaginationBar from './PagePaginationBar.vue'
import SelectionIsland from './SelectionIsland.vue'
import TagBatchCreateDialog from './TagBatchCreateDialog.vue'
import TagFormDialog from './TagFormDialog.vue'
import { normalizeTagColors } from '../utils/tagColors'
import { getTagTypeLabel, TAG_TYPE_OPTIONS } from '../utils/tagTypes'

const FULL_LOAD_PAGE_SIZE = 400
const PAGED_PAGE_SIZE_OPTIONS = [25, 50, 100, 200]

function toErrorMessage(err) {
  if (!err) return '未知错误'
  if (typeof err === 'string') return err
  if (err instanceof Error) return err.message
  try {
    return JSON.stringify(err)
  } catch {
    return String(err)
  }
}

function dedupeIds(rawIds) {
  if (!Array.isArray(rawIds)) return []
  const result = []
  const seen = new Set()
  for (const value of rawIds) {
    const normalizedId = Number(value)
    if (!Number.isInteger(normalizedId) || seen.has(normalizedId)) continue
    seen.add(normalizedId)
    result.push(normalizedId)
  }
  return result
}

function buildConfirmCode() {
  return String(Math.floor(10000000 + Math.random() * 90000000))
}

function uniqueNamesFromTags(tags) {
  return Array.from(new Set(
    (Array.isArray(tags) ? tags : [])
      .map(tag => String(tag?.name || '').trim())
      .filter(Boolean)
  ))
}

function cloneTag(tag) {
  if (!tag || typeof tag !== 'object') return null
  return {
    ...tag,
    metadata: tag.metadata && typeof tag.metadata === 'object'
      ? JSON.parse(JSON.stringify(tag.metadata))
      : {},
  }
}

export default {
  name: 'TagManagerPanel',
  components: {
    BreadcrumbHeader,
    ConfirmationDialog,
    LoadingSpinner,
    PagePaginationBar,
    SelectionIsland,
    TagBatchCreateDialog,
    TagFormDialog,
  },
  props: {
    apiBase: {
      type: String,
      default: 'http://127.0.0.1:8000',
    },
  },
  emits: ['back'],
  data() {
    return {
      loading: false,
      loadError: '',
      allTags: [],
      pagedTags: [],
      totalCount: 0,
      paginationEnabled: false,
      currentPage: 1,
      pageSize: PAGED_PAGE_SIZE_OPTIONS[1],
      pageSizeOptions: PAGED_PAGE_SIZE_OPTIONS,
      columnFilters: {
        id: '',
        name: '',
        display_name: '',
        description: '',
        type: '',
      },
      filterVisibility: {
        id: false,
        name: false,
        display_name: false,
        description: false,
        type: false,
      },
      selectedIds: [],
      lastSelectionAnchorId: null,
      messageText: '',
      messageType: 'success',
      messageTimer: null,
      deleteConfirmVisible: false,
      deleteConfirmBusy: false,
      deleteConfirmCode: '',
      deleteConfirmInput: '',
      deleteConfirmError: '',
      batchCreateVisible: false,
      batchCreateBusy: false,
      batchCreateError: '',
      batchCreateRowErrors: [],
      tagFormVisible: false,
      tagFormSaving: false,
      tagFormError: '',
      tagFormTag: null,
      tagFormExistingNames: [],
    }
  },
  computed: {
    headerCrumbs() {
      return [
        { label: '设置', title: '设置', to: '/settings' },
        { label: '标签管理', title: '标签管理', current: true },
      ]
    },
    tagTypeOptions() {
      return TAG_TYPE_OPTIONS
    },
    loadedTags() {
      return this.paginationEnabled ? this.pagedTags : this.allTags
    },
    normalizedColumnFilters() {
      return {
        id: String(this.columnFilters.id || '').trim().toLowerCase(),
        name: String(this.columnFilters.name || '').trim().toLowerCase(),
        display_name: String(this.columnFilters.display_name || '').trim().toLowerCase(),
        description: String(this.columnFilters.description || '').trim().toLowerCase(),
        type: String(this.columnFilters.type || '').trim().toLowerCase(),
      }
    },
    filteredTags() {
      const filters = this.normalizedColumnFilters
      return this.loadedTags.filter(tag => {
        const tagId = String(tag?.id || '').toLowerCase()
        const name = String(tag?.name || '').toLowerCase()
        const displayName = String(tag?.display_name || '').toLowerCase()
        const description = String(tag?.description || '').toLowerCase()
        const type = String(tag?.type || '').toLowerCase()
        if (filters.id && !tagId.includes(filters.id)) return false
        if (filters.name && !name.includes(filters.name)) return false
        if (filters.display_name && !displayName.includes(filters.display_name)) return false
        if (filters.description && !description.includes(filters.description)) return false
        if (filters.type && type !== filters.type) return false
        return true
      })
    },
    paginationTotalPages() {
      const safePageSize = Math.max(1, Number(this.pageSize) || 1)
      return Math.max(1, Math.ceil((Number(this.totalCount) || 0) / safePageSize))
    },
    allVisibleSelected() {
      return this.filteredTags.length > 0 && this.filteredTags.every(tag => this.selectedIds.includes(Number(tag?.id)))
    },
    someVisibleSelected() {
      return this.filteredTags.some(tag => this.selectedIds.includes(Number(tag?.id)))
    },
    hasActiveFilters() {
      return Object.values(this.normalizedColumnFilters).some(Boolean)
    },
    viewModeSummary() {
      if (this.loading) return '正在读取标签列表…'
      const loadedCount = this.loadedTags.length
      const filteredCount = this.filteredTags.length
      if (this.paginationEnabled) {
        if (this.hasActiveFilters) {
          return `分页模式：当前第 ${this.currentPage} 页，已载入本页 ${loadedCount} 项，筛选后显示 ${filteredCount} 项，共 ${this.totalCount} 个标签。`
        }
        return `分页模式：当前第 ${this.currentPage} 页，本页 ${loadedCount} 项，共 ${this.totalCount} 个标签。`
      }
      if (this.hasActiveFilters) {
        return `全量模式：已载入全部 ${loadedCount} 个标签，筛选后显示 ${filteredCount} 项。`
      }
      return `全量模式：已载入全部 ${loadedCount} 个标签。`
    },
    selectAllButtonLabel() {
      if (this.hasActiveFilters) return '全选筛选结果'
      return this.paginationEnabled ? '全选当前页' : '全选全部'
    },
    deleteConfirmMessage() {
      if (!this.selectedIds.length) return ''
      return `此操作会永久删除 ${this.selectedIds.length} 个标签，并从所有已关联图片中移除这些标签引用。\n请输入下面显示的 8 位数字确认码继续。`
    },
    deleteConfirmHint() {
      if (this.deleteConfirmError) {
        return this.deleteConfirmError
      }
      return this.deleteConfirmCode ? `确认码：${this.deleteConfirmCode}` : ''
    },
    headerBusy() {
      return this.loading || this.deleteConfirmBusy || this.batchCreateBusy || this.tagFormVisible || this.tagFormSaving
    },
    tableBusy() {
      return this.loading || this.deleteConfirmBusy || this.batchCreateBusy || this.tagFormSaving
    },
    islandBusy() {
      return this.deleteConfirmBusy || this.batchCreateBusy || this.tagFormVisible || this.tagFormSaving
    },
  },
  mounted() {
    this.loadTags()
    this.syncSelectAllCheckbox()
    window.addEventListener('keydown', this.onWindowKeydown)
  },
  updated() {
    this.syncSelectAllCheckbox()
  },
  beforeUnmount() {
    this.clearMessageTimer()
    window.removeEventListener('keydown', this.onWindowKeydown)
  },
  methods: {
    getTagTypeLabel,
    chipStyle(tag) {
      const { color, borderColor, backgroundColor } = normalizeTagColors(tag)
      return {
        color,
        borderColor,
        backgroundColor,
      }
    },
    previewLabel(tag) {
      return String(tag?.display_name || tag?.name || '预览标签').trim() || '预览标签'
    },
    async fetchTagsPage(limit, offset) {
      const res = await fetch(`${this.apiBase}/api/tags?limit=${limit}&offset=${offset}`)
      if (!res.ok) {
        const payload = await res.json().catch(() => ({}))
        throw new Error(payload.detail || `HTTP ${res.status}`)
      }
      return res.json()
    },
    async loadTags() {
      this.loading = true
      this.loadError = ''
      try {
        if (this.paginationEnabled) {
          await this.loadPagedTags()
        } else {
          await this.loadAllTags()
        }
      } catch (err) {
        this.loadError = `加载标签失败：${toErrorMessage(err)}`
      } finally {
        this.loading = false
      }
    },
    async loadAllTags() {
      let offset = 0
      let expectedTotal = null
      const nextTags = []

      while (expectedTotal === null || nextTags.length < expectedTotal) {
        const payload = await this.fetchTagsPage(FULL_LOAD_PAGE_SIZE, offset)
        const pageItems = Array.isArray(payload?.items) ? payload.items : []
        expectedTotal = Number.isInteger(payload?.total) ? payload.total : Number(payload?.total || 0)
        nextTags.push(...pageItems)
        if (!pageItems.length || pageItems.length < FULL_LOAD_PAGE_SIZE) {
          break
        }
        offset += FULL_LOAD_PAGE_SIZE
      }

      this.allTags = nextTags
      this.pagedTags = []
      this.totalCount = nextTags.length

      const existingIds = new Set(nextTags.map(tag => Number(tag?.id)).filter(id => Number.isInteger(id)))
      this.selectedIds = this.selectedIds.filter(id => existingIds.has(id))
      if (this.lastSelectionAnchorId !== null && !existingIds.has(this.lastSelectionAnchorId)) {
        this.lastSelectionAnchorId = null
      }
    },
    async loadPagedTags() {
      const limit = Math.max(1, Number(this.pageSize) || PAGED_PAGE_SIZE_OPTIONS[0])
      const offset = (Math.max(1, this.currentPage) - 1) * limit
      const payload = await this.fetchTagsPage(limit, offset)
      const nextTotal = Number.isInteger(payload?.total) ? payload.total : Number(payload?.total || 0)
      this.totalCount = Math.max(0, nextTotal)

      const nextTotalPages = Math.max(1, Math.ceil(this.totalCount / limit))
      if (this.currentPage > nextTotalPages) {
        this.currentPage = nextTotalPages
        return this.loadPagedTags()
      }

      this.pagedTags = Array.isArray(payload?.items) ? payload.items : []
      this.allTags = []
    },
    togglePaginationMode(nextValue) {
      if (this.headerBusy) return
      const normalizedValue = Boolean(nextValue)
      if (normalizedValue === this.paginationEnabled) return
      this.paginationEnabled = normalizedValue
      this.currentPage = 1
      this.lastSelectionAnchorId = null
      void this.loadTags()
    },
    async onPaginationPageChange(nextPage) {
      if (!this.paginationEnabled || this.loading) return
      const normalizedPage = Math.max(1, Number(nextPage) || 1)
      if (normalizedPage === this.currentPage) return
      this.currentPage = normalizedPage
      await this.loadTags()
    },
    async onPaginationPageSizeChange(nextPageSize) {
      const normalizedPageSize = Math.max(1, Number(nextPageSize) || this.pageSize)
      if (normalizedPageSize === this.pageSize) return
      this.pageSize = normalizedPageSize
      this.currentPage = 1
      await this.loadTags()
    },
    isSelected(tagId) {
      return this.selectedIds.includes(Number(tagId))
    },
    isFilterVisible(field) {
      return Boolean(this.filterVisibility?.[field])
    },
    isFilterActive(field) {
      return Boolean(String(this.columnFilters?.[field] ?? '').trim())
    },
    focusFilterField(field) {
      this.$nextTick(() => {
        const target = this.$refs[`filter-${field}`]
        const element = Array.isArray(target) ? target[0] : target
        if (!element || typeof element.focus !== 'function') return
        element.focus()
        if (field !== 'type' && typeof element.select === 'function') {
          element.select()
        }
      })
    },
    toggleFilterField(field) {
      if (this.tableBusy) return
      const nextVisible = !this.isFilterVisible(field)
      this.filterVisibility = {
        id: false,
        name: false,
        display_name: false,
        description: false,
        type: false,
      }
      if (!nextVisible) {
        return
      }
      this.filterVisibility = {
        ...this.filterVisibility,
        [field]: true,
      }
      this.focusFilterField(field)
    },
    hideFilterField(field) {
      if (!this.isFilterVisible(field)) return
      this.filterVisibility = {
        ...this.filterVisibility,
        [field]: false,
      }
    },
    syncSelectAllCheckbox() {
      const checkbox = this.$refs.selectAllCheckbox
      if (!checkbox) return
      checkbox.indeterminate = this.someVisibleSelected && !this.allVisibleSelected
    },
    getCurrentViewIds() {
      return this.filteredTags.map(tag => Number(tag?.id)).filter(id => Number.isInteger(id))
    },
    toggleSelectAllVisible() {
      const visibleIds = this.getCurrentViewIds()
      if (!visibleIds.length) return
      if (this.allVisibleSelected) {
        const visibleIdSet = new Set(visibleIds)
        this.selectedIds = this.selectedIds.filter(id => !visibleIdSet.has(id))
        if (this.lastSelectionAnchorId !== null && visibleIdSet.has(this.lastSelectionAnchorId) && !this.selectedIds.includes(this.lastSelectionAnchorId)) {
          this.lastSelectionAnchorId = null
        }
        return
      }
      this.selectedIds = dedupeIds([...this.selectedIds, ...visibleIds])
      this.lastSelectionAnchorId = visibleIds[visibleIds.length - 1] || null
    },
    selectAllCurrentView() {
      const visibleIds = this.getCurrentViewIds()
      if (!visibleIds.length) return
      this.selectedIds = dedupeIds([...this.selectedIds, ...visibleIds])
      this.lastSelectionAnchorId = visibleIds[visibleIds.length - 1] || null
    },
    clearSelection() {
      this.selectedIds = []
      this.lastSelectionAnchorId = null
    },
    getVisibleIndexById(tagId) {
      return this.filteredTags.findIndex(tag => Number(tag?.id) === Number(tagId))
    },
    toggleSingleSelection(tagId) {
      const normalizedId = Number(tagId)
      if (!Number.isInteger(normalizedId)) return
      if (this.selectedIds.includes(normalizedId)) {
        this.selectedIds = this.selectedIds.filter(id => id !== normalizedId)
        return
      }
      this.selectedIds = [...this.selectedIds, normalizedId]
    },
    applyRangeSelection(targetIndex, preserveExisting = false) {
      if (!Number.isInteger(targetIndex) || targetIndex < 0 || targetIndex >= this.filteredTags.length) return
      const targetId = Number(this.filteredTags[targetIndex]?.id)
      if (!Number.isInteger(targetId)) return

      const anchorIndex = this.lastSelectionAnchorId !== null
        ? this.getVisibleIndexById(this.lastSelectionAnchorId)
        : -1
      if (anchorIndex < 0) {
        this.toggleSingleSelection(targetId)
        this.lastSelectionAnchorId = targetId
        return
      }

      const start = Math.min(anchorIndex, targetIndex)
      const end = Math.max(anchorIndex, targetIndex)
      const rangeIds = this.filteredTags
        .slice(start, end + 1)
        .map(tag => Number(tag?.id))
        .filter(id => Number.isInteger(id))

      const nextSelectedIdSet = new Set(preserveExisting ? this.selectedIds : [])
      rangeIds.forEach(id => nextSelectedIdSet.add(id))
      this.selectedIds = Array.from(nextSelectedIdSet)
      this.lastSelectionAnchorId = targetId
    },
    applySelection(tagId, index, event) {
      const normalizedId = Number(tagId)
      if (!Number.isInteger(normalizedId)) return
      if (event?.shiftKey) {
        this.applyRangeSelection(index, Boolean(event.ctrlKey || event.metaKey))
        return
      }
      this.toggleSingleSelection(normalizedId)
      this.lastSelectionAnchorId = normalizedId
    },
    isInteractiveTarget(target) {
      return Boolean(target?.closest?.('input, button, select, textarea, a, label, [data-stop-row-select="true"]'))
    },
    handleRowMouseDown(event) {
      if (this.isInteractiveTarget(event?.target)) return
      event.preventDefault()
    },
    handleRowSelection(tagId, index, event) {
      if (this.tableBusy || this.isInteractiveTarget(event?.target)) return
      this.applySelection(tagId, index, event)
    },
    handleCheckboxSelection(tagId, index, event) {
      if (this.tableBusy) return
      this.applySelection(tagId, index, event)
    },
    onWindowKeydown(event) {
      const key = String(event?.key || '').toLowerCase()
      if (!(event.ctrlKey || event.metaKey) || key !== 'a') return
      const target = event?.target
      const tagName = String(target?.tagName || '').toLowerCase()
      if (tagName === 'input' || tagName === 'textarea' || tagName === 'select' || target?.isContentEditable) {
        return
      }
      event.preventDefault()
      this.selectAllCurrentView()
    },
    clearMessageTimer() {
      if (!this.messageTimer) return
      clearTimeout(this.messageTimer)
      this.messageTimer = null
    },
    showMessage(type, text, duration = null) {
      this.clearMessageTimer()
      this.messageType = type
      this.messageText = text
      const timeout = duration ?? (type === 'error' ? 4200 : 2600)
      this.messageTimer = setTimeout(() => {
        this.messageText = ''
        this.messageTimer = null
      }, timeout)
    },
    openDeleteConfirm() {
      if (!this.selectedIds.length || this.deleteConfirmBusy) return
      this.deleteConfirmCode = buildConfirmCode()
      this.deleteConfirmInput = ''
      this.deleteConfirmError = ''
      this.deleteConfirmVisible = true
    },
    closeDeleteConfirm(force = false) {
      if (this.deleteConfirmBusy && !force) return
      this.deleteConfirmVisible = false
      this.deleteConfirmInput = ''
      this.deleteConfirmError = ''
      this.deleteConfirmCode = ''
    },
    async confirmDeleteSelected() {
      if (String(this.deleteConfirmInput || '').trim() !== this.deleteConfirmCode) {
        this.deleteConfirmError = '确认码输入不正确，请重新输入 8 位数字'
        return
      }

      this.deleteConfirmBusy = true
      this.deleteConfirmError = ''
      try {
        const res = await fetch(`${this.apiBase}/api/tags/bulk-delete`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ids: this.selectedIds }),
        })
        if (!res.ok) {
          const payload = await res.json().catch(() => ({}))
          throw new Error(payload.detail || `HTTP ${res.status}`)
        }

        const payload = await res.json()
        const deletedIds = dedupeIds(payload?.deleted_tag_ids || [])
        const deletedIdSet = new Set(deletedIds)
        this.selectedIds = this.selectedIds.filter(id => !deletedIdSet.has(id))
        if (this.lastSelectionAnchorId !== null && deletedIdSet.has(this.lastSelectionAnchorId)) {
          this.lastSelectionAnchorId = null
        }

        const nextTotal = Math.max(0, Number(this.totalCount || 0) - deletedIds.length)
        const nextTotalPages = Math.max(1, Math.ceil(nextTotal / Math.max(1, Number(this.pageSize) || 1)))
        if (this.paginationEnabled && this.currentPage > nextTotalPages) {
          this.currentPage = nextTotalPages
        }

        this.closeDeleteConfirm(true)
        await this.loadTags()
        this.showMessage('success', `已删除 ${payload?.deleted_count || deletedIds.length || 0} 个标签，解除 ${payload?.detached_image_count || 0} 张图片的关联。`)
      } catch (err) {
        this.deleteConfirmError = `删除失败：${toErrorMessage(err)}`
      } finally {
        this.deleteConfirmBusy = false
      }
    },
    openBatchCreateDialog() {
      if (this.batchCreateBusy || this.tagFormVisible || this.tagFormSaving) return
      this.batchCreateError = ''
      this.batchCreateRowErrors = []
      this.batchCreateVisible = true
    },
    closeBatchCreateDialog() {
      if (this.batchCreateBusy) return
      this.batchCreateVisible = false
      this.batchCreateError = ''
      this.batchCreateRowErrors = []
    },
    async submitBatchCreate(payload) {
      this.batchCreateBusy = true
      this.batchCreateError = ''
      this.batchCreateRowErrors = []
      try {
        const res = await fetch(`${this.apiBase}/api/tags/bulk-create`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
        const responsePayload = await res.json().catch(() => ({}))
        if (!res.ok) {
          this.batchCreateRowErrors = Array.isArray(responsePayload?.row_errors) ? responsePayload.row_errors : []
          this.batchCreateError = responsePayload?.detail
            ? `批量新增失败：${responsePayload.detail}`
            : `批量新增失败：HTTP ${res.status}`
          return
        }

        this.batchCreateVisible = false
        await this.loadTags()
        this.showMessage('success', `已新增 ${Number(responsePayload?.created || 0)} 个标签。`)
      } catch (err) {
        this.batchCreateError = `批量新增失败：${toErrorMessage(err)}`
      } finally {
        this.batchCreateBusy = false
      }
    },
    resetTagFormState() {
      this.tagFormVisible = false
      this.tagFormSaving = false
      this.tagFormError = ''
      this.tagFormTag = null
      this.tagFormExistingNames = []
    },
    closeTagForm() {
      if (this.tagFormSaving) return
      this.resetTagFormState()
    },
    async fetchTagFormExistingNames() {
      if (!this.paginationEnabled && this.allTags.length === this.totalCount) {
        return uniqueNamesFromTags(this.allTags)
      }

      let offset = 0
      let expectedTotal = null
      const nextTags = []
      while (expectedTotal === null || nextTags.length < expectedTotal) {
        const payload = await this.fetchTagsPage(FULL_LOAD_PAGE_SIZE, offset)
        const items = Array.isArray(payload?.items) ? payload.items : []
        expectedTotal = Number.isInteger(payload?.total) ? payload.total : Number(payload?.total || 0)
        nextTags.push(...items)
        if (!items.length || items.length < FULL_LOAD_PAGE_SIZE) {
          break
        }
        offset += FULL_LOAD_PAGE_SIZE
      }
      return uniqueNamesFromTags(nextTags)
    },
    async openEditTagForm(tag) {
      const tagId = Number(tag?.id)
      if (!Number.isInteger(tagId) || this.headerBusy || this.batchCreateVisible || this.deleteConfirmVisible || this.tagFormVisible) return

      this.tagFormError = ''
      try {
        this.tagFormExistingNames = await this.fetchTagFormExistingNames()
        this.tagFormTag = cloneTag(tag)
        this.tagFormVisible = true
      } catch (err) {
        this.showMessage('error', `标签编辑初始化失败：${toErrorMessage(err)}`)
      }
    },
    async submitTagForm(payload) {
      const tagId = Number(payload?.id || this.tagFormTag?.id)
      if (!Number.isInteger(tagId) || this.tagFormSaving) return

      this.tagFormSaving = true
      this.tagFormError = ''
      try {
        const res = await fetch(`${this.apiBase}/api/tags/${tagId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
        if (!res.ok) {
          const responsePayload = await res.json().catch(() => ({}))
          throw new Error(responsePayload.detail || `HTTP ${res.status}`)
        }

        const savedTag = await res.json()
        await this.loadTags()
        this.resetTagFormState()
        this.showMessage('success', `已更新标签“${savedTag?.display_name || savedTag?.name || tagId}”。`)
      } catch (err) {
        this.tagFormError = `标签保存失败：${toErrorMessage(err)}`
      } finally {
        this.tagFormSaving = false
      }
    },
    displayRowNumber(index) {
      const pageOffset = this.paginationEnabled
        ? (Math.max(1, Number(this.currentPage) || 1) - 1) * Math.max(1, Number(this.pageSize) || 1)
        : 0
      return pageOffset + index + 1
    },
  },
}
</script>

<style scoped lang="css">
.tag-manager-page {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  height: calc(100dvh - 5rem);
  min-height: calc(100vh - 5rem);
  overflow: hidden;
}

.tag-manager-page__header-actions {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.tag-manager-page__mode-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  min-height: 34px;
  padding: 0 0.8rem;
  border: 1px solid rgba(203, 213, 225, 0.92);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.92);
  color: #334155;
  font-size: 0.78rem;
  font-weight: 700;
}

.tag-manager-page__mode-checkbox {
  margin: 0;
}

.tag-manager-page__header-btn {
  border: 0;
  border-radius: 12px;
  padding: 0.72rem 0.95rem;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 800;
  transition: transform 160ms ease, box-shadow 160ms ease, opacity 160ms ease;
}

.tag-manager-page__header-btn:hover:not(:disabled) {
  transform: translateY(-1px);
}

.tag-manager-page__header-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.tag-manager-page__header-btn--primary {
  background: linear-gradient(135deg, #1d4ed8, #0f766e);
  color: #ffffff;
  box-shadow: 0 12px 24px rgba(29, 78, 216, 0.18);
}

.tag-manager-page__body {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding-right: 0.25rem;
  padding-bottom: 5.5rem;
  scrollbar-gutter: stable;
}

.tag-manager-page__body::-webkit-scrollbar {
  width: 10px;
}

.tag-manager-page__body::-webkit-scrollbar-track {
  background: transparent;
}

.tag-manager-page__body::-webkit-scrollbar-thumb {
  border: 2px solid transparent;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.6);
  background-clip: padding-box;
}

.tag-manager-page__intro {
  display: flex;
  flex-direction: column;
  gap: 0.28rem;
  margin-bottom: 0.85rem;
}

.tag-manager-page__summary,
.tag-manager-page__hint,
.tag-manager-page__error,
.tag-manager-page__empty-title,
.tag-manager-page__empty-desc {
  margin: 0;
}

.tag-manager-page__summary {
  color: #0f172a;
  font-size: 0.88rem;
  font-weight: 700;
}

.tag-manager-page__hint {
  color: #64748b;
  font-size: 0.8rem;
  line-height: 1.6;
}

.tag-manager-page__error {
  border: 1px solid rgba(248, 113, 113, 0.28);
  border-radius: 16px;
  padding: 0.9rem 1rem;
  background: rgba(254, 242, 242, 0.9);
  color: #b91c1c;
  font-size: 0.84rem;
  font-weight: 700;
}

.tag-manager-page__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.42rem;
  min-height: 280px;
  border: 1px dashed rgba(148, 163, 184, 0.4);
  border-radius: 24px;
  background: rgba(248, 250, 252, 0.86);
  text-align: center;
}

.tag-manager-page__empty-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 3rem;
  height: 3rem;
  border-radius: 999px;
  background: rgba(226, 232, 240, 0.92);
  color: #0f172a;
  font-size: 1.15rem;
  font-weight: 800;
}

.tag-manager-page__empty-title {
  color: #0f172a;
  font-size: 0.92rem;
  font-weight: 800;
}

.tag-manager-page__empty-desc {
  max-width: 520px;
  color: #64748b;
  font-size: 0.82rem;
  line-height: 1.68;
}

.tag-manager-page__table-wrap {
  overflow: auto;
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 22px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.96));
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
}

.tag-manager-table {
  width: 100%;
  min-width: 1220px;
  border-collapse: separate;
  border-spacing: 0;
}

.tag-manager-table th,
.tag-manager-table td {
  user-select: none;
}

.tag-manager-table input,
.tag-manager-table select,
.tag-manager-table button {
  user-select: text;
}

.tag-manager-table thead th {
  text-align: left;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
}

.tag-manager-table__head-row th {
  position: sticky;
  top: 0;
  z-index: 3;
  padding: 0.82rem 0.9rem;
  vertical-align: middle;
  background: rgba(241, 245, 249, 0.98);
  color: #334155;
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.02em;
}

.tag-manager-table__head-inline {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 2rem;
  width: 100%;
  min-width: 0;
  overflow: hidden;
}

.tag-manager-table__head-label {
  display: inline-flex;
  align-items: center;
  gap: 0.38rem;
  flex: 1 1 auto;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tag-manager-table__head-label--active {
  color: #1d4ed8;
}

.tag-manager-table__filter-state-dot {
  width: 0.46rem;
  height: 0.46rem;
  flex: 0 0 auto;
  border-radius: 999px;
  background: #2563eb;
  box-shadow: 0 0 0 3px rgba(191, 219, 254, 0.75);
}

.tag-manager-table tbody td {
  padding: 0.88rem 0.9rem;
  border-bottom: 1px solid rgba(226, 232, 240, 0.82);
  color: #0f172a;
  font-size: 0.84rem;
  line-height: 1.65;
  background: transparent;
}

.tag-manager-table tbody tr {
  cursor: pointer;
  transition: background 150ms ease, box-shadow 150ms ease;
}

.tag-manager-table tbody tr:hover {
  background: rgba(239, 246, 255, 0.8);
}

.tag-manager-table tbody tr:last-child td {
  border-bottom: 0;
}

.tag-manager-table__row--selected td {
  background: rgba(219, 234, 254, 0.62);
}

.tag-manager-table__empty-cell {
  padding: 2rem 1rem;
  color: #64748b;
  text-align: center;
  font-size: 0.86rem;
  font-weight: 700;
}

.tag-manager-table__checkbox {
  width: 1rem;
  height: 1rem;
  cursor: pointer;
}

.tag-manager-table__filter-input {
  width: 100%;
  min-width: 0;
  border: 1px solid rgba(148, 163, 184, 0.36);
  border-radius: 12px;
  padding: 0.5rem 0.68rem;
  background: rgba(255, 255, 255, 0.98);
  color: #0f172a;
  font-size: 0.78rem;
}

.tag-manager-table__filter-input--header {
  flex: 1 1 auto;
  width: auto;
  min-width: 0;
  max-width: 100%;
  height: 2rem;
  padding: 0.32rem 0.62rem;
  font-size: 0.76rem;
}

.tag-manager-table__id-col .tag-manager-table__filter-input--header {
  flex: 0 1 3.8rem;
  width: 3.8rem;
  max-width: 3.8rem;
  padding-left: 0.48rem;
  padding-right: 0.48rem;
}

.tag-manager-table__filter-select {
  cursor: pointer;
}

.tag-manager-table__filter-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.7rem;
  height: 1.7rem;
  border: 0;
  border-radius: 999px;
  padding: 0;
  background: rgba(226, 232, 240, 0.84);
  color: #64748b;
  cursor: pointer;
  font-size: 0.86rem;
  line-height: 1;
  transition: transform 150ms ease, background 150ms ease, color 150ms ease, opacity 150ms ease;
}

.tag-manager-table__filter-toggle:hover:not(:disabled) {
  transform: translateY(-1px);
  background: rgba(191, 219, 254, 0.88);
  color: #1d4ed8;
}

.tag-manager-table__filter-toggle--active {
  background: rgba(191, 219, 254, 0.98);
  color: #1d4ed8;
}

.tag-manager-table__filter-toggle:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.tag-manager-table__select-col {
  width: 64px;
  text-align: center;
}

.tag-manager-table__sequence-col {
  width: 84px;
  color: #475569;
  font-weight: 700;
}

.tag-manager-table__id-col {
  width: 104px;
  color: #475569;
  font-weight: 700;
}

.tag-manager-table__name-col {
  width: 220px;
}

.tag-manager-table__display-col {
  width: 220px;
}

.tag-manager-table__description-col {
  width: 270px;
  color: #475569;
}

.tag-manager-table__type-col {
  width: 150px;
}

.tag-manager-table__preview-col {
  width: 220px;
}

.tag-manager-table__actions-col {
  width: 92px;
  text-align: center;
}

.tag-manager-table__mono {
  font-family: 'Consolas', 'SFMono-Regular', 'Liberation Mono', monospace;
}

.tag-manager-table__type-badge {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  border-radius: 999px;
  padding: 0.22rem 0.7rem;
  background: rgba(241, 245, 249, 0.96);
  color: #334155;
  font-size: 0.76rem;
  font-weight: 800;
  white-space: nowrap;
}

.tag-manager-table__preview-chip {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  min-height: 34px;
  border: 1px solid currentColor;
  border-radius: 999px;
  padding: 0.42rem 0.78rem;
  font-size: 0.78rem;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tag-manager-table__edit-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border: 1px solid rgba(148, 163, 184, 0.34);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.96);
  color: #1d4ed8;
  cursor: pointer;
  transition: transform 160ms ease, background 160ms ease, box-shadow 160ms ease, opacity 160ms ease;
}

.tag-manager-table__edit-btn svg {
  width: 16px;
  height: 16px;
}

.tag-manager-table__edit-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  background: rgba(239, 246, 255, 0.98);
  box-shadow: 0 10px 20px rgba(29, 78, 216, 0.12);
}

.tag-manager-table__edit-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.tag-manager-page__pagination {
  margin-top: 0.9rem;
}

.floating-message {
  position: fixed;
  top: 0.9rem;
  left: 50%;
  z-index: 80;
  min-width: min(520px, calc(100vw - 2rem));
  max-width: calc(100vw - 2rem);
  border-radius: 16px;
  padding: 0.85rem 1rem;
  font-size: 0.86rem;
  font-weight: 700;
  text-align: center;
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.16);
  transform: translateX(-50%);
  pointer-events: none;
}

.floating-message--success {
  background: rgba(220, 252, 231, 0.9);
  color: #166534;
}

.floating-message--error {
  background: rgba(254, 226, 226, 0.92);
  color: #991b1b;
}

.tag-manager-message-enter-active,
.tag-manager-message-leave-active {
  transition: opacity 180ms ease, transform 180ms ease;
}

.tag-manager-message-enter-from,
.tag-manager-message-leave-to {
  opacity: 0;
  transform: translate(-50%, -10px);
}

@media (max-width: 860px) {
  .tag-manager-page__header-actions {
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .tag-manager-page__body {
    padding-bottom: 6rem;
  }
}

@media (max-width: 640px) {
  .tag-manager-page {
    height: auto;
    min-height: calc(100vh - 5rem);
  }
}
</style>