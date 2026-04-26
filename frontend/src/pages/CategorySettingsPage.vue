<template>
  <section class="category-page">
    <BreadcrumbHeader
      :show-back="true"
      :crumbs="headerCrumbs"
      :item-count="categories.length"
      count-suffix="个主分类"
      @back="goBack"
    >
      <div class="header-actions" role="group" aria-label="主分类工具">
        <button
          class="header-btn header-btn--manage"
          :class="{ active: manageMode }"
          type="button"
          @click="toggleManageMode()"
        >
          {{ manageMode ? '完成管理' : '管理' }}
        </button>
        <button class="header-btn header-btn--primary" type="button" @click="requestCreateCategory">
          新建主分类
        </button>
      </div>
    </BreadcrumbHeader>

    <Transition name="page-message">
      <p v-if="messageText" class="floating-message" :class="messageType === 'error' ? 'floating-message--error' : 'floating-message--success'">
        {{ messageText }}
      </p>
    </Transition>

    <div class="category-page__scroller">
      <LoadingSpinner v-if="loading" />

      <div v-else-if="!categories.length" class="empty-hint">
        <span class="empty-hint__icon">🗂</span>
        <p>当前还没有可管理的主分类。</p>
      </div>

      <section v-else class="category-grid">
        <article
          v-for="category in categories"
          :key="category.id"
          class="category-card"
          :class="{
            'category-card--default': isDefaultCategory(category),
            'category-card--inactive': !category.is_active,
            'category-card--manage': manageMode,
            'category-card--selected': isSelected(category.id),
          }"
        >
          <div class="category-card__topline">
            <div class="category-card__lead">
              <span class="category-card__badge">{{ badgeText(category) }}</span>
            </div>

            <div class="category-card__meta">
              <span v-if="isDefaultCategory(category)" class="category-card__pill">默认</span>
              <button
                v-else-if="manageMode"
                class="category-card__pick"
                type="button"
                :aria-pressed="isSelected(category.id) ? 'true' : 'false'"
                :aria-label="isSelected(category.id) ? '取消选择主分类' : '选择主分类'"
                @click.stop="toggleSelection(category.id)"
              >
                <span v-if="isSelected(category.id)" class="category-card__pick-mark">✓</span>
              </button>
            </div>
          </div>

          <div class="category-card__main">
            <div class="category-card__title-group">
              <h3 class="category-card__title">{{ category.display_name }}</h3>
              <p class="category-card__name">{{ category.name }}</p>
            </div>

            <button
              class="category-switch"
              :class="{ 'category-switch--on': category.is_active }"
              type="button"
              :disabled="savingToggleId === category.id || isDefaultCategory(category)"
              @click.stop="toggleCategoryActive(category)"
            >
              <span class="category-switch__knob"></span>
            </button>
          </div>

          <p class="category-card__description">{{ category.description || '暂无说明，建议补充主分类适用范围。' }}</p>

          <div class="category-card__bottom">
            <div class="category-card__stats">
              <span class="category-card__stat">图片 {{ category.usage_count?.image || 0 }}</span>
            </div>

            <div v-if="!isDefaultCategory(category)" class="category-card__actions">
              <button
                class="category-card__action category-card__action--danger"
                :class="{ 'category-card__action--hidden': !manageMode }"
                type="button"
                @click.stop="requestDeleteCategories([category.id], category.display_name)"
              >
                移除
              </button>
              <button
                class="category-card__action"
                type="button"
                @click.stop="openEditDialog(category)"
              >
                编辑
              </button>
            </div>
          </div>
        </article>
      </section>
    </div>

    <SelectionIsland
      v-if="manageMode"
      collapse-label="收起管理操作"
      expand-label="展开管理操作"
    >
      <span class="selection-island__count">已选 {{ selectedIds.length }} 个主分类</span>
      <button class="selection-island__btn" type="button" :disabled="!canActivateSelected || bulkActionBusy" @click="batchSetSelectedCategories(true)">打开</button>
      <button class="selection-island__btn" type="button" :disabled="!canDeactivateSelected || bulkActionBusy" @click="batchSetSelectedCategories(false)">关闭</button>
      <button class="selection-island__btn" type="button" :disabled="!editableCategories.length || bulkActionBusy" @click="selectAllCategories">全选</button>
      <button class="selection-island__btn" type="button" :disabled="!selectedIds.length || bulkActionBusy" @click="clearSelection">取消选择</button>
    </SelectionIsland>

    <CategoryFormDialog
      :visible="formDialog.visible"
      :saving="formSaving"
      :mode="formDialog.mode"
      :initial-category="formDialog.category"
      :existing-names="existingNames"
      @close="closeFormDialog"
      @submit="submitCategoryForm"
    />

    <ConfirmationDialog
      :visible="confirmDialog.visible"
      :title="confirmDialog.title"
      :message="confirmDialog.message"
      :confirm-label="confirmDialog.confirmLabel"
      :cancel-label="confirmDialog.cancelLabel"
      :tone="confirmDialog.tone"
      :show-cancel="confirmDialog.showCancel"
      @cancel="closeConfirmDialog"
      @confirm="handleConfirmDialogConfirm"
    />
  </section>
</template>

<script>
import BreadcrumbHeader from '../components/BreadcrumbHeader.vue'
import CategoryFormDialog from '../components/CategoryFormDialog.vue'
import ConfirmationDialog from '../components/ConfirmationDialog.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import SelectionIsland from '../components/SelectionIsland.vue'

const API_BASE = 'http://127.0.0.1:8000'
const DEFAULT_CATEGORY_ID = 1

function createDialogState() {
  return {
    visible: false,
    title: '请确认操作',
    message: '',
    confirmLabel: '确认',
    cancelLabel: '取消',
    tone: 'danger',
    showCancel: true,
    onConfirm: null,
  }
}

function createFormDialogState() {
  return {
    visible: false,
    mode: 'create',
    category: null,
  }
}

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

export default {
  name: 'CategorySettingsPage',
  components: {
    BreadcrumbHeader,
    CategoryFormDialog,
    ConfirmationDialog,
    LoadingSpinner,
    SelectionIsland,
  },
  data() {
    return {
      categories: [],
      loading: true,
      messageText: '',
      messageType: 'success',
      messageTimer: null,
      manageMode: false,
      selectedIds: [],
      savingToggleId: null,
      bulkActionBusy: false,
      formSaving: false,
      formDialog: createFormDialogState(),
      confirmDialog: createDialogState(),
    }
  },
  computed: {
    headerCrumbs() {
      return [
        { label: '设置', title: '设置', to: '/settings' },
        { label: '主分类配置', title: '主分类配置', current: true },
      ]
    },
    editableCategories() {
      return this.categories.filter(category => !this.isDefaultCategory(category))
    },
    selectedCategories() {
      const selectedSet = new Set(this.selectedIds)
      return this.categories.filter(category => selectedSet.has(category.id))
    },
    canActivateSelected() {
      return this.selectedCategories.some(category => !category.is_active)
    },
    canDeactivateSelected() {
      return this.selectedCategories.some(category => category.is_active)
    },
    existingNames() {
      return this.categories.map(category => category.name).filter(Boolean)
    },
  },
  created() {
    this.loadCategories()
  },
  beforeUnmount() {
    this.clearMessageTimer()
  },
  methods: {
    goBack() {
      this.$router.push('/settings')
    },

    async loadCategories() {
      this.loading = true
      try {
        const res = await fetch(`${API_BASE}/api/categories`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        this.categories = Array.isArray(data.items) ? data.items : []
        this.selectedIds = this.selectedIds.filter(id => this.categories.some(category => category.id === id && !this.isDefaultCategory(category)))
      } catch (err) {
        this.showMessage('error', `加载主分类失败：${toErrorMessage(err)}`, 4200)
      } finally {
        this.loading = false
      }
    },

    isDefaultCategory(category) {
      return Number(category?.id) === DEFAULT_CATEGORY_ID
    },

    isSelected(categoryId) {
      return this.selectedIds.includes(categoryId)
    },

    badgeText(category) {
      const source = category?.display_name || category?.name || 'C'
      return source.slice(0, 1).toUpperCase()
    },

    toggleManageMode(forceValue = null) {
      const nextValue = typeof forceValue === 'boolean' ? forceValue : !this.manageMode
      this.manageMode = nextValue
      if (!nextValue) {
        this.clearSelection()
      }
    },

    clearSelection() {
      this.selectedIds = []
    },

    selectAllCategories() {
      this.selectedIds = this.editableCategories.map(category => category.id)
    },

    toggleSelection(categoryId) {
      if (!Number.isInteger(categoryId) || categoryId === DEFAULT_CATEGORY_ID) return
      if (this.selectedIds.includes(categoryId)) {
        this.selectedIds = this.selectedIds.filter(id => id !== categoryId)
        return
      }
      this.selectedIds = [...this.selectedIds, categoryId]
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

    openEditDialog(category) {
      if (!category || this.isDefaultCategory(category)) return
      this.formDialog = {
        visible: true,
        mode: 'edit',
        category,
      }
    },

    requestCreateCategory() {
      if (this.editableCategories.length >= 10) {
        this.openConfirmDialog({
          title: '主分类数量提醒',
          message: '当前主分类已经超过 10 个。继续新增不会被阻止，但可能让配置和浏览筛选变得更难维护。确认继续创建吗？',
          confirmLabel: '继续创建',
          cancelLabel: '取消',
          tone: 'accent',
          onConfirm: () => {
            this.formDialog = { visible: true, mode: 'create', category: null }
          },
        })
        return
      }
      this.formDialog = { visible: true, mode: 'create', category: null }
    },

    closeFormDialog() {
      if (this.formSaving) return
      this.formDialog = createFormDialogState()
    },

    async submitCategoryForm(payload) {
      this.formSaving = true
      try {
        const isEdit = this.formDialog.mode === 'edit' && this.formDialog.category?.id
        const targetUrl = isEdit
          ? `${API_BASE}/api/categories/${this.formDialog.category.id}`
          : `${API_BASE}/api/categories`
        const method = isEdit ? 'PATCH' : 'POST'
        const res = await fetch(targetUrl, {
          method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
        if (!res.ok) {
          const data = await res.json().catch(() => ({}))
          throw new Error(data.detail || `HTTP ${res.status}`)
        }

        this.formDialog = createFormDialogState()
        this.showMessage('success', isEdit ? '主分类已更新。' : '主分类已创建。')
        await this.loadCategories()
      } catch (err) {
        this.showMessage('error', `保存主分类失败：${toErrorMessage(err)}`, 4200)
      } finally {
        this.formSaving = false
      }
    },

    async toggleCategoryActive(category) {
      if (!category || this.isDefaultCategory(category)) return
      this.savingToggleId = category.id
      try {
        const res = await fetch(`${API_BASE}/api/categories/${category.id}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ is_active: !category.is_active }),
        })
        if (!res.ok) {
          const data = await res.json().catch(() => ({}))
          throw new Error(data.detail || `HTTP ${res.status}`)
        }
        this.showMessage('success', category.is_active ? '主分类已关闭。' : '主分类已打开。')
        await this.loadCategories()
      } catch (err) {
        this.showMessage('error', `更新主分类状态失败：${toErrorMessage(err)}`, 4200)
      } finally {
        this.savingToggleId = null
      }
    },

    async batchSetSelectedCategories(nextActive) {
      if (!this.selectedIds.length) return
      this.bulkActionBusy = true
      try {
        const res = await fetch(`${API_BASE}/api/categories/bulk`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: nextActive ? 'activate' : 'deactivate', ids: this.selectedIds }),
        })
        if (!res.ok) {
          const data = await res.json().catch(() => ({}))
          throw new Error(data.detail || `HTTP ${res.status}`)
        }
        const data = await res.json()
        this.showMessage('success', nextActive
          ? `已打开 ${data.updated || 0} 个主分类。`
          : `已关闭 ${data.updated || 0} 个主分类。`)
        await this.loadCategories()
      } catch (err) {
        this.showMessage('error', `${nextActive ? '打开' : '关闭'}主分类失败：${toErrorMessage(err)}`, 4200)
      } finally {
        this.bulkActionBusy = false
      }
    },

    requestDeleteCategories(ids, displayName = null) {
      const validIds = ids.filter(id => Number.isInteger(id) && id !== DEFAULT_CATEGORY_ID)
      if (!validIds.length) return
      const message = displayName
        ? `确认移除主分类“${displayName}”吗？所有关联图片及已删除图片记录都会回退到默认主分类。`
        : `确认移除已选中的 ${validIds.length} 个主分类吗？所有关联图片及已删除图片记录都会回退到默认主分类。`
      this.openConfirmDialog({
        title: '确认移除主分类',
        message,
        confirmLabel: '移除',
        cancelLabel: '取消',
        tone: 'danger',
        onConfirm: () => this.executeDeleteCategories(validIds),
      })
    },

    async executeDeleteCategories(ids) {
      try {
        const res = await fetch(`${API_BASE}/api/categories/bulk`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'delete', ids }),
        })
        if (!res.ok) {
          const data = await res.json().catch(() => ({}))
          throw new Error(data.detail || `HTTP ${res.status}`)
        }
        const data = await res.json()
        this.selectedIds = this.selectedIds.filter(id => !ids.includes(id))
        this.showMessage('success', `已移除 ${data.deleted || 0} 个主分类，相关图片已回退到默认主分类。`)
        await this.loadCategories()
      } catch (err) {
        this.showMessage('error', `移除主分类失败：${toErrorMessage(err)}`, 4200)
      }
    },

    openConfirmDialog(options = {}) {
      this.confirmDialog = {
        ...createDialogState(),
        ...options,
        visible: true,
      }
    },

    closeConfirmDialog() {
      this.confirmDialog = createDialogState()
    },

    async handleConfirmDialogConfirm() {
      const onConfirm = this.confirmDialog.onConfirm
      this.closeConfirmDialog()
      if (typeof onConfirm === 'function') {
        await onConfirm()
      }
    },
  },
}
</script>

<style scoped lang="css">
.category-page {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  height: calc(100dvh - 5rem);
  min-height: calc(100vh - 5rem);
  overflow: hidden;
}

.category-page__scroller {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding-right: 0.25rem;
  padding-bottom: 5.5rem;
  scrollbar-gutter: stable;
}

.category-page__scroller::-webkit-scrollbar {
  width: 10px;
}

.category-page__scroller::-webkit-scrollbar-track {
  background: transparent;
}

.category-page__scroller::-webkit-scrollbar-thumb {
  border: 2px solid transparent;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.6);
  background-clip: padding-box;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.header-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 34px;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  background: #ffffff;
  color: #334155;
  cursor: pointer;
  padding: 0 0.95rem;
  font-size: 0.8rem;
  font-weight: 700;
  white-space: nowrap;
  transition: background 150ms ease, color 150ms ease, box-shadow 150ms ease, border-color 150ms ease, opacity 150ms ease;
}

.header-btn:hover:not(:disabled) {
  background: #e2e8f0;
  color: #1e293b;
  border-color: #94a3b8;
}

.header-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.header-btn--manage {
  width: 96px;
  padding: 0;
}

.header-btn--manage.active {
  background: #0f172a;
  color: #ffffff;
  border-color: #0f172a;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.18);
}

.header-btn--manage.active:hover:not(:disabled) {
  background: #0f172a;
  color: #ffffff;
  border-color: #0f172a;
}

.header-btn--primary {
  background: linear-gradient(135deg, #0f766e, #0284c7);
  color: #ffffff;
  border-color: transparent;
  box-shadow: 0 10px 24px rgba(8, 145, 178, 0.18);
}

.header-btn--primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #0f766e, #0284c7);
  color: #ffffff;
  border-color: transparent;
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

.page-message-enter-active,
.page-message-leave-active {
  transition: opacity 180ms ease, transform 180ms ease;
}

.page-message-enter-from,
.page-message-leave-to {
  opacity: 0;
  transform: translate(-50%, -10px);
}

.empty-hint {
  border: 2px dashed #cbd5e1;
  background: #f8fafc;
  border-radius: 1rem;
  padding: 4rem 1rem;
  text-align: center;
  color: #94a3b8;
  font-size: 0.9rem;
}

.empty-hint__icon {
  display: block;
  margin-bottom: 0.75rem;
  font-size: 2.6rem;
}

.category-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 420px), 420px));
  gap: 1rem;
  justify-content: start;
  align-content: start;
}

.category-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.95rem;
  width: 100%;
  min-height: 250px;
  aspect-ratio: 14 / 8;
  border: 1px solid rgba(203, 213, 225, 0.82);
  border-radius: 22px;
  padding: 1rem;
  background:
    radial-gradient(circle at top left, rgba(255, 255, 255, 0.96), transparent 45%),
    linear-gradient(160deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.08);
  text-align: left;
  transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease, opacity 180ms ease;
}

.category-card--manage:hover,
.category-card:hover {
  transform: translateY(-3px);
  border-color: rgba(14, 165, 233, 0.42);
  box-shadow: 0 24px 42px rgba(15, 23, 42, 0.12);
}

.category-card--default {
  background:
    radial-gradient(circle at top right, rgba(254, 240, 138, 0.7), transparent 35%),
    linear-gradient(160deg, rgba(255, 251, 235, 0.98), rgba(255, 255, 255, 0.98));
}

.category-card--inactive {
  opacity: 0.72;
}

.category-card--selected {
  border-color: #0f172a;
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.16);
}

.category-card__topline,
.category-card__main,
.category-card__lead,
.category-card__meta,
.category-card__stats,
.category-card__bottom,
.category-card__actions {
  display: flex;
  align-items: center;
}

.category-card__topline,
.category-card__main {
  justify-content: space-between;
  gap: 0.8rem;
}

.category-card__lead,
.category-card__meta,
.category-card__stats,
.category-card__actions {
  gap: 0.5rem;
}

.category-card__lead {
  min-width: 0;
}

.category-card__meta {
  min-width: 2rem;
  justify-content: flex-end;
}

.category-card__badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 46px;
  border-radius: 16px;
  background: linear-gradient(135deg, #0f766e, #0284c7);
  color: #fff;
  font-size: 1rem;
  font-weight: 900;
}

.category-card__pill,
.category-card__stat {
  border-radius: 999px;
  padding: 0.34rem 0.68rem;
  font-size: 0.72rem;
  font-weight: 800;
}

.category-card__pill {
  background: rgba(226, 232, 240, 0.92);
  color: #475569;
}

.category-card__pick {
  width: 26px;
  height: 26px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 2px solid rgba(15, 23, 42, 0.85);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.12);
  padding: 0;
  cursor: pointer;
  transition: transform 140ms ease, background 140ms ease, border-color 140ms ease;
}

.category-card__pick:hover:not(:disabled) {
  transform: scale(1.04);
}

.category-card__pick-mark {
  color: #ffffff;
  font-size: 0.8rem;
  font-weight: 700;
  line-height: 1;
}

.category-card--selected .category-card__pick {
  border-color: #0f172a;
  background: #0f172a;
}

.category-card__title {
  margin: 0;
  color: #0f172a;
  font-size: 1.05rem;
  font-weight: 800;
}

.category-card__name {
  margin: 0.24rem 0 0;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.category-card__title-group {
  min-width: 0;
}

.category-card__description {
  margin: 0;
  color: #334155;
  font-size: 0.86rem;
  line-height: 1.7;
  min-height: 3.4rem;
}

.category-card__stat {
  background: rgba(241, 245, 249, 0.94);
  color: #334155;
}

.category-switch {
  position: relative;
  width: 48px;
  height: 28px;
  border: 0;
  border-radius: 999px;
  background: #cbd5e1;
  cursor: pointer;
  transition: background 160ms ease, opacity 160ms ease;
}

.category-switch--on {
  background: #0f766e;
}

.category-switch__knob {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 22px;
  height: 22px;
  border-radius: 999px;
  background: #fff;
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.18);
  transition: transform 160ms ease;
}

.category-switch--on .category-switch__knob {
  transform: translateX(20px);
}

.category-switch:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.category-card__bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
  margin-top: auto;
}

.category-card__stats {
  flex: 1 1 auto;
  flex-wrap: wrap;
}

.category-card__actions {
  flex-shrink: 0;
  justify-content: flex-end;
}

.category-card__action {
  border: 0;
  border-radius: 12px;
  padding: 0.5rem 0.8rem;
  background: rgba(226, 232, 240, 0.86);
  color: #334155;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 140ms ease, color 140ms ease, transform 140ms ease;
}

.category-card__action:hover {
  background: #e2e8f0;
  color: #0f172a;
  transform: translateY(-1px);
}

.category-card__action--danger {
  background: rgba(254, 226, 226, 0.92);
  color: #b91c1c;
}

.category-card__action--hidden {
  visibility: hidden;
  pointer-events: none;
}

@media (max-width: 720px) {
  .category-page {
    height: auto;
    min-height: 0;
    overflow: visible;
  }

  .category-page__scroller {
    overflow: visible;
    padding-bottom: 6rem;
  }

  .header-actions {
    gap: 0.45rem;
  }
}

@media (orientation: portrait) {
  .category-grid {
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 280px), 280px));
  }

  .category-card {
    width: 100%;
    min-height: 300px;
    aspect-ratio: 5 / 6;
  }

  .category-card__bottom {
    align-items: stretch;
    flex-direction: column;
  }

  .category-card__actions {
    width: 100%;
    justify-content: flex-end;
  }
}

@media (max-width: 640px) {
  .floating-message {
    top: 0.75rem;
    min-width: calc(100vw - 1rem);
    max-width: calc(100vw - 1rem);
  }

  .header-actions {
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .header-btn--manage {
    width: 90px;
  }

  .category-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .category-card {
    aspect-ratio: auto;
  }
}
</style>