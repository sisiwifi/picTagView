<template>
  <section class="top-level-page tag-overview-page" :style="pageVars">
    <TopLevelPageHeader
      title="标签总览"
      subtitle="左侧按首字母浏览全部标签，右侧保留高频与最近使用入口。"
    >
      <div class="tag-overview-page__toolbar">
        <button
          class="tag-overview-page__toolbar-btn"
          type="button"
          :disabled="tagFormVisible || tagFormSaving || confirmDialogVisible || confirmDialogBusy"
          @click="openCreateTagForm()"
        >
          增加标签
        </button>
        <button
          class="tag-overview-page__toolbar-btn"
          :class="{ 'tag-overview-page__toolbar-btn--active': editMode }"
          type="button"
          :disabled="tagFormVisible || tagFormSaving || confirmDialogVisible || confirmDialogBusy"
          @click="toggleEditMode"
        >
          {{ editMode ? '完成编辑' : '编辑标签' }}
        </button>
      </div>
      <div v-if="!loading && !loadError" class="tag-overview-page__summary">
        <span class="tag-overview-page__summary-pill">{{ tags.length }} 个 Tag</span>
        <span class="tag-overview-page__summary-pill">{{ tagGroups.length }} 个字母分组</span>
      </div>
    </TopLevelPageHeader>

    <div v-if="actionError" class="tag-overview-page__alert" role="alert">
      {{ actionError }}
    </div>

    <LoadingSpinner v-if="loading" />

    <div v-else-if="loadError" class="tag-overview-empty tag-overview-empty--error">
      <span class="tag-overview-empty__icon">!</span>
      <p>{{ loadError }}</p>
    </div>

    <div v-else-if="!tags.length" class="tag-overview-empty">
      <span class="tag-overview-empty__icon">🏷</span>
      <p>当前还没有可显示的标签。</p>
    </div>

    <div v-else class="tag-overview-page__layout">
      <section class="tag-overview-page__main">
        <article
          v-for="group in tagGroups"
          :key="group.key"
          class="tag-overview-group"
        >
          <header class="tag-overview-group__header">
            <div>
              <h3 class="tag-overview-group__title">{{ group.key }}</h3>
              <p class="tag-overview-group__meta">{{ group.tags.length }} 个标签</p>
            </div>
            <button
              v-if="groupHasOverflow(group.key)"
              class="tag-overview-group__toggle"
              type="button"
              @click="toggleGroup(group.key)"
            >
              {{ isGroupExpanded(group.key) ? '收起' : '展开更多' }}
            </button>
          </header>

          <div class="tag-overview-group__viewport">
            <div
              :ref="`group-body-${group.key}`"
              class="tag-overview-group__chips"
              :class="{ 'tag-overview-group__chips--collapsed': !isGroupExpanded(group.key) }"
            >
              <span
                v-for="tag in group.tags"
                :key="tag.id"
                class="tag-overview-chip-shell"
                :style="chipStyle(tag)"
              >
                <button
                  class="tag-chip tag-overview-chip"
                  type="button"
                  :title="editMode ? `编辑标签：${tag.name || ''}` : (tag.description || '')"
                  @click="openTag(tag)"
                >
                  {{ tag.display_name || tag.name || '' }}
                </button>
                <button
                  v-if="editMode"
                  class="tag-overview-chip__remove"
                  type="button"
                  :disabled="tagFormVisible || tagFormSaving || confirmDialogBusy"
                  :title="`删除标签 ${tag.name || ''}`"
                  @click="requestDeleteTag(tag)"
                >x</button>
              </span>
            </div>

            <div
              v-if="groupHasOverflow(group.key) && !isGroupExpanded(group.key)"
              class="tag-overview-group__fade"
              aria-hidden="true"
            ></div>
          </div>
        </article>
      </section>

      <aside class="tag-overview-page__sidebar">
        <section class="tag-rank-card">
          <header class="tag-rank-card__header">
            <h3 class="tag-rank-card__title">使用次数 Top 10</h3>
            <p class="tag-rank-card__subtitle">按 usage_count 降序</p>
          </header>
          <ol class="tag-rank-card__list">
            <li v-for="(tag, index) in topUsageTags" :key="`usage-${tag.id}`" class="tag-rank-card__item">
              <div class="tag-rank-card__button" :class="{ 'tag-rank-card__button--editing': editMode }">
                <span class="tag-rank-card__index">{{ index + 1 }}</span>
                <button
                  class="tag-chip tag-rank-card__chip"
                  type="button"
                  :style="chipStyle(tag)"
                  :title="editMode ? `编辑标签：${tag.name || ''}` : (tag.description || '')"
                  @click="openTag(tag)"
                >
                  <span
                    :ref="`rank-chip-${rankChipKey('usage', tag.id)}`"
                    class="tag-rank-card__chip-viewport"
                  >
                    <span
                      class="tag-rank-card__chip-track"
                      :class="{ 'tag-rank-card__chip-track--scrolling': isRankChipAutoScrolling(rankChipKey('usage', tag.id)) }"
                      :style="rankChipTrackStyle(rankChipKey('usage', tag.id))"
                    >
                      <span class="tag-rank-card__chip-label">{{ tag.display_name || tag.name || '' }}</span>
                      <span
                        v-if="isRankChipAutoScrolling(rankChipKey('usage', tag.id))"
                        class="tag-rank-card__chip-gap"
                        aria-hidden="true"
                      ></span>
                      <span
                        v-if="isRankChipAutoScrolling(rankChipKey('usage', tag.id))"
                        class="tag-rank-card__chip-label"
                        aria-hidden="true"
                      >{{ tag.display_name || tag.name || '' }}</span>
                    </span>
                  </span>
                </button>
                <span class="tag-rank-card__metric">{{ formatUsageCount(tag.usage_count) }}</span>
                <button
                  v-if="editMode"
                  class="tag-rank-card__remove"
                  type="button"
                  :disabled="tagFormVisible || tagFormSaving || confirmDialogBusy"
                  :title="`删除标签 ${tag.name || ''}`"
                  @click="requestDeleteTag(tag)"
                >x</button>
              </div>
            </li>
          </ol>
        </section>

        <section class="tag-rank-card">
          <header class="tag-rank-card__header">
            <h3 class="tag-rank-card__title">最近使用 Top 10</h3>
            <p class="tag-rank-card__subtitle">按 last_used_at 降序</p>
          </header>
          <ol v-if="recentTags.length" class="tag-rank-card__list">
            <li v-for="(tag, index) in recentTags" :key="`recent-${tag.id}`" class="tag-rank-card__item">
              <div class="tag-rank-card__button" :class="{ 'tag-rank-card__button--editing': editMode }">
                <span class="tag-rank-card__index">{{ index + 1 }}</span>
                <button
                  class="tag-chip tag-rank-card__chip"
                  type="button"
                  :style="chipStyle(tag)"
                  :title="editMode ? `编辑标签：${tag.name || ''}` : (tag.description || '')"
                  @click="openTag(tag)"
                >
                  <span
                    :ref="`rank-chip-${rankChipKey('recent', tag.id)}`"
                    class="tag-rank-card__chip-viewport"
                  >
                    <span
                      class="tag-rank-card__chip-track"
                      :class="{ 'tag-rank-card__chip-track--scrolling': isRankChipAutoScrolling(rankChipKey('recent', tag.id)) }"
                      :style="rankChipTrackStyle(rankChipKey('recent', tag.id))"
                    >
                      <span class="tag-rank-card__chip-label">{{ tag.display_name || tag.name || '' }}</span>
                      <span
                        v-if="isRankChipAutoScrolling(rankChipKey('recent', tag.id))"
                        class="tag-rank-card__chip-gap"
                        aria-hidden="true"
                      ></span>
                      <span
                        v-if="isRankChipAutoScrolling(rankChipKey('recent', tag.id))"
                        class="tag-rank-card__chip-label"
                        aria-hidden="true"
                      >{{ tag.display_name || tag.name || '' }}</span>
                    </span>
                  </span>
                </button>
                <span class="tag-rank-card__metric tag-rank-card__metric--datetime">{{ formatLastUsedAt(tag.last_used_at) }}</span>
                <button
                  v-if="editMode"
                  class="tag-rank-card__remove"
                  type="button"
                  :disabled="tagFormVisible || tagFormSaving || confirmDialogBusy"
                  :title="`删除标签 ${tag.name || ''}`"
                  @click="requestDeleteTag(tag)"
                >x</button>
              </div>
            </li>
          </ol>
          <p v-else class="tag-rank-card__empty">暂时还没有可排序的最近使用标签。</p>
        </section>
      </aside>
    </div>

    <TagFormDialog
      :visible="tagFormVisible"
      :saving="tagFormSaving"
      :mode="tagFormMode"
      :initial-tag="tagFormTag"
      :existing-names="tagFormExistingNames"
      :error-message="tagFormError"
      @close="closeTagForm"
      @submit="submitTagForm"
    />

    <ConfirmationDialog
      :visible="confirmDialogVisible"
      title="删除标签"
      :message="confirmDialogMessage"
      confirm-label="确认删除"
      cancel-label="取消"
      tone="danger"
      :busy="confirmDialogBusy"
      busy-label="删除中…"
      :model-value="confirmDialogInput"
      :input-visible="true"
      input-label="输入标签 name 以确认"
      :input-placeholder="confirmDialogTarget?.name || ''"
      :input-hint="confirmDialogHint"
      @update:modelValue="updateConfirmDialogInput"
      @cancel="closeDeleteConfirmation"
      @confirm="confirmDeleteTag"
    />
  </section>
</template>

<script>
import ConfirmationDialog from '../components/ConfirmationDialog.vue'
import LoadingSpinner from '../components/LoadingSpinner.vue'
import TagFormDialog from '../components/TagFormDialog.vue'
import TopLevelPageHeader from './TopLevelPageHeader.vue'
import { normalizeTagColors } from '../utils/tagColors'
import { API_BASE, topLevelPageVars } from './topLevelPageConvention'

const TAG_PAGE_SIZE = 400
const GROUP_COLLAPSED_HEIGHT_PX = 88
const RANK_TAG_AUTOSCROLL_GAP_PX = 24
const RANK_TAG_AUTOSCROLL_SPEED_PX_PER_SECOND = 28
const RANK_TAG_AUTOSCROLL_MIN_DURATION_S = 3.8

function booleanMapEquals(left, right) {
  const leftKeys = Object.keys(left || {})
  const rightKeys = Object.keys(right || {})
  if (leftKeys.length !== rightKeys.length) return false
  return leftKeys.every(key => Boolean(left[key]) === Boolean(right[key]))
}

function rankOverflowMapEquals(left, right) {
  const leftKeys = Object.keys(left || {})
  const rightKeys = Object.keys(right || {})
  if (leftKeys.length !== rightKeys.length) return false
  return leftKeys.every(key => {
    const leftItem = left[key] || {}
    const rightItem = right[key] || {}
    return Boolean(leftItem.active) === Boolean(rightItem.active)
      && Number(leftItem.distance || 0) === Number(rightItem.distance || 0)
      && Number(leftItem.duration || 0) === Number(rightItem.duration || 0)
  })
}

function normalizeInitial(name) {
  const firstChar = String(name || '').trim().charAt(0).toUpperCase()
  return /^[A-Z]$/.test(firstChar) ? firstChar : '#'
}

function compareByDisplayName(left, right) {
  const leftLabel = String(left?.display_name || left?.name || '').toLowerCase()
  const rightLabel = String(right?.display_name || right?.name || '').toLowerCase()
  if (leftLabel && rightLabel && leftLabel !== rightLabel) {
    return leftLabel.localeCompare(rightLabel)
  }
  return Number(left?.id || 0) - Number(right?.id || 0)
}

function compareByUsage(left, right) {
  const usageDiff = Number(right?.usage_count || 0) - Number(left?.usage_count || 0)
  if (usageDiff !== 0) return usageDiff
  return compareByDisplayName(left, right)
}

function compareByLastUsed(left, right) {
  const leftValue = String(left?.last_used_at || '')
  const rightValue = String(right?.last_used_at || '')
  if (leftValue !== rightValue) {
    return rightValue.localeCompare(leftValue)
  }
  return compareByUsage(left, right)
}

export default {
  name: 'TagOverviewPage',
  components: {
    ConfirmationDialog,
    LoadingSpinner,
    TagFormDialog,
    TopLevelPageHeader,
  },
  data() {
    return {
      loading: false,
      loadError: '',
      actionError: '',
      tags: [],
      editMode: false,
      groupExpansion: {},
      groupOverflow: {},
      rankChipOverflow: {},
      tagFormVisible: false,
      tagFormMode: 'create',
      tagFormSaving: false,
      tagFormError: '',
      tagFormTag: null,
      tagFormExistingNames: [],
      confirmDialogVisible: false,
      confirmDialogBusy: false,
      confirmDialogTarget: null,
      confirmDialogInput: '',
      confirmDialogError: '',
    }
  },
  computed: {
    pageVars() {
      return {
        ...topLevelPageVars(),
        '--tag-overview-collapsed-height': `${GROUP_COLLAPSED_HEIGHT_PX}px`,
      }
    },
    tagGroups() {
      const groups = new Map()
      for (const tag of this.tags) {
        const initial = normalizeInitial(tag?.name || tag?.display_name)
        if (!groups.has(initial)) {
          groups.set(initial, [])
        }
        groups.get(initial).push(tag)
      }

      return Array.from(groups.entries())
        .map(([key, items]) => ({
          key,
          tags: [...items].sort(compareByDisplayName),
        }))
        .sort((left, right) => {
          if (left.key === right.key) return 0
          if (left.key === '#') return 1
          if (right.key === '#') return -1
          return left.key.localeCompare(right.key)
        })
    },
    topUsageTags() {
      return [...this.tags]
        .sort(compareByUsage)
        .slice(0, 10)
    },
    recentTags() {
      return this.tags
        .filter(tag => String(tag?.last_used_at || '').trim())
        .sort(compareByLastUsed)
        .slice(0, 10)
    },
    confirmDialogMessage() {
      const tag = this.confirmDialogTarget
      if (!tag) return ''
      return `此操作会永久删除标签“${tag.display_name || tag.name || ''}”。\n请输入其 name 完成二次确认。`
    },
    confirmDialogHint() {
      if (this.confirmDialogError) {
        return this.confirmDialogError
      }
      const name = String(this.confirmDialogTarget?.name || '')
      if (!name) return ''
      return `必须精确输入 ${name}`
    },
  },
  mounted() {
    this.fetchAllTags()
    this.installLayoutResizeObserver()
    window.addEventListener('resize', this.handleWindowResize, { passive: true })
  },
  beforeUnmount() {
    this.layoutResizeObserver?.disconnect?.()
    window.removeEventListener('resize', this.handleWindowResize)
  },
  methods: {
    chipStyle(tag) {
      const { color, borderColor, backgroundColor } = normalizeTagColors(tag)
      return {
        '--tag-chip-color': color,
        '--tag-chip-border-color': borderColor,
        '--tag-chip-bg': backgroundColor,
      }
    },
    async fetchAllTags() {
      this.loading = true
      this.loadError = ''

      try {
        let offset = 0
        let total = Infinity
        const nextTags = []

        while (offset < total) {
          const res = await fetch(`${API_BASE}/api/tags?offset=${offset}&limit=${TAG_PAGE_SIZE}`)
          if (!res.ok) {
            throw new Error(`HTTP ${res.status}`)
          }

          const payload = await res.json()
          const items = Array.isArray(payload?.items) ? payload.items : []
          total = Number(payload?.total || 0)
          nextTags.push(...items)

          if (!items.length) {
            break
          }
          offset += items.length
        }

        this.tags = nextTags
        this.syncGroupState()
        this.refreshLayoutMeasurements()
      } catch (err) {
        this.tags = []
        this.loadError = `标签总览加载失败：${err?.message || '未知错误'}`
      } finally {
        this.loading = false
      }
    },
    syncGroupState() {
      const nextExpansion = {}
      const nextOverflow = {}
      for (const group of this.tagGroups) {
        nextExpansion[group.key] = Boolean(this.groupExpansion[group.key])
        nextOverflow[group.key] = Boolean(this.groupOverflow[group.key])
      }
      this.groupExpansion = nextExpansion
      this.groupOverflow = nextOverflow
    },
    measureGroupOverflow() {
      const nextOverflow = {}
      for (const group of this.tagGroups) {
        const rawRef = this.$refs[`group-body-${group.key}`]
        const el = Array.isArray(rawRef) ? rawRef[0] : rawRef
        if (!el) {
          nextOverflow[group.key] = false
          continue
        }

        nextOverflow[group.key] = el.scrollHeight > el.clientHeight + 2
        if (this.groupExpansion[group.key]) {
          nextOverflow[group.key] = el.scrollHeight > GROUP_COLLAPSED_HEIGHT_PX + 2
        }
      }
      if (!booleanMapEquals(this.groupOverflow, nextOverflow)) {
        this.groupOverflow = nextOverflow
      }
    },
    measureRankChipOverflow() {
      const nextOverflow = {}
      const rankEntries = [
        ...this.topUsageTags.map(tag => this.rankChipKey('usage', tag?.id)),
        ...this.recentTags.map(tag => this.rankChipKey('recent', tag?.id)),
      ]

      for (const key of rankEntries) {
        const rawRef = this.$refs[`rank-chip-${key}`]
        const viewport = Array.isArray(rawRef) ? rawRef[0] : rawRef
        const label = viewport?.querySelector?.('.tag-rank-card__chip-label')
        if (!viewport || !label) continue

        const labelWidth = Math.ceil(label.scrollWidth)
        const overflowDistance = labelWidth - viewport.clientWidth
        if (overflowDistance <= 0) continue

        const duration = Math.max(
          RANK_TAG_AUTOSCROLL_MIN_DURATION_S,
          Number(((labelWidth + RANK_TAG_AUTOSCROLL_GAP_PX) / RANK_TAG_AUTOSCROLL_SPEED_PX_PER_SECOND).toFixed(2))
        )
        nextOverflow[key] = {
          active: true,
          distance: Math.ceil(labelWidth + RANK_TAG_AUTOSCROLL_GAP_PX),
          duration,
        }
      }

      if (!rankOverflowMapEquals(this.rankChipOverflow, nextOverflow)) {
        this.rankChipOverflow = nextOverflow
      }
    },
    refreshLayoutMeasurements() {
      this.$nextTick(() => {
        window.requestAnimationFrame(() => {
          this.measureGroupOverflow()
          this.measureRankChipOverflow()
        })
      })
    },
    installLayoutResizeObserver() {
      if (typeof ResizeObserver === 'undefined' || !this.$el) return
      this.layoutResizeObserver = new ResizeObserver(() => {
        this.refreshLayoutMeasurements()
      })
      this.layoutResizeObserver.observe(this.$el)
    },
    handleWindowResize() {
      this.refreshLayoutMeasurements()
    },
    rankChipKey(section, tagId) {
      return `${section}-${Number(tagId || 0)}`
    },
    isRankChipAutoScrolling(key) {
      return Boolean(this.rankChipOverflow[key]?.active)
    },
    rankChipTrackStyle(key) {
      const state = this.rankChipOverflow[key]
      if (!state?.active) return null
      return {
        '--tag-rank-scroll-distance': `${state.distance}px`,
        '--tag-rank-scroll-duration': `${state.duration}s`,
      }
    },
    async fetchTagFormExistingNames() {
      const fallbackNames = this.tags
        .map(tag => String(tag?.name || '').trim())
        .filter(Boolean)

      try {
        const res = await fetch(`${API_BASE}/api/tags?offset=0&limit=1000`)
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`)
        }
        const data = await res.json()
        return [...new Set((data.items || []).map(item => String(item?.name || '').trim()).filter(Boolean))].sort()
      } catch {
        return [...new Set(fallbackNames)].sort()
      }
    },
    async reserveTagDraft() {
      const res = await fetch(`${API_BASE}/api/tags/draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      if (!res.ok) {
        const payload = await res.json().catch(() => ({}))
        throw new Error(payload.detail || `HTTP ${res.status}`)
      }
      return res.json()
    },
    resetTagFormState() {
      this.tagFormVisible = false
      this.tagFormMode = 'create'
      this.tagFormSaving = false
      this.tagFormError = ''
      this.tagFormTag = null
      this.tagFormExistingNames = []
    },
    async closeTagForm() {
      if (this.tagFormSaving) return
      const shouldDeleteDraft = this.tagFormMode === 'create' && Number.isInteger(this.tagFormTag?.id)
      const draftId = shouldDeleteDraft ? this.tagFormTag.id : null
      this.resetTagFormState()

      if (!draftId) return
      try {
        await fetch(`${API_BASE}/api/tags/${draftId}`, { method: 'DELETE' })
      } catch {
        // keep UI responsive even if draft cleanup fails
      }
    },
    async openCreateTagForm() {
      if (this.tagFormVisible || this.tagFormSaving || this.confirmDialogVisible || this.confirmDialogBusy) return

      this.tagFormError = ''
      this.actionError = ''
      try {
        const [draftTag, existingNames] = await Promise.all([
          this.reserveTagDraft(),
          this.fetchTagFormExistingNames(),
        ])
        this.tagFormMode = 'create'
        this.tagFormTag = draftTag
        this.tagFormExistingNames = existingNames
        this.tagFormVisible = true
      } catch (err) {
        this.tagFormError = ''
        this.actionError = `新建标签初始化失败：${err?.message || '未知错误'}`
      }
    },
    async fetchTagDetail(tagId) {
      const res = await fetch(`${API_BASE}/api/tags/${tagId}`)
      if (!res.ok) {
        const payload = await res.json().catch(() => ({}))
        throw new Error(payload.detail || `HTTP ${res.status}`)
      }
      return res.json()
    },
    async openEditTagForm(tag) {
      const tagId = Number(tag?.id)
      if (!Number.isInteger(tagId) || this.tagFormVisible || this.tagFormSaving || this.confirmDialogVisible || this.confirmDialogBusy) return

      this.tagFormError = ''
      this.actionError = ''
      try {
        const [detail, existingNames] = await Promise.all([
          this.fetchTagDetail(tagId),
          this.fetchTagFormExistingNames(),
        ])
        this.tagFormMode = 'edit'
        this.tagFormTag = detail
        this.tagFormExistingNames = existingNames
        this.tagFormVisible = true
      } catch (err) {
        this.actionError = `标签详情读取失败：${err?.message || '未知错误'}`
      }
    },
    async submitTagForm(payload) {
      const mode = this.tagFormMode
      const tagId = mode === 'create'
        ? Number(this.tagFormTag?.id)
        : Number(payload?.id || this.tagFormTag?.id)
      if (!Number.isInteger(tagId) || this.tagFormSaving) return

      this.tagFormSaving = true
      this.tagFormError = ''
      try {
        const requestBody = mode === 'create'
          ? { ...payload, created_by: 'admin' }
          : payload
        const res = await fetch(`${API_BASE}/api/tags/${tagId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(requestBody),
        })
        if (!res.ok) {
          const responsePayload = await res.json().catch(() => ({}))
          throw new Error(responsePayload.detail || `HTTP ${res.status}`)
        }

        const savedTag = await res.json()
        const savedGroupKey = normalizeInitial(savedTag?.name || savedTag?.display_name)
        const existingIndex = this.tags.findIndex(tag => tag?.id === savedTag?.id)
        const nextTags = [...this.tags]
        if (existingIndex >= 0) {
          nextTags.splice(existingIndex, 1, savedTag)
        } else {
          nextTags.push(savedTag)
        }
        this.tags = nextTags
        this.groupExpansion = {
          ...this.groupExpansion,
          [savedGroupKey]: true,
        }
        this.resetTagFormState()
        this.syncGroupState()
        this.refreshLayoutMeasurements()
      } catch (err) {
        this.tagFormError = `标签保存失败：${err?.message || '未知错误'}`
      } finally {
        this.tagFormSaving = false
      }
    },
    toggleEditMode() {
      if (this.tagFormVisible || this.tagFormSaving || this.confirmDialogVisible || this.confirmDialogBusy) return
      this.editMode = !this.editMode
      this.refreshLayoutMeasurements()
    },
    requestDeleteTag(tag) {
      if (!this.editMode || !Number.isInteger(tag?.id) || this.tagFormVisible || this.tagFormSaving) return
      this.confirmDialogTarget = tag
      this.confirmDialogInput = ''
      this.confirmDialogError = ''
      this.confirmDialogBusy = false
      this.confirmDialogVisible = true
      this.actionError = ''
    },
    closeDeleteConfirmation(force = false) {
      if (this.confirmDialogBusy && !force) return
      this.confirmDialogVisible = false
      this.confirmDialogTarget = null
      this.confirmDialogInput = ''
      this.confirmDialogError = ''
    },
    updateConfirmDialogInput(value) {
      this.confirmDialogInput = value
      if (this.confirmDialogError) {
        this.confirmDialogError = ''
      }
    },
    async confirmDeleteTag() {
      const tag = this.confirmDialogTarget
      const tagId = Number(tag?.id)
      const expectedName = String(tag?.name || '').trim()
      if (!Number.isInteger(tagId) || !expectedName) return

      if (String(this.confirmDialogInput || '').trim() !== expectedName) {
        this.confirmDialogError = `删除确认失败：请输入标签 name “${expectedName}”。`
        return
      }

      this.confirmDialogBusy = true
      this.confirmDialogError = ''
      this.actionError = ''
      try {
        const res = await fetch(`${API_BASE}/api/tags/${tagId}`, { method: 'DELETE' })
        if (!res.ok) {
          const payload = await res.json().catch(() => ({}))
          throw new Error(payload.detail || `HTTP ${res.status}`)
        }

        this.tags = this.tags.filter(item => item?.id !== tagId)
        this.syncGroupState()
        this.refreshLayoutMeasurements()
        this.closeDeleteConfirmation(true)
      } catch (err) {
        this.confirmDialogError = `删除标签失败：${err?.message || '未知错误'}`
      } finally {
        this.confirmDialogBusy = false
      }
    },
    toggleGroup(groupKey) {
      this.groupExpansion = {
        ...this.groupExpansion,
        [groupKey]: !this.groupExpansion[groupKey],
      }
      this.refreshLayoutMeasurements()
    },
    isGroupExpanded(groupKey) {
      return Boolean(this.groupExpansion[groupKey])
    },
    groupHasOverflow(groupKey) {
      return Boolean(this.groupOverflow[groupKey])
    },
    openTag(tag) {
      if (!Number.isInteger(tag?.id)) return
      if (this.editMode) {
        void this.openEditTagForm(tag)
        return
      }
      this.$router.push(`/tags/${tag.id}`)
    },
    formatUsageCount(value) {
      return `${Number(value || 0)} 次`
    },
    formatLastUsedAt(value) {
      const normalized = String(value || '').trim()
      if (!/^\d{14}$/.test(normalized)) {
        return '未记录'
      }
      return `${normalized.slice(0, 4)}-${normalized.slice(4, 6)}-${normalized.slice(6, 8)} ${normalized.slice(8, 10)}:${normalized.slice(10, 12)}`
    },
  },
}
</script>

<style scoped lang="css">
.tag-overview-page {
  @apply flex flex-col gap-6;
  min-height: 0;
}

.tag-overview-page__summary {
  @apply flex flex-wrap items-center gap-2;
}

.tag-overview-page__toolbar {
  @apply flex flex-wrap items-center gap-2;
}

.tag-overview-page__alert {
  @apply rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700;
}

.tag-overview-page__toolbar-btn {
  @apply rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition-colors duration-150;
}

.tag-overview-page__toolbar-btn:hover:not(:disabled) {
  @apply border-slate-300 bg-slate-100 text-slate-900;
}

.tag-overview-page__toolbar-btn:disabled {
  @apply cursor-not-allowed opacity-60;
}

.tag-overview-page__toolbar-btn--active {
  @apply border-amber-300 bg-amber-50 text-amber-800;
}

.tag-overview-page__summary-pill {
  @apply inline-flex items-center rounded-full border border-slate-200 bg-white px-3 py-1 text-xs font-semibold text-slate-600 shadow-sm;
}

.tag-overview-empty {
  @apply flex min-h-[320px] flex-col items-center justify-center rounded-[1.8rem] border border-dashed border-slate-300 bg-slate-50 text-center text-slate-600;
}

.tag-overview-empty--error {
  @apply border-rose-200 bg-rose-50 text-rose-700;
}

.tag-overview-empty__icon {
  @apply mb-4 text-4xl leading-none;
}

.tag-overview-page__layout {
  display: grid;
  grid-template-columns: minmax(0, 2.2fr) minmax(280px, 0.95fr);
  gap: 1.05rem;
  align-items: start;
  min-height: 0;
  padding: 1.05rem;
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 2rem;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.74), rgba(248, 250, 252, 0.92)),
    radial-gradient(circle at top right, rgba(226, 232, 240, 0.46), transparent 38%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
}

.tag-overview-page__main {
  @apply flex flex-col gap-4;
  min-height: 0;
}

.tag-overview-group {
  @apply rounded-[1.6rem] px-5 py-4;
  border: 1px solid rgba(226, 232, 240, 0.88);
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 14px 32px rgba(15, 23, 42, 0.05);
  backdrop-filter: blur(8px);
}

.tag-overview-group__header {
  @apply mb-3 flex items-start justify-between gap-3;
}

.tag-overview-group__title {
  @apply m-0 text-lg font-semibold text-slate-900;
}

.tag-overview-group__meta {
  @apply mt-1 mb-0 text-xs font-medium uppercase tracking-[0.18em] text-slate-400;
}

.tag-overview-group__toggle {
  @apply rounded-full px-3 py-1 text-xs font-semibold text-slate-600 transition-colors duration-150;
  border: 1px solid rgba(203, 213, 225, 0.85);
  background: rgba(248, 250, 252, 0.78);
}

.tag-overview-group__toggle:hover {
  @apply border-slate-300 bg-slate-100 text-slate-900;
}

.tag-overview-group__viewport {
  position: relative;
  padding-top: 0.14rem;
}

.tag-overview-group__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.tag-overview-chip-shell {
  display: inline-flex;
  align-items: center;
  gap: 0.38rem;
  min-height: 1.42rem;
  padding: 0.16rem 0.56rem;
  border-radius: 999px;
  border: 1px solid var(--tag-chip-border-color, var(--tag-chip-color, #64748b));
  color: var(--tag-chip-color, #334155);
  background: var(--tag-chip-bg, rgba(100, 116, 139, 0.4));
}

.tag-overview-group__chips--collapsed {
  max-height: var(--tag-overview-collapsed-height);
  overflow: hidden;
}

.tag-overview-group__fade {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 3.25rem;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0), rgba(255, 255, 255, 0.88) 56%, rgba(255, 255, 255, 1));
  pointer-events: none;
}

.tag-overview-chip {
  cursor: pointer;
  min-height: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  box-shadow: none;
  transition: box-shadow 140ms ease, background 140ms ease, border-color 140ms ease, color 140ms ease, opacity 140ms ease;
}

.tag-overview-chip:hover {
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.1);
}

.tag-overview-chip__remove {
  border: 0;
  background: transparent;
  color: inherit;
  font-size: 0.76rem;
  font-weight: 700;
  line-height: 1;
  cursor: pointer;
  padding: 0;
}

.tag-overview-chip__remove:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.tag-overview-page__sidebar {
  @apply flex flex-col gap-4;
  position: static;
  align-self: start;
}

.tag-rank-card {
  @apply rounded-[1.6rem] px-4 py-4;
  border: 1px solid rgba(226, 232, 240, 0.88);
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 14px 32px rgba(15, 23, 42, 0.05);
  backdrop-filter: blur(8px);
}

.tag-rank-card__header {
  @apply mb-3 flex flex-col gap-1;
}

.tag-rank-card__title {
  @apply m-0 text-base font-semibold text-slate-900;
}

.tag-rank-card__subtitle {
  @apply m-0 text-xs text-slate-500;
}

.tag-rank-card__list {
  @apply m-0 flex list-none flex-col gap-2 p-0;
}

.tag-rank-card__item {
  @apply m-0;
}

.tag-rank-card__button {
  @apply flex w-full items-center gap-2 rounded-2xl px-2 py-2 text-left transition-colors duration-150;
  border: 1px solid transparent;
  background: rgba(248, 250, 252, 0.88);
}

.tag-rank-card__button:hover {
  @apply border-slate-200 bg-slate-100;
}

.tag-rank-card__button--editing {
  @apply pr-3;
}

.tag-rank-card__index {
  @apply inline-flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white;
}

.tag-rank-card__chip {
  flex: 1 1 auto;
  min-width: 0;
  border: 0;
  background: transparent;
  padding: 0;
}

.tag-rank-card__chip-viewport {
  display: block;
  width: 100%;
  overflow: hidden;
  white-space: nowrap;
}

.tag-rank-card__chip-track {
  display: inline-flex;
  align-items: center;
  min-width: max-content;
  white-space: nowrap;
}

.tag-rank-card__chip-track--scrolling {
  animation: tag-rank-chip-pan var(--tag-rank-scroll-duration, 4s) linear infinite;
  will-change: transform;
}

.tag-rank-card__chip-label {
  display: inline-block;
  flex: 0 0 auto;
  white-space: nowrap;
}

.tag-rank-card__chip-gap {
  width: 1.5rem;
  flex: 0 0 auto;
}

.tag-rank-card__remove {
  border: 0;
  background: transparent;
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 800;
  line-height: 1;
  cursor: pointer;
  padding: 0;
}

.tag-rank-card__remove:hover:not(:disabled) {
  color: #991b1b;
}

.tag-rank-card__remove:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.tag-rank-card__metric {
  @apply ml-auto text-right text-xs font-semibold text-slate-500;
}

.tag-rank-card__metric--datetime {
  min-width: 7.8rem;
}

.tag-rank-card__empty {
  @apply m-0 rounded-2xl bg-slate-50 px-3 py-4 text-sm text-slate-500;
}

@keyframes tag-rank-chip-pan {
  0%, 14% {
    transform: translateX(0);
  }

  100% {
    transform: translateX(calc(-1 * var(--tag-rank-scroll-distance, 0px)));
  }
}

@media (prefers-reduced-motion: reduce) {
  .tag-rank-card__chip-track--scrolling {
    animation: none;
  }
}

@media (max-width: 1100px) {
  .tag-overview-page__layout {
    grid-template-columns: minmax(0, 1fr);
    padding: 0;
    border: 0;
    border-radius: 0;
    background: transparent;
    box-shadow: none;
  }

  .tag-overview-page__sidebar {
    position: static;
  }
}

@media (max-width: 640px) {
  .tag-overview-group {
    @apply px-4 py-4;
  }

  .tag-rank-card__button {
    @apply items-start;
  }

  .tag-rank-card__metric {
    @apply min-w-0;
  }
}
</style>