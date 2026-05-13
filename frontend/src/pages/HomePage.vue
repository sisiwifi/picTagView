<template>
  <section class="top-level-page home-page" :style="pageVars">
    <div class="home-page__shell">
      <div class="home-page__top-shell">
        <TopLevelPageHeader
          hide-text
          title="主页"
          subtitle="按显示主分类统计图片概览，并为当前可见 Tag 连续加载代表图。"
        />

        <div class="stats-row">
          <button class="home-stat-card" type="button" @click="openGalleryOverview">
            <span class="home-stat-card__icon">🖼️</span>
            <div class="home-stat-card__body">
              <span class="home-stat-card__num">{{ formatExactCount(stats.visible_image_count) }}</span>
              <span class="home-stat-card__label">图片总数</span>
            </div>
          </button>

          <button class="home-stat-card home-stat-card--tag" type="button" @click="openTagOverview">
            <span class="home-stat-card__icon">🏷️</span>
            <div class="home-stat-card__body">
              <span class="home-stat-card__num">{{ formatExactCount(stats.global_tag_count) }}</span>
              <span class="home-stat-card__label">标签总数</span>
            </div>
          </button>
        </div>
      </div>

      <section class="home-page__wall-shell">
        <header class="home-page__wall-header">
          <div class="home-page__wall-header-main">
            <h3 class="home-page__wall-title">当前活动图库</h3>
          </div>
          <button
            class="home-page__wall-action"
            type="button"
            :disabled="loadingInitial || loadingMore"
            @click="refreshHomePage"
          >
            重新换一批图
          </button>
        </header>

        <LoadingSpinner v-if="loadingInitial && !tagWallItems.length" />

        <div v-else-if="loadError && !tagWallItems.length" class="home-page__state home-page__state--error">
          <span class="home-page__state-icon">!</span>
          <p class="home-page__state-text">{{ loadError }}</p>
          <button class="home-page__state-action" type="button" @click="refreshHomePage">重试</button>
        </div>

        <div v-else-if="!stats.visible_image_count" class="home-page__state">
          <span class="home-page__state-icon">🖼️</span>
          <p class="home-page__state-text">当前显示主分类下还没有可见图片。先去图库管理导入或恢复可见分类。</p>
          <button class="home-page__state-action" type="button" @click="openGalleryOverview">前往图库总览</button>
        </div>

        <div v-else-if="!stats.visible_tag_count" class="home-page__state">
          <span class="home-page__state-icon">🏷️</span>
          <p class="home-page__state-text">当前显示主分类下暂无可见 Tag。可以先在图片上打标，或检查主分类显示状态。</p>
          <button class="home-page__state-action" type="button" @click="openTagOverview">前往标签总览</button>
        </div>

        <div v-else class="home-page__wall-stage">
          <div ref="wallViewport" class="home-page__wall-viewport" @scroll.passive="handleWallScroll">
            <div class="home-page__wall-virtual" :style="virtualCanvasStyle">
              <div class="home-page__wall-window" :style="virtualWindowStyle">
                <div class="home-page__wall-grid" :style="virtualGridStyle">
                  <ThumbCard
                    v-for="entry in virtualTagWallItems"
                    :key="entry.tag.id"
                    :src="resolvedTagCoverPreviewUrl(entry)"
                    :badge-label="animatedBadgeLabel(entry.cover)"
                    class="home-tag-card"
                    :style="virtualCardStyle"
                    :overlay-opacity="0.24"
                    :rounded="'1.5rem'"
                    @click="openTagWallItem(entry)"
                  >
                    <article class="home-tag-card__body">
                      <div class="home-tag-card__copy">
                        <h3 class="home-tag-card__title">{{ displayTagLabel(entry) }}</h3>
                        <p class="home-tag-card__description">{{ displayTagDescription(entry) }}</p>
                      </div>
                    </article>
                  </ThumbCard>
                </div>
              </div>
            </div>
          </div>

          <div v-if="loadingMore" class="home-page__wall-status">
            <LoadingSpinner>继续加载标签卡片…</LoadingSpinner>
          </div>

          <div v-else-if="loadError && tagWallItems.length" class="home-page__wall-status home-page__wall-status--error">
            <span>{{ loadError }}</span>
            <button class="home-page__inline-action" type="button" @click="loadMoreTagWall">重试继续加载</button>
          </div>

        </div>

        <transition name="home-toast">
          <div v-if="completionToastVisible" class="home-page__floating-toast" role="status" aria-live="polite">
            已加载全部 {{ formatExactCount(stats.visible_tag_count) }} 个可见 Tag
          </div>
        </transition>
      </section>
    </div>
  </section>
</template>

<script>
import LoadingSpinner from '../components/LoadingSpinner.vue'
import ThumbCard from '../components/ThumbCard.vue'
import { resolveAnimatedBadgeLabel } from '../utils/animatedMedia'
import TopLevelPageHeader from './TopLevelPageHeader.vue'
import {
  API_BASE,
  TOP_LEVEL_PAGE_STANDARD,
  resolvePreviewUrl,
  topLevelPageVars,
} from './topLevelPageConvention'

const HOME_BATCH_SIZE = 24
const HOME_GRID_GAP_PX = 18
const HOME_CARD_TARGET_EDGE_PX = 280
const HOME_CARD_MIN_EDGE_PX = 160
const HOME_VIRTUAL_ROWS = 4
const HOME_OVERSCAN_ROWS = 2
const HOME_PREFETCH_THRESHOLD_PX = 960
const HOME_COVER_HISTORY_KEY = 'ptv:home-cover-history:v1'
const HOME_COVER_HISTORY_LIMIT = 120

function createEmptyStats() {
  return {
    visible_image_count: 0,
    global_tag_count: 0,
    visible_tag_count: 0,
  }
}

function toPositiveInt(value) {
  const parsed = Number(value)
  if (!Number.isInteger(parsed) || parsed <= 0) return 0
  return parsed
}

function normalizeIdList(values, limit = HOME_COVER_HISTORY_LIMIT) {
  const normalized = []
  const seen = new Set()
  for (const value of Array.isArray(values) ? values : []) {
    const parsed = toPositiveInt(value)
    if (!parsed || seen.has(parsed)) continue
    seen.add(parsed)
    normalized.push(parsed)
    if (normalized.length >= limit) break
  }
  return normalized
}

function readCoverHistory() {
  if (typeof window === 'undefined') return []
  try {
    return normalizeIdList(JSON.parse(window.localStorage.getItem(HOME_COVER_HISTORY_KEY) || '[]'))
  } catch {
    return []
  }
}

function persistCoverHistory(values) {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(HOME_COVER_HISTORY_KEY, JSON.stringify(normalizeIdList(values)))
  } catch {
    // Ignore local storage write failures and keep the current session working.
  }
}

function mergeTagWallItems(previousItems, nextItems) {
  const merged = []
  const seen = new Set()
  for (const item of [...(Array.isArray(previousItems) ? previousItems : []), ...(Array.isArray(nextItems) ? nextItems : [])]) {
    const tagId = toPositiveInt(item?.tag?.id)
    if (!tagId || seen.has(tagId)) continue
    seen.add(tagId)
    merged.push(item)
  }
  return merged
}

function collectCoverIds(items) {
  return normalizeIdList((items || []).map(item => item?.cover?.id))
}

function formatCompactCount(value) {
  const parsed = Number(value || 0)
  if (!Number.isFinite(parsed) || parsed <= 0) return '0'
  if (parsed < 1000) return String(Math.floor(parsed))
  if (parsed < 10000) return `${(parsed / 1000).toFixed(1).replace(/\.0$/, '')}k`
  return `${Math.floor(parsed / 1000)}k`
}

function formatExactCount(value) {
  const parsed = Number(value || 0)
  if (!Number.isFinite(parsed) || parsed <= 0) return '0'
  return new Intl.NumberFormat('zh-CN').format(Math.floor(parsed))
}

function formatTagTypeLabel(value) {
  switch (String(value || '').trim()) {
    case 'artist':
      return '艺术家'
    case 'copyright':
      return '作品'
    case 'character':
      return '角色'
    case 'series':
      return '系列'
    case 'normal':
    default:
      return '标签'
  }
}

export default {
  name: 'HomePage',
  components: {
    LoadingSpinner,
    ThumbCard,
    TopLevelPageHeader,
  },
  data() {
    return {
      stats: createEmptyStats(),
      tagWallItems: [],
      tagWallTotal: 0,
      loadingInitial: false,
      loadingMore: false,
      loadError: '',
      requestController: null,
      coverHistoryIds: [],
      wallViewportWidth: 0,
      wallViewportHeight: 0,
      wallViewportScrollTop: 0,
      wallResizeObserver: null,
      wallResizeFrame: null,
      coverRepairQueue: [],
      coverRepairTimer: null,
      coverRepairInFlight: false,
      coverRepairAttemptTokens: {},
      completionToastVisible: false,
      completionToastTimer: null,
    }
  },
  computed: {
    pageVars() {
      return topLevelPageVars()
    },
    hasMoreTagWallItems() {
      return this.tagWallItems.length < this.tagWallTotal
    },
    wallColumnCount() {
      const availableWidth = Number(this.wallViewportWidth || 0)
      if (!Number.isFinite(availableWidth) || availableWidth <= 0) {
        return 1
      }
      return Math.max(
        1,
        Math.floor((availableWidth + HOME_GRID_GAP_PX) / (HOME_CARD_TARGET_EDGE_PX + HOME_GRID_GAP_PX))
      )
    },
    wallCardEdge() {
      const availableWidth = Math.max(0, Number(this.wallViewportWidth || 0))
      if (!availableWidth) {
        return TOP_LEVEL_PAGE_STANDARD.thumbEdgePx
      }
      const columns = Math.max(1, this.wallColumnCount)
      const rawWidth = Math.floor((availableWidth - HOME_GRID_GAP_PX * Math.max(0, columns - 1)) / columns)
      if (columns === 1) {
        return Math.max(1, Math.min(TOP_LEVEL_PAGE_STANDARD.thumbEdgePx, rawWidth || availableWidth))
      }
      return Math.max(
        HOME_CARD_MIN_EDGE_PX,
        Math.min(TOP_LEVEL_PAGE_STANDARD.thumbEdgePx, rawWidth || HOME_CARD_MIN_EDGE_PX)
      )
    },
    wallGridWidth() {
      return this.wallColumnCount * this.wallCardEdge + Math.max(0, this.wallColumnCount - 1) * HOME_GRID_GAP_PX
    },
    wallRowStride() {
      return this.wallCardEdge + HOME_GRID_GAP_PX
    },
    totalWallRows() {
      if (!this.tagWallItems.length) return 0
      return Math.ceil(this.tagWallItems.length / this.wallColumnCount)
    },
    visibleWallRows() {
      if (!this.wallViewportHeight) {
        return HOME_VIRTUAL_ROWS
      }
      return Math.max(
        HOME_VIRTUAL_ROWS,
        Math.ceil((this.wallViewportHeight + HOME_GRID_GAP_PX) / Math.max(this.wallRowStride, 1))
      )
    },
    wallStartRow() {
      if (!this.tagWallItems.length) return 0
      return Math.max(0, Math.floor(this.wallViewportScrollTop / Math.max(this.wallRowStride, 1)) - HOME_OVERSCAN_ROWS)
    },
    wallEndRow() {
      return Math.min(this.totalWallRows, this.wallStartRow + this.visibleWallRows + HOME_OVERSCAN_ROWS * 2)
    },
    wallStartIndex() {
      return this.wallStartRow * this.wallColumnCount
    },
    wallEndIndex() {
      return Math.min(this.tagWallItems.length, this.wallEndRow * this.wallColumnCount)
    },
    virtualTagWallItems() {
      return this.tagWallItems.slice(this.wallStartIndex, this.wallEndIndex)
    },
    wallVirtualOffsetY() {
      return this.wallStartRow * this.wallRowStride
    },
    wallVirtualTotalHeight() {
      if (!this.totalWallRows) return 0
      return this.totalWallRows * this.wallCardEdge + Math.max(0, this.totalWallRows - 1) * HOME_GRID_GAP_PX
    },
    virtualCanvasStyle() {
      return {
        height: `${Math.max(0, this.wallVirtualTotalHeight)}px`,
      }
    },
    virtualWindowStyle() {
      return {
        transform: `translate(-50%, ${this.wallVirtualOffsetY}px)`,
      }
    },
    virtualGridStyle() {
      return {
        width: `${Math.max(this.wallGridWidth, this.wallCardEdge)}px`,
        gridTemplateColumns: `repeat(${this.wallColumnCount}, ${this.wallCardEdge}px)`,
      }
    },
    virtualCardStyle() {
      return {
        width: `${this.wallCardEdge}px`,
      }
    },
  },
  watch: {
    virtualTagWallItems: {
      handler(items) {
        this.enqueueMissingCoverRepairs(items)
      },
    },
  },
  created() {
    this.coverHistoryIds = readCoverHistory()
    this.refreshHomePage()
    window.addEventListener('library-refreshed', this.onLibraryRefreshed)
  },
  mounted() {
    this.installWallResizeObserver()
  },
  beforeUnmount() {
    if (this.requestController) {
      this.requestController.abort()
      this.requestController = null
    }
    if (this.coverRepairTimer) {
      window.clearTimeout(this.coverRepairTimer)
      this.coverRepairTimer = null
    }
    if (this.completionToastTimer) {
      window.clearTimeout(this.completionToastTimer)
      this.completionToastTimer = null
    }
    if (this.wallResizeFrame) {
      window.cancelAnimationFrame(this.wallResizeFrame)
      this.wallResizeFrame = null
    }
    this.wallResizeObserver?.disconnect?.()
    window.removeEventListener('library-refreshed', this.onLibraryRefreshed)
  },
  methods: {
    animatedBadgeLabel: resolveAnimatedBadgeLabel,
    resolvePreviewUrl,
    formatCompactCount,
    formatExactCount,
    formatVisibleUsageCount(value) {
      const label = formatCompactCount(value)
      return `${label} 张`
    },
    displayTagLabel(entry) {
      const label = entry?.tag?.display_name || entry?.tag?.name || '未命名 Tag'
      return `#${label}`
    },
    displayTagDescription(entry) {
      const description = String(entry?.tag?.description || '').trim()
      if (description) return description
      return `${formatTagTypeLabel(entry?.tag?.type)} · ${this.formatVisibleUsageCount(entry?.visible_usage_count)}`
    },
    resolvedTagCoverPreviewUrl(entry) {
      return this.resolvePreviewUrl(entry?.cover)
    },
    buildOverviewParams(offset = 0) {
      const params = new URLSearchParams()
      params.set('limit', String(HOME_BATCH_SIZE))
      params.set('offset', String(Math.max(0, Number(offset || 0))))
      for (const imageId of this.collectExcludedCoverIds()) {
        params.append('exclude_image_ids', String(imageId))
      }
      return params
    },
    collectExcludedCoverIds() {
      return normalizeIdList([
        ...collectCoverIds(this.tagWallItems),
        ...this.coverHistoryIds,
      ])
    },
    persistRecentCoverIds(newIds) {
      this.coverHistoryIds = normalizeIdList([
        ...normalizeIdList(newIds),
        ...this.coverHistoryIds,
      ])
      persistCoverHistory(this.coverHistoryIds)
    },
    resetCoverRepairState() {
      this.coverRepairQueue = []
      this.coverRepairInFlight = false
      this.coverRepairAttemptTokens = {}
      if (this.coverRepairTimer) {
        window.clearTimeout(this.coverRepairTimer)
        this.coverRepairTimer = null
      }
    },
    hideCompletionToast() {
      this.completionToastVisible = false
      if (this.completionToastTimer) {
        window.clearTimeout(this.completionToastTimer)
        this.completionToastTimer = null
      }
    },
    showCompletionToast() {
      if (!this.stats.visible_tag_count) return
      this.completionToastVisible = true
      if (this.completionToastTimer) {
        window.clearTimeout(this.completionToastTimer)
      }
      this.completionToastTimer = window.setTimeout(() => {
        this.completionToastVisible = false
        this.completionToastTimer = null
      }, 2600)
    },
    refreshHomePage() {
      this.wallViewportScrollTop = 0
      this.tagWallItems = []
      this.tagWallTotal = 0
      this.stats = createEmptyStats()
      this.loadError = ''
      this.hideCompletionToast()
      this.resetCoverRepairState()
      this.fetchHomeOverview({ append: false })
    },
    loadMoreTagWall() {
      this.fetchHomeOverview({ append: true })
    },
    async fetchHomeOverview({ append = false } = {}) {
      if (append) {
        if (this.loadingInitial || this.loadingMore || !this.hasMoreTagWallItems) {
          return
        }
      } else if (this.requestController) {
        this.requestController.abort()
      }

      const controller = new AbortController()
      this.requestController = controller
      if (append) {
        this.loadingMore = true
      } else {
        this.loadingInitial = true
      }
      this.loadError = ''

      try {
        const offset = append ? this.tagWallItems.length : 0
        const response = await fetch(`${API_BASE}/api/home/overview?${this.buildOverviewParams(offset).toString()}`, {
          signal: controller.signal,
        })
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }
        const payload = await response.json()
        if (controller.signal.aborted) {
          return
        }

        const nextStats = {
          ...createEmptyStats(),
          ...(payload?.stats || {}),
        }
        const nextItems = Array.isArray(payload?.tag_wall?.items) ? payload.tag_wall.items : []
        this.stats = nextStats
        this.tagWallTotal = Math.max(0, Number(payload?.tag_wall?.total || nextItems.length || 0))
        this.tagWallItems = append
          ? mergeTagWallItems(this.tagWallItems, nextItems)
          : mergeTagWallItems([], nextItems)
        this.persistRecentCoverIds(collectCoverIds(nextItems))

        this.$nextTick(() => {
          this.installWallResizeObserver()
          this.refreshWallViewportMetrics()
          if (!append) {
            this.resetWallViewportScroll()
          }
          this.maybeLoadMoreIfNeeded()
          if (this.tagWallItems.length && !this.hasMoreTagWallItems) {
            this.showCompletionToast()
          }
        })
      } catch (error) {
        if (error?.name === 'AbortError') {
          return
        }
        this.loadError = append
          ? '继续加载标签卡片失败，请重试。'
          : '主页概览加载失败，请确认前后端服务均已启动。'
      } finally {
        if (this.requestController === controller) {
          this.requestController = null
        }
        if (!controller.signal.aborted) {
          this.loadingInitial = false
          this.loadingMore = false
        }
      }
    },
    maybeLoadMoreIfNeeded() {
      if (this.loadingInitial || this.loadingMore || !this.hasMoreTagWallItems) return
      const remainingHeight = this.wallVirtualTotalHeight - (this.wallViewportScrollTop + this.wallViewportHeight)
      if (!this.wallViewportHeight || remainingHeight <= HOME_PREFETCH_THRESHOLD_PX) {
        this.loadMoreTagWall()
      }
    },
    installWallResizeObserver() {
      const viewport = this.$refs.wallViewport
      if (!viewport || typeof ResizeObserver === 'undefined') return
      if (!this.wallResizeObserver) {
        this.wallResizeObserver = new ResizeObserver(() => {
          this.scheduleWallViewportRefresh()
        })
      }
      this.wallResizeObserver.disconnect()
      this.wallResizeObserver.observe(viewport)
      this.scheduleWallViewportRefresh()
    },
    scheduleWallViewportRefresh() {
      if (typeof window === 'undefined') {
        this.refreshWallViewportMetrics()
        this.maybeLoadMoreIfNeeded()
        return
      }
      if (this.wallResizeFrame) return
      this.wallResizeFrame = window.requestAnimationFrame(() => {
        this.wallResizeFrame = null
        this.refreshWallViewportMetrics()
        this.maybeLoadMoreIfNeeded()
      })
    },
    refreshWallViewportMetrics() {
      const viewport = this.$refs.wallViewport
      const nextWidth = viewport?.clientWidth || 0
      const nextHeight = viewport?.clientHeight || 0
      if (nextWidth !== this.wallViewportWidth) {
        this.wallViewportWidth = nextWidth
      }
      if (nextHeight !== this.wallViewportHeight) {
        this.wallViewportHeight = nextHeight
      }
    },
    resetWallViewportScroll() {
      const viewport = this.$refs.wallViewport
      if (!viewport) return
      viewport.scrollTop = 0
    },
    handleWallScroll(event) {
      this.wallViewportScrollTop = event?.target?.scrollTop || 0
      this.maybeLoadMoreIfNeeded()
    },
    coverRepairStateKey(entry) {
      const imageId = toPositiveInt(entry?.cover?.id)
      return imageId ? String(imageId) : ''
    },
    coverRepairToken(entry) {
      return `${entry?.cover?.cache_thumb_url || ''}|${entry?.cover?.thumb_url || ''}`
    },
    shouldRepairCover(entry) {
      return Boolean(this.coverRepairStateKey(entry)) && !this.resolvedTagCoverPreviewUrl(entry)
    },
    enqueueMissingCoverRepairs(entries) {
      if (!Array.isArray(entries) || !entries.length) return
      let didQueue = false
      const nextAttemptTokens = { ...this.coverRepairAttemptTokens }
      const nextQueue = [...this.coverRepairQueue]

      for (const entry of entries) {
        if (!this.shouldRepairCover(entry)) continue
        const stateKey = this.coverRepairStateKey(entry)
        const token = this.coverRepairToken(entry)
        if (!stateKey || nextAttemptTokens[stateKey] === token) continue

        nextAttemptTokens[stateKey] = token
        const imageId = toPositiveInt(entry?.cover?.id)
        if (imageId && !nextQueue.includes(imageId)) {
          nextQueue.push(imageId)
          didQueue = true
        }
      }

      if (!didQueue) return
      this.coverRepairAttemptTokens = nextAttemptTokens
      this.coverRepairQueue = nextQueue
      if (this.coverRepairTimer) {
        window.clearTimeout(this.coverRepairTimer)
      }
      this.coverRepairTimer = window.setTimeout(() => {
        this.coverRepairTimer = null
        this.flushCoverRepairQueue()
      }, 90)
    },
    async flushCoverRepairQueue() {
      const repairIds = normalizeIdList(this.coverRepairQueue)
      this.coverRepairQueue = []
      if (!repairIds.length) return

      if (this.coverRepairInFlight) {
        this.coverRepairQueue = normalizeIdList([...this.coverRepairQueue, ...repairIds])
        return
      }

      this.coverRepairInFlight = true
      try {
        const response = await fetch(`${API_BASE}/api/admin/refresh?mode=quick`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            repair_cache: true,
            image_ids: repairIds,
          }),
        })
        if (!response.ok) return
        await response.json().catch(() => null)
        await this.refreshCoverPreviewMetadata(repairIds)
      } catch {
        // Ignore targeted preview repair failures and keep placeholders visible.
      } finally {
        this.coverRepairInFlight = false
        if (this.coverRepairQueue.length) {
          this.flushCoverRepairQueue()
        }
      }
    },
    async refreshCoverPreviewMetadata(imageIds) {
      if (!Array.isArray(imageIds) || !imageIds.length) return
      try {
        const response = await fetch(`${API_BASE}/api/images/meta?ids=${imageIds.join(',')}`)
        if (!response.ok) return
        const payload = await response.json()
        const metaMap = new Map((payload.items || []).map(item => [item.id, item]))
        if (!metaMap.size) return

        const nextAttemptTokens = { ...this.coverRepairAttemptTokens }
        this.tagWallItems = this.tagWallItems.map((entry) => {
          const coverId = toPositiveInt(entry?.cover?.id)
          const meta = metaMap.get(coverId)
          if (!coverId || !meta || !entry.cover) return entry

          const nextCover = {
            ...entry.cover,
            cache_thumb_url: meta.cache_thumb_url || '',
            thumb_url: meta.thumb_url || '',
            width: Number(meta.width) > 0 ? meta.width : entry.cover.width,
            height: Number(meta.height) > 0 ? meta.height : entry.cover.height,
            category_id: toPositiveInt(meta.category_id) || entry.cover.category_id,
          }
          const nextEntry = {
            ...entry,
            cover: nextCover,
          }

          const stateKey = this.coverRepairStateKey(nextEntry)
          if (stateKey && nextAttemptTokens[stateKey] !== this.coverRepairToken(nextEntry)) {
            delete nextAttemptTokens[stateKey]
          }
          return nextEntry
        })
        this.coverRepairAttemptTokens = nextAttemptTokens
      } catch {
        // Ignore preview metadata refresh failures.
      }
    },
    openGalleryOverview() {
      this.$router.push('/gallery/all').catch(() => {})
    },
    openTagOverview() {
      this.$router.push('/tags').catch(() => {})
    },
    openTagWallItem(entry) {
      const tagId = toPositiveInt(entry?.tag?.id)
      if (!tagId) return
      this.$router.push(`/tags/${tagId}`).catch(() => {})
    },
    onLibraryRefreshed() {
      this.refreshHomePage()
    },
  },
}
</script>

<style scoped lang="css">
.top-level-page {
  @apply flex flex-col gap-6;
}

.home-page {
  min-height: 0;
}

.home-page__shell {
  display: flex;
  flex-direction: column;
  min-height: calc(100dvh - 5rem);
  height: calc(100dvh - 5rem);
  gap: 1rem;
}

.home-page__top-shell {
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  gap: 1rem;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.home-stat-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  width: 100%;
  padding: 1.3rem 1.4rem;
  border: 1px solid rgba(14, 116, 144, 0.12);
  border-radius: 1.45rem;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(241, 245, 249, 0.98)),
    radial-gradient(circle at top right, rgba(56, 189, 248, 0.12), transparent 38%);
  text-align: left;
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.06);
  transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
}

.home-stat-card:hover {
  transform: translateY(-2px);
  border-color: rgba(14, 116, 144, 0.22);
  box-shadow: 0 24px 42px rgba(15, 23, 42, 0.08);
}

.home-stat-card--tag {
  border-color: rgba(16, 185, 129, 0.16);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(240, 253, 250, 0.98)),
    radial-gradient(circle at top right, rgba(16, 185, 129, 0.12), transparent 38%);
}

.home-stat-card--tag:hover {
  border-color: rgba(16, 185, 129, 0.28);
}

.home-stat-card__icon {
  @apply text-4xl leading-none;
}

.home-stat-card__body {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.28rem;
}

.home-stat-card__num {
  @apply text-4xl font-bold leading-none text-slate-900;
}

.home-stat-card__label {
  @apply text-base font-semibold text-slate-700;
}

.home-page__wall-shell {
  display: flex;
  flex: 1 1 auto;
  min-height: 0;
  flex-direction: column;
  gap: 0.9rem;
  padding: 1rem;
  border: 1px solid rgba(14, 116, 144, 0.12);
  border-radius: 1.9rem;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98)),
    radial-gradient(circle at top right, rgba(56, 189, 248, 0.08), transparent 38%),
    radial-gradient(circle at bottom left, rgba(16, 185, 129, 0.08), transparent 42%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
}

.home-page__wall-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.home-page__wall-header-main {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.28rem;
}

.home-page__wall-title {
  @apply m-0 text-lg font-semibold text-slate-900;
}

.home-page__wall-subtitle {
  @apply m-0 text-sm text-slate-500;
}

.home-page__wall-action,
.home-page__state-action,
.home-page__inline-action {
  @apply rounded-full border px-4 py-2 text-sm font-semibold transition;
}

.home-page__wall-action {
  flex: 0 0 auto;
  white-space: nowrap;
}

.home-page__wall-action,
.home-page__state-action {
  border-color: rgba(14, 116, 144, 0.16);
  background: rgba(239, 246, 255, 0.96);
  color: #075985;
}

.home-page__wall-action:hover:not(:disabled),
.home-page__state-action:hover:not(:disabled) {
  background: rgba(224, 242, 254, 0.98);
}

.home-page__inline-action {
  border-color: rgba(244, 114, 182, 0.14);
  background: rgba(255, 241, 242, 0.96);
  color: #be185d;
}

.home-page__inline-action:hover:not(:disabled) {
  background: rgba(255, 228, 230, 0.98);
}

.home-page__wall-action:disabled,
.home-page__state-action:disabled,
.home-page__inline-action:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.home-page__wall-stage {
  display: flex;
  flex: 1 1 auto;
  min-height: 0;
  flex-direction: column;
  gap: 0.75rem;
  position: relative;
}

.home-page__wall-viewport {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
  padding-right: 0.2rem;
}

.home-page__wall-virtual {
  position: relative;
  width: 100%;
}

.home-page__wall-window {
  position: absolute;
  top: 0;
  left: 50%;
  will-change: transform;
}

.home-page__wall-grid {
  display: grid;
  gap: 1.125rem;
  justify-content: center;
  align-content: start;
  margin: 0 auto;
}

.home-tag-card {
  aspect-ratio: 1 / 1;
}

.home-tag-card__body {
  display: flex;
  height: 100%;
  width: 100%;
  flex-direction: column;
  justify-content: flex-end;
  align-items: center;
  padding: 1.2rem 1rem 1.25rem;
  text-align: center;
}

.home-tag-card__copy {
  display: flex;
  min-height: 0;
  flex-direction: column;
  align-items: center;
  gap: 0.42rem;
  width: 100%;
  max-width: 88%;
  color: #ffffff;
  text-align: center;
}

.home-tag-card__title {
  @apply m-0 font-semibold leading-snug;
  font-size: clamp(1.2rem, 0.9rem + 0.8vw, 1.5rem);
  display: -webkit-box;
  line-clamp: 2;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
  text-shadow: 0 8px 22px rgba(15, 23, 42, 0.6);
}

.home-tag-card__description {
  @apply m-0 text-sm;
  color: rgba(255, 255, 255, 0.76);
  display: -webkit-box;
  line-clamp: 3;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-shadow: 0 6px 16px rgba(15, 23, 42, 0.52);
}

.home-page__state {
  @apply flex min-h-[260px] w-full flex-1 flex-col items-center justify-center rounded-[1.8rem] border border-dashed border-slate-300 bg-slate-50 px-6 py-16 text-center text-sm text-slate-500;
}

.home-page__state--error {
  @apply border-rose-200 bg-rose-50 text-rose-600;
}

.home-page__state-icon {
  @apply mb-3 block text-5xl leading-none;
}

.home-page__state-text {
  @apply m-0 mb-4 max-w-[40rem] text-sm leading-6;
}

.home-page__wall-status {
  @apply flex items-center justify-center gap-3 rounded-full border border-slate-200 px-4 py-2 text-sm text-slate-500;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8px);
}

.home-page__wall-status--error {
  @apply border-rose-200 text-rose-600;
  background: rgba(255, 241, 242, 0.9);
}

.home-page__wall-status--quiet {
  @apply border-slate-200 text-slate-500;
  background: rgba(248, 250, 252, 0.92);
}

.home-page__floating-toast {
  position: absolute;
  left: 50%;
  bottom: 0.75rem;
  transform: translateX(-50%);
  max-width: min(80vw, 26rem);
  padding: 0.72rem 1rem;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.8);
  color: #ffffff;
  font-size: 0.85rem;
  font-weight: 600;
  line-height: 1.2;
  text-align: center;
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.24);
  backdrop-filter: blur(10px);
  pointer-events: none;
  z-index: 2;
}

.home-toast-enter-active,
.home-toast-leave-active {
  transition: opacity 220ms ease, transform 220ms ease;
}

.home-toast-enter-from,
.home-toast-leave-to {
  opacity: 0;
  transform: translate(-50%, 12px);
}

@media (max-width: 900px) {
  .home-page__shell,
  .home-page__top-shell,
  .stats-row,
  .home-page__wall-shell {
    gap: 0.75rem;
  }

  .home-stat-card {
    gap: 0.85rem;
    padding: 1.05rem 1.1rem;
  }

  .home-stat-card__icon {
    font-size: 2rem;
  }

  .home-stat-card__num {
    font-size: 2.3rem;
  }

  .home-stat-card__label {
    font-size: 0.95rem;
  }

  .home-page__wall-header {
    align-items: center;
    flex-direction: row;
    gap: 0.75rem;
  }

  .home-page__wall-shell {
    padding: 0.85rem;
  }
}

@media (max-width: 640px) {
  .home-page__shell {
    min-height: auto;
    height: auto;
  }

  .home-page__wall-shell {
    min-height: 70vh;
    border-radius: 1.45rem;
  }

  .stats-row {
    gap: 0.65rem;
  }

  .home-stat-card,
  .home-page__wall-shell {
    border-radius: 1.35rem;
  }

  .home-stat-card {
    gap: 0.7rem;
    padding: 0.92rem 0.95rem;
  }

  .home-stat-card__icon {
    font-size: 1.7rem;
  }

  .home-stat-card__num {
    font-size: 1.95rem;
  }

  .home-stat-card__label,
  .home-page__wall-action {
    font-size: 0.875rem;
  }

  .home-page__wall-shell {
    padding: 0.75rem;
  }

  .home-page__wall-header {
    gap: 0.65rem;
  }
}
</style>
