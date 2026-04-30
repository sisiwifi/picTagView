<template>
  <section class="top-level-page search-page" :style="pageVars">
    <TopLevelPageHeader
      title="搜索"
      subtitle="单输入统一搜索文件名、Tag，或直接输入图片路径后按 quick hash 反查。"
    >
      <div class="search-page__mode-pill">当前模式：{{ effectiveModeLabel }}</div>
    </TopLevelPageHeader>

    <label class="search-bar" for="search-input">
      <span class="search-bar__icon">⌕</span>
      <input
        id="search-input"
        v-model="rawQuery"
        class="search-bar__input"
        type="text"
        autocomplete="off"
        spellcheck="false"
        placeholder="输入文件名，tag:角色名，或 media/2024-01/example.jpg"
        @keyup.esc="clearSearch"
      >
      <button v-if="rawQuery" type="button" class="search-bar__clear" @click="clearSearch">清空</button>
    </label>

    <div class="search-page__hints">
      <span class="search-page__hint">默认：文件名 + Tag 混合匹配</span>
      <span class="search-page__hint">Tag：<strong>tag:角色名</strong> 或 <strong>#角色名</strong></span>
      <span class="search-page__hint">路径：<strong>path:media/2024-01/a.jpg</strong></span>
    </div>

    <div v-if="hasQuery" class="search-page__status">
      <span class="search-page__status-main">{{ resultSummary }}</span>
      <span v-if="searchResponse.quick_hash" class="search-page__status-side">Quick Hash：{{ shortQuickHash }}</span>
    </div>

    <LoadingSpinner v-if="loading" />

    <div v-else-if="errorMessage" class="search-empty search-empty--error">
      <span class="search-empty__icon">!</span>
      <p>{{ errorMessage }}</p>
    </div>

    <div v-else-if="!hasQuery" class="search-empty">
      <span class="search-empty__icon">⌕</span>
      <p>输入后立即搜索。普通文本默认匹配文件名与 Tag；路径会切换为 quick hash 反查。</p>
    </div>

    <div v-else-if="!searchResponse.items.length" class="search-empty">
      <span class="search-empty__icon">∅</span>
      <p>{{ emptyStateText }}</p>
    </div>

    <div v-else class="search-result-grid">
      <ThumbCard
        v-for="item in searchResponse.items"
        :key="item.id"
        :src="resolvePreviewUrl(item)"
        class="search-result-card"
        :overlay-opacity="0.18"
        :rounded="'1.25rem'"
        @click="openBrowseLocation(item)"
      >
        <article class="search-result-card__body">
          <div class="search-result-card__badges">
            <span
              v-for="badge in item.matched_by"
              :key="`${item.id}-${badge}`"
              class="search-result-card__badge"
            >
              {{ formatMatchedByLabel(badge) }}
            </span>
          </div>

          <div class="search-result-card__meta">
            <h3 class="search-result-card__title">{{ item.name || '未命名图片' }}</h3>
            <p class="search-result-card__path">{{ item.media_rel_path || '无路径信息' }}</p>

            <TagChipList
              v-if="tagsForItem(item).length"
              :tags="tagsForItem(item)"
              compact
            />
            <div v-else class="search-result-card__tag-placeholder">暂无标签</div>

            <div class="search-result-card__actions" @click.stop>
              <button type="button" class="search-result-card__action" @click="openBrowseLocation(item)">定位</button>
              <a
                v-if="buildOriginalMediaUrl(item.media_rel_path)"
                class="search-result-card__action search-result-card__action--link"
                :href="buildOriginalMediaUrl(item.media_rel_path)"
                target="_blank"
                rel="noopener noreferrer"
              >原图</a>
            </div>
          </div>
        </article>
      </ThumbCard>
    </div>
  </section>
</template>

<script>
import LoadingSpinner from '../components/LoadingSpinner.vue'
import TagChipList from '../components/TagChipList.vue'
import ThumbCard from '../components/ThumbCard.vue'
import TopLevelPageHeader from './TopLevelPageHeader.vue'
import {
  API_BASE,
  TOP_LEVEL_PAGE_STANDARD,
  buildBrowseLocation,
  buildOriginalMediaUrl,
  detectSearchMode,
  formatMatchedByLabel,
  formatSearchModeLabel,
  resolvePreviewUrl,
  shortenQuickHash,
  topLevelPageVars,
} from './topLevelPageConvention'

function createEmptySearchResponse() {
  return {
    query: '',
    requested_mode: 'auto',
    resolved_mode: 'auto',
    limit: TOP_LEVEL_PAGE_STANDARD.searchResultLimit,
    total: 0,
    source_media_rel_path: null,
    quick_hash: null,
    included_tags: [],
    items: [],
  }
}

export default {
  name: 'SearchPage',
  components: {
    LoadingSpinner,
    TagChipList,
    ThumbCard,
    TopLevelPageHeader,
  },
  data() {
    return {
      rawQuery: '',
      loading: false,
      errorMessage: '',
      searchResponse: createEmptySearchResponse(),
      debounceTimer: null,
      requestController: null,
    }
  },
  computed: {
    pageVars() {
      return topLevelPageVars()
    },
    modeInfo() {
      return detectSearchMode(this.rawQuery)
    },
    hasQuery() {
      return this.modeInfo.normalizedQuery.length > 0
    },
    effectiveModeLabel() {
      const resolved = this.searchResponse.resolved_mode
      if (this.hasQuery && resolved && resolved !== 'auto') {
        return formatSearchModeLabel(resolved)
      }
      return formatSearchModeLabel(this.modeInfo.mode)
    },
    resultTagMap() {
      return this.searchResponse.included_tags.reduce((map, tag) => {
        map[tag.id] = tag
        return map
      }, {})
    },
    resultSummary() {
      if (!this.hasQuery) return ''
      const total = Number(this.searchResponse.total || 0)
      if (this.modeInfo.mode === 'path' && this.searchResponse.quick_hash) {
        return `已按路径解析并用 quick hash 找到 ${total} 条结果`
      }
      return `共找到 ${total} 条结果`
    },
    shortQuickHash() {
      return shortenQuickHash(this.searchResponse.quick_hash)
    },
    emptyStateText() {
      if (this.modeInfo.mode === 'path') {
        return '未找到该路径对应的图片，或该图片当前不在可见范围内。'
      }
      return '没有匹配结果。可以尝试更短的文件名、tag: 前缀，或直接输入 media 路径。'
    },
  },
  watch: {
    rawQuery() {
      this.syncRouteQuery()
      this.scheduleSearch()
    },
    '$route.query.q': {
      immediate: true,
      handler(value) {
        const nextValue = typeof value === 'string' ? value : ''
        if (nextValue !== this.rawQuery) {
          this.rawQuery = nextValue
        }
      },
    },
  },
  beforeUnmount() {
    if (this.debounceTimer) {
      window.clearTimeout(this.debounceTimer)
      this.debounceTimer = null
    }
    if (this.requestController) {
      this.requestController.abort()
      this.requestController = null
    }
  },
  methods: {
    resolvePreviewUrl,
    buildOriginalMediaUrl,
    formatMatchedByLabel,
    tagsForItem(item) {
      return (item.tags || [])
        .map(tagId => this.resultTagMap[tagId])
        .filter(Boolean)
        .slice(0, 4)
    },
    clearSearch() {
      this.rawQuery = ''
      this.errorMessage = ''
      this.searchResponse = createEmptySearchResponse()
      if (this.requestController) {
        this.requestController.abort()
        this.requestController = null
      }
      if (this.debounceTimer) {
        window.clearTimeout(this.debounceTimer)
        this.debounceTimer = null
      }
    },
    syncRouteQuery() {
      const nextValue = this.rawQuery || undefined
      const currentValue = typeof this.$route.query.q === 'string' ? this.$route.query.q : undefined
      if (nextValue === currentValue) {
        return
      }

      const query = { ...this.$route.query }
      if (nextValue) {
        query.q = nextValue
      } else {
        delete query.q
      }
      this.$router.replace({ query }).catch(() => {})
    },
    scheduleSearch() {
      if (this.debounceTimer) {
        window.clearTimeout(this.debounceTimer)
      }

      if (!this.hasQuery) {
        this.loading = false
        this.errorMessage = ''
        this.searchResponse = createEmptySearchResponse()
        if (this.requestController) {
          this.requestController.abort()
          this.requestController = null
        }
        return
      }

      this.debounceTimer = window.setTimeout(() => {
        this.performSearch()
      }, TOP_LEVEL_PAGE_STANDARD.searchDebounceMs)
    },
    async performSearch() {
      const { mode, normalizedQuery } = this.modeInfo
      if (!normalizedQuery) {
        return
      }

      if (this.requestController) {
        this.requestController.abort()
      }
      const controller = new AbortController()
      this.requestController = controller
      this.loading = true
      this.errorMessage = ''

      try {
        const params = new URLSearchParams({
          q: normalizedQuery,
          mode,
          limit: String(TOP_LEVEL_PAGE_STANDARD.searchResultLimit),
        })
        const response = await fetch(`${API_BASE}/api/search/images?${params.toString()}`, {
          signal: controller.signal,
        })
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }
        const payload = await response.json()
        if (controller.signal.aborted) {
          return
        }
        this.searchResponse = {
          ...createEmptySearchResponse(),
          ...payload,
        }
      } catch (error) {
        if (error?.name === 'AbortError') {
          return
        }
        this.searchResponse = createEmptySearchResponse()
        this.errorMessage = '搜索接口不可用，请确认前后端服务均已启动。'
      } finally {
        if (this.requestController === controller) {
          this.requestController = null
        }
        if (!controller.signal.aborted) {
          this.loading = false
        }
      }
    },
    openBrowseLocation(item) {
      const target = buildBrowseLocation(item?.media_rel_path)
      if (!target) {
        return
      }
      this.$router.push(target).catch(() => {})
    },
  },
}
</script>

<style scoped lang="css">
.top-level-page {
  @apply flex flex-col gap-6;
}

.search-page__mode-pill {
  @apply rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700;
}

.search-bar {
  @apply flex items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3 shadow-sm;
}

.search-bar__icon {
  @apply text-slate-400 text-lg leading-none;
}

.search-bar__input {
  @apply min-w-0 flex-1 border-0 bg-transparent p-0 text-base text-slate-900 outline-none;
}

.search-bar__clear {
  @apply rounded-full border border-slate-200 px-3 py-1 text-xs text-slate-500 transition hover:bg-slate-100;
}

.search-page__hints {
  @apply flex flex-wrap gap-2 text-xs text-slate-500;
}

.search-page__hint {
  @apply rounded-full bg-slate-100 px-3 py-1;
}

.search-page__status {
  @apply flex flex-wrap items-center justify-between gap-3 text-sm text-slate-600;
}

.search-page__status-main {
  @apply font-medium text-slate-700;
}

.search-page__status-side {
  @apply rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-500;
}

.search-empty {
  @apply rounded-2xl border border-dashed border-slate-300 bg-slate-50 px-6 py-16 text-center text-sm text-slate-500;
}

.search-empty--error {
  @apply border-rose-200 bg-rose-50 text-rose-600;
}

.search-empty__icon {
  @apply mb-3 block text-5xl leading-none;
}

.search-result-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, var(--top-level-thumb-edge)), var(--top-level-thumb-edge)));
  gap: 1.5rem;
  justify-content: center;
}

.search-result-card {
  width: min(100%, var(--top-level-thumb-edge));
  aspect-ratio: 1 / 1;
}

.search-result-card__body {
  @apply flex h-full w-full flex-col justify-between p-4 text-left;
}

.search-result-card__badges {
  @apply flex flex-wrap gap-2;
}

.search-result-card__badge {
  @apply rounded-full bg-black/55 px-2.5 py-1 text-[11px] font-medium tracking-[0.04em] text-white backdrop-blur-sm;
}

.search-result-card__meta {
  @apply rounded-2xl bg-black/55 p-3 text-white backdrop-blur-md;
}

.search-result-card__title {
  @apply m-0 text-sm font-semibold leading-snug;
}

.search-result-card__path {
  @apply mt-1 text-xs text-white/75;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-all;
}

.search-result-card__tag-placeholder {
  @apply mt-3 text-xs text-white/60;
}

.search-result-card__actions {
  @apply mt-3 flex gap-2;
}

.search-result-card__action {
  @apply rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-medium text-white transition hover:bg-white/20;
}

.search-result-card__action--link {
  @apply inline-flex items-center no-underline;
}

@media (max-width: 640px) {
  .search-result-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .search-result-card {
    width: 100%;
  }
}
</style>