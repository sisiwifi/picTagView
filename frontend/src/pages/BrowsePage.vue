<template>
  <section class="page" :class="{ 'page--paged': isPagedBrowseMode }">
    <BreadcrumbHeader
      :show-back="true"
      :crumbs="headerCrumbs"
      :item-count="totalCount"
      :show-sort="true"
      :sort-by="sortBy"
      :sort-dir="sortDir"
      @back="onPageBack"
      @update:sortBy="onSortModeSelect"
      @toggle-sort-dir="toggleSortDir"
    >
      <button
        v-for="action in pageHeaderActions"
        :key="action.key"
        class="browse-header__action"
        :class="action.className"
        type="button"
        :disabled="action.disabled"
        @click="runConfiguredHandler(action.handler)"
      >
        {{ action.label }}
      </button>

      <div class="vm-btns" role="group" aria-label="视图模式">
        <button
          class="vm-btn"
          :class="{ active: viewMode === 'grid' }"
          title="大缩略图"
          @click="switchViewMode('grid')"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <rect x="1" y="1" width="5" height="5" rx="1" fill="currentColor"/>
            <rect x="8" y="1" width="5" height="5" rx="1" fill="currentColor"/>
            <rect x="1" y="8" width="5" height="5" rx="1" fill="currentColor"/>
            <rect x="8" y="8" width="5" height="5" rx="1" fill="currentColor"/>
          </svg>
        </button>
        <button
          class="vm-btn"
          :class="{ active: viewMode === 'list' }"
          title="列表显示"
          @click="switchViewMode('list')"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <rect x="1" y="2" width="12" height="2" rx="1" fill="currentColor"/>
            <rect x="1" y="6" width="12" height="2" rx="1" fill="currentColor"/>
            <rect x="1" y="10" width="12" height="2" rx="1" fill="currentColor"/>
          </svg>
        </button>
        <button
          class="vm-btn"
          :class="{ active: selectionMode }"
          :title="selectionMode ? '退出选择模式' : '进入选择模式'"
          :aria-pressed="selectionMode ? 'true' : 'false'"
          @click="toggleSelectionMode()"
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M3 1L3 11L6 8.5L8 13L9.5 12.3L7.5 7.8L11 7.8Z" fill="currentColor"/>
          </svg>
        </button>
      </div>
    </BreadcrumbHeader>

    <div ref="pageMain" class="page-main">
      <LoadingSpinner v-if="loading" />

      <div v-else-if="!items.length" class="empty-hint">
        <span class="empty-hint__icon">{{ emptyStateIcon }}</span>
        <p>{{ emptyStateText }}</p>
      </div>

      <div
        v-else-if="selectionMode && viewMode === 'grid'"
        ref="itemGrid"
        class="selection-grid"
        :style="selectionGridStyle"
      >
        <div
          v-for="entry in visibleSelectionEntries"
          :key="itemKey(entry.item, entry.index)"
          class="selection-wrap"
          :class="{
            'is-selected': isItemSelected(entry.item, entry.index),
            'is-disabled': isItemDisabled(entry.item),
          }"
          :data-index="entry.index"
          :data-select-index="entry.index"
          @pointerdown="onSelectionPointerDown($event, entry.item, entry.index)"
        >
          <MediaItemCard
            :src="resolvedUrl(entry.item)"
            :alt="entry.item.name || ''"
            :info-text="displayInfoText(entry.item)"
            :info-tags="displayInfoTags(entry.item)"
            :info-title="selectionInfoMode === 'tags' ? '当前显示 Tag，点击切换为文件名' : '当前显示文件名，点击切换为 Tag'"
            :item-type="entry.item.type"
            :selected="isItemSelected(entry.item, entry.index)"
            :disabled="isItemDisabled(entry.item)"
            :cover-marked="Boolean(entry.item?.is_cover)"
            @toggle-select="onItemSelectionButtonClick(entry.item, entry.index)"
            @toggle-info="toggleInfoDisplayMode"
            @details="onReservedDetailsClick(entry.item, entry.index)"
            @img-error="onMediaCardPreviewError(entry.item)"
          />
        </div>
      </div>

      <div
        v-else-if="viewMode === 'grid' && !isPortraitMasonryMode"
        ref="itemGrid"
        class="photo-grid"
        :style="photoGridStyle"
      >
        <div
          v-for="(row, ri) in activePhotoRows"
          :key="ri"
          class="jl-row"
          :style="{ height: row.height + 'px' }"
        >
          <div
            v-for="item in row.items"
            :key="item.public_id || item.id || item._idx"
            class="photo-wrap"
            :data-index="item._idx"
            :style="{ width: item.computedWidth + 'px' }"
          >
            <div v-if="!resolvedUrl(item)" class="photo-skeleton">
              <span class="skeleton-label">...</span>
            </div>

            <div
              v-else
              class="photo-card"
              :class="{ 'photo-card--cover-picking': coverPickerMode && canPickContainerCoverItem(item) }"
              @click="openItem(item)"
            >
              <img
                :src="resolvedUrl(item)"
                class="photo-img"
                loading="lazy"
                :alt="item.name || ''"
                @load="onImgLoad(item, $event)"
                @error="onPrimaryPreviewError(item)"
              />
              <span v-if="item.is_cover" class="item-cover-badge">封面</span>
              <div v-if="item.type === 'album'" class="album-badge">
                <span class="badge-icon">📁</span>
                <span class="badge-name">{{ item.name }}</span>
                <span class="badge-count">{{ item.count }} 张</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div
        v-else-if="viewMode === 'grid' && isPortraitMasonryMode && !masonrySkeletonReady"
        ref="itemGrid"
        class="photo-grid photo-grid--masonry-skeleton"
      >
        <div class="masonry-skeleton-col">
          <div v-for="h in [120, 180, 100, 200]" :key="h" class="photo-skeleton masonry-skeleton-item" :style="{ height: h + 'px' }" />
        </div>
        <div class="masonry-skeleton-col">
          <div v-for="h in [160, 100, 220, 140]" :key="h" class="photo-skeleton masonry-skeleton-item" :style="{ height: h + 'px' }" />
        </div>
      </div>

      <div
        v-else-if="viewMode === 'grid' && isPortraitMasonryMode"
        ref="itemGrid"
        class="photo-grid photo-grid--masonry"
        :style="masonryGridStyle"
      >
        <div
          v-for="item in activeMasonryPlacements"
          :key="item.public_id || item.id || item._idx"
          class="photo-wrap photo-wrap--masonry"
          :data-index="item._idx"
          :style="{
            left: item.col * (masonryColWidth + 6) + 'px',
            top: item.top + 'px',
            width: item.computedWidth + 'px',
            height: item.computedHeight + 'px',
          }"
          @click="openItem(item)"
        >
          <div v-if="!resolvedUrl(item)" class="photo-skeleton">
            <span class="skeleton-label">...</span>
          </div>
          <div
            v-else
            class="photo-card"
            :class="{ 'photo-card--cover-picking': coverPickerMode && canPickContainerCoverItem(item) }"
          >
            <img
              :src="resolvedUrl(item)"
              class="photo-img"
              loading="lazy"
              :alt="item.name || ''"
              @load="onImgLoad(item, $event)"
              @error="onPrimaryPreviewError(item)"
            />
            <span v-if="item.is_cover" class="item-cover-badge">封面</span>
            <div v-if="item.type === 'album'" class="album-badge">
              <span class="badge-icon">📁</span>
              <span class="badge-name">{{ item.name }}</span>
              <span class="badge-count">{{ item.count }} 张</span>
            </div>
          </div>
        </div>
      </div>

      <div v-else ref="itemGrid" class="list-view" :style="listViewStyle">
        <div
          v-for="entry in visibleListEntries"
          :key="entry.item.public_id || entry.item.id || entry.index"
          class="list-row"
          :class="{
            'list-row--selecting': selectionMode,
            'is-selected': isItemSelected(entry.item, entry.index),
            'is-disabled': isItemDisabled(entry.item),
          }"
          :data-index="entry.index"
          :data-select-index="entry.index"
          @pointerdown="onListPointerDown($event, entry.item, entry.index)"
          @click="onListRowClick($event, entry.item, entry.index)"
        >
          <button
            v-if="selectionMode"
            class="list-pick"
            type="button"
            :disabled="isItemDisabled(entry.item)"
            :aria-pressed="isItemSelected(entry.item, entry.index) ? 'true' : 'false'"
            :aria-label="isItemSelected(entry.item, entry.index) ? '取消选择' : '选择项目'"
            @pointerdown.stop
            @click.stop="onItemSelectionButtonClick(entry.item, entry.index)"
          >
            <span v-if="isItemSelected(entry.item, entry.index)" class="list-pick__mark">✓</span>
          </button>
          <div class="list-thumb-wrap" :class="{ 'list-thumb-wrap--cover-picking': coverPickerMode && canPickContainerCoverItem(entry.item) }">
            <div v-if="!resolvedUrl(entry.item)" class="list-thumb-skeleton" />
            <img
              v-else
              :src="resolvedUrl(entry.item)"
              class="list-thumb-img"
              :alt="entry.item.name || ''"
              @load="onImgLoad(entry.item, $event)"
              @error="onPrimaryPreviewError(entry.item)"
            />
            <span v-if="entry.item.is_cover" class="list-cover-badge">封面</span>
          </div>
          <div class="list-main">
            <div class="list-title-row">
              <span v-if="entry.item.type === 'album'" class="list-type-pill">ALB</span>
              <span class="list-name">{{ entry.item.name || entry.item.full_filename || '未知文件' }}</span>
            </div>
          </div>
        </div>
      </div>

      <div
        v-if="isPagedBrowseMode && items.length"
        ref="paginationHost"
        class="page-pagination-host"
        :class="{ 'page-pagination-host--selection': selectionMode }"
      >
        <PagePaginationBar
          :current-page="activePaginationConfig.currentPage"
          :total-pages="activePaginationConfig.totalPages"
          :page-size="activePaginationConfig.pageSize"
          :page-size-options="activePaginationConfig.pageSizeOptions"
          @update:page="onPaginationPageChange"
          @update:pageSize="onPaginationPageSizeChange"
        />
      </div>
    </div>

    <SelectionIsland
      v-if="selectionMode"
      :floating-style="selectionIslandStyle"
      collapse-label="收起选择操作"
      expand-label="展开选择操作"
      @collapsed-change="onSelectionIslandCollapsedChange"
    >
      <span class="selection-island__count">{{ selectionSummaryText }}</span>
      <button
        v-for="action in pageSelectionActions"
        :key="action.key"
        class="selection-island__btn"
        :class="action.className"
        type="button"
        :disabled="action.disabled"
        @click="runConfiguredHandler(action.handler)"
      >{{ action.label }}</button>
      <div
        ref="selectionIslandMenu"
        class="selection-island__menu-wrap"
        :class="{ 'is-open': selectAllMenuOpen }"
      >
        <button
          class="selection-island__btn"
          type="button"
          :disabled="actionBusy"
          :aria-expanded="hasMixedSelectableTypes ? (selectAllMenuOpen ? 'true' : 'false') : 'false'"
          @click="handleSelectAllButtonClick"
        >全选</button>
        <div v-if="hasMixedSelectableTypes" class="selection-island__submenu">
          <button class="selection-island__submenu-btn" type="button" @click="onSelectAllTypeClick('album')">相册</button>
          <button class="selection-island__submenu-btn" type="button" @click="onSelectAllTypeClick('image')">图片</button>
        </div>
      </div>
      <button class="selection-island__btn" type="button" :disabled="actionBusy" @click="clearSelection">取消选择</button>
    </SelectionIsland>

    <SelectionDetailOverlay
      :visible="selectionDetailsOpen"
      :layer-style="selectionDetailsLayerStyle"
      :panel-style="selectionDetailsPanelStyle"
      :preview-items="selectionDetailPreviewItems"
      :is-multi="selectionDetailPreviewItems.length > 1"
      :name-field="selectionDetailNameField"
      :category-field="selectionDetailCategoryField"
      :tags-field="selectionDetailTagsField"
      :size-field="selectionDetailSizeField"
      :size-label="selectionDetailSizeLabel"
      :imported-field="selectionDetailImportedField"
      :created-field="selectionDetailCreatedField"
      :raw-name="selectionDetailRawName"
      :raw-category-id="selectionDetailRawCategoryId"
      :raw-created-at="selectionDetailRawCreatedAt"
      :primary-action-label="selectionDetailPolicy.primaryActionLabel"
      :primary-action-tone="selectionDetailPolicy.primaryActionTone"
      :can-open-primary-action="selectionDetailPolicy.canOpenPrimaryAction"
      :primary-action-disabled="selectionDetailPolicy.primaryActionDisabled"
      :secondary-action-label="selectionDetailPolicy.secondaryActionLabel"
      :secondary-action-tone="selectionDetailPolicy.secondaryActionTone"
      :secondary-action-disabled="selectionDetailPolicy.secondaryActionDisabled"
      :metadata-permissions="selectionDetailPolicy.metadataPermissions"
      :can-open-collection-menu="canOpenCollectionMenu"
      :collection-menu-disabled="collectionMenuBusy || actionBusy"
      :can-edit-tags="canOpenTagMenu"
      :tag-menu-disabled="tagMenuBusy || actionBusy"
      :can-edit-name="canEditSelectionName"
      :can-edit-category="canEditSelectionCategory"
      :can-edit-created-at="canEditSelectionCreatedAt"
      :edit-busy="metadataEditBusy"
      :current-date-group="dateGroup"
      :category-options="selectionDetailCategoryOptions"
      @close="closeSelectionDetails"
      @open-collection-menu="openCollectionMenu"
      @open-tag-menu="openTagMenu"
      @open-primary="openPrimaryFromDetails"
      @secondary-action="onSelectionDetailSecondaryAction"
      @preview-error="onSelectionDetailPreviewError"
      @submit-name-edit="submitSelectionNameEdit"
      @submit-category-edit="submitSelectionCategoryEdit"
      @submit-created-edit="submitSelectionCreatedEdit"
    />

    <TagMenuDialog
      :visible="tagMenuVisible"
      :busy="tagMenuBusy"
      :search-busy="tagMenuSearchBusy"
      :error-message="tagMenuError"
      :query="tagMenuQuery"
      :existing-tags="tagMenuExistingTags"
      :suggestions="tagMenuSuggestions"
      :recent-tags="tagMenuRecentTags"
      :confirm-disabled="!tagMenuDirty"
      @close="closeTagMenu"
      @cancel="closeTagMenu"
      @confirm="confirmTagMenuChanges"
      @query-change="onTagMenuQueryChange"
      @add-tag="addTagFromMenu"
      @remove-tag="removeTagFromMenu"
      @edit-tag="editTagMetadataFromMenu"
      @add-new-tag="addNewTagFromMenu"
      @auto-tag="applyAutoTagFromMenu"
    />

    <CollectionMenuDialog
      :visible="collectionMenuVisible"
      :busy="collectionMenuBusy"
      :search-busy="collectionMenuSearchBusy"
      :error-message="collectionMenuError"
      :query="collectionMenuQuery"
      :selection-items="collectionMenuSelectionItems"
      :suggestions="collectionMenuSuggestions"
      :selected-collection="collectionMenuSelectedCollection"
      :item-actions="collectionMenuActionItems"
      :confirm-disabled="collectionMenuConfirmDisabled"
      :confirm-label="collectionMenuConfirmLabel"
      @close="closeCollectionMenu"
      @cancel="closeCollectionMenu"
      @confirm="confirmCollectionMenuChanges"
      @query-change="onCollectionMenuQueryChange"
      @select-collection="handleCollectionMenuSelect"
      @item-action-change="setCollectionMenuImageAction"
    />

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
      :visible="confirmDialog.visible"
      :title="confirmDialog.title"
      :message="confirmDialog.message"
      :confirm-label="confirmDialog.confirmLabel"
      :cancel-label="confirmDialog.cancelLabel"
      :tone="confirmDialog.tone"
      :show-cancel="confirmDialog.showCancel"
      :busy="confirmDialog.busy"
      :busy-label="confirmDialog.busyLabel"
      @cancel="closeConfirmDialog"
      @confirm="handleConfirmDialogConfirm"
    />

    <ActionProgressOverlay
      :visible="actionBusy"
      :title="actionBusyTitleResolved"
      :message="actionBusyMessageResolved"
    />
  </section>
</template>

<script>
import LoadingSpinner from '../components/LoadingSpinner.vue'
import BreadcrumbHeader from '../components/BreadcrumbHeader.vue'
import MediaItemCard from '../components/MediaItemCard.vue'
import ConfirmationDialog from '../components/ConfirmationDialog.vue'
import ActionProgressOverlay from '../components/ActionProgressOverlay.vue'
import PagePaginationBar from '../components/PagePaginationBar.vue'
import SelectionIsland from '../components/SelectionIsland.vue'
import SelectionDetailOverlay from '../components/SelectionDetailOverlay.vue'
import CollectionMenuDialog from '../components/CollectionMenuDialog.vue'
import TagMenuDialog from '../components/TagMenuDialog.vue'
import TagFormDialog from '../components/TagFormDialog.vue'
import { normalizeTagColors } from '../utils/tagColors'
import { getCommonBrowsePageContract } from '../utils/commonBrowsePage'
import {
  DEFAULT_PAGE_CONFIG,
  PAGE_BROWSE_MODE_PAGED,
  PAGE_BROWSE_MODE_SCROLL,
  PAGE_CONFIG_UPDATED_EVENT,
  fetchPageConfig,
  getCachedPageConfig,
} from '../utils/pageConfig'

const API_BASE = 'http://127.0.0.1:8000'
const POLL_MS = 180
const DEBOUNCE_MS = 300
const LONG_PRESS_MS = 220
const TAG_BATCH_SIZE = 120
const LIST_ROW_HEIGHT = 62
const LIST_OVERSCAN_ROWS = 12
const SELECTION_INFO_HEIGHT = 56
const SELECTION_OVERSCAN_ROWS = 2
const SELECTION_LANDSCAPE_COLS = 5
const SELECTION_PORTRAIT_COLS = 3
const SELECTION_LANDSCAPE_GAP = 16
const SELECTION_PORTRAIT_GAP = 12
const LANDSCAPE_SELECTION_ROWS = 2
const PORTRAIT_SELECTION_ROWS = 3
const FIRST_ROW_TOLERANCE_PX = 12
const RESTORE_ANCHOR_PADDING_PX = 12
const DIMENSION_CORRECTION_BATCH_MS = 60
const PHOTO_GRID_GAP_PX = 4
const PHOTO_GRID_TARGET_HEIGHT_PX = 440
const PHOTO_GRID_MIN_TARGET_HEIGHT_PX = 140
const PHOTO_GRID_MAX_TARGET_HEIGHT_PX = 640
const LANDSCAPE_PHOTO_ROWS = 2
const PORTRAIT_MASONRY_COLS = 2
const PORTRAIT_MASONRY_GAP_PX = 6
const MASONRY_SKELETON_MIN_LOADED = 1
const MIN_PAGED_PHOTO_ROWS = 2
const MIN_PAGED_SELECTION_ROWS = 2
const PAGED_GRID_BOTTOM_RESERVE_PX = 12
const PAGED_LIST_BOTTOM_RESERVE_PX = 12
const PAGE_SECTION_GAP_PX = 10
const DEFAULT_LIST_PAGE_SIZE = 20
const LIST_PAGE_SIZE_OPTIONS = Object.freeze([10, 20, 50, 100])
const JUSTIFIED_LAYOUT_CACHE = new Map()
const JUSTIFIED_LAYOUT_CACHE_LIMIT = 36

function rememberJustifiedLayout(cacheKey, rows) {
  if (JUSTIFIED_LAYOUT_CACHE.has(cacheKey)) {
    JUSTIFIED_LAYOUT_CACHE.delete(cacheKey)
  }
  JUSTIFIED_LAYOUT_CACHE.set(cacheKey, rows)
  while (JUSTIFIED_LAYOUT_CACHE.size > JUSTIFIED_LAYOUT_CACHE_LIMIT) {
    const oldestKey = JUSTIFIED_LAYOUT_CACHE.keys().next().value
    JUSTIFIED_LAYOUT_CACHE.delete(oldestKey)
  }
  return rows
}

function createDialogState() {
  return {
    visible: false,
    title: '请确认操作',
    message: '',
    confirmLabel: '确认',
    cancelLabel: '取消',
    tone: 'danger',
    showCancel: true,
    busy: false,
    busyLabel: '处理中…',
    onConfirm: null,
  }
}

export default {
  name: 'BrowsePage',
  components: { LoadingSpinner, BreadcrumbHeader, MediaItemCard, ConfirmationDialog, ActionProgressOverlay, PagePaginationBar, SelectionIsland, SelectionDetailOverlay, CollectionMenuDialog, TagMenuDialog, TagFormDialog },

  data() {
    const cachedPageConfig = getCachedPageConfig()
    return {
      items: [],
      loading: true,
      cacheUrls: {},
      previewFailureTokens: {},
      detailOriginalFailureTokens: {},
      previewRepairQueue: [],
      previewRepairTimer: null,
      previewRepairInFlight: false,
      pollTimer: null,
      taskId: null,
      observer: null,
      debounceTimer: null,
      resizeObserver: null,
      lastCenter: -1,
      lastScrollDirection: 'none',
      lastObservedScrollTop: typeof window !== 'undefined' ? (window.scrollY || window.pageYOffset || 0) : 0,
      cacheRequestGeneration: 0,
      cacheStatusCursor: 0,
      lastCacheRequestSignature: '',
      imgDimensions: {},
      layoutFingerprint: '',
      pendingViewAnchor: null,
      pendingDimensionCorrections: {},
      dimensionFlushTimer: null,
      containerWidth: 0,
      itemGridViewportTop: 0,
      paginationHostHeight: 0,
      viewMode: 'grid',
      pageBrowseMode: cachedPageConfig.browseMode || DEFAULT_PAGE_CONFIG.browseMode,
      pageScrollWindowSize: cachedPageConfig.scrollWindowSize || DEFAULT_PAGE_CONFIG.scrollWindowSize,
      sortBy: 'alpha',
      sortDir: 'asc',
      albumInfo: null,
      coverPickerMode: false,
      photoPageIndex: 0,
      selectionGridPageIndex: 0,
      listPageIndex: 0,
      listPageSize: DEFAULT_LIST_PAGE_SIZE,
      selectionMode: false,
      viewModeBeforeSelection: 'grid',
      selectionInfoMode: 'name',
      selectedMap: {},
      selectionTypeLock: null,
      selectionAnchorIndex: null,
      pointerSelection: null,
      longPressTimer: null,
      suppressNextListClick: false,
      tagLookupMap: {},
      categoryDisplayMap: {},
      tagsLoading: false,
      tagFetchSerial: 0,
      scrollTop: typeof window !== 'undefined' ? (window.scrollY || window.pageYOffset || 0) : 0,
      viewportHeight: typeof window !== 'undefined' ? window.innerHeight : 0,
      viewportWidth: typeof window !== 'undefined' ? window.innerWidth : 0,
      pageMainHeight: 0,
      virtualStartIndex: 0,
      virtualEndIndex: 0,
      virtualAnchorIndex: 0,
      virtualContainerTop: 0,
      selectionRowHeight: 0,
      scrollFrameId: null,
      selectionDetailsOpen: false,
      selectionDetailsBounds: {
        top: '0px',
        right: '0px',
        bottom: '0px',
        left: '0px',
      },
      selectionDetailsHostWidth: 0,
      selectionDetailsHostHeight: 0,
      scrollLockState: null,
      selectionDetailFetchSerial: 0,
      collectionMenuVisible: false,
      collectionMenuBusy: false,
      collectionMenuSearchBusy: false,
      collectionMenuError: '',
      collectionMenuQuery: '',
      collectionMenuSuggestions: [],
      collectionMenuSelectedCollection: null,
      collectionMenuActionByImageId: {},
      collectionMenuSearchTimer: null,
      tagMenuVisible: false,
      tagMenuBusy: false,
      tagMenuSearchBusy: false,
      tagMenuError: '',
      tagMenuQuery: '',
      tagMenuSuggestions: [],
      tagMenuRecentTags: [],
      tagMenuExistingTags: [],
      tagMenuDraftByImageId: {},
      tagMenuOriginalByImageId: {},
      tagMenuDirty: false,
      tagMenuSearchTimer: null,
      tagFormVisible: false,
      tagFormMode: 'create',
      tagFormSaving: false,
      tagFormError: '',
      tagFormTag: null,
      tagFormExistingNames: [],
      selectAllMenuOpen: false,
      metadataEditBusy: false,
      actionBusy: false,
      actionBusyTitle: '',
      actionBusyText: '',
      messageText: '',
      messageType: 'success',
      lastPreviewRepairSignature: '',
      reconcileInFlight: false,
      confirmDialog: createDialogState(),
    }
  },

  computed: {
    pageContractName() {
      return this.$route.meta?.browseContract || 'calendar'
    },
    pageContract() {
      return getCommonBrowsePageContract(this.pageContractName)
    },
    isTrashMode() {
      return this.pageContractName === 'trash'
    },
    isCollectionMode() {
      return this.pageContractName === 'collection'
    },
    isTagMode() {
      return this.pageContractName === 'tag'
    },
    dateGroup() {
      return this.$route.params.group || ''
    },
    collectionPublicId() {
      return this.$route.params.collectionId || ''
    },
    currentBrowseTagId() {
      const raw = this.$route.params.tagId
      const value = Number.parseInt(Array.isArray(raw) ? raw[0] : raw, 10)
      return Number.isInteger(value) ? value : null
    },
    albumPath() {
      const raw = this.$route.params.albumPath
      if (!raw) return ''
      return Array.isArray(raw) ? raw.join('/') : raw
    },
    isAlbumMode() {
      return this.albumPath.length > 0
    },
    fullAlbumPath() {
      if (!this.albumPath) return ''
      return `${this.dateGroup}/${this.albumPath}`
    },
    headerCrumbs() {
      return this.pageContract.buildCrumbs(this)
    },
    pageHeaderActions() {
      return this.pageContract.buildHeaderActions(this)
    },
    emptyStateIcon() {
      return this.pageContract.emptyState?.icon || '📂'
    },
    emptyStateText() {
      return this.pageContract.emptyState?.text || '此页面尚无内容。'
    },
    totalCount() {
      return this.items.length
    },
    cachePageToken() {
      if (this.isCollectionMode) {
        return `browse:collection:${this.collectionPublicId}`
      }
      if (this.isTagMode) {
        return `browse:tag:${this.currentBrowseTagId || 'unknown'}`
      }
      if (this.isAlbumMode) {
        return `browse:${this.fullAlbumPath}`
      }
      return `browse:${this.dateGroup}`
    },
    cacheSortSignature() {
      return `${this.sortBy}:${this.sortDir}:${this.items.length}`
    },
    scrollWindowRadius() {
      return Math.max(1, Math.floor((this.pageScrollWindowSize || DEFAULT_PAGE_CONFIG.scrollWindowSize) / 2))
    },
    isPhotoGridMode() {
      return this.viewMode === 'grid' && !this.selectionMode
    },
    isSelectionGridMode() {
      return this.selectionMode && this.viewMode === 'grid'
    },
    isPagedBrowseMode() {
      return this.pageBrowseMode === PAGE_BROWSE_MODE_PAGED
    },
    isVirtualizedMode() {
      return !this.isPagedBrowseMode && (this.isSelectionGridMode || this.viewMode === 'list')
    },
    isPortrait() {
      const width = this.viewportWidth || (typeof window !== 'undefined' ? window.innerWidth : 0)
      const height = this.viewportHeight || (typeof window !== 'undefined' ? window.innerHeight : 0)
      if (!width || !height) return false
      return height > width
    },
    isPortraitMasonryMode() {
      return this.isPhotoGridMode && this.isPortrait
    },
    masonryColWidth() {
      const gap = PORTRAIT_MASONRY_GAP_PX
      const width = this.containerWidth || (typeof window !== 'undefined' ? window.innerWidth : 800)
      return Math.max(60, Math.floor((width - gap * (PORTRAIT_MASONRY_COLS - 1)) / PORTRAIT_MASONRY_COLS))
    },
    masonrySkeletonReady() {
      if (!this.isPortraitMasonryMode) return true
      return Object.keys(this.imgDimensions).length >= MASONRY_SKELETON_MIN_LOADED
    },
    masonryLayout() {
      if (!this.isPortraitMasonryMode || !this.items.length) {
        return { placements: [], totalHeight: 0 }
      }
      const colWidth = this.masonryColWidth
      const gap = PORTRAIT_MASONRY_GAP_PX
      const items = this.items
      const cacheKey = `masonry|${this.cachePageToken}|${this.cacheSortSignature}|${colWidth}|${this.layoutFingerprint}`
      if (JUSTIFIED_LAYOUT_CACHE.has(cacheKey)) {
        return JUSTIFIED_LAYOUT_CACHE.get(cacheKey)
      }
      const colHeights = Array(PORTRAIT_MASONRY_COLS).fill(0)
      const placements = items.map((item, idx) => {
        const key = item?.id || item?.public_id
        const dims = this.imgDimensions[key] || { w: 4, h: 3 }
        const itemHeight = Math.max(40, Math.round(colWidth * dims.h / dims.w))
        let col = 0
        let minH = colHeights[0]
        for (let c = 1; c < PORTRAIT_MASONRY_COLS; c++) {
          if (colHeights[c] < minH) { minH = colHeights[c]; col = c }
        }
        const top = colHeights[col]
        colHeights[col] += itemHeight + gap
        return { ...item, _idx: idx, col, top, computedWidth: colWidth, computedHeight: itemHeight }
      })
      const totalHeight = Math.max(0, Math.max(...colHeights) - gap)
      const result = { placements, totalHeight }
      return rememberJustifiedLayout(cacheKey, result)
    },
    masonryPages() {
      if (!this.isPagedBrowseMode || !this.isPortraitMasonryMode || !this.items.length) return []
      const budget = this.pagedGridHeightBudget
      const colWidth = this.masonryColWidth
      const gap = PORTRAIT_MASONRY_GAP_PX
      const items = this.items
      const pages = []
      let pageStartIdx = 0
      while (pageStartIdx < items.length) {
        const colHeights = Array(PORTRAIT_MASONRY_COLS).fill(0)
        const pagePlacements = []
        let i = pageStartIdx
        while (i < items.length) {
          const item = items[i]
          const key = item?.id || item?.public_id
          const dims = this.imgDimensions[key] || { w: 4, h: 3 }
          const itemHeight = Math.max(40, Math.round(colWidth * dims.h / dims.w))
          let col = 0
          let minH = colHeights[0]
          for (let c = 1; c < PORTRAIT_MASONRY_COLS; c++) {
            if (colHeights[c] < minH) { minH = colHeights[c]; col = c }
          }
          const prospectiveFill = colHeights[col] + itemHeight
          if (pagePlacements.length > 0 && prospectiveFill > budget) break
          const top = colHeights[col]
          colHeights[col] += itemHeight + gap
          pagePlacements.push({ ...item, _idx: i, col, top, computedWidth: colWidth, computedHeight: itemHeight })
          i++
        }
        const totalHeight = Math.max(0, Math.max(...colHeights) - gap)
        pages.push({
          placements: pagePlacements,
          totalHeight,
          startIndex: pagePlacements[0]?._idx ?? pageStartIdx,
          endIndex: pagePlacements[pagePlacements.length - 1]?._idx ?? pageStartIdx,
        })
        pageStartIdx = i
      }
      return pages
    },
    activeMasonryPlacements() {
      if (!this.isPortraitMasonryMode) return []
      if (!this.isPagedBrowseMode) return this.masonryLayout.placements
      return this.masonryPages[this.normalizedPhotoPageIndex]?.placements || []
    },
    activeMasonryTotalHeight() {
      if (!this.isPortraitMasonryMode) return 0
      if (!this.isPagedBrowseMode) return this.masonryLayout.totalHeight
      return this.masonryPages[this.normalizedPhotoPageIndex]?.totalHeight || 0
    },
    masonryGridStyle() {
      if (!this.isPortraitMasonryMode) return null
      const height = this.isPagedBrowseMode ? this.pagedGridHeightBudget : this.activeMasonryTotalHeight
      return {
        position: 'relative',
        height: `${Math.max(100, height)}px`,
        overflow: this.isPagedBrowseMode ? 'hidden' : 'visible',
      }
    },
    photoGridRowCount() {
      return this.isPhotoGridMode && !this.isPortraitMasonryMode ? this.justifiedRows.length : 0
    },
    selectionColumnCount() {
      return this.isPortrait ? SELECTION_PORTRAIT_COLS : SELECTION_LANDSCAPE_COLS
    },
    selectionRowsPerPageTarget() {
      return this.isPortrait ? PORTRAIT_SELECTION_ROWS : LANDSCAPE_SELECTION_ROWS
    },
    selectionGridGapPx() {
      return this.selectionColumnCount === SELECTION_LANDSCAPE_COLS
        ? SELECTION_LANDSCAPE_GAP
        : SELECTION_PORTRAIT_GAP
    },
    pagedSelectionCardHeight() {
      const rows = this.selectionRowsPerPageTarget
      const gap = this.selectionGridGapPx
      const budget = this.pagedGridHeightBudget
      const totalGap = gap * Math.max(0, rows - 1)
      const height = (budget - totalGap) / rows
      return Math.max(SELECTION_INFO_HEIGHT + 60, Math.floor(height))
    },
    effectiveSelectionRowHeight() {
      if (this.isPagedBrowseMode && this.isSelectionGridMode) {
        return this.pagedSelectionCardHeight
      }
      if (this.selectionRowHeight > 0) return this.selectionRowHeight

      const width = this.containerWidth || (typeof window !== 'undefined' ? window.innerWidth - 48 : 800)
      const totalGap = this.selectionGridGapPx * Math.max(0, this.selectionColumnCount - 1)
      const cardWidth = Math.max(0, (width - totalGap) / this.selectionColumnCount)
      return Math.max(SELECTION_INFO_HEIGHT + 80, Math.round(cardWidth + SELECTION_INFO_HEIGHT + 2))
    },
    visibleSelectionEntries() {
      const start = this.isSelectionGridMode
        ? (this.isPagedBrowseMode ? this.selectionGridPageStartIndex : this.virtualStartIndex)
        : 0
      const end = this.isSelectionGridMode
        ? (this.isPagedBrowseMode ? this.selectionGridPageEndIndex : this.virtualEndIndex)
        : this.items.length
      return this.items.slice(start, end).map((item, offset) => ({ item, index: start + offset }))
    },
    isPaginationBarVisible() {
      if (!this.isPagedBrowseMode || !this.items.length || !this.activePaginationConfig) return false
      if (this.activePaginationConfig.pageSize !== null) return true
      return Number(this.activePaginationConfig.totalPages || 0) > 1
    },
    selectionIslandStyle() {
      if (!this.selectionMode || !this.isPagedBrowseMode || !this.isPaginationBarVisible) return null
      const hostHeight = this.paginationHostHeight > 0 ? this.paginationHostHeight : 52
      return {
        bottom: `${hostHeight + 10}px`,
      }
    },
    selectionGridStyle() {
      if (!this.isSelectionGridMode) return null

      if (this.isPagedBrowseMode) {
        const rows = this.selectionRowsPerPageTarget
        const cardHeight = this.pagedSelectionCardHeight
        return {
          minHeight: `${this.pagedGridHeightBudget}px`,
          height: `${this.pagedGridHeightBudget}px`,
          overflow: 'hidden',
          alignContent: 'start',
          gridAutoRows: `${cardHeight}px`,
          gridTemplateRows: `repeat(${rows}, ${cardHeight}px)`,
        }
      }

      const totalRows = Math.ceil(this.items.length / this.selectionColumnCount)
      const startRow = Math.floor(this.virtualStartIndex / this.selectionColumnCount)
      const endRow = Math.ceil(this.virtualEndIndex / this.selectionColumnCount)
      const visibleRows = Math.max(0, endRow - startRow)
      const rowHeight = this.effectiveSelectionRowHeight
      const gap = this.selectionGridGapPx
      const totalHeight = totalRows
        ? totalRows * rowHeight + Math.max(0, totalRows - 1) * gap
        : 0
      const paddingTop = startRow * (rowHeight + gap)
      const renderedHeight = visibleRows
        ? visibleRows * rowHeight + Math.max(0, visibleRows - 1) * gap
        : 0

      return {
        paddingTop: `${paddingTop}px`,
        paddingBottom: `${Math.max(0, totalHeight - paddingTop - renderedHeight)}px`,
      }
    },
    visibleListEntries() {
      const start = this.viewMode === 'list'
        ? (this.isPagedBrowseMode ? this.listPageStartIndex : this.virtualStartIndex)
        : 0
      const end = this.viewMode === 'list'
        ? (this.isPagedBrowseMode ? this.listPageEndIndex : this.virtualEndIndex)
        : this.items.length
      return this.items.slice(start, end).map((item, offset) => ({ item, index: start + offset }))
    },
    listViewStyle() {
      if (this.viewMode !== 'list') return null

      if (this.isPagedBrowseMode) {
        return {
          minHeight: `${this.pagedListHeightBudget}px`,
          height: `${this.pagedListHeightBudget}px`,
          overflow: 'hidden',
        }
      }

      return {
        paddingTop: `${this.virtualStartIndex * LIST_ROW_HEIGHT}px`,
        paddingBottom: `${Math.max(0, (this.items.length - this.virtualEndIndex) * LIST_ROW_HEIGHT)}px`,
      }
    },
    photoGridStyle() {
      if (!this.isPhotoGridMode || !this.isPagedBrowseMode || this.isPortraitMasonryMode) return null
      return {
        minHeight: `${this.pagedGridHeightBudget}px`,
        height: `${this.pagedGridHeightBudget}px`,
        overflow: 'hidden',
      }
    },
    pagedGridHeightBudget() {
      const hostHeight = this.pageMainHeight > 0 ? this.pageMainHeight : this.viewportHeight
      return Math.max(
        220,
        hostHeight - this.pagedPaginationHostReservePx - PAGED_GRID_BOTTOM_RESERVE_PX,
      )
    },
    pagedListHeightBudget() {
      const hostHeight = this.pageMainHeight > 0 ? this.pageMainHeight : this.viewportHeight
      return Math.max(
        180,
        hostHeight - this.pagedPaginationHostReservePx - PAGED_LIST_BOTTOM_RESERVE_PX,
      )
    },
    photoGridTargetHeight() {
      // In paged mode, derive a target row height that fits the requested rows-per-page
      // (2 in landscape, 3 in portrait) within the available budget. Scroll mode keeps
      // the legacy fixed target height to preserve historical look.
      if (!this.isPagedBrowseMode) return PHOTO_GRID_TARGET_HEIGHT_PX
      const rows = this.isPortrait ? PORTRAIT_SELECTION_ROWS : LANDSCAPE_PHOTO_ROWS
      const budget = this.pagedGridHeightBudget
      const totalGap = PHOTO_GRID_GAP_PX * Math.max(0, rows - 1)
      const candidate = (budget - totalGap) / rows
      if (!Number.isFinite(candidate) || candidate <= 0) return PHOTO_GRID_TARGET_HEIGHT_PX
      return Math.min(
        PHOTO_GRID_MAX_TARGET_HEIGHT_PX,
        Math.max(PHOTO_GRID_MIN_TARGET_HEIGHT_PX, Math.floor(candidate)),
      )
    },
    justifiedRows() {
      const width = this.containerWidth || (typeof window !== 'undefined' ? window.innerWidth - 48 : 800)
      const gap = PHOTO_GRID_GAP_PX
      const targetHeight = this.photoGridTargetHeight
      const items = this.items
      if (!items.length) return []

      const cacheKey = `${this.cachePageToken}|${this.cacheSortSignature}|${Math.max(1, Math.round(width))}|${targetHeight}|${this.layoutFingerprint}`
      if (JUSTIFIED_LAYOUT_CACHE.has(cacheKey)) {
        return JUSTIFIED_LAYOUT_CACHE.get(cacheKey)
      }

      const rows = []
      let rowStart = 0
      let rowAspectRatio = 0

      for (let i = 0; i < items.length; i++) {
        const key = items[i].id || items[i].public_id
        const dims = this.imgDimensions[key] || { w: 4, h: 3 }
        rowAspectRatio += dims.w / dims.h
        const isLast = i === items.length - 1
        const rowLen = i - rowStart + 1
        const neededWidth = rowAspectRatio * targetHeight + gap * (rowLen - 1)

        if (neededWidth >= width || isLast) {
          const totalGap = gap * (rowLen - 1)
          const actualHeight = (isLast && neededWidth < width)
            ? targetHeight
            : Math.round((width - totalGap) / rowAspectRatio)
          const rowItems = []
          for (let j = rowStart; j <= i; j++) {
            const item = items[j]
            const itemKey = item.id || item.public_id
            const dimsForItem = this.imgDimensions[itemKey] || { w: 4, h: 3 }
            rowItems.push({
              ...item,
              _idx: j,
              computedWidth: Math.round((dimsForItem.w / dimsForItem.h) * actualHeight),
            })
          }
          rows.push({ items: rowItems, height: actualHeight })
          rowStart = i + 1
          rowAspectRatio = 0
        }
      }
      return rememberJustifiedLayout(cacheKey, rows)
    },
    photoGridPages() {
      if (!this.isPagedBrowseMode || !this.justifiedRows.length) return []

      const pages = []
      const budget = this.pagedGridHeightBudget
      const estimatedRows = Math.max(
        1,
        Math.floor((budget + PHOTO_GRID_GAP_PX) / (PHOTO_GRID_TARGET_HEIGHT_PX + PHOTO_GRID_GAP_PX)),
      )
      const minRowsPerPage = this.justifiedRows.length > 1 && estimatedRows > 1 ? MIN_PAGED_PHOTO_ROWS : 1
      const buildPage = (pageRows) => {
        const firstIndex = pageRows[0]?.items?.[0]?._idx ?? 0
        const lastRow = pageRows[pageRows.length - 1]
        const lastIndex = lastRow?.items?.[lastRow.items.length - 1]?._idx ?? firstIndex
        return { rows: pageRows, startIndex: firstIndex, endIndex: lastIndex }
      }

      let pageRows = []
      let pageHeight = 0

      for (let rowIndex = 0; rowIndex < this.justifiedRows.length; rowIndex += 1) {
        const row = this.justifiedRows[rowIndex]
        const nextRowHeight = row.height + (pageRows.length ? PHOTO_GRID_GAP_PX : 0)
        const remainingRows = this.justifiedRows.length - rowIndex
        const canSplit = pageRows.length >= minRowsPerPage
        const canLeaveFollowingPage = remainingRows > Math.max(0, minRowsPerPage - 1)

        if (pageRows.length && pageHeight + nextRowHeight > budget && canSplit && canLeaveFollowingPage) {
          pages.push(buildPage(pageRows))
          pageRows = []
          pageHeight = 0
        }

        pageRows.push(row)
        pageHeight += row.height + (pageRows.length > 1 ? PHOTO_GRID_GAP_PX : 0)
      }

      if (pageRows.length) {
        pages.push(buildPage(pageRows))
      }

      if (minRowsPerPage > 1 && pages.length > 1) {
        const lastPage = pages[pages.length - 1]
        const previousPage = pages[pages.length - 2]
        if (lastPage.rows.length < minRowsPerPage && previousPage.rows.length > minRowsPerPage) {
          while (lastPage.rows.length < minRowsPerPage && previousPage.rows.length > minRowsPerPage) {
            lastPage.rows.unshift(previousPage.rows.pop())
          }
          pages.splice(pages.length - 2, 2, buildPage(previousPage.rows), buildPage(lastPage.rows))
        }
      }

      return pages
    },
    photoGridTotalPages() {
      if (!this.isPagedBrowseMode) return 1
      if (this.isPortraitMasonryMode) return Math.max(1, this.masonryPages.length)
      return Math.max(1, this.photoGridPages.length)
    },
    normalizedPhotoPageIndex() {
      return Math.min(Math.max(0, this.photoPageIndex), Math.max(0, this.photoGridTotalPages - 1))
    },
    activePhotoRows() {
      if (this.isPortraitMasonryMode) return []
      if (!this.isPagedBrowseMode) return this.justifiedRows
      return this.photoGridPages[this.normalizedPhotoPageIndex]?.rows || []
    },
    selectionGridRowsPerPage() {
      if (!this.isPagedBrowseMode || !this.isSelectionGridMode) return 0

      const totalRows = Math.ceil(this.items.length / this.selectionColumnCount)
      if (!totalRows) return 0

      const rowSpan = this.effectiveSelectionRowHeight + this.selectionGridGapPx
      const estimatedRows = Math.max(1, Math.floor((this.pagedGridHeightBudget + this.selectionGridGapPx) / rowSpan))
      const minRows = totalRows > 1 && estimatedRows > 1 ? MIN_PAGED_SELECTION_ROWS : 1
      return Math.min(totalRows, Math.max(minRows, estimatedRows))
    },
    selectionGridPageSize() {
      if (!this.isPagedBrowseMode || !this.isSelectionGridMode) return this.items.length || 1
      return Math.max(1, this.selectionGridRowsPerPage * this.selectionColumnCount)
    },
    selectionGridTotalPages() {
      if (!this.isPagedBrowseMode || !this.isSelectionGridMode) return 1
      return Math.max(1, Math.ceil(this.items.length / this.selectionGridPageSize))
    },
    normalizedSelectionGridPageIndex() {
      return Math.min(Math.max(0, this.selectionGridPageIndex), Math.max(0, this.selectionGridTotalPages - 1))
    },
    selectionGridPageStartIndex() {
      if (!this.isPagedBrowseMode || !this.isSelectionGridMode) return 0
      return this.normalizedSelectionGridPageIndex * this.selectionGridPageSize
    },
    selectionGridPageEndIndex() {
      if (!this.isPagedBrowseMode || !this.isSelectionGridMode) return this.items.length
      return Math.min(this.items.length, this.selectionGridPageStartIndex + this.selectionGridPageSize)
    },
    listTotalPages() {
      if (!this.isPagedBrowseMode || this.viewMode !== 'list') return 1
      return Math.max(1, Math.ceil(this.items.length / this.listPageSize))
    },
    normalizedListPageIndex() {
      return Math.min(Math.max(0, this.listPageIndex), Math.max(0, this.listTotalPages - 1))
    },
    listPageStartIndex() {
      if (!this.isPagedBrowseMode || this.viewMode !== 'list') return 0
      return this.normalizedListPageIndex * this.listPageSize
    },
    listPageEndIndex() {
      if (!this.isPagedBrowseMode || this.viewMode !== 'list') return this.items.length
      return Math.min(this.items.length, this.listPageStartIndex + this.listPageSize)
    },
    activePaginationConfig() {
      if (!this.isPagedBrowseMode || !this.items.length) return null

      if (this.viewMode === 'list') {
        return {
          kind: 'list',
          currentPage: this.normalizedListPageIndex + 1,
          totalPages: this.listTotalPages,
          pageSize: this.listPageSize,
          pageSizeOptions: LIST_PAGE_SIZE_OPTIONS,
        }
      }

      if (this.isSelectionGridMode) {
        return {
          kind: 'selection-grid',
          currentPage: this.normalizedSelectionGridPageIndex + 1,
          totalPages: this.selectionGridTotalPages,
          pageSize: null,
          pageSizeOptions: [],
        }
      }

      return {
        kind: 'photo-grid',
        currentPage: this.normalizedPhotoPageIndex + 1,
        totalPages: this.photoGridTotalPages,
        pageSize: null,
        pageSizeOptions: [],
      }
    },
    pagedPaginationHostReservePx() {
      if (this.paginationHostHeight <= 0) return 0
      return this.paginationHostHeight + PAGE_SECTION_GAP_PX
    },
    selectedCount() {
      return Object.keys(this.selectedMap).length
    },
    selectionSummaryText() {
      if (!this.selectedCount) return '已选 0 项'
      if (this.selectionTypeLock === 'album') return `已选 ${this.selectedCount} 个相册`
      if (this.selectionTypeLock === 'image') return `已选 ${this.selectedCount} 张图片`
      return `已选 ${this.selectedCount} 项`
    },
    availableSelectionTypes() {
      const types = new Set()
      for (const item of this.items) {
        if (item?.type === 'album' || item?.type === 'image') {
          types.add(item.type)
        }
      }
      return Array.from(types)
    },
    hasMixedSelectableTypes() {
      return this.availableSelectionTypes.includes('album') && this.availableSelectionTypes.includes('image')
    },
    selectedEntries() {
      const entries = []
      for (let index = 0; index < this.items.length; index++) {
        const item = this.items[index]
        if (this.isItemSelected(item, index)) {
          entries.push({ item, index })
        }
      }
      return entries
    },
    selectionDetailPreviewItems() {
      return this.selectedEntries.map(({ item, index }) => ({
        key: this.itemKey(item, index),
        name: this.detailNameText(item),
        type: item?.type || 'image',
        previewUrl: this.detailPreviewUrl(item),
        aspectRatio: this.detailAspectRatio(item),
      }))
    },
    selectionDetailsLayerStyle() {
      return this.selectionDetailsBounds
    },
    selectionDetailsPanelStyle() {
      const hostWidth = this.selectionDetailsHostWidth || (typeof window !== 'undefined' ? window.innerWidth : 0)
      const hostHeight = this.selectionDetailsHostHeight || (typeof window !== 'undefined' ? window.innerHeight : 0)
      if (!hostWidth || !hostHeight) return null

      const availableWidth = Math.max(0, Math.floor(hostWidth - 12))
      const availableHeight = Math.max(0, Math.floor(hostHeight - 12))
      const isPortraitLike = hostWidth <= 960 || hostWidth < hostHeight

      if (isPortraitLike) {
        const panelWidth = Math.min(
          availableWidth,
          Math.max(Math.min(availableWidth, 320), Math.floor(hostWidth * 0.98)),
        )
        const desiredHeight = Math.floor(hostHeight * 0.96)
        const panelHeight = Math.min(
          availableHeight,
          Math.max(Math.min(availableHeight, 360), desiredHeight),
        )
        return {
          width: `${panelWidth}px`,
          maxWidth: `${availableWidth}px`,
          height: `${panelHeight}px`,
          maxHeight: `${availableHeight}px`,
        }
      }

      const panelWidth = Math.min(
        1180,
        availableWidth,
        Math.max(Math.min(availableWidth, 760), Math.floor(hostWidth * 0.8)),
      )
      const panelHeight = Math.min(
        availableHeight,
        Math.max(Math.min(availableHeight, 460), Math.round(panelWidth * 0.58)),
      )
      return {
        width: `${panelWidth}px`,
        height: `${panelHeight}px`,
        maxWidth: `${availableWidth}px`,
        maxHeight: `${availableHeight}px`,
      }
    },
    selectionDetailNameField() {
      return this.buildDetailField(this.selectedEntries.map(({ item }) => this.detailNameText(item)))
    },
    selectionDetailRawName() {
      const item = this.selectedEntries[0]?.item
      if (item?.type !== 'image') return ''
      return this.detailNameText(item)
    },
    selectionDetailCategoryField() {
      return this.buildDetailField(this.selectedEntries.map(({ item }) => this.detailCategoryText(item)))
    },
    selectionDetailRawCategoryId() {
      const item = this.selectedEntries[0]?.item
      const categoryId = Number(item?.category_id)
      if (item?.type !== 'image' || !Number.isInteger(categoryId) || categoryId <= 0) return null
      return categoryId
    },
    selectionDetailCategoryOptions() {
      return Object.entries(this.categoryDisplayMap)
        .map(([id, label]) => ({
          value: Number(id),
          label: label || `#${id}`,
        }))
        .filter(option => Number.isInteger(option.value) && option.value > 0)
        .sort((left, right) => left.value - right.value)
    },
    selectionDetailTagsField() {
      const imageEntries = this.selectedEntries.filter(({ item }) => item?.type === 'image')
      if (!imageEntries.length) {
        return {
          text: '',
          isVarious: false,
          isEmpty: true,
          items: [],
        }
      }

      const tagIdLists = imageEntries.map(({ item }) => {
        const ids = Array.isArray(item?.tags) ? item.tags.filter(id => Number.isInteger(id)) : []
        return this.sortTagIdsByName([...new Set(ids)])
      })

      const commonTagIds = tagIdLists.reduce((previous, current) => {
        if (!previous.length) return []
        const currentSet = new Set(current)
        return previous.filter(id => currentSet.has(id))
      }, [...(tagIdLists[0] || [])])

      const sortedCommonTagIds = this.sortTagIdsByName([...new Set(commonTagIds)])
      if (sortedCommonTagIds.length) {
        return {
          text: '',
          isVarious: false,
          isEmpty: false,
          items: this.buildTagItemsByIds(sortedCommonTagIds),
        }
      }

      const hasAnyTag = tagIdLists.some(ids => ids.length > 0)
      if (hasAnyTag) {
        return {
          text: 'various',
          isVarious: true,
          isEmpty: false,
          items: [],
        }
      }

      return {
        text: '',
        isVarious: false,
        isEmpty: true,
        items: [],
      }
    },
    selectionDetailSizeField() {
      return this.buildDetailField(this.selectedEntries.map(({ item }) => this.detailSizeText(item)))
    },
    selectionDetailSizeLabel() {
      return this.selectionDetailType === 'album' ? '图片数量' : '尺寸'
    },
    selectionDetailImportedField() {
      return this.buildDetailField(this.selectedEntries.map(({ item }) => this.detailImportedText(item)))
    },
    selectionDetailCreatedField() {
      return this.buildDetailField(this.selectedEntries.map(({ item }) => this.detailCreatedText(item)))
    },
    selectionDetailRawCreatedAt() {
      const item = this.selectedEntries[0]?.item
      if (item?.type !== 'image') return null
      return item?.file_created_at || null
    },
    selectionDetailType() {
      return this.selectedEntries[0]?.item?.type || null
    },
    selectionDetailPrimaryActionLabel() {
      return this.selectionDetailType === 'album' ? '查看相册' : '查看原图'
    },
    selectionDetailPolicy() {
      return this.pageContract.buildDetailPolicy(this)
    },
    canOpenPrimaryActionFromDetails() {
      if (this.selectedEntries.length !== 1) return false
      const entry = this.selectedEntries[0]
      if (entry?.item?.type === 'image') {
        return Number.isInteger(entry?.item?.id)
      }
      return entry?.item?.type === 'album' && typeof entry?.item?.album_path === 'string' && entry.item.album_path.length > 0
    },
    selectedImageIds() {
      return this.selectedEntries
        .map(({ item }) => item)
        .filter(item => item?.type === 'image' && Number.isInteger(item?.id))
        .map(item => item.id)
    },
    canEditSelectionName() {
      if (this.actionBusy || this.metadataEditBusy) return false
      if (this.selectedEntries.length !== 1) return false
      return this.selectedEntries[0]?.item?.type === 'image' && Number.isInteger(this.selectedEntries[0]?.item?.id)
    },
    canEditSelectionCategory() {
      if (this.actionBusy || this.metadataEditBusy) return false
      return this.selectedImageIds.length > 0 && this.selectionDetailCategoryOptions.length > 0
    },
    canEditSelectionCreatedAt() {
      if (this.actionBusy || this.metadataEditBusy) return false
      return this.selectedImageIds.length > 0
    },
    canOpenCollectionMenu() {
      if (this.isTrashMode || this.actionBusy) return false
      return this.selectedImageIds.length > 0
    },
    containerImageItems() {
      return this.items.filter(item => item?.type === 'image' && Number.isInteger(item?.id))
    },
    canPickContainerCover() {
      if (this.actionBusy || !this.containerImageItems.length) return false
      if (this.isCollectionMode) return true
      return this.pageContractName === 'calendar' && this.isAlbumMode
    },
    canOpenTagMenu() {
      return this.selectedImageIds.length > 0
    },
    collectionMenuSelectionItems() {
      return this.selectedEntries
        .map(({ item, index }) => ({ item, index }))
        .filter(({ item }) => item?.type === 'image' && Number.isInteger(item?.id))
        .map(({ item, index }) => ({
          key: this.itemKey(item, index),
          imageId: item.id,
          name: this.detailNameText(item),
          previewUrl: this.detailPreviewUrl(item),
          aspectRatio: this.detailAspectRatio(item),
        }))
    },
    collectionMenuActionItems() {
      const selectedCollection = this.collectionMenuSelectedCollection
      const matchedSet = new Set(selectedCollection?.matched_image_ids || [])
      const isMulti = this.collectionMenuSelectionItems.length > 1
      return this.collectionMenuSelectionItems.map((item) => {
        const existsInCollection = matchedSet.has(item.imageId)
        const defaultAction = existsInCollection
          ? (isMulti ? 'keep' : 'remove')
          : 'add'
        return {
          ...item,
          existsInCollection,
          action: this.collectionMenuActionByImageId[item.imageId] || defaultAction,
          canChangeAction: Boolean(isMulti && existsInCollection && !selectedCollection?.isNew),
        }
      })
    },
    collectionMenuConfirmDisabled() {
      if (this.collectionMenuBusy || !this.canOpenCollectionMenu) return true
      return !this.collectionMenuSelectedCollection
    },
    collectionMenuConfirmLabel() {
      const selectedCollection = this.collectionMenuSelectedCollection
      if (!selectedCollection) return '确定'
      if (selectedCollection.isNew) return '创建并加入'
      if (this.collectionMenuSelectionItems.length === 1) {
        const imageId = this.collectionMenuSelectionItems[0]?.imageId
        const action = imageId != null ? this.collectionMenuActionByImageId[imageId] : ''
        return action === 'remove' ? '移除' : '加入'
      }
      return '应用'
    },
    pageSelectionActions() {
      return this.pageContract.buildSelectionActions(this)
    },
    actionBusyTitleResolved() {
      return this.actionBusyTitle || (this.isTrashMode ? '处理中' : '删除中')
    },
    actionBusyMessageResolved() {
      if (this.actionBusyText) return this.actionBusyText
      return this.isTrashMode
        ? '正在处理回收站操作，请稍候…'
        : '正在移动所选内容到回收站，请稍候…'
    },
  },

  watch: {
    '$route.fullPath': {
      handler() { this.loadData() },
    },
    photoGridRowCount(newVal, oldVal) {
      if (newVal !== oldVal) {
        this.refreshObservedGrid()
      }
    },
    viewMode() {
      if (this.selectionMode) return
      this.refreshObservedGrid()
    },
    selectionMode(nextValue) {
      if (nextValue) {
        this.coverPickerMode = false
      }
      if (!nextValue) {
        this.closeSelectionDetails()
        this.closeCollectionMenu()
        this.closeSelectAllMenu()
      }
    },
    selectedCount(nextValue) {
      if (!nextValue) {
        this.closeSelectionDetails()
        this.closeCollectionMenu()
        this.closeSelectAllMenu()
      }
    },
    selectionDetailsOpen(nextValue) {
      if (!nextValue) {
        this.closeCollectionMenu()
        this.closeTagMenu()
      }
    },
  },

  created() {
    this.loadData()
    this.fetchPageConfigSetting()
    window.addEventListener('resize', this.onResize)
    window.addEventListener('scroll', this.onWindowScroll, { passive: true })
    window.addEventListener('keydown', this.onWindowKeydown)
    window.addEventListener('pointerdown', this.onWindowPointerDown)
    window.addEventListener(PAGE_CONFIG_UPDATED_EVENT, this.onPageConfigUpdated)
  },

  beforeUnmount() {
    this.teardownObserver()
    this.teardownResizeObserver()
    this.stopPoll()
    this.clearPointerGesture()
    this.unlockPageScroll()
    window.removeEventListener('resize', this.onResize)
    window.removeEventListener('scroll', this.onWindowScroll)
    window.removeEventListener('keydown', this.onWindowKeydown)
    window.removeEventListener('pointerdown', this.onWindowPointerDown)
    window.removeEventListener(PAGE_CONFIG_UPDATED_EVENT, this.onPageConfigUpdated)
    if (this.previewRepairTimer) {
      clearTimeout(this.previewRepairTimer)
      this.previewRepairTimer = null
    }
    if (this.scrollFrameId) {
      cancelAnimationFrame(this.scrollFrameId)
      this.scrollFrameId = null
    }
    if (this.dimensionFlushTimer) {
      clearTimeout(this.dimensionFlushTimer)
      this.dimensionFlushTimer = null
    }
    if (this.tagMenuSearchTimer) {
      clearTimeout(this.tagMenuSearchTimer)
      this.tagMenuSearchTimer = null
    }
  },

  methods: {
    logBrowseDebug(event, payload = {}) {
      console.debug('[BrowsePage]', { event, ...payload })
    },

    async fetchPageConfigSetting() {
      try {
        const config = await fetchPageConfig()
        this.applyPageConfig(config, false)
      } catch {
        // keep cached or default page config when settings fetch fails
      }
    },

    onPageConfigUpdated(event) {
      this.applyPageConfig(event?.detail || {}, true)
    },

    applyPageConfig(nextConfig = {}, captureAnchor = true) {
      const normalizedMode = nextConfig?.browseMode === PAGE_BROWSE_MODE_PAGED
        ? PAGE_BROWSE_MODE_PAGED
        : PAGE_BROWSE_MODE_SCROLL
      const numericWindowSize = Number.parseInt(
        String(nextConfig?.scrollWindowSize || DEFAULT_PAGE_CONFIG.scrollWindowSize),
        10,
      )
      const normalizedWindowSize = Number.isFinite(numericWindowSize) && numericWindowSize > 0
        ? numericWindowSize
        : DEFAULT_PAGE_CONFIG.scrollWindowSize
      const modeChanged = normalizedMode !== this.pageBrowseMode
      const windowChanged = normalizedWindowSize !== this.pageScrollWindowSize
      if (!modeChanged && !windowChanged) return

      const anchor = captureAnchor ? this.captureViewportAnchor() : null
      this.pageBrowseMode = normalizedMode
      this.pageScrollWindowSize = normalizedWindowSize
      this.lastCacheRequestSignature = ''

      if (modeChanged) {
        this.clearPointerGesture()
        this.closeSelectAllMenu()
        this.normalizePaginationState()
      }

      if (anchor) {
        this.pendingViewAnchor = anchor
      }

      this.$nextTick(() => {
        this.refreshObservedGrid()
      })
    },

    applyPageBrowseMode(nextMode, captureAnchor = true) {
      this.applyPageConfig({
        browseMode: nextMode,
        scrollWindowSize: this.pageScrollWindowSize,
      }, captureAnchor)
    },

    measureItemGridMetrics() {
      const pageMainRect = this.$refs.pageMain?.getBoundingClientRect?.()
      this.pageMainHeight = pageMainRect ? Math.round(pageMainRect.height) : 0
      if (!this.$refs.itemGrid) return

      const rect = this.$refs.itemGrid.getBoundingClientRect()
      this.containerWidth = this.$refs.itemGrid.offsetWidth
      this.itemGridViewportTop = Math.max(0, Math.round(rect.top))
      this.virtualContainerTop = rect.top + (window.scrollY || window.pageYOffset || 0)

      const paginationHostRect = this.$refs.paginationHost?.getBoundingClientRect?.()
      this.paginationHostHeight = paginationHostRect ? Math.round(paginationHostRect.height) : 0
    },

    normalizePaginationState() {
      this.photoPageIndex = Math.min(Math.max(0, this.photoPageIndex), Math.max(0, this.photoGridTotalPages - 1))
      this.selectionGridPageIndex = Math.min(Math.max(0, this.selectionGridPageIndex), Math.max(0, this.selectionGridTotalPages - 1))
      this.listPageIndex = Math.min(Math.max(0, this.listPageIndex), Math.max(0, this.listTotalPages - 1))
    },

    findPhotoPageIndexForItem(targetIndex) {
      const pages = this.isPortraitMasonryMode ? this.masonryPages : this.photoGridPages
      for (let pageIndex = 0; pageIndex < pages.length; pageIndex += 1) {
        const page = pages[pageIndex]
        if (!page) continue
        if (targetIndex >= page.startIndex && targetIndex <= page.endIndex) {
          return pageIndex
        }
      }
      return 0
    },

    restorePagedPageByIndex(targetIndex) {
      if (this.viewMode === 'list') {
        this.listPageIndex = Math.floor(targetIndex / this.listPageSize)
      } else if (this.isSelectionGridMode) {
        const pageSize = Math.max(1, this.selectionGridPageSize)
        this.selectionGridPageIndex = Math.floor(targetIndex / pageSize)
      } else {
        this.photoPageIndex = this.findPhotoPageIndexForItem(targetIndex)
      }

      this.normalizePaginationState()
      this.$nextTick(() => {
        this.queueCurrentPageCache(true, 'restore-paged')
      })
    },

    currentPageAnchorIndex() {
      if (!this.items.length) return -1
      if (this.viewMode === 'list') return this.listPageStartIndex
      if (this.isSelectionGridMode) return this.selectionGridPageStartIndex
      if (this.isPortraitMasonryMode) {
        return this.masonryPages[this.normalizedPhotoPageIndex]?.startIndex ?? 0
      }
      return this.photoGridPages[this.normalizedPhotoPageIndex]?.startIndex ?? 0
    },

    queueCurrentPageCache(immediate = false, reason = 'paged-refresh') {
      const anchorIndex = this.currentPageAnchorIndex()
      if (!Number.isInteger(anchorIndex) || anchorIndex < 0) return

      if (this.viewMode === 'list' || this.isSelectionGridMode) {
        this.queueCachePlan(this.buildVirtualCachePlan(anchorIndex), immediate, reason)
        return
      }

      this.queuePhotoGridCachePlan(anchorIndex, immediate, reason)
    },

    scrollItemGridIntoView() {
      if (!this.$refs.itemGrid || typeof window === 'undefined') return
      const rect = this.$refs.itemGrid.getBoundingClientRect()
      const desiredTop = (window.scrollY || window.pageYOffset || 0) + rect.top - RESTORE_ANCHOR_PADDING_PX
      window.scrollTo({ top: Math.max(0, Math.round(desiredTop)), behavior: 'instant' })
    },

    onPaginationPageChange(nextPage) {
      if (!this.isPagedBrowseMode) return

      const targetPageIndex = Math.max(0, Number(nextPage || 1) - 1)
      if (this.viewMode === 'list') {
        this.listPageIndex = targetPageIndex
      } else if (this.isSelectionGridMode) {
        this.selectionGridPageIndex = targetPageIndex
      } else {
        this.photoPageIndex = targetPageIndex
      }

      this.normalizePaginationState()
      this.$nextTick(() => {
        this.scrollItemGridIntoView()
        this.queueCurrentPageCache(true, 'pagination-change')
      })
    },

    onPaginationPageSizeChange(nextPageSize) {
      if (this.viewMode !== 'list' || !this.isPagedBrowseMode) return

      const normalizedPageSize = LIST_PAGE_SIZE_OPTIONS.includes(nextPageSize)
        ? nextPageSize
        : DEFAULT_LIST_PAGE_SIZE
      if (normalizedPageSize === this.listPageSize) return

      const anchor = this.captureViewportAnchor()
      this.listPageSize = normalizedPageSize
      this.normalizePaginationState()
      if (anchor) {
        this.pendingViewAnchor = anchor
      }

      this.refreshObservedGrid()
      window.requestAnimationFrame(() => {
        this.scrollItemGridIntoView()
      })
    },

    computeLayoutFingerprint(items, dimensions) {
      let hash = 2166136261
      const updateHash = (value) => {
        const text = String(value)
        for (let idx = 0; idx < text.length; idx++) {
          hash ^= text.charCodeAt(idx)
          hash = Math.imul(hash, 16777619)
        }
      }

      for (let index = 0; index < items.length; index++) {
        const item = items[index]
        const key = item?.id || item?.public_id || index
        const dims = dimensions[key] || {}
        updateHash(`${key}:${dims.w || 0}x${dims.h || 0}:${item?.is_cover ? 1 : 0};`)
      }
      return (hash >>> 0).toString(36)
    },

    async loadData(options = {}) {
      const preserveSelection = Boolean(options?.preserveSelection)
      const preserveView = Object.prototype.hasOwnProperty.call(options || {}, 'preserveView')
        ? Boolean(options.preserveView)
        : preserveSelection
      const selectionSnapshot = preserveSelection ? this.captureSelectionSnapshot() : null

      this.loading = true
      this.messageText = ''
      const defaultSort = this.pageContract.defaultSort(this)
      this.sortBy = defaultSort.sortBy
      this.sortDir = defaultSort.sortDir
      this.cacheUrls = {}
      this.imgDimensions = {}
      this.layoutFingerprint = ''
      this.lastCenter = -1
      this.lastScrollDirection = 'none'
      this.lastObservedScrollTop = typeof window !== 'undefined' ? (window.scrollY || window.pageYOffset || 0) : 0
      this.cacheRequestGeneration = 0
      this.cacheStatusCursor = 0
      this.lastCacheRequestSignature = ''
      this.previewFailureTokens = {}
      this.detailOriginalFailureTokens = {}
      this.previewRepairQueue = []
      this.previewRepairInFlight = false
      this.lastPreviewRepairSignature = ''
      this.selectionRowHeight = 0
      this.albumInfo = null
      this.coverPickerMode = false
      this.pendingViewAnchor = null
      this.pendingDimensionCorrections = {}
      if (this.dimensionFlushTimer) {
        clearTimeout(this.dimensionFlushTimer)
        this.dimensionFlushTimer = null
      }
      if (this.previewRepairTimer) {
        clearTimeout(this.previewRepairTimer)
        this.previewRepairTimer = null
      }
      if (preserveSelection) {
        this.closeSelectAllMenu()
      } else {
        this.closeSelectionDetails()
        this.closeSelectAllMenu()
        this.clearSelection()
      }
      this.clearPointerGesture()
      this.tagFetchSerial += 1
      this.tagsLoading = false
      this.virtualStartIndex = 0
      this.virtualEndIndex = 0
      this.virtualAnchorIndex = 0
      this.virtualContainerTop = 0
      if (!preserveView) {
        this.photoPageIndex = 0
        this.selectionGridPageIndex = 0
        this.listPageIndex = 0
      }
      this.scrollTop = typeof window !== 'undefined' ? (window.scrollY || window.pageYOffset || 0) : 0
      this.viewportHeight = typeof window !== 'undefined' ? window.innerHeight : this.viewportHeight
      this.teardownObserver()
      this.teardownResizeObserver()
      this.stopPoll()

      if (!this.selectionMode) {
        this.viewMode = 'grid'
      }

      try {
        const payload = await this.pageContract.loadItems(this)
        this.albumInfo = payload?.album || null
        this.applyFetchedItems(payload?.items || [])
      } catch (err) {
        this.items = []
        this.albumInfo = null
        if (this.isTrashMode) {
          this.showMessage('error', err?.message || '加载回收站失败')
        }
      } finally {
        this.loading = false
      }

      if (preserveSelection) {
        this.restoreSelectionSnapshot(selectionSnapshot)
      }
      if (!preserveView) {
        window.scrollTo({ top: 0, behavior: 'instant' })
      }
      this.refreshObservedGrid()
      this.pageContract.afterLoad(this)
    },

    async fetchDateGroup() {
      const res = await fetch(`${API_BASE}/api/dates/${this.dateGroup}/items`)
      if (!res.ok) {
        this.items = []
        return
      }
      const data = await res.json()
      this.applyFetchedItems(data.items)
    },

    async fetchAlbum() {
      const res = await fetch(`${API_BASE}/api/albums/by-path/${encodeURI(this.fullAlbumPath)}`)
      if (!res.ok) {
        this.items = []
        return
      }
      const data = await res.json()
      this.albumInfo = data.album || null
      this.applyFetchedItems(data.items)
    },

    applyFetchedItems(rawItems) {
      const normalizedItems = this.pageContract.normalizeItems(rawItems || [], this)
      const nextItems = this.sortItems(normalizedItems || [])
      const nextCacheUrls = {}
      const nextDimensions = {}

      for (const item of nextItems) {
        if (item.id && item.cache_thumb_url) {
          nextCacheUrls[item.id] = item.cache_thumb_url
        }

        const key = item.layout_key || item.id || item.public_id
        const width = Number(item?.width)
        const height = Number(item?.height)
        if (key && Number.isFinite(width) && Number.isFinite(height) && width > 0 && height > 0) {
          nextDimensions[key] = { w: width, h: height }
        }
      }

      this.items = nextItems
      this.virtualStartIndex = 0
      this.virtualEndIndex = nextItems.length
      this.cacheUrls = nextCacheUrls
      this.imgDimensions = nextDimensions
      this.layoutFingerprint = this.computeLayoutFingerprint(nextItems, nextDimensions)
    },

    getAncestorTitle(segIndex, fallback) {
      const ancestors = this.albumInfo?.ancestors || []
      if (segIndex < ancestors.length) return ancestors[segIndex].title
      return fallback
    },

    previewStateKey(item) {
      if (!item) return ''
      if (item.stable_key) return String(item.stable_key)
      if (Number.isInteger(item?.id)) return `${item?.type || 'item'}:${item.id}`
      if (item?.public_id) return `${item?.type || 'item'}:${item.public_id}`
      if (item?.album_path) return `${item?.type || 'item'}:${item.album_path}`
      if (item?.media_rel_path) return `${item?.type || 'item'}:${item.media_rel_path}`
      return ''
    },

    primaryPreviewPath(item) {
      if (!item) return ''
      if (item.id) {
        const cached = this.cacheUrls[item.id]
        if (cached) return cached
      }
      if (item.cache_thumb_url) return item.cache_thumb_url
      if (item.thumb_url) return item.thumb_url
      return ''
    },

    originalPreviewPath(item) {
      if (item?.preview_original_url) return item.preview_original_url
      if (!item || item.type !== 'image' || !item.media_rel_path) return ''
      return `/media/${String(item.media_rel_path).replace(/\\/g, '/')}`
    },

    selectionSnapshotToken(item) {
      if (!item) return null

      if (item.type === 'album') {
        const key = item.public_id || item.album_path || item.id
        if (!key) return null
        return {
          type: 'album',
          key: String(key),
        }
      }

      if (item.type === 'image') {
        const imageId = Number(item?.id)
        return {
          type: 'image',
          id: Number.isInteger(imageId) && imageId > 0 ? imageId : null,
          mediaRelPath: item?.media_rel_path ? String(item.media_rel_path) : '',
          name: item?.name ? String(item.name) : '',
        }
      }

      return null
    },

    matchesSelectionSnapshotItem(item, target) {
      if (!item || !target || item.type !== target.type) return false

      if (target.type === 'album') {
        const key = item.public_id || item.album_path || item.id
        return Boolean(target.key) && String(key || '') === String(target.key)
      }

      const imageId = Number(item?.id)
      if (Number.isInteger(target.id) && target.id > 0 && Number.isInteger(imageId) && imageId > 0) {
        return imageId === target.id
      }
      if (target.mediaRelPath) {
        return String(item?.media_rel_path || '') === target.mediaRelPath
      }
      if (target.name) {
        return String(item?.name || '') === target.name
      }
      return false
    },

    findSelectionSnapshotIndex(target) {
      if (!target) return -1
      return this.items.findIndex(item => this.matchesSelectionSnapshotItem(item, target))
    },

    captureSelectionSnapshot() {
      const selectedItems = this.selectedEntries
        .map(({ item }) => this.selectionSnapshotToken(item))
        .filter(Boolean)
      const anchorItem = Number.isInteger(this.selectionAnchorIndex)
        ? this.selectionSnapshotToken(this.items[this.selectionAnchorIndex])
        : null

      return {
        selectedItems,
        anchorItem,
        selectionTypeLock: this.selectionTypeLock,
        detailsOpen: this.selectionDetailsOpen,
      }
    },

    restoreSelectionSnapshot(snapshot) {
      if (!snapshot) return

      const nextSelectedMap = {}
      let firstMatchedIndex = null
      for (const target of (snapshot.selectedItems || [])) {
        const matchedIndex = this.findSelectionSnapshotIndex(target)
        if (matchedIndex < 0) continue
        nextSelectedMap[this.itemKey(this.items[matchedIndex], matchedIndex)] = true
        if (firstMatchedIndex === null) {
          firstMatchedIndex = matchedIndex
        }
      }

      const matchedKeys = Object.keys(nextSelectedMap)
      this.selectedMap = nextSelectedMap
      if (!matchedKeys.length) {
        this.selectionTypeLock = null
        this.selectionAnchorIndex = null
        this.closeSelectionDetails()
        return
      }

      const anchorIndex = this.findSelectionSnapshotIndex(snapshot.anchorItem)
      this.selectionTypeLock = snapshot.selectionTypeLock || this.items[firstMatchedIndex]?.type || null
      this.selectionAnchorIndex = anchorIndex >= 0 ? anchorIndex : firstMatchedIndex

      if (snapshot.detailsOpen) {
        if (this.selectionDetailsOpen) {
          this.$nextTick(() => {
            this.updateSelectionDetailsBounds()
          })
          this.fetchSelectionDetailMetadata()
        } else {
          this.openSelectionDetails()
        }
      } else if (this.selectionDetailsOpen) {
        this.closeSelectionDetails()
      }
    },

    isPrimaryPreviewSuppressed(item) {
      const key = this.previewStateKey(item)
      const token = this.primaryPreviewPath(item)
      if (!key || !token) return false
      return this.previewFailureTokens[key] === token
    },

    clearPreviewFailureState(item, includeDetail = true) {
      const key = this.previewStateKey(item)
      if (!key) return

      if (Object.prototype.hasOwnProperty.call(this.previewFailureTokens, key)) {
        const nextFailures = { ...this.previewFailureTokens }
        delete nextFailures[key]
        this.previewFailureTokens = nextFailures
      }

      if (!includeDetail) return
      if (Object.prototype.hasOwnProperty.call(this.detailOriginalFailureTokens, key)) {
        const nextDetailFailures = { ...this.detailOriginalFailureTokens }
        delete nextDetailFailures[key]
        this.detailOriginalFailureTokens = nextDetailFailures
      }
    },

    markPrimaryPreviewFailure(item) {
      const key = this.previewStateKey(item)
      const token = this.primaryPreviewPath(item)
      if (!key || !token) return false
      if (this.previewFailureTokens[key] === token) return false
      this.previewFailureTokens = {
        ...this.previewFailureTokens,
        [key]: token,
      }
      return true
    },

    markDetailOriginalFailure(item) {
      const key = this.previewStateKey(item)
      const token = this.originalPreviewPath(item)
      if (!key || !token) return false
      if (this.detailOriginalFailureTokens[key] === token) return false
      this.detailOriginalFailureTokens = {
        ...this.detailOriginalFailureTokens,
        [key]: token,
      }
      return true
    },

    resolvedUrl(item) {
      const previewPath = this.primaryPreviewPath(item)
      if (!previewPath || this.isPrimaryPreviewSuppressed(item)) return ''
      return `${API_BASE}${previewPath}`
    },

    openImageTarget(item) {
      if (!item?.id) return
      const pathSuffix = item.media_rel_path ? `?path=${encodeURIComponent(item.media_rel_path)}` : ''
      fetch(`${API_BASE}/api/images/${item.id}/open${pathSuffix}`).catch(() => {})
    },

    openItem(item) {
      if (this.coverPickerMode) {
        if (this.canPickContainerCoverItem(item)) {
          void this.pickContainerCover(item)
        }
        return
      }
      if (this.selectionMode) return
      this.pageContract.openItem(this, item)
    },

    canPickContainerCoverItem(item) {
      return this.coverPickerMode && item?.type === 'image' && Number.isInteger(item?.id)
    },

    applyContainerCoverLocally(coverPhotoId) {
      const normalizedCoverId = Number(coverPhotoId)
      const nextCoverId = Number.isInteger(normalizedCoverId) && normalizedCoverId > 0
        ? normalizedCoverId
        : null
      const nextItems = this.items.map(item => {
        if (item?.type !== 'image') return item
        return {
          ...item,
          is_cover: Boolean(nextCoverId && item.id === nextCoverId),
        }
      })

      if (this.albumInfo) {
        this.albumInfo = {
          ...this.albumInfo,
          cover_photo_id: nextCoverId,
        }
      }

      this.items = nextItems
      this.layoutFingerprint = this.computeLayoutFingerprint(nextItems, this.imgDimensions)
      this.lastCacheRequestSignature = ''
    },

    toggleCoverPicker() {
      if (!this.canPickContainerCover) return

      const nextValue = !this.coverPickerMode
      if (nextValue) {
        this.closeSelectionDetails()
        this.closeCollectionMenu()
        this.closeTagMenu()
        this.closeSelectAllMenu()
        this.showMessage('success', '点击图片将其设为封面。')
      }

      this.coverPickerMode = nextValue
    },

    async pickContainerCover(item) {
      if (!this.canPickContainerCoverItem(item) || this.actionBusy || typeof this.pageContract.updateCover !== 'function') {
        return
      }

      this.actionBusy = true
      this.actionBusyTitle = '设置封面中'
      this.actionBusyText = '正在更新当前页面封面，请稍候…'

      try {
        const payload = await this.pageContract.updateCover(this, item)
        this.applyContainerCoverLocally(payload?.cover_photo_id ?? item.id)
        this.coverPickerMode = false
        this.showMessage('success', '封面已更新。')
      } catch (err) {
        this.showMessage('error', err?.message || '设置封面失败')
      } finally {
        this.actionBusy = false
        this.actionBusyTitle = ''
        this.actionBusyText = ''
      }
    },

    openPrimaryFromDetails() {
      const target = this.selectedEntries[0]?.item
      if (!target) return
      this.pageContract.openPrimary(this, target)
    },

    onSelectionDetailSecondaryAction() {
      this.pageContract.runSecondaryAction(this)
    },

    openSelectionDetailsFromIsland() {
      if (!this.selectedCount) return
      this.openSelectionDetails()
    },

    openSelectionDetails() {
      if (!this.selectedCount) return
      this.updateSelectionDetailsBounds()
      this.selectionDetailsOpen = true
      this.lockPageScroll()
      this.$nextTick(() => {
        this.updateSelectionDetailsBounds()
      })
      this.ensureTagLabelsLoaded(true)
      this.ensureCategoryLabelsLoaded(true)
      this.fetchSelectionDetailMetadata()
    },

    closeSelectionDetails() {
      this.selectionDetailsOpen = false
      this.unlockPageScroll()
    },

    updateSelectionDetailsBounds() {
      if (typeof window === 'undefined') return
      const host = (this.$el && typeof this.$el.closest === 'function')
        ? (this.$el.closest('main') || this.$el)
        : this.$el
      if (!host || typeof host.getBoundingClientRect !== 'function') return

      const rect = host.getBoundingClientRect()
      const visibleTop = Math.max(0, Math.round(rect.top))
      const visibleBottom = Math.max(0, Math.round(window.innerHeight - rect.bottom))
      const visibleLeft = Math.max(0, Math.round(rect.left))
      const visibleRight = Math.max(0, Math.round(window.innerWidth - rect.right))

      const visibleWidth = Math.max(0, window.innerWidth - visibleLeft - visibleRight)
      const visibleHeight = Math.max(0, window.innerHeight - visibleTop - visibleBottom)

      this.selectionDetailsHostWidth = visibleWidth
      this.selectionDetailsHostHeight = visibleHeight
      this.selectionDetailsBounds = {
        top: `${visibleTop}px`,
        right: `${visibleRight}px`,
        bottom: `${visibleBottom}px`,
        left: `${visibleLeft}px`,
      }
    },

    lockPageScroll() {
      if (typeof window === 'undefined' || this.scrollLockState) return

      const root = document.documentElement
      const body = document.body
      const scrollY = window.scrollY || window.pageYOffset || 0
      const scrollbarWidth = Math.max(0, window.innerWidth - root.clientWidth)

      this.scrollLockState = {
        scrollY,
        bodyOverflow: body.style.overflow,
        bodyPosition: body.style.position,
        bodyTop: body.style.top,
        bodyLeft: body.style.left,
        bodyRight: body.style.right,
        bodyWidth: body.style.width,
        bodyPaddingRight: body.style.paddingRight,
        rootOverflow: root.style.overflow,
        rootOverscrollBehavior: root.style.overscrollBehavior,
      }

      root.style.overflow = 'hidden'
      root.style.overscrollBehavior = 'none'
      body.style.overflow = 'hidden'
      body.style.position = 'fixed'
      body.style.top = `-${scrollY}px`
      body.style.left = '0'
      body.style.right = '0'
      body.style.width = '100%'
      if (scrollbarWidth > 0) {
        body.style.paddingRight = `${scrollbarWidth}px`
      }
    },

    unlockPageScroll() {
      if (typeof window === 'undefined' || !this.scrollLockState) return

      const root = document.documentElement
      const body = document.body
      const state = this.scrollLockState

      root.style.overflow = state.rootOverflow
      root.style.overscrollBehavior = state.rootOverscrollBehavior
      body.style.overflow = state.bodyOverflow
      body.style.position = state.bodyPosition
      body.style.top = state.bodyTop
      body.style.left = state.bodyLeft
      body.style.right = state.bodyRight
      body.style.width = state.bodyWidth
      body.style.paddingRight = state.bodyPaddingRight

      this.scrollLockState = null
      window.scrollTo({ top: state.scrollY, behavior: 'instant' })
    },

    detailNameText(item) {
      return item?.name || item?.full_filename || '未命名'
    },

    detailCategoryText(item) {
      if (item?.type !== 'image') return ''
      const categoryId = Number(item?.category_id)
      if (!Number.isInteger(categoryId) || categoryId <= 0) return ''
      return this.categoryDisplayMap[categoryId] || ''
    },

    detailPreviewUrl(item) {
      const previewPath = this.primaryPreviewPath(item)
      if (!previewPath) return ''
      if (!this.isPrimaryPreviewSuppressed(item)) {
        return `${API_BASE}${previewPath}`
      }

      const key = this.previewStateKey(item)
      const originalPath = this.originalPreviewPath(item)
      if (key && originalPath && this.detailOriginalFailureTokens[key] !== originalPath) {
        return `${API_BASE}${originalPath}`
      }
      return ''
    },

    onMediaCardPreviewError(item) {
      this.onPrimaryPreviewError(item)
    },

    onPrimaryPreviewError(item) {
      if (!item) return
      const didChange = this.markPrimaryPreviewFailure(item)
      if (!didChange && !Number.isInteger(item?.id)) return
      this.enqueuePreviewRepair(item)
    },

    onSelectionDetailPreviewError(preview) {
      const matchedEntry = this.selectedEntries.find(entry => this.itemKey(entry.item, entry.index) === preview?.key)
      const item = matchedEntry?.item
      if (!item) return

      const originalPath = this.originalPreviewPath(item)
      if (originalPath && preview?.previewUrl === `${API_BASE}${originalPath}`) {
        this.markDetailOriginalFailure(item)
        return
      }

      const didChange = this.markPrimaryPreviewFailure(item)
      if (!didChange && !Number.isInteger(item?.id)) return
      this.enqueuePreviewRepair(item)
    },

    enqueuePreviewRepair(item) {
      if (!Number.isInteger(item?.id)) return
      if (this.previewRepairQueue.includes(item.id)) return
      this.previewRepairQueue = [...this.previewRepairQueue, item.id]
      if (this.previewRepairTimer) {
        clearTimeout(this.previewRepairTimer)
      }
      this.previewRepairTimer = setTimeout(() => {
        this.previewRepairTimer = null
        this.flushPreviewRepairQueue()
      }, 90)
    },

    async flushPreviewRepairQueue() {
      const repairIds = [...new Set(this.previewRepairQueue.filter(id => Number.isInteger(id) && id > 0))]
      this.previewRepairQueue = []
      if (!repairIds.length) return

      if (this.previewRepairInFlight) {
        this.previewRepairQueue = [...new Set([...this.previewRepairQueue, ...repairIds])]
        return
      }

      this.previewRepairInFlight = true
      try {
        const repairPayloadKey = this.pageContract.previewRepairPayloadKey || 'image_ids'
        const res = await fetch(`${API_BASE}/api/admin/refresh?mode=quick`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            repair_cache: true,
            [repairPayloadKey]: repairIds,
          }),
        })
        if (!res.ok) return
        await res.json().catch(() => null)
        await this.pageContract.afterPreviewRepair(this, repairIds)
      } catch {
        // ignore targeted preview repair failures
      } finally {
        this.previewRepairInFlight = false
        if (this.previewRepairQueue.length) {
          this.flushPreviewRepairQueue()
        }
      }
    },

    async refreshPreviewMetadata(imageIds) {
      if (!Array.isArray(imageIds) || !imageIds.length) return
      try {
        const res = await fetch(`${API_BASE}/api/images/meta?ids=${imageIds.join(',')}`)
        if (!res.ok) return

        const data = await res.json()
        const metaMap = new Map((data.items || []).map(meta => [meta.id, meta]))
        if (!metaMap.size) return

        const nextCacheUrls = { ...this.cacheUrls }
        const nextDimensions = { ...this.imgDimensions }
        const nextItems = this.items.map((item) => {
          if (!Number.isInteger(item?.id)) return item
          const meta = metaMap.get(item.id)
          if (!meta) return item

          if (meta.cache_thumb_url) {
            nextCacheUrls[item.id] = meta.cache_thumb_url
          } else {
            delete nextCacheUrls[item.id]
          }

          const width = Number(meta.width)
          const height = Number(meta.height)
          if (Number.isFinite(width) && width > 0 && Number.isFinite(height) && height > 0) {
            nextDimensions[item.id] = { w: width, h: height }
          }

          return {
            ...item,
            cache_thumb_url: meta.cache_thumb_url || '',
            thumb_url: meta.thumb_url || item.thumb_url,
            width: Number.isFinite(width) && width > 0 ? width : item.width,
            height: Number.isFinite(height) && height > 0 ? height : item.height,
          }
        })

        this.items = nextItems
        this.cacheUrls = nextCacheUrls
        this.imgDimensions = nextDimensions
        this.layoutFingerprint = this.computeLayoutFingerprint(nextItems, nextDimensions)
        imageIds.forEach((imageId) => {
          const matched = nextItems.find(item => item?.id === imageId)
          if (matched) {
            this.clearPreviewFailureState(matched)
          }
        })
      } catch {
        // ignore preview metadata refresh failures
      }
    },

    detailAspectRatio(item) {
      const width = Number(item?.width)
      const height = Number(item?.height)
      if (!Number.isFinite(width) || width <= 0 || !Number.isFinite(height) || height <= 0) {
        return '4 / 3'
      }
      return `${width} / ${height}`
    },

    itemHasDetailMetadata(item) {
      if (!item || item.type !== 'image') return true
      return ['file_size', 'imported_at', 'file_created_at'].every(field => (
        Object.prototype.hasOwnProperty.call(item, field)
      ))
    },

    async fetchSelectionDetailMetadata() {
      if (this.isTrashMode) return
      const imageIds = this.selectedEntries
        .map(({ item }) => item)
        .filter(item => item?.type === 'image' && Number.isInteger(item?.id) && !this.itemHasDetailMetadata(item))
        .map(item => item.id)

      if (!imageIds.length) return

      const requestSerial = ++this.selectionDetailFetchSerial

      try {
        const res = await fetch(`${API_BASE}/api/images/meta?ids=${imageIds.join(',')}`)
        if (!res.ok) return

        const data = await res.json()
        if (requestSerial !== this.selectionDetailFetchSerial) return

        const metaMap = new Map(
          (data.items || []).map(meta => [meta.id, meta])
        )
        if (!metaMap.size) return

        this.items = this.items.map(item => {
          if (item?.type !== 'image' || !Number.isInteger(item?.id)) return item
          const meta = metaMap.get(item.id)
          if (!meta) return item
          return {
            ...item,
            ...meta,
            tags: Array.isArray(meta.tags) ? meta.tags : (item.tags || []),
            name: meta.name || item.name,
          }
        })
        this.ensureCategoryLabelsLoaded()
      } catch {
        // ignore metadata hydration failures and keep current values visible
      }
    },

    async ensureCategoryLabelsLoaded(force = false) {
      if (!force && Object.keys(this.categoryDisplayMap).length) return
      try {
        const res = await fetch(`${API_BASE}/api/categories`)
        if (!res.ok) return
        const data = await res.json()
        const nextMap = {}
        for (const category of (data.items || [])) {
          if (!Number.isInteger(category?.id)) continue
          nextMap[category.id] = category.display_name || category.name || `#${category.id}`
        }
        this.categoryDisplayMap = nextMap
      } catch {
        // ignore category label load failures in overlay
      }
    },

    selectedImageMetadataTargets() {
      const seen = new Set()
      return this.selectedEntries
        .map(({ item }) => item)
        .filter(item => item?.type === 'image' && Number.isInteger(item?.id))
        .map(item => ({
          image_id: item.id,
          media_rel_path: item.media_rel_path || null,
        }))
        .filter((target) => {
          const key = `${target.image_id}:${target.media_rel_path || ''}`
          if (seen.has(key)) return false
          seen.add(key)
          return true
        })
    },

    openMetadataEditErrorDialog(message, title = '修改失败') {
      this.openConfirmDialog({
        title,
        message: message || '修改失败，请稍后重试。',
        confirmLabel: '知道了',
        tone: 'danger',
        showCancel: false,
      })
    },

    buildSortTimestamp(value) {
      if (!value) return null
      const parsed = value instanceof Date ? value : new Date(value)
      if (Number.isNaN(parsed.getTime())) return null
      return Math.floor(parsed.getTime() / 1000)
    },

    deriveImageSortTimestamp(item, nextFileCreatedAt = undefined) {
      const createdCandidate = nextFileCreatedAt !== undefined ? nextFileCreatedAt : item?.file_created_at
      return this.buildSortTimestamp(createdCandidate)
        ?? this.buildSortTimestamp(item?.imported_at)
        ?? this.buildSortTimestamp(item?.created_at)
        ?? (Number.isFinite(Number(item?.sort_ts)) ? Number(item.sort_ts) : null)
    },

    matchesCurrentBrowseContextMediaPath(mediaRelPath) {
      const normalizedPath = String(mediaRelPath || '').replace(/\\/g, '/')
      if (!normalizedPath) return false

      if (this.isAlbumMode) {
        return normalizedPath.startsWith(`media/${this.fullAlbumPath}/`)
      }

      const prefix = `media/${this.dateGroup}/`
      if (!normalizedPath.startsWith(prefix)) return false
      const remaining = normalizedPath.slice(prefix.length)
      return remaining.length > 0 && !remaining.includes('/')
    },

    applySelectionImageMetadataResponse(responseItems, payload = {}) {
      const updates = Array.isArray(responseItems) ? responseItems : []
      if (!updates.length) return

      const selectionSnapshot = this.captureSelectionSnapshot()
      const updatesBySourcePath = new Map()
      const updatesByImageId = new Map()
      let shouldRefreshCategoryLabels = false

      for (const update of updates) {
        const sourcePath = String(update?.source_media_rel_path || '').trim()
        if (sourcePath) {
          updatesBySourcePath.set(sourcePath, update)
        }

        const imageId = Number(update?.image_id)
        if (Number.isInteger(imageId) && imageId > 0) {
          updatesByImageId.set(imageId, update)
        }

        const categoryId = Number(update?.category_id)
        if (
          Number.isInteger(categoryId)
          && categoryId > 0
          && !Object.prototype.hasOwnProperty.call(this.categoryDisplayMap, categoryId)
        ) {
          shouldRefreshCategoryLabels = true
        }
      }

      const shouldReorder = typeof payload?.name === 'string'
        || Object.prototype.hasOwnProperty.call(payload, 'file_created_at')
        || updates.some(update => Boolean(update?.moved))

      let changed = false
      let nextItems = []
      for (const item of this.items) {
        if (item?.type !== 'image' || !Number.isInteger(item?.id)) {
          nextItems.push(item)
          continue
        }

        const currentPath = String(item.media_rel_path || '').trim()
        const update = (currentPath && updatesBySourcePath.get(currentPath)) || updatesByImageId.get(item.id)
        if (!update) {
          nextItems.push(item)
          continue
        }

        changed = true
        const hasCreatedAt = Object.prototype.hasOwnProperty.call(update, 'file_created_at')
        const nextFileCreatedAt = hasCreatedAt ? (update.file_created_at || null) : item.file_created_at
        const nextCategoryId = Number(update?.category_id)
        const nextItem = {
          ...item,
          name: update?.name || item.name,
          media_rel_path: update?.media_rel_path || item.media_rel_path,
          category_id: Number.isInteger(nextCategoryId) && nextCategoryId > 0 ? nextCategoryId : item.category_id,
          file_created_at: nextFileCreatedAt,
        }

        const nextSortTs = this.deriveImageSortTimestamp(nextItem, nextFileCreatedAt)
        if (nextSortTs != null) {
          nextItem.sort_ts = nextSortTs
        }

        if (!this.matchesCurrentBrowseContextMediaPath(nextItem.media_rel_path)) {
          continue
        }

        nextItems.push(nextItem)
      }

      if (!changed) return

      if (shouldReorder) {
        nextItems = this.sortItems(nextItems)
      }

      this.items = nextItems
      this.layoutFingerprint = this.computeLayoutFingerprint(nextItems, this.imgDimensions)
      this.lastCacheRequestSignature = ''
      this.restoreSelectionSnapshot(selectionSnapshot)
      this.refreshObservedGrid()

      if (shouldRefreshCategoryLabels) {
        this.ensureCategoryLabelsLoaded(true)
      }
    },

    async applySelectionImageMetadata(payload) {
      if (this.metadataEditBusy) return

      const targets = this.selectedImageMetadataTargets()
      if (!targets.length) return

      this.metadataEditBusy = true
      try {
        const res = await fetch(`${API_BASE}/api/images/metadata`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            items: targets,
            ...payload,
          }),
        })

        const data = await res.json().catch(() => null)
        if (!res.ok) {
          this.openMetadataEditErrorDialog(
            data?.detail || `请求未成功完成，服务器返回 HTTP ${res.status}。`
          )
          return
        }

        this.applySelectionImageMetadataResponse(data?.items, payload)
      } catch (err) {
        this.openMetadataEditErrorDialog(err?.message || '修改失败，请稍后重试。')
      } finally {
        this.metadataEditBusy = false
      }
    },

    async submitSelectionNameEdit(name) {
      const normalizedName = String(name || '').trim()
      if (!normalizedName) return
      await this.applySelectionImageMetadata({ name: normalizedName })
    },

    async submitSelectionCategoryEdit(categoryId) {
      const normalizedCategoryId = Number(categoryId)
      if (!Number.isInteger(normalizedCategoryId) || normalizedCategoryId <= 0) return
      await this.applySelectionImageMetadata({ category_id: normalizedCategoryId })
    },

    async submitSelectionCreatedEdit(localDateTime) {
      const normalizedValue = String(localDateTime || '').trim()
      if (!normalizedValue) return
      await this.applySelectionImageMetadata({ file_created_at: normalizedValue })
    },

    buildDetailField(values, options = {}) {
      const emptyText = Object.prototype.hasOwnProperty.call(options, 'emptyText')
        ? options.emptyText
        : '—'
      const normalized = Array.isArray(values)
        ? values.map(value => (value == null ? '' : String(value).trim()))
        : []

      if (!normalized.length) {
        return {
          text: emptyText,
          isVarious: false,
          isEmpty: !emptyText,
        }
      }

      const first = normalized[0]
      const allSame = normalized.every(value => value === first)
      if (!allSame) {
        return {
          text: 'various',
          isVarious: true,
          isEmpty: false,
        }
      }

      const isEmpty = first.length === 0
      return {
        text: isEmpty ? emptyText : first,
        isVarious: false,
        isEmpty,
      }
    },

    formatDateTime(value) {
      if (!value) return ''
      const date = value instanceof Date ? value : new Date(value)
      if (Number.isNaN(date.getTime())) return ''

      const pad = segment => String(segment).padStart(2, '0')
      return [
        `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`,
        `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`,
      ].join(' ')
    },

    formatFileSizeMb(bytesValue) {
      const bytes = Number(bytesValue)
      if (!Number.isFinite(bytes) || bytes < 0) return ''
      const megaBytes = bytes / (1024 * 1024)
      if (!Number.isFinite(megaBytes)) return ''
      const formatted = megaBytes >= 100
        ? megaBytes.toFixed(1)
        : megaBytes.toFixed(2)
      return formatted.replace(/\.00$/, '').replace(/(\.\d)0$/, '$1')
    },

    detailSizeText(item) {
      if (!item) return ''

      if (item.type === 'album') {
        const photoCount = Number(item?.photo_count)
        if (Number.isFinite(photoCount) && photoCount >= 0) {
          return `${photoCount} 张`
        }

        const fallbackCount = Number(item?.count)
        if (Number.isFinite(fallbackCount) && fallbackCount >= 0) {
          return `${fallbackCount} 张`
        }
        return ''
      }

      if (item.type !== 'image') return ''

      const width = Number(item?.width)
      const height = Number(item?.height)
      const parts = []
      if (Number.isFinite(width) && width > 0 && Number.isFinite(height) && height > 0) {
        parts.push(`${width} × ${height} px`)
      }

      const fileSizeMb = this.formatFileSizeMb(item?.file_size)
      if (fileSizeMb) {
        parts.push(`${fileSizeMb} MB`)
      }

      return parts.join(' · ')
    },

    detailImportedText(item) {
      if (!item || item.type !== 'image') return ''
      return this.formatDateTime(item.imported_at)
    },

    detailCreatedText(item) {
      if (!item) return ''
      if (item.type === 'album') {
        return this.formatDateTime(item.created_at)
      }
      if (item.type !== 'image') return ''
      return this.formatDateTime(item.file_created_at)
    },

    onPageBack() {
      this.pageContract.back(this)
    },

    runConfiguredHandler(handlerName) {
      if (!handlerName || typeof this[handlerName] !== 'function') return
      this[handlerName]()
    },

    onImgLoad(item, evt) {
      this.clearPreviewFailureState(item)
      const { naturalWidth: width, naturalHeight: height } = evt.target
      if (!width || !height) return
      const key = item.id || item.public_id
      const existing = this.imgDimensions[key]
      if (existing && existing.w > 0 && existing.h > 0) return
      this.pendingDimensionCorrections = {
        ...this.pendingDimensionCorrections,
        [key]: { w: width, h: height },
      }
      if (this.dimensionFlushTimer) {
        clearTimeout(this.dimensionFlushTimer)
      }
      this.dimensionFlushTimer = window.setTimeout(() => {
        this.flushDimensionCorrections()
      }, DIMENSION_CORRECTION_BATCH_MS)
    },

    flushDimensionCorrections() {
      if (this.dimensionFlushTimer) {
        clearTimeout(this.dimensionFlushTimer)
        this.dimensionFlushTimer = null
      }
      const corrections = this.pendingDimensionCorrections
      const keys = Object.keys(corrections)
      if (!keys.length) return

      const nextDimensions = { ...this.imgDimensions }
      for (const key of keys) {
        const correction = corrections[key]
        if (!correction?.w || !correction?.h) continue
        const existing = nextDimensions[key]
        if (existing && existing.w > 0 && existing.h > 0) continue
        nextDimensions[key] = correction
      }

      this.pendingDimensionCorrections = {}
      this.imgDimensions = nextDimensions
      this.layoutFingerprint = this.computeLayoutFingerprint(this.items, nextDimensions)
      this.logBrowseDebug('layout-dimension-fallback', { count: keys.length })
    },

    onResize() {
      const anchorBeforeReflow = this.$refs.itemGrid ? this.captureViewportAnchor() : null
      this.viewportHeight = typeof window !== 'undefined' ? window.innerHeight : this.viewportHeight
      this.viewportWidth = typeof window !== 'undefined' ? window.innerWidth : this.viewportWidth
      if (this.$refs.itemGrid) {
        if (this.isPagedBrowseMode) {
          if (anchorBeforeReflow) {
            this.pendingViewAnchor = anchorBeforeReflow
          }
          this.refreshObservedGrid()
        } else {
          this.measureItemGridMetrics()
        }
        if (this.isVirtualizedMode) {
          this.syncVirtualWindow(true)
          if (this.isSelectionGridMode) {
            this.measureSelectionRowHeight()
          }
        }
      }
      if (this.selectionDetailsOpen) {
        this.updateSelectionDetailsBounds()
      }
    },

    onWindowScroll() {
      const nextScrollTop = window.scrollY || window.pageYOffset || 0
      if (nextScrollTop > this.lastObservedScrollTop) {
        this.lastScrollDirection = 'forward'
      } else if (nextScrollTop < this.lastObservedScrollTop) {
        this.lastScrollDirection = 'backward'
      }
      this.lastObservedScrollTop = nextScrollTop

      if (!this.isVirtualizedMode && !this.selectionDetailsOpen) return
      if (this.scrollFrameId) return

      this.scrollFrameId = window.requestAnimationFrame(() => {
        this.scrollFrameId = null
        if (this.isVirtualizedMode) {
          this.scrollTop = window.scrollY || window.pageYOffset || 0
          this.syncVirtualWindow()
        }
        if (this.selectionDetailsOpen) {
          this.updateSelectionDetailsBounds()
        }
      })
    },

    isCacheablePreviewItem(item) {
      return Number.isInteger(item?.id) && (item?.type === 'image' || item?.type === 'album')
    },

    hasCachedThumb(item) {
      if (!item?.id) return false
      return Boolean(this.cacheUrls[item.id] || item.cache_thumb_url)
    },

    collectVisibleDomEntries() {
      if (!this.$refs.itemGrid || typeof window === 'undefined') return []
      return Array.from(this.$refs.itemGrid.querySelectorAll('[data-index]'))
        .map((element) => {
          const index = Number(element.getAttribute('data-index'))
          if (!Number.isInteger(index)) return null
          const rect = element.getBoundingClientRect()
          if (rect.bottom <= 0 || rect.top >= window.innerHeight) return null
          return {
            index,
            left: rect.left,
            top: rect.top,
          }
        })
        .filter(Boolean)
        .sort((leftEntry, rightEntry) => {
          if (Math.abs(leftEntry.top - rightEntry.top) <= FIRST_ROW_TOLERANCE_PX) {
            return leftEntry.left - rightEntry.left
          }
          return leftEntry.top - rightEntry.top
        })
    },

    captureViewportAnchor() {
      const visibleEntries = this.collectVisibleDomEntries()
      if (visibleEntries.length) {
        const entry = visibleEntries[0]
        const item = this.items[entry.index]
        if (item) {
          const hostRect = this.$refs.itemGrid?.getBoundingClientRect?.() || { left: 0 }
          return {
            index: entry.index,
            itemKey: this.itemKey(item, entry.index),
            anchorOffset: Math.max(0, Math.round(entry.left - hostRect.left)),
          }
        }
      }

      const fallbackIndex = Number.isInteger(this.virtualAnchorIndex) && this.virtualAnchorIndex >= 0
        ? this.virtualAnchorIndex
        : 0
      const item = this.items[fallbackIndex]
      if (!item) return null
      return {
        index: fallbackIndex,
        itemKey: this.itemKey(item, fallbackIndex),
        anchorOffset: 0,
      }
    },

    resolveRestoreAnchorIndex(anchor) {
      if (!anchor || !this.items.length) return -1
      if (Number.isInteger(anchor.index) && anchor.index >= 0 && anchor.index < this.items.length) {
        return anchor.index
      }
      if (anchor.itemKey) {
        const matchedIndex = this.items.findIndex((item, index) => this.itemKey(item, index) === anchor.itemKey)
        if (matchedIndex >= 0) return matchedIndex
      }
      return Math.min(this.items.length - 1, Math.max(0, anchor.index || 0))
    },

    restorePendingViewAnchor() {
      const anchor = this.pendingViewAnchor
      this.pendingViewAnchor = null
      if (!anchor) {
        if (this.isPagedBrowseMode) {
          this.queueCurrentPageCache(true, 'refresh-paged')
          return
        }

        if (this.isPhotoGridMode) {
          this.queuePhotoGridCachePlan(0, true, 'refresh')
        }
        return
      }

      const targetIndex = this.resolveRestoreAnchorIndex(anchor)
      if (!Number.isInteger(targetIndex) || targetIndex < 0) return

      if (this.isPagedBrowseMode) {
        this.restorePagedPageByIndex(targetIndex)
        return
      }

      if (this.viewMode === 'list') {
        const desiredTop = this.virtualContainerTop + (targetIndex * LIST_ROW_HEIGHT) - RESTORE_ANCHOR_PADDING_PX
        window.scrollTo({ top: Math.max(0, Math.round(desiredTop)), behavior: 'instant' })
        this.logBrowseDebug('anchor-restore', { mode: 'list', targetIndex })
        window.requestAnimationFrame(() => {
          this.syncVirtualWindow(true)
        })
        return
      }

      if (this.isSelectionGridMode) {
        const rowIndex = Math.floor(targetIndex / this.selectionColumnCount)
        const desiredTop = this.virtualContainerTop + (rowIndex * (this.effectiveSelectionRowHeight + this.selectionGridGapPx)) - RESTORE_ANCHOR_PADDING_PX
        window.scrollTo({ top: Math.max(0, Math.round(desiredTop)), behavior: 'instant' })
        this.logBrowseDebug('anchor-restore', { mode: 'selection-grid', targetIndex, rowIndex })
        window.requestAnimationFrame(() => {
          this.syncVirtualWindow(true)
        })
        return
      }

      this.$nextTick(() => {
        // masonry 滚动模式锚点恢复：按 placement.top 直接定位
        if (this.isPortraitMasonryMode) {
          const placement = this.masonryLayout.placements.find(p => p._idx === targetIndex)
          if (placement) {
            const desiredTop = this.virtualContainerTop + placement.top - RESTORE_ANCHOR_PADDING_PX
            window.scrollTo({ top: Math.max(0, Math.round(desiredTop)), behavior: 'instant' })
            this.logBrowseDebug('anchor-restore', { mode: 'masonry', targetIndex, top: placement.top })
            window.requestAnimationFrame(() => {
              this.queuePhotoGridCachePlan(targetIndex, true, 'restore')
            })
            return
          }
        }
        const target = this.$refs.itemGrid?.querySelector?.(`[data-index="${targetIndex}"]`)
        if (!target) return
        const rect = target.getBoundingClientRect()
        const desiredTop = (window.scrollY || window.pageYOffset || 0) + rect.top - RESTORE_ANCHOR_PADDING_PX
        window.scrollTo({ top: Math.max(0, Math.round(desiredTop)), behavior: 'instant' })
        this.logBrowseDebug('anchor-restore', { mode: 'photo-grid', targetIndex })
        window.requestAnimationFrame(() => {
          this.queuePhotoGridCachePlan(targetIndex, true, 'restore')
        })
      })
    },

    resolveNearestImageIndex(anchorIndex, preferredIndices = []) {
      for (const index of preferredIndices) {
        if (!Number.isInteger(index)) continue
        const item = this.items[index]
        if (this.isCacheablePreviewItem(item)) return index
      }

      if (!Number.isInteger(anchorIndex) || anchorIndex < 0) return -1
      for (let offset = 0; offset <= this.scrollWindowRadius; offset++) {
        const forwardIndex = anchorIndex + offset
        if (this.isCacheablePreviewItem(this.items[forwardIndex])) return forwardIndex
        const backwardIndex = anchorIndex - offset
        if (offset && this.isCacheablePreviewItem(this.items[backwardIndex])) return backwardIndex
      }
      return -1
    },

    collectPhotoGridRowIndices(anchorIndex) {
      for (const row of this.justifiedRows) {
        const indices = row.items.map(item => item._idx)
        if (indices.includes(anchorIndex)) {
          return indices
        }
      }
      return [anchorIndex]
    },

    collectMasonryNearbyIndices(anchorIndex) {
      const placement = this.masonryLayout.placements[anchorIndex]
      if (!placement) return [anchorIndex]
      const col = placement.col
      const inSameCol = this.masonryLayout.placements
        .filter(p => p.col === col)
        .map(p => p._idx)
      const pos = inSameCol.indexOf(anchorIndex)
      return inSameCol.slice(Math.max(0, pos - 1), pos + 2)
    },

    collectVirtualFirstRowIndices(anchorIndex) {
      if (this.viewMode === 'list') {
        return [anchorIndex]
      }
      const rowStart = Math.floor(anchorIndex / this.selectionColumnCount) * this.selectionColumnCount
      return Array.from({ length: this.selectionColumnCount }, (_value, offset) => rowStart + offset)
        .filter(index => index >= 0 && index < this.items.length)
    },

    buildPhotoGridCachePlan(anchorIndex, anchorSnapshot = null) {
      if (!Number.isInteger(anchorIndex) || anchorIndex < 0 || anchorIndex >= this.items.length) return null
      const item = this.items[anchorIndex]
      if (!item) return null
      const firstRowIndices = this.isPortraitMasonryMode
        ? this.collectMasonryNearbyIndices(anchorIndex)
        : this.collectPhotoGridRowIndices(anchorIndex)
      const cacheAnchorIndex = this.resolveNearestImageIndex(anchorIndex, firstRowIndices)
      if (cacheAnchorIndex < 0) return null
      return {
        visualAnchorIndex: anchorIndex,
        cacheAnchorIndex,
        firstRowIndices,
        anchorItemKey: this.itemKey(item, anchorIndex),
        anchorOffset: anchorSnapshot?.anchorOffset || 0,
        direction: this.lastScrollDirection,
      }
    },

    buildVirtualCachePlan(anchorIndex) {
      if (!Number.isInteger(anchorIndex) || anchorIndex < 0 || anchorIndex >= this.items.length) return null
      const item = this.items[anchorIndex]
      if (!item) return null
      const firstRowIndices = this.collectVirtualFirstRowIndices(anchorIndex)
      const cacheAnchorIndex = this.resolveNearestImageIndex(anchorIndex, firstRowIndices)
      if (cacheAnchorIndex < 0) return null
      return {
        visualAnchorIndex: anchorIndex,
        cacheAnchorIndex,
        firstRowIndices,
        anchorItemKey: this.itemKey(item, anchorIndex),
        anchorOffset: 0,
        direction: this.lastScrollDirection,
      }
    },

    buildPrioritizedCacheIds(plan) {
      if (!plan) return []
      const orderedIds = []
      const seenIds = new Set()
      const pushIndex = (index) => {
        if (!Number.isInteger(index) || index < 0 || index >= this.items.length) return
        const item = this.items[index]
        if (!this.isCacheablePreviewItem(item) || this.hasCachedThumb(item)) return
        if (seenIds.has(item.id)) return
        seenIds.add(item.id)
        orderedIds.push(item.id)
      }

      pushIndex(plan.cacheAnchorIndex)
      for (const index of plan.firstRowIndices || []) {
        pushIndex(index)
      }
      for (let offset = 1; offset <= this.scrollWindowRadius; offset++) {
        pushIndex(plan.cacheAnchorIndex + offset)
        pushIndex(plan.cacheAnchorIndex - offset)
      }
      return orderedIds
    },

    queueCachePlan(plan, immediate = false, reason = 'unknown') {
      if (!plan) return
      const orderedImageIds = this.buildPrioritizedCacheIds(plan)
      if (!orderedImageIds.length) return

      const requestSignature = [
        this.cachePageToken,
        this.cacheSortSignature,
        plan.visualAnchorIndex,
        plan.cacheAnchorIndex,
        orderedImageIds.join(','),
      ].join('|')

      const dispatch = () => {
        if (requestSignature === this.lastCacheRequestSignature) return
        this.lastCacheRequestSignature = requestSignature
        this.lastCenter = plan.cacheAnchorIndex
        this.triggerCacheForPlan(plan, orderedImageIds, reason)
      }

      clearTimeout(this.debounceTimer)
      if (immediate) {
        dispatch()
        return
      }
      this.debounceTimer = setTimeout(dispatch, DEBOUNCE_MS)
    },

    queuePhotoGridCachePlan(anchorIndex, immediate = false, reason = 'photo-grid') {
      const anchorSnapshot = this.captureViewportAnchor()
      const plan = this.buildPhotoGridCachePlan(anchorIndex, anchorSnapshot)
      this.queueCachePlan(plan, immediate, reason)
    },

    syncVirtualWindow(force = false) {
      if (!this.$refs.itemGrid) return

      this.scrollTop = window.scrollY || window.pageYOffset || 0
      this.viewportHeight = window.innerHeight || this.viewportHeight
      this.containerWidth = this.$refs.itemGrid.offsetWidth
      const rect = this.$refs.itemGrid.getBoundingClientRect()
      this.virtualContainerTop = rect.top + this.scrollTop

      if (!this.isVirtualizedMode) {
        this.virtualStartIndex = 0
        this.virtualEndIndex = this.items.length
        this.virtualAnchorIndex = this.items.length ? 0 : -1
        return
      }

      const viewportTop = Math.max(0, this.scrollTop - this.virtualContainerTop)
      const viewportBottom = viewportTop + this.viewportHeight
      let startIndex = 0
      let endIndex = this.items.length
      let anchorIndex = this.items.length ? 0 : -1

      if (this.viewMode === 'list') {
        const firstVisibleIndex = Math.min(
          this.items.length - 1,
          Math.max(0, Math.floor(viewportTop / LIST_ROW_HEIGHT)),
        )
        anchorIndex = firstVisibleIndex
        startIndex = Math.max(0, firstVisibleIndex - LIST_OVERSCAN_ROWS)
        endIndex = Math.min(
          this.items.length,
          Math.ceil(viewportBottom / LIST_ROW_HEIGHT) + LIST_OVERSCAN_ROWS,
        )
      } else if (this.isSelectionGridMode) {
        const rowSpan = this.effectiveSelectionRowHeight + this.selectionGridGapPx
        const totalRows = Math.ceil(this.items.length / this.selectionColumnCount)
        const firstVisibleRow = Math.min(
          Math.max(0, Math.floor(viewportTop / rowSpan)),
          Math.max(0, totalRows - 1),
        )
        const endVisibleRow = Math.min(
          totalRows,
          Math.ceil(viewportBottom / rowSpan) + SELECTION_OVERSCAN_ROWS,
        )
        anchorIndex = Math.min(this.items.length - 1, firstVisibleRow * this.selectionColumnCount)
        startIndex = Math.max(0, (firstVisibleRow - SELECTION_OVERSCAN_ROWS) * this.selectionColumnCount)
        endIndex = Math.min(this.items.length, endVisibleRow * this.selectionColumnCount)
      }

      const rangeChanged =
        force ||
        startIndex !== this.virtualStartIndex ||
        endIndex !== this.virtualEndIndex ||
        anchorIndex !== this.virtualAnchorIndex

      if (!rangeChanged) return

      this.virtualStartIndex = startIndex
      this.virtualEndIndex = endIndex
      this.virtualAnchorIndex = anchorIndex
      this.queueCachePlan(this.buildVirtualCachePlan(anchorIndex), force, 'virtual-window')

      if (this.isSelectionGridMode) {
        this.$nextTick(() => {
          this.measureSelectionRowHeight()
        })
      }
    },

    measureSelectionRowHeight() {
      if (!this.isSelectionGridMode || !this.$refs.itemGrid) return
      const sample = this.$refs.itemGrid.querySelector('.selection-wrap')
      if (!sample) return

      const nextHeight = Math.round(sample.getBoundingClientRect().height)
      if (nextHeight > 0 && Math.abs(nextHeight - this.selectionRowHeight) > 1) {
        this.selectionRowHeight = nextHeight
        if (this.isPagedBrowseMode) {
          this.normalizePaginationState()
        } else {
          this.syncVirtualWindow(true)
        }
      }
    },

    onWindowKeydown(event) {
      if (this.tagFormVisible && event.key === 'Escape') {
        event.preventDefault()
        this.closeTagForm()
        return
      }
      if (this.collectionMenuVisible && event.key === 'Escape') {
        event.preventDefault()
        this.closeCollectionMenu()
        return
      }
      if (this.tagMenuVisible && event.key === 'Escape') {
        event.preventDefault()
        this.closeTagMenu()
        return
      }
      if (this.selectionDetailsOpen && event.key === 'Escape') {
        event.preventDefault()
        this.closeSelectionDetails()
        return
      }
      if (this.coverPickerMode && event.key === 'Escape') {
        event.preventDefault()
        this.coverPickerMode = false
        return
      }
      if (!this.selectionMode) return
      const key = event.key.toLowerCase()
      if ((event.ctrlKey || event.metaKey) && key === 'a') {
        event.preventDefault()
        this.selectAllOfCurrentType()
      }
      if (event.key === 'Escape') {
        event.preventDefault()
        if (this.selectedCount) {
          this.clearSelection()
        } else {
          this.toggleSelectionMode(false)
        }
      }
    },

    bcLabel(str) {
      if (!str) return ''
      return str.length > 20 ? str.slice(0, 20) + '…' : str
    },

    itemDateTs(item) {
      const ts = Number(item?.sort_ts)
      if (Number.isFinite(ts)) return ts
      const fallbackId = Number(item?.id)
      return Number.isFinite(fallbackId) ? fallbackId : 0
    },

    itemAlphaKey(item) {
      return (item?.name || item?.full_filename || '').toString()
    },

    sortItems(items) {
      const arr = Array.isArray(items) ? [...items] : []
      const dir = this.sortDir === 'desc' ? -1 : 1

      const compare = (a, b) => {
        if (this.sortBy === 'date') {
          const ta = this.itemDateTs(a)
          const tb = this.itemDateTs(b)
          if (ta !== tb) return (ta - tb) * dir
        } else {
          const na = this.itemAlphaKey(a)
          const nb = this.itemAlphaKey(b)
          const nc = na.localeCompare(nb, undefined, { sensitivity: 'base', numeric: true })
          if (nc !== 0) return nc * dir
        }
        const ta = this.itemDateTs(a)
        const tb = this.itemDateTs(b)
        if (ta !== tb) return (ta - tb) * dir
        const na = this.itemAlphaKey(a)
        const nb = this.itemAlphaKey(b)
        return na.localeCompare(nb, undefined, { sensitivity: 'base', numeric: true }) * dir
      }

      const albums = arr.filter(it => it?.type === 'album').sort(compare)
      const images = arr.filter(it => it?.type !== 'album').sort(compare)
      return [...albums, ...images]
    },

    refreshSortResult() {
      this.items = this.sortItems(this.items)
      this.layoutFingerprint = this.computeLayoutFingerprint(this.items, this.imgDimensions)
      this.lastCacheRequestSignature = ''
      if (this.loading) return
      this.clearSelection()
      this.refreshObservedGrid()
      if (this.selectionInfoMode === 'tags') {
        this.ensureTagLabelsLoaded()
      }
    },

    onSortModeSelect(mode) {
      if (this.sortBy === mode) return
      this.sortBy = mode
      this.sortDir = 'asc'
      this.refreshSortResult()
    },

    toggleSortDir() {
      this.sortDir = this.sortDir === 'asc' ? 'desc' : 'asc'
      this.refreshSortResult()
    },

    switchViewMode(mode) {
      if (!['grid', 'list'].includes(mode)) return
      const modeChanged = this.viewMode !== mode
      const wasSelecting = this.selectionMode
      const anchor = (modeChanged || wasSelecting) ? this.captureViewportAnchor() : null
      this.closeSelectAllMenu()

      this.viewMode = mode

      if (wasSelecting) {
        this.selectionMode = false
        this.clearSelection()
        this.clearPointerGesture()
        this.suppressNextListClick = false
      }

      if (anchor) {
        this.pendingViewAnchor = anchor
      }

      if (wasSelecting || !modeChanged) {
        this.refreshObservedGrid()
      }
    },

    toggleSelectionMode(forceValue = null) {
      const nextValue = typeof forceValue === 'boolean' ? forceValue : !this.selectionMode
      if (nextValue === this.selectionMode) return
      const anchor = this.captureViewportAnchor()
      this.closeSelectAllMenu()

      if (nextValue) {
        this.viewModeBeforeSelection = this.viewMode
        this.selectionMode = true
        this.viewMode = 'grid'
      } else {
        this.selectionMode = false
        this.viewMode = this.viewModeBeforeSelection || 'grid'
        this.clearSelection()
        this.clearPointerGesture()
        this.suppressNextListClick = false
      }

      if (anchor) {
        this.pendingViewAnchor = anchor
      }

      if (this.selectionInfoMode === 'tags') {
        this.ensureTagLabelsLoaded()
      }
      this.refreshObservedGrid()
    },

    itemKey(item, index) {
      if (item?.stable_key) {
        return String(item.stable_key)
      }
      if (item?.type === 'album') {
        return `album:${item.public_id || item.album_path || item.id || index}`
      }
      return `image:${item?.media_rel_path || item?.id || item?.name || index}`
    },

    isItemSelected(item, index) {
      return Boolean(this.selectedMap[this.itemKey(item, index)])
    },

    isItemDisabled(item) {
      return Boolean(this.selectionTypeLock && item?.type !== this.selectionTypeLock)
    },

    clearSelection() {
      this.selectedMap = {}
      this.selectionTypeLock = null
      this.selectionAnchorIndex = null
      this.closeSelectionDetails()
      this.closeSelectAllMenu()
    },

    selectOnlyIndex(index) {
      const item = this.items[index]
      if (!item) return
      this.selectionTypeLock = item.type
      this.selectedMap = { [this.itemKey(item, index)]: true }
      this.selectionAnchorIndex = index
    },

    addIndexToSelection(index, useAsAnchor = false) {
      const item = this.items[index]
      if (!item) return
      if (this.selectionTypeLock && this.selectionTypeLock !== item.type) return
      const key = this.itemKey(item, index)
      if (this.selectedMap[key]) {
        if (useAsAnchor) this.selectionAnchorIndex = index
        return
      }
      this.selectionTypeLock = item.type
      this.selectedMap = { ...this.selectedMap, [key]: true }
      if (useAsAnchor || this.selectionAnchorIndex === null) {
        this.selectionAnchorIndex = index
      }
    },

    removeIndexFromSelection(index) {
      const key = this.itemKey(this.items[index], index)
      if (!this.selectedMap[key]) return
      const next = { ...this.selectedMap }
      delete next[key]
      this.selectedMap = next
      if (!Object.keys(next).length) {
        this.selectionTypeLock = null
        this.selectionAnchorIndex = null
      }
    },

    onItemSelectionButtonClick(item, index) {
      if (!item || this.isItemDisabled(item)) return
      if (this.isItemSelected(item, index)) {
        this.removeIndexFromSelection(index)
        return
      }

      if (!this.selectionMode) {
        this.viewModeBeforeSelection = this.viewMode
        this.selectionMode = true
      }

      if (!this.selectedCount) {
        this.selectOnlyIndex(index)
        return
      }

      this.addIndexToSelection(index, true)
    },

    toggleIndexSelection(index) {
      const item = this.items[index]
      if (!item || this.isItemDisabled(item)) return
      const key = this.itemKey(item, index)
      if (this.selectedMap[key]) {
        this.removeIndexFromSelection(index)
      } else {
        this.addIndexToSelection(index, true)
      }
    },

    applyRangeSelection(targetIndex, additive = false) {
      const targetItem = this.items[targetIndex]
      if (!targetItem) return
      const anchorIndex = this.selectionAnchorIndex === null ? targetIndex : this.selectionAnchorIndex
      const anchorItem = this.items[anchorIndex]
      const lockedType = this.selectionTypeLock || targetItem.type || anchorItem?.type
      if (!lockedType) return

      const start = Math.min(anchorIndex, targetIndex)
      const end = Math.max(anchorIndex, targetIndex)
      const next = additive ? { ...this.selectedMap } : {}

      this.selectionTypeLock = lockedType
      for (let i = start; i <= end; i++) {
        const item = this.items[i]
        if (!item || item.type !== lockedType) continue
        next[this.itemKey(item, i)] = true
      }

      this.selectedMap = next
      this.selectionAnchorIndex = targetIndex
      if (!Object.keys(next).length) {
        this.selectionTypeLock = null
      }
    },

    selectAllOfType(type) {
      if (!type) return
      const next = {}
      let anchorIndex = null
      for (let i = 0; i < this.items.length; i++) {
        const item = this.items[i]
        if (!item || item.type !== type) continue
        next[this.itemKey(item, i)] = true
        if (anchorIndex === null) anchorIndex = i
      }
      this.selectedMap = next
      this.selectionTypeLock = type
      this.selectionAnchorIndex = anchorIndex
      this.closeSelectAllMenu()
    },

    selectAllOfCurrentType() {
      const type = this.selectionTypeLock
        || (this.availableSelectionTypes.length === 1
          ? this.availableSelectionTypes[0]
          : (this.availableSelectionTypes.includes('image') ? 'image' : this.availableSelectionTypes[0]))
      this.selectAllOfType(type)
    },

    handleSelectAllButtonClick() {
      if (!this.hasMixedSelectableTypes) {
        this.selectAllOfCurrentType()
        return
      }

      this.selectAllMenuOpen = !this.selectAllMenuOpen
    },

    onSelectAllTypeClick(type) {
      this.selectAllOfType(type)
    },

    closeSelectAllMenu() {
      this.selectAllMenuOpen = false
    },

    onSelectionIslandCollapsedChange(collapsed) {
      if (!collapsed) return
      this.closeSelectAllMenu()
    },

    onWindowPointerDown(event) {
      if (!this.selectAllMenuOpen) return
      const host = this.$refs.selectionIslandMenu
      if (host && typeof host.contains === 'function' && host.contains(event.target)) {
        return
      }
      this.closeSelectAllMenu()
    },

    onSelectionPointerDown(event, item, index) {
      if (!this.selectionMode) return
      if (event.pointerType === 'mouse' && event.button !== 0) return
      if (this.isItemDisabled(item)) return

      if (this.coverPickerMode) {
        event.preventDefault()
        if (this.canPickContainerCoverItem(item)) {
          void this.pickContainerCover(item)
        }
        return
      }

      event.preventDefault()

      if (event.shiftKey) {
        this.applyRangeSelection(index, event.ctrlKey || event.metaKey)
        return
      }

      if (event.ctrlKey || event.metaKey) {
        this.toggleIndexSelection(index)
        return
      }

      this.clearPointerGesture()
      this.pointerSelection = {
        pointerId: event.pointerId,
        startIndex: index,
        type: item.type,
        sweeping: false,
        action: null,
        visitedKeys: {},
      }

      this.longPressTimer = window.setTimeout(() => {
        this.beginSweepSelection(index)
      }, LONG_PRESS_MS)

      window.addEventListener('pointermove', this.onGlobalPointerMove)
      window.addEventListener('pointerup', this.onGlobalPointerUp)
      window.addEventListener('pointercancel', this.onGlobalPointerCancel)
    },

    enterListSelectionMode() {
      this.viewModeBeforeSelection = 'list'
      this.selectionMode = true
      this.viewMode = 'list'
    },

    onListPointerDown(event, item, index) {
      if (event.pointerType === 'mouse' && event.button !== 0) return

      if (this.selectionMode) {
        this.onSelectionPointerDown(event, item, index)
        return
      }

      if (event.shiftKey || event.ctrlKey || event.metaKey) {
        event.preventDefault()
        this.enterListSelectionMode()
        this.suppressNextListClick = true
        if (event.shiftKey) {
          this.applyRangeSelection(index, event.ctrlKey || event.metaKey)
        } else {
          this.toggleIndexSelection(index)
        }
        return
      }

      this.clearPointerGesture()
      this.pointerSelection = {
        pointerId: event.pointerId,
        startIndex: index,
        type: item.type,
        sweeping: false,
        action: null,
        visitedKeys: {},
        origin: 'list-browse',
      }

      this.longPressTimer = window.setTimeout(() => {
        this.activateListLongPressSelection(index)
      }, LONG_PRESS_MS)

      window.addEventListener('pointermove', this.onGlobalPointerMove)
      window.addEventListener('pointerup', this.onGlobalPointerUp)
      window.addEventListener('pointercancel', this.onGlobalPointerCancel)
    },

    activateListLongPressSelection(index) {
      const session = this.pointerSelection
      const item = this.items[index]
      if (!session || !item || session.sweeping) return

      this.enterListSelectionMode()
      this.suppressNextListClick = true
      this.selectOnlyIndex(index)

      session.origin = 'list-selection'
      session.sweeping = true
      session.action = 'add'
      session.type = item.type
      session.visitedKeys = {}
      this.applySweepToIndex(index)
    },

    onListRowClick(_event, item) {
      if (this.suppressNextListClick) {
        this.suppressNextListClick = false
        return
      }
      if (this.selectionMode) {
        if (this.coverPickerMode && this.canPickContainerCoverItem(item)) {
          void this.pickContainerCover(item)
        }
        return
      }
      this.openItem(item)
    },

    beginSweepSelection(startIndex) {
      const session = this.pointerSelection
      const item = this.items[startIndex]
      if (!session || session.sweeping || !item || this.isItemDisabled(item)) return

      session.sweeping = true
      session.action = this.isItemSelected(item, startIndex) ? 'remove' : 'add'
      session.type = item.type
      this.applySweepToIndex(startIndex)
    },

    applySweepToIndex(index) {
      const session = this.pointerSelection
      const item = this.items[index]
      if (!session || !session.sweeping || !item) return
      if (item.type !== session.type) return
      if (this.selectionTypeLock && this.selectionTypeLock !== item.type) return

      const key = this.itemKey(item, index)
      if (session.visitedKeys[key]) return
      session.visitedKeys[key] = true

      if (session.action === 'remove') {
        this.removeIndexFromSelection(index)
      } else {
        this.addIndexToSelection(index)
      }
    },

    onGlobalPointerMove(event) {
      const session = this.pointerSelection
      if (!session || event.pointerId !== session.pointerId || !session.sweeping) return
      const target = document.elementFromPoint(event.clientX, event.clientY)
      const wrap = target && target.closest('[data-select-index]')
      if (!wrap) return
      const index = Number(wrap.getAttribute('data-select-index'))
      if (Number.isInteger(index)) {
        this.applySweepToIndex(index)
      }
    },

    onGlobalPointerUp(event) {
      const session = this.pointerSelection
      if (!session || event.pointerId !== session.pointerId) return
      const startIndex = session.startIndex
      const sweeping = session.sweeping
      const origin = session.origin
      this.clearPointerGesture()
      if (origin === 'list-browse' && !this.selectionMode) {
        return
      }
      if (!sweeping) {
        this.selectOnlyIndex(startIndex)
      }
    },

    onGlobalPointerCancel(event) {
      const session = this.pointerSelection
      if (!session || event.pointerId !== session.pointerId) return
      this.clearPointerGesture()
    },

    clearPointerGesture() {
      if (this.longPressTimer) {
        clearTimeout(this.longPressTimer)
        this.longPressTimer = null
      }
      window.removeEventListener('pointermove', this.onGlobalPointerMove)
      window.removeEventListener('pointerup', this.onGlobalPointerUp)
      window.removeEventListener('pointercancel', this.onGlobalPointerCancel)
      this.pointerSelection = null
    },

    toggleInfoDisplayMode() {
      this.selectionInfoMode = this.selectionInfoMode === 'name' ? 'tags' : 'name'
      if (this.selectionInfoMode === 'tags') {
        this.ensureTagLabelsLoaded()
      }
    },

    displayInfoText(item) {
      if (this.selectionInfoMode !== 'tags') {
        return item?.name || item?.full_filename || '未命名'
      }
      if (item?.type === 'album') {
        return item?.name || '未命名相册'
      }
      return this.tagTextForItem(item)
    },

    displayInfoTags(item) {
      if (this.selectionInfoMode !== 'tags' || item?.type === 'album') {
        return []
      }

      const ids = Array.isArray(item?.tags)
        ? item.tags.filter(id => Number.isInteger(id))
        : []
      if (!ids.length) return []

      const sortedIds = this.sortTagIdsByName(ids)
      const tags = []
      for (const id of sortedIds) {
        const tag = this.tagLookupMap[id]
        if (!tag) continue
        tags.push({
          id,
          name: tag.name || `#${id}`,
          display_name: tag.displayName || tag.name || `#${id}`,
          color: tag.color || '',
          border_color: tag.borderColor || '',
          background_color: tag.backgroundColor || '',
        })
      }
      return tags
    },

    buildTagLookupEntry(rawTag) {
      if (!Number.isInteger(rawTag?.id)) return null
      const metadata = rawTag?.metadata && typeof rawTag.metadata === 'object' ? rawTag.metadata : {}
      const { color, borderColor, backgroundColor } = normalizeTagColors(rawTag)
      return {
        id: rawTag.id,
        publicId: String(rawTag?.public_id || ''),
        name: String(rawTag?.name || ''),
        displayName: String(rawTag?.display_name || rawTag?.name || `#${rawTag.id}`),
        type: String(rawTag?.type || 'normal'),
        description: String(rawTag?.description || ''),
        metadata,
        color: String(color || ''),
        borderColor: String(borderColor || ''),
        backgroundColor: String(backgroundColor || ''),
      }
    },

    sortTagIdsByName(tagIds) {
      return [...tagIds].sort((leftId, rightId) => {
        const leftName = String(this.tagLookupMap[leftId]?.name || '')
        const rightName = String(this.tagLookupMap[rightId]?.name || '')
        if (leftName && rightName && leftName !== rightName) {
          return leftName.localeCompare(rightName)
        }
        if (leftName && !rightName) return -1
        if (!leftName && rightName) return 1
        return leftId - rightId
      })
    },

    buildTagItemsByIds(tagIds) {
      const sortedIds = this.sortTagIdsByName(tagIds)
      return sortedIds.map((id) => {
        const tag = this.tagLookupMap[id]
        if (!tag) {
          return {
            id,
            public_id: '',
            name: `#${id}`,
            display_name: `#${id}`,
            type: 'normal',
            description: '',
            metadata: {},
            color: '',
            border_color: '',
            background_color: '',
          }
        }
        return {
          id,
          public_id: tag.publicId || '',
          name: tag.name || `#${id}`,
          display_name: tag.displayName || tag.name || `#${id}`,
          type: tag.type || 'normal',
          description: tag.description || '',
          metadata: tag.metadata || {},
          color: tag.color || '',
          border_color: tag.borderColor || '',
          background_color: tag.backgroundColor || '',
        }
      })
    },

    tagIdsForImage(imageId) {
      const item = this.items.find(candidate => candidate?.type === 'image' && candidate?.id === imageId)
      const ids = Array.isArray(item?.tags) ? item.tags.filter(id => Number.isInteger(id)) : []
      return this.sortTagIdsByName([...new Set(ids)])
    },

    collectCommonTagIdsFromMap(imageIds, tagMap) {
      if (!imageIds.length) return []
      const tagIdLists = imageIds.map((imageId) => {
        const ids = Array.isArray(tagMap?.[imageId]) ? tagMap[imageId].filter(id => Number.isInteger(id)) : []
        return this.sortTagIdsByName([...new Set(ids)])
      })

      const commonTagIds = tagIdLists.reduce((previous, current) => {
        if (!previous.length) return []
        const currentSet = new Set(current)
        return previous.filter(id => currentSet.has(id))
      }, [...(tagIdLists[0] || [])])

      return this.sortTagIdsByName([...new Set(commonTagIds)])
    },

    normalizeCollectionMenuItems(rawItems) {
      return (rawItems || [])
        .filter(item => Number.isInteger(item?.id))
        .map(item => ({
          id: item.id,
          public_id: item.public_id || '',
          title: item.title || '',
          description: item.description || '',
          collection_path: item.collection_path || '',
          photo_count: Number(item.photo_count || 0) || 0,
          matched_image_ids: Array.isArray(item.matched_image_ids) ? item.matched_image_ids.filter(id => Number.isInteger(id)) : [],
          selected_match_count: Number(item.selected_match_count || 0) || 0,
          contains_all_selected: Boolean(item.contains_all_selected),
        }))
    },

    initializeCollectionMenuActions(selectedCollection) {
      const matchedSet = new Set(selectedCollection?.matched_image_ids || [])
      const isMulti = this.collectionMenuSelectionItems.length > 1
      const nextActions = {}
      for (const item of this.collectionMenuSelectionItems) {
        if (matchedSet.has(item.imageId)) {
          nextActions[item.imageId] = isMulti ? 'keep' : 'remove'
        } else {
          nextActions[item.imageId] = 'add'
        }
      }
      this.collectionMenuActionByImageId = nextActions
    },

    async openCollectionMenu() {
      if (!this.canOpenCollectionMenu || this.collectionMenuBusy) return
      if (this.tagMenuVisible) {
        this.closeTagMenu()
      }
      this.collectionMenuVisible = true
      this.collectionMenuBusy = false
      this.collectionMenuSearchBusy = false
      this.collectionMenuError = ''
      this.collectionMenuQuery = ''
      this.collectionMenuSuggestions = []
      this.collectionMenuSelectedCollection = null
      this.collectionMenuActionByImageId = {}
      await this.fetchCollectionMenuSuggestions('')
    },

    closeCollectionMenu() {
      this.collectionMenuVisible = false
      this.collectionMenuBusy = false
      this.collectionMenuSearchBusy = false
      this.collectionMenuError = ''
      this.collectionMenuQuery = ''
      this.collectionMenuSuggestions = []
      this.collectionMenuSelectedCollection = null
      this.collectionMenuActionByImageId = {}
      if (this.collectionMenuSearchTimer) {
        clearTimeout(this.collectionMenuSearchTimer)
        this.collectionMenuSearchTimer = null
      }
    },

    onCollectionMenuQueryChange(nextQuery) {
      this.collectionMenuError = ''
      this.collectionMenuQuery = String(nextQuery || '')
      this.collectionMenuSelectedCollection = null
      this.collectionMenuActionByImageId = {}
      if (this.collectionMenuSearchTimer) {
        clearTimeout(this.collectionMenuSearchTimer)
      }
      this.collectionMenuSearchTimer = setTimeout(() => {
        this.collectionMenuSearchTimer = null
        this.fetchCollectionMenuSuggestions(this.collectionMenuQuery)
      }, 180)
    },

    async fetchCollectionMenuSuggestions(rawQuery) {
      if (!this.collectionMenuVisible) return
      this.collectionMenuSearchBusy = true
      this.collectionMenuError = ''

      try {
        const res = await fetch(`${API_BASE}/api/collections/search`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            q: String(rawQuery || '').trim(),
            image_ids: this.selectedImageIds,
            limit: 12,
          }),
        })
        if (!res.ok) {
          const payload = await res.json().catch(() => ({}))
          throw new Error(payload.detail || `HTTP ${res.status}`)
        }

        const data = await res.json()
        this.collectionMenuSuggestions = this.normalizeCollectionMenuItems(data.items || [])
      } catch (err) {
        this.collectionMenuSuggestions = []
        this.collectionMenuError = `收藏搜索失败：${err?.message || '未知错误'}`
      } finally {
        this.collectionMenuSearchBusy = false
      }
    },

    handleCollectionMenuSelect(collectionItem) {
      if (!collectionItem) return
      const normalizedItem = collectionItem.isNew
        ? {
            id: null,
            isNew: true,
            title: String(collectionItem.title || '').trim(),
            description: '',
            collection_path: '',
            photo_count: 0,
            matched_image_ids: [],
            selected_match_count: 0,
            contains_all_selected: false,
          }
        : {
            ...collectionItem,
            isNew: false,
            title: String(collectionItem.title || '').trim(),
          }
      if (!normalizedItem.title) return
      this.collectionMenuSelectedCollection = normalizedItem
      this.initializeCollectionMenuActions(normalizedItem)
    },

    setCollectionMenuImageAction(payload) {
      const imageId = Number(payload?.imageId)
      const action = String(payload?.action || '').trim().toLowerCase()
      if (!Number.isInteger(imageId) || !['keep', 'remove', 'add'].includes(action)) return
      this.collectionMenuActionByImageId = {
        ...this.collectionMenuActionByImageId,
        [imageId]: action,
      }
    },

    async confirmCollectionMenuChanges() {
      if (!this.collectionMenuSelectedCollection || this.collectionMenuBusy) return
      this.collectionMenuBusy = true
      this.collectionMenuError = ''

      try {
        const imageActions = this.collectionMenuSelectionItems.map((item) => ({
          image_id: item.imageId,
          action: this.collectionMenuActionByImageId[item.imageId] || 'add',
        }))

        const selectedCollection = this.collectionMenuSelectedCollection
        const res = await fetch(`${API_BASE}/api/collections/apply`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            collection_id: Number.isInteger(selectedCollection.id) ? selectedCollection.id : null,
            title: selectedCollection.isNew ? selectedCollection.title : '',
            image_actions: imageActions,
          }),
        })
        if (!res.ok) {
          const payload = await res.json().catch(() => ({}))
          throw new Error(payload.detail || `HTTP ${res.status}`)
        }

        const payload = await res.json()
        const label = payload.title || selectedCollection.title || '收藏'
        if (this.collectionMenuSelectionItems.length === 1) {
          const action = imageActions[0]?.action
          this.showMessage('success', action === 'remove' ? `已从“${label}”移除。` : `已加入“${label}”。`)
        } else {
          const addedCount = Number(payload.added_count || 0) || 0
          const removedCount = Number(payload.removed_count || 0) || 0
          this.showMessage('success', `收藏已更新：新增 ${addedCount} 张，移除 ${removedCount} 张。`)
        }

        if (this.isCollectionMode && selectedCollection.public_id === this.collectionPublicId) {
          await this.reloadContractItemsPreservingAnchor({
            preserveSelection: false,
            reopenDetails: false,
            runAfterLoad: true,
          })
        }

        this.closeCollectionMenu()
      } catch (err) {
        this.collectionMenuError = `收藏更新失败：${err?.message || '未知错误'}`
      } finally {
        this.collectionMenuBusy = false
      }
    },

    updateTagMenuDirty() {
      const imageIds = this.selectedImageIds
      this.tagMenuDirty = imageIds.some((imageId) => {
        const beforeIds = this.sortTagIdsByName([...(this.tagMenuOriginalByImageId[imageId] || [])])
        const afterIds = this.sortTagIdsByName([...(this.tagMenuDraftByImageId[imageId] || [])])
        if (beforeIds.length !== afterIds.length) return true
        for (let index = 0; index < beforeIds.length; index++) {
          if (beforeIds[index] !== afterIds[index]) return true
        }
        return false
      })
    },

    refreshTagMenuExistingTags() {
      const commonTagIds = this.collectCommonTagIdsFromMap(this.selectedImageIds, this.tagMenuDraftByImageId)
      this.tagMenuExistingTags = this.buildTagItemsByIds(commonTagIds)
      this.updateTagMenuDirty()
    },

    normalizeTagMenuItems(rawItems) {
      const nextTagMap = { ...this.tagLookupMap }
      const normalizedItems = []
      for (const rawTag of (rawItems || [])) {
        const normalizedTag = this.buildTagLookupEntry(rawTag)
        if (!normalizedTag) continue
        nextTagMap[normalizedTag.id] = normalizedTag
        normalizedItems.push({
          id: normalizedTag.id,
          public_id: normalizedTag.publicId,
          name: normalizedTag.name,
          display_name: normalizedTag.displayName,
          type: normalizedTag.type,
          description: normalizedTag.description,
          metadata: normalizedTag.metadata,
          color: normalizedTag.color,
          border_color: normalizedTag.borderColor,
          background_color: normalizedTag.backgroundColor,
          last_used_at: String(rawTag?.last_used_at || ''),
        })
      }
      this.tagLookupMap = nextTagMap
      return normalizedItems
    },

    async openTagMenu() {
      if (!this.canOpenTagMenu || this.tagMenuBusy) return
      this.tagMenuVisible = true
      this.tagMenuError = ''
      this.tagMenuQuery = ''
      this.tagMenuSuggestions = []
      this.tagMenuRecentTags = []
      this.tagMenuDraftByImageId = {}
      this.tagMenuOriginalByImageId = {}
      this.tagMenuDirty = false

      for (const imageId of this.selectedImageIds) {
        const ids = this.tagIdsForImage(imageId)
        this.tagMenuDraftByImageId[imageId] = [...ids]
        this.tagMenuOriginalByImageId[imageId] = [...ids]
      }

      await this.ensureTagLabelsLoaded(true)
      this.refreshTagMenuExistingTags()
      this.fetchTagMenuSuggestions('')
    },

    closeTagMenu() {
      if (this.tagFormVisible) {
        void this.closeTagForm()
      }
      this.tagMenuVisible = false
      this.tagMenuBusy = false
      this.tagMenuSearchBusy = false
      this.tagMenuError = ''
      this.tagMenuQuery = ''
      this.tagMenuSuggestions = []
      this.tagMenuRecentTags = []
      this.tagMenuExistingTags = []
      this.tagMenuDraftByImageId = {}
      this.tagMenuOriginalByImageId = {}
      this.tagMenuDirty = false
      if (this.tagMenuSearchTimer) {
        clearTimeout(this.tagMenuSearchTimer)
        this.tagMenuSearchTimer = null
      }
    },

    async fetchTagFormExistingNames() {
      const fallbackNames = Object.values(this.tagLookupMap)
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

    async fetchTagDetail(tagId) {
      const res = await fetch(`${API_BASE}/api/tags/${tagId}`)
      if (!res.ok) {
        const payload = await res.json().catch(() => ({}))
        throw new Error(payload.detail || `HTTP ${res.status}`)
      }
      return res.json()
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
        // ignore draft cleanup failure and keep UI responsive
      }
    },

    async refreshTagCollectionsAfterSave(savedTag, options = {}) {
      const { attachToSelection = false } = options
      const normalizedTag = this.buildTagLookupEntry(savedTag)
      if (normalizedTag) {
        this.tagLookupMap = {
          ...this.tagLookupMap,
          [normalizedTag.id]: normalizedTag,
        }
      }

      if (this.isTagMode && normalizedTag && this.albumInfo?.id === normalizedTag.id) {
        this.albumInfo = {
          ...this.albumInfo,
          id: normalizedTag.id,
          public_id: normalizedTag.publicId || this.albumInfo.public_id || '',
          title: normalizedTag.displayName || normalizedTag.name || this.albumInfo.title,
          description: normalizedTag.description || '',
          name: normalizedTag.name || '',
          display_name: normalizedTag.displayName || normalizedTag.name || this.albumInfo.display_name || '',
          type: normalizedTag.type || this.albumInfo.type || 'normal',
          usage_count: Number(savedTag?.usage_count ?? this.albumInfo.usage_count ?? 0),
          last_used_at: String(savedTag?.last_used_at || this.albumInfo.last_used_at || ''),
          metadata: normalizedTag.metadata || {},
          photo_count: this.items.length,
        }
      }

      if (attachToSelection) {
        await this.addTagFromMenu(savedTag)
      } else {
        this.refreshTagMenuExistingTags()
      }

      if (this.tagMenuVisible) {
        await this.fetchTagMenuSuggestions(this.tagMenuQuery)
      }
    },

    async editCurrentBrowseTag() {
      const tagId = this.currentBrowseTagId
      if (!Number.isInteger(tagId) || this.tagMenuBusy || this.tagFormSaving) return

      this.tagMenuBusy = true
      this.tagFormError = ''
      this.tagMenuError = ''
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
        this.showMessage('error', `标签详情读取失败：${err?.message || '未知错误'}`)
      } finally {
        this.tagMenuBusy = false
      }
    },

    onTagMenuQueryChange(nextQuery) {
      this.tagMenuError = ''
      this.tagMenuQuery = String(nextQuery || '')
      if (this.tagMenuSearchTimer) {
        clearTimeout(this.tagMenuSearchTimer)
      }
      this.tagMenuSearchTimer = setTimeout(() => {
        this.tagMenuSearchTimer = null
        this.fetchTagMenuSuggestions(this.tagMenuQuery)
      }, 180)
    },

    async fetchTagMenuSuggestions(rawQuery) {
      if (!this.tagMenuVisible) return
      const query = String(rawQuery || '').trim()
      this.tagMenuSearchBusy = true
      this.tagMenuError = ''

      try {
        if (!query) {
          const res = await fetch(`${API_BASE}/api/tags?offset=0&limit=5&sort_by=last_used_desc`)
          if (!res.ok) {
            throw new Error(`HTTP ${res.status}`)
          }
          const data = await res.json()
          this.tagMenuRecentTags = this.normalizeTagMenuItems(data.items || [])
          this.tagMenuSuggestions = []
          return
        }

        const q = `&q=${encodeURIComponent(query)}`
        const res = await fetch(`${API_BASE}/api/tags?offset=0&limit=24${q}`)
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`)
        }

        const data = await res.json()
        this.tagMenuSuggestions = this.normalizeTagMenuItems(data.items || [])
        this.tagMenuRecentTags = []
      } catch (err) {
        this.tagMenuSuggestions = []
        this.tagMenuRecentTags = []
        this.tagMenuError = `标签搜索失败：${err?.message || '未知错误'}`
      } finally {
        this.tagMenuSearchBusy = false
      }
    },

    async addTagFromMenu(tagItem) {
      const tagId = Number(tagItem?.id)
      if (!this.canOpenTagMenu || !Number.isInteger(tagId) || this.tagMenuBusy) return

      this.tagMenuError = ''
      for (const imageId of this.selectedImageIds) {
        const nextIds = this.sortTagIdsByName([...(this.tagMenuDraftByImageId[imageId] || [])])
        if (!nextIds.includes(tagId)) {
          nextIds.push(tagId)
        }
        this.tagMenuDraftByImageId[imageId] = this.sortTagIdsByName(nextIds)
      }

      const normalizedTag = this.buildTagLookupEntry(tagItem)
      if (normalizedTag) {
        this.tagLookupMap = {
          ...this.tagLookupMap,
          [normalizedTag.id]: normalizedTag,
        }
      }
      this.refreshTagMenuExistingTags()
    },

    async removeTagFromMenu(tagItem) {
      const tagId = Number(tagItem?.id)
      if (!this.canOpenTagMenu || !Number.isInteger(tagId) || this.tagMenuBusy) return

      this.tagMenuError = ''
      for (const imageId of this.selectedImageIds) {
        const nextIds = (this.tagMenuDraftByImageId[imageId] || []).filter(id => id !== tagId)
        this.tagMenuDraftByImageId[imageId] = this.sortTagIdsByName(nextIds)
      }
      this.refreshTagMenuExistingTags()
    },

    async applyAutoTagFromMenu() {
      if (!this.canOpenTagMenu || this.tagMenuBusy) return
      this.tagMenuBusy = true
      this.tagMenuError = ''

      try {
        const res = await fetch(`${API_BASE}/api/images/tags/filename-match`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            image_ids: this.selectedImageIds,
            apply: false,
            merge_mode: 'append_unique',
            include_tokens: false,
          }),
        })
        if (!res.ok) {
          const payload = await res.json().catch(() => ({}))
          throw new Error(payload.detail || `HTTP ${res.status}`)
        }

        const payload = await res.json()
        const nextTagMap = { ...this.tagLookupMap }
        for (const row of (payload?.items || [])) {
          if (Number.isInteger(row?.image_id) && Array.isArray(row?.matched_tag_ids)) {
            const imageId = row.image_id
            const beforeIds = this.sortTagIdsByName([...(this.tagMenuDraftByImageId[imageId] || [])])
            const mergedSet = new Set(beforeIds)
            for (const tagId of row.matched_tag_ids) {
              if (Number.isInteger(tagId)) mergedSet.add(tagId)
            }
            this.tagMenuDraftByImageId[imageId] = this.sortTagIdsByName(Array.from(mergedSet))
          }
          for (const tag of (row?.matched_tags || [])) {
            const normalizedTag = this.buildTagLookupEntry(tag)
            if (!normalizedTag) continue
            nextTagMap[normalizedTag.id] = normalizedTag
          }
        }
        this.tagLookupMap = nextTagMap
        this.refreshTagMenuExistingTags()
      } catch (err) {
        this.tagMenuError = `自动标签失败：${err?.message || '未知错误'}`
      } finally {
        this.tagMenuBusy = false
      }
    },

    async confirmTagMenuChanges() {
      if (!this.canOpenTagMenu || !this.tagMenuDirty || this.tagMenuBusy) return

      this.tagMenuBusy = true
      this.tagMenuError = ''
      try {
        const changedImageIds = this.selectedImageIds.filter((imageId) => {
          const beforeIds = this.sortTagIdsByName([...(this.tagMenuOriginalByImageId[imageId] || [])])
          const afterIds = this.sortTagIdsByName([...(this.tagMenuDraftByImageId[imageId] || [])])
          if (beforeIds.length !== afterIds.length) return true
          for (let index = 0; index < beforeIds.length; index++) {
            if (beforeIds[index] !== afterIds[index]) return true
          }
          return false
        })

        for (const imageId of changedImageIds) {
          const res = await fetch(`${API_BASE}/api/images/tags/apply`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              image_ids: [imageId],
              tag_ids: this.sortTagIdsByName([...(this.tagMenuDraftByImageId[imageId] || [])]),
              merge_mode: 'replace',
            }),
          })
          if (!res.ok) {
            const payload = await res.json().catch(() => ({}))
            throw new Error(payload.detail || `HTTP ${res.status}`)
          }
        }

        if (changedImageIds.length) {
          const changedIdSet = new Set(changedImageIds)
          this.items = this.items.map((item) => {
            if (item?.type !== 'image' || !Number.isInteger(item?.id)) return item
            if (!changedIdSet.has(item.id)) return item
            return {
              ...item,
              tags: this.sortTagIdsByName([...(this.tagMenuDraftByImageId[item.id] || [])]),
            }
          })
        }

        await this.ensureTagLabelsLoaded(true)
        this.closeTagMenu()
      } catch (err) {
        this.tagMenuError = `标签回写失败：${err?.message || '未知错误'}`
      } finally {
        this.tagMenuBusy = false
      }
    },

    async editTagMetadataFromMenu(tagItem) {
      const tagId = Number(tagItem?.id)
      if (!this.canOpenTagMenu || !Number.isInteger(tagId) || this.tagMenuBusy) return

      this.tagMenuBusy = true
      this.tagFormError = ''
      this.tagMenuError = ''
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
        this.tagMenuError = `标签详情读取失败：${err?.message || '未知错误'}`
      } finally {
        this.tagMenuBusy = false
      }
    },

    async addNewTagFromMenu() {
      if (!this.canOpenTagMenu || this.tagMenuBusy) return

      this.tagMenuBusy = true
      this.tagFormError = ''
      this.tagMenuError = ''
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
        this.tagMenuError = `新建标签初始化失败：${err?.message || '未知错误'}`
      } finally {
        this.tagMenuBusy = false
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
        this.resetTagFormState()
        await this.refreshTagCollectionsAfterSave(savedTag, { attachToSelection: mode === 'create' })
      } catch (err) {
        this.tagFormError = `标签保存失败：${err?.message || '未知错误'}`
      } finally {
        this.tagFormSaving = false
      }
    },

    tagTextForItem(item) {
      const ids = Array.isArray(item?.tags)
        ? item.tags.filter(id => Number.isInteger(id))
        : []
      if (!ids.length) return '无标签'

      const names = []
      let allResolved = true
      for (const id of ids) {
        if (!Object.prototype.hasOwnProperty.call(this.tagLookupMap, id)) {
          allResolved = false
          continue
        }
        const label = this.tagLookupMap[id]?.displayName || ''
        if (label) names.push(label)
      }

      if (names.length) return names.join(' · ')
      if (!allResolved && this.tagsLoading) return '加载标签中...'
      return '无标签'
    },

    detailTagTextForItem(item) {
      if (item?.type !== 'image') return ''
      const ids = Array.isArray(item?.tags)
        ? item.tags.filter(id => Number.isInteger(id))
        : []
      if (!ids.length) return ''

      const sortedIds = this.sortTagIdsByName(ids)
      const names = []
      let allResolved = true
      for (const id of sortedIds) {
        if (!Object.prototype.hasOwnProperty.call(this.tagLookupMap, id)) {
          allResolved = false
          continue
        }
        const label = this.tagLookupMap[id]?.displayName || ''
        if (label) names.push(label)
      }

      if (names.length) return names.join(' · ')
      if (!allResolved && this.tagsLoading) return '加载标签中...'
      return ''
    },

    collectMissingTagIds() {
      const result = []
      const seen = new Set()
      for (const item of this.items) {
        if (item?.type !== 'image' || !Array.isArray(item.tags)) continue
        for (const id of item.tags) {
          if (!Number.isInteger(id)) continue
          if (seen.has(id)) continue
          seen.add(id)
          if (!Object.prototype.hasOwnProperty.call(this.tagLookupMap, id)) {
            result.push(id)
          }
        }
      }
      return result
    },

    async ensureTagLabelsLoaded(force = false) {
      if (!force && this.selectionInfoMode !== 'tags') return
      const missingIds = this.collectMissingTagIds()
      if (!missingIds.length) return

      const requestSerial = ++this.tagFetchSerial
      const nextMap = { ...this.tagLookupMap }
      this.tagsLoading = true

      try {
        for (let i = 0; i < missingIds.length; i += TAG_BATCH_SIZE) {
          const chunk = missingIds.slice(i, i + TAG_BATCH_SIZE)
          const res = await fetch(`${API_BASE}/api/tags?ids=${chunk.join(',')}&limit=${chunk.length}`)
          if (!res.ok) continue
          const data = await res.json()
          const returnedIds = new Set()
          for (const tag of (data.items || [])) {
            const normalizedTag = this.buildTagLookupEntry(tag)
            if (!normalizedTag) continue
            returnedIds.add(tag.id)
            nextMap[tag.id] = normalizedTag
          }
          for (const id of chunk) {
            if (!returnedIds.has(id) && !Object.prototype.hasOwnProperty.call(nextMap, id)) {
              nextMap[id] = {
                id,
                name: '',
                displayName: '',
                color: '',
                borderColor: '',
                backgroundColor: '',
              }
            }
          }
        }

        if (requestSerial === this.tagFetchSerial) {
          this.tagLookupMap = nextMap
        }
      } catch {
        // ignore tag fetch failures and keep filename mode available
      } finally {
        if (requestSerial === this.tagFetchSerial) {
          this.tagsLoading = false
        }
      }
    },

    onReservedDetailsClick(item, index) {
      if (!item) return
      const alreadySelected = this.isItemSelected(item, index)

      if (!this.selectedCount) {
        this.selectOnlyIndex(index)
      } else if (this.selectedCount === 1) {
        if (!alreadySelected) {
          this.selectOnlyIndex(index)
        }
      } else if (!alreadySelected) {
        this.selectOnlyIndex(index)
      }

      this.openSelectionDetails()
    },

    openConfirmDialog(options = {}) {
      this.confirmDialog = {
        ...createDialogState(),
        ...options,
        visible: true,
      }
    },

    showMessage(type, text) {
      this.messageType = type
      this.messageText = text
    },

    closeConfirmDialog() {
      if (this.confirmDialog.busy) return
      this.confirmDialog = createDialogState()
    },

    async handleConfirmDialogConfirm() {
      if (this.confirmDialog.busy) return
      const onConfirm = this.confirmDialog.onConfirm
      if (typeof onConfirm !== 'function') {
        this.closeConfirmDialog()
        return
      }

      this.confirmDialog = {
        ...this.confirmDialog,
        busy: true,
      }

      let followupDialog = null
      try {
        followupDialog = await onConfirm()
      } finally {
        this.confirmDialog = createDialogState()
      }

      if (followupDialog) {
        this.openConfirmDialog(followupDialog)
      }
    },

    moveSelectedToTrash() {
      if (!this.selectedCount || this.actionBusy) return
      const label = this.selectionTypeLock === 'album'
        ? `确认删除已选中的 ${this.selectedCount} 个相册吗？`
        : `确认删除已选中的 ${this.selectedCount} 张图片吗？`
      this.openConfirmDialog({
        title: '移入回收站',
        message: `${label}\n原始文件会从 media 中移走，之后可在回收站中还原。`,
        confirmLabel: '移入回收站',
        cancelLabel: '取消',
        tone: 'danger',
        busyLabel: '删除中…',
        onConfirm: () => this.executeMoveSelectedToTrash(),
      })
    },

    async executeMoveSelectedToTrash() {
      if (!this.selectedCount || this.actionBusy) return null

      this.actionBusy = true
      this.actionBusyTitle = '删除中'
      this.actionBusyText = '正在移动所选内容到回收站，请稍候…'

      const payload = {
        items: this.selectedEntries.map(({ item }) => (
          item.type === 'album'
            ? { type: 'album', album_path: item.album_path }
            : { type: 'image', image_id: item.id, media_rel_path: item.media_rel_path }
        ))
      }

      try {
        const res = await fetch(`${API_BASE}/api/trash/move`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        })
        if (!res.ok) {
          return {
            title: '移入回收站失败',
            message: `请求未成功完成，服务器返回 HTTP ${res.status}。`,
            confirmLabel: '知道了',
            tone: 'danger',
            showCancel: false,
          }
        }

        const data = await res.json()
        await this.loadData()
        if (Array.isArray(data.errors) && data.errors.length) {
          return {
            title: '移入回收站失败',
            message: data.errors.join('；'),
            confirmLabel: '知道了',
            tone: 'danger',
            showCancel: false,
          }
        }
        return null
      } catch (err) {
        return {
          title: '移入回收站失败',
          message: err?.message || '删除失败，请稍后重试。',
          confirmLabel: '知道了',
          tone: 'danger',
          showCancel: false,
        }
      } finally {
        this.actionBusy = false
        this.actionBusyTitle = ''
        this.actionBusyText = ''
      }
    },

    onReservedDeleteClick() {
      this.onSelectionDetailSecondaryAction()
    },

    restoreSelection() {
      if (!this.selectedCount || this.actionBusy) return
      this.closeSelectAllMenu()
      this.openConfirmDialog({
        title: '确认还原',
        message: `确认还原已选中的 ${this.selectedCount} 项吗？\n若目标位置已存在同名项目，系统会自动补编号避免覆盖。`,
        confirmLabel: '还原',
        cancelLabel: '取消',
        tone: 'accent',
        busyLabel: '还原中…',
        onConfirm: () => this.executeRestoreSelection(),
      })
    },

    async executeRestoreSelection() {
      if (!this.selectedCount || this.actionBusy) return null
      this.actionBusy = true
      this.actionBusyTitle = '还原中'
      this.actionBusyText = '正在还原所选内容，请稍候…'
      try {
        const res = await fetch(`${API_BASE}/api/trash/restore`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ entry_ids: this.selectedEntries.map(({ item }) => item.id) }),
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        if (data.errors?.length) {
          this.showMessage('error', data.errors.join('；'))
        } else {
          this.showMessage('success', `已还原 ${data.restored} 项。`)
        }
        await this.loadData()
        return null
      } catch (err) {
        this.showMessage('error', err?.message || '还原失败')
        return null
      } finally {
        this.actionBusy = false
        this.actionBusyTitle = ''
        this.actionBusyText = ''
      }
    },

    hardDeleteSelection() {
      if (!this.selectedCount || this.actionBusy) return
      this.closeSelectAllMenu()
      this.openConfirmDialog({
        title: '确认彻底删除',
        message: `确认彻底删除已选中的 ${this.selectedCount} 项吗？\n此操作会直接移除 trash 中的文件，且无法恢复。`,
        confirmLabel: '彻底删除',
        cancelLabel: '取消',
        tone: 'danger',
        busyLabel: '删除中…',
        onConfirm: () => this.executeHardDeleteSelection(),
      })
    },

    async executeHardDeleteSelection() {
      if (!this.selectedCount || this.actionBusy) return null
      this.actionBusy = true
      this.actionBusyTitle = '删除中'
      this.actionBusyText = '正在彻底删除所选内容，请稍候…'
      try {
        const res = await fetch(`${API_BASE}/api/trash/hard-delete`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ entry_ids: this.selectedEntries.map(({ item }) => item.id) }),
        })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        if (data.errors?.length) {
          this.showMessage('error', data.errors.join('；'))
        } else {
          this.showMessage('success', `已删除 ${data.deleted} 项。`)
        }
        await this.loadData()
        return null
      } catch (err) {
        this.showMessage('error', err?.message || '删除失败')
        return null
      } finally {
        this.actionBusy = false
        this.actionBusyTitle = ''
        this.actionBusyText = ''
      }
    },

    clearTrash() {
      if (!this.totalCount || this.actionBusy) return
      this.closeSelectAllMenu()
      this.openConfirmDialog({
        title: '确认清空回收站',
        message: '确认清空回收站吗？\n此操作会物理删除 trash 中的全部文件和目录，且无法恢复。',
        confirmLabel: '清空回收站',
        cancelLabel: '取消',
        tone: 'danger',
        busyLabel: '清空中…',
        onConfirm: () => this.executeClearTrash(),
      })
    },

    async executeClearTrash() {
      if (!this.totalCount || this.actionBusy) return null
      this.actionBusy = true
      this.actionBusyTitle = '清空中'
      this.actionBusyText = '正在清空回收站，请稍候…'
      try {
        const res = await fetch(`${API_BASE}/api/trash`, { method: 'DELETE' })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        if (data.errors?.length) {
          this.showMessage('error', data.errors.join('；'))
        } else {
          this.showMessage('success', `已清空回收站，共删除 ${data.deleted} 项。`)
        }
        await this.loadData()
        return null
      } catch (err) {
        this.showMessage('error', err?.message || '清空回收站失败')
        return null
      } finally {
        this.actionBusy = false
        this.actionBusyTitle = ''
        this.actionBusyText = ''
      }
    },

    async reloadContractItemsPreservingAnchor({ preserveSelection = true, reopenDetails = false, runAfterLoad = true } = {}) {
      const anchor = this.captureViewportAnchor()
      const selectionSnapshot = preserveSelection ? this.captureSelectionSnapshot() : null

      try {
        const payload = await this.pageContract.loadItems(this)
        this.albumInfo = payload?.album || null
        this.applyFetchedItems(payload?.items || [])
        this.lastPreviewRepairSignature = ''
        if (preserveSelection) {
          this.restoreSelectionSnapshot(selectionSnapshot)
        }
        if (anchor) {
          this.pendingViewAnchor = anchor
        }
        this.$nextTick(() => {
          this.refreshObservedGrid()
          if (runAfterLoad) {
            this.pageContract.afterLoad(this)
          }
          if (reopenDetails && this.selectedCount) {
            this.openSelectionDetails()
          }
        })
        return true
      } catch {
        return false
      }
    },

    async triggerSilentRepair() {
      if (!this.isTrashMode || this.reconcileInFlight) return
      this.reconcileInFlight = true
      try {
        const res = await fetch(`${API_BASE}/api/trash/reconcile`, { method: 'POST' })
        if (!res.ok) return
        const data = await res.json().catch(() => ({}))
        if (data?.changed) {
          await this.reloadContractItemsPreservingAnchor({
            preserveSelection: true,
            reopenDetails: this.selectionDetailsOpen,
            runAfterLoad: false,
          })
        }
      } catch {
        // ignore silent reconcile failures
      } finally {
        this.reconcileInFlight = false
      }
    },

    async triggerCacheForPlan(plan, orderedImageIds, reason = 'cache-anchor') {
      if (!plan || !orderedImageIds.length) return
      const anchorItem = this.items[plan.cacheAnchorIndex]
      if (!anchorItem?.id) return

      const generation = ++this.cacheRequestGeneration
      const body = {
        ordered_image_ids: orderedImageIds,
        generation,
        page_token: this.cachePageToken,
        sort_signature: this.cacheSortSignature,
        direction: plan.direction || 'none',
        anchor_image_id: anchorItem.id,
        anchor_item_key: plan.anchorItemKey,
        anchor_offset: plan.anchorOffset || 0,
      }

      this.logBrowseDebug('cache-request', {
        reason,
        generation,
        visualAnchorIndex: plan.visualAnchorIndex,
        cacheAnchorIndex: plan.cacheAnchorIndex,
        orderedCount: orderedImageIds.length,
        firstRowIndices: plan.firstRowIndices,
      })

      try {
        const res = await fetch(`${API_BASE}/api/thumbnails/cache`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        if (!res.ok) return
        const data = await res.json()
        if (generation !== this.cacheRequestGeneration) return
        this.taskId = data.task_id
        this.cacheStatusCursor = 0
        this.startPoll(generation)
      } catch {
        // ignore thumbnail trigger failures
      }
    },

    startPoll(expectedGeneration = this.cacheRequestGeneration) {
      this.stopPoll(false)
      const poll = async () => {
        if (!this.taskId || expectedGeneration !== this.cacheRequestGeneration) return
        try {
          const res = await fetch(`${API_BASE}/api/thumbnails/cache/status/${this.taskId}?cursor=${this.cacheStatusCursor}`)
          if (!res.ok) return
          const data = await res.json()
          if (expectedGeneration !== this.cacheRequestGeneration) return
          const newUrls = {}
          for (const item of (data.items || [])) {
            if (item.id && item.cache_thumb_url) newUrls[item.id] = item.cache_thumb_url
          }
          if (Object.keys(newUrls).length > 0) {
            this.cacheUrls = { ...this.cacheUrls, ...newUrls }
          }
          if (Number.isInteger(data.next_cursor)) {
            this.cacheStatusCursor = data.next_cursor
          } else {
            this.cacheStatusCursor += (data.items || []).length
          }
          if (data.status === 'running') {
            this.pollTimer = setTimeout(poll, POLL_MS)
          }
        } catch {
          // ignore polling failures
        }
      }
      this.pollTimer = setTimeout(poll, POLL_MS)
    },

    stopPoll(resetTask = true) {
      if (this.pollTimer) {
        clearTimeout(this.pollTimer)
        this.pollTimer = null
      }
      if (resetTask) {
        this.taskId = null
      }
      this.cacheStatusCursor = 0
    },

    refreshObservedGrid() {
      this.$nextTick(() => {
        this.teardownObserver()
        this.teardownResizeObserver()
        if (!this.$refs.itemGrid) return
        this.measureItemGridMetrics()
        this.normalizePaginationState()
        if (this.isVirtualizedMode) {
          this.syncVirtualWindow(true)
        } else {
          this.virtualStartIndex = 0
          this.virtualEndIndex = this.items.length
          this.virtualAnchorIndex = this.items.length ? 0 : -1
        }
        if (this.isPhotoGridMode && !this.isPagedBrowseMode) {
          this.setupObserver()
        }
        this.setupResizeObserver()
        if (this.isSelectionGridMode) {
          this.measureSelectionRowHeight()
        }
        if (this.pendingViewAnchor) {
          this.restorePendingViewAnchor()
        } else if (this.isPagedBrowseMode) {
          this.queueCurrentPageCache(true, 'refresh-paged')
        } else if (this.isPhotoGridMode) {
          const anchor = this.captureViewportAnchor()
          if (anchor) {
            this.queuePhotoGridCachePlan(anchor.index, true, 'refresh')
          }
        }
      })
    },

    setupObserver() {
      if (!this.$refs.itemGrid || !this.isPhotoGridMode) return
      this.observer = new IntersectionObserver(
        (entries) => {
          const visible = entries
            .filter(entry => entry.isIntersecting)
            .map(entry => parseInt(entry.target.dataset.index, 10))
          if (!visible.length) return
          const topIndex = Math.min(...visible)
          this.queuePhotoGridCachePlan(topIndex, false, 'observer')
        },
        { root: null, rootMargin: '0px', threshold: 0.1 },
      )
      for (const el of this.$refs.itemGrid.querySelectorAll('[data-index]')) {
        this.observer.observe(el)
      }
    },

    teardownObserver() {
      if (this.observer) {
        this.observer.disconnect()
        this.observer = null
      }
      if (this.debounceTimer) {
        clearTimeout(this.debounceTimer)
        this.debounceTimer = null
      }
    },

    setupResizeObserver() {
      if (!this.$refs.itemGrid) return
      if (this.resizeObserver) {
        this.resizeObserver.disconnect()
        this.resizeObserver = null
      }
      this.resizeObserver = new ResizeObserver(() => {
        requestAnimationFrame(() => {
          if (this.$refs.itemGrid) {
            if (this.isPagedBrowseMode) {
              const anchor = this.captureViewportAnchor()
              if (anchor) {
                this.pendingViewAnchor = anchor
              }
              this.refreshObservedGrid()
            } else {
              this.measureItemGridMetrics()
              if (this.isVirtualizedMode) {
                this.syncVirtualWindow(true)
                if (this.isSelectionGridMode) {
                  this.measureSelectionRowHeight()
                }
              }
            }
          }
        })
      })
      this.resizeObserver.observe(this.$refs.itemGrid)
    },

    teardownResizeObserver() {
      if (this.resizeObserver) {
        this.resizeObserver.disconnect()
        this.resizeObserver = null
      }
    },
  },
}
</script>

<style scoped lang="css">
.page {
  @apply flex flex-col gap-6;
  position: relative;
}

.page-main {
  display: flex;
  flex: 1 1 auto;
  min-height: 0;
  flex-direction: column;
}

.page--paged {
  height: calc(100dvh - 5rem);
  min-height: calc(100vh - 5rem);
  overflow: hidden;
}

.page--paged .empty-hint,
.page--paged .selection-grid,
.page--paged .photo-grid,
.page--paged .list-view {
  flex: 1 1 auto;
  min-height: 0;
}

.page--paged .list-view {
  overflow-y: auto !important;
}

.page--paged .selection-wrap {
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
}

.page--paged .selection-wrap :deep(.media-card) {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page--paged .selection-wrap :deep(.media-card__visual) {
  flex: 1 1 0;
  min-height: 0;
  aspect-ratio: auto;
}

.page--paged .empty-hint {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.vm-btns {
  display: flex;
  align-items: center;
  background: #f1f5f9;
  border-radius: 8px;
  padding: 2px;
  gap: 1px;
}

.vm-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  padding: 0;
  transition: background 150ms ease, color 150ms ease, box-shadow 150ms ease, opacity 150ms ease;
}

.vm-btn:hover:not(:disabled) {
  background: #e2e8f0;
  color: #1e293b;
}

.vm-btn.active {
  background: #fff;
  color: #1e293b;
  box-shadow: 0 1px 3px rgba(0,0,0,.12);
}

.vm-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.browse-header__action {
  height: 30px;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 8px;
  padding: 0 0.8rem;
  background: rgba(255, 255, 255, 0.92);
  color: #334155;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  transition: background 140ms ease, border-color 140ms ease, color 140ms ease, opacity 140ms ease;
}

.browse-header__action:hover:not(:disabled) {
  border-color: rgba(100, 116, 139, 0.34);
  background: #f8fafc;
  color: #0f172a;
}

.browse-header__action--active {
  border-color: rgba(15, 23, 42, 0.9);
  background: #0f172a;
  color: #ffffff;
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.16);
}

.browse-header__action--active:hover:not(:disabled) {
  border-color: rgba(15, 23, 42, 0.9);
  background: #0f172a;
  color: #ffffff;
}

.browse-header__action:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.browse-header__action--danger {
  border-color: rgba(234, 88, 12, 0.22);
  background: rgba(255, 237, 213, 0.86);
  color: #b45309;
}

.browse-header__action--danger:hover:not(:disabled) {
  border-color: rgba(234, 88, 12, 0.3);
  background: rgba(255, 237, 213, 1);
}

.empty-hint {
  @apply border-2 border-dashed border-slate-300 bg-slate-50 rounded-xl py-16 text-center text-slate-400 text-sm;
}

.empty-hint__icon { @apply text-5xl block mb-3; }

.page-note {
  margin: 0.5rem 0 0;
  padding: 0.7rem 0.95rem;
  border-radius: 12px;
  font-size: 0.88rem;
  font-weight: 700;
}

.page-note--success {
  color: #166534;
  background: rgba(220, 252, 231, 0.88);
  border: 1px solid rgba(34, 197, 94, 0.18);
}

.page-note--error {
  color: #b91c1c;
  background: rgba(254, 226, 226, 0.92);
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.selection-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
  align-items: start;
}

.selection-wrap {
  min-width: 0;
  cursor: pointer;
  user-select: none;
  touch-action: pan-y;
}

.selection-wrap.is-disabled {
  cursor: not-allowed;
}

.photo-grid {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.photo-grid--masonry {
  width: 100%;
}

.photo-wrap--masonry {
  position: absolute;
  overflow: hidden;
  border-radius: 10px;
}

.photo-wrap--masonry .photo-card {
  border-radius: 10px;
}

.photo-grid--masonry-skeleton {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  padding: 4px 0;
}

.masonry-skeleton-col {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.masonry-skeleton-item {
  border-radius: 10px;
  width: 100%;
  flex-shrink: 0;
}

.jl-row {
  display: flex;
  flex-direction: row;
  gap: 4px;
  overflow: hidden;
}

.photo-wrap {
  overflow: hidden;
  flex-shrink: 0;
  height: 100%;
}

.photo-skeleton {
  @apply w-full h-full rounded-xl overflow-hidden flex items-center justify-center;
  background: linear-gradient(90deg, #e2e8f0 25%, #f1f5f9 50%, #e2e8f0 75%);
  background-size: 200% 100%;
  animation: skeleton-wave 1.4s ease-in-out infinite;
}

.skeleton-label {
  @apply text-slate-400 text-xs font-mono tracking-widest select-none;
  animation: skeleton-fade 1.4s ease-in-out infinite;
}

@keyframes skeleton-wave {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@keyframes skeleton-fade {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.8; }
}

.photo-card {
  @apply relative cursor-pointer rounded-xl overflow-hidden shadow-md;
  width: 100%;
  height: 100%;
  transition: box-shadow 200ms ease, transform 200ms ease;
}

.photo-card--cover-picking {
  box-shadow: 0 0 0 2px rgba(15, 23, 42, 0.28), 0 16px 30px rgba(15, 23, 42, 0.12);
}

.photo-card:hover { @apply shadow-xl -translate-y-0.5; }

.photo-img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 300ms ease;
}

.photo-card:hover .photo-img { transform: scale(1.03); }

.item-cover-badge,
.list-cover-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  min-width: 44px;
  height: 24px;
  padding: 0 0.5rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.88);
  color: #ffffff;
  font-size: 0.66rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  line-height: 1;
  white-space: nowrap;
  word-break: keep-all;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.22);
  pointer-events: none;
}

.album-badge {
  @apply absolute top-2 right-2 flex flex-col items-center gap-0.5 px-2 py-1 rounded-lg;
  background: rgba(255, 255, 255, 0.90);
  box-shadow: 0 1px 4px rgba(0,0,0,.15);
  pointer-events: none;
}

.badge-icon { font-size: 1rem; }

.badge-name {
  @apply text-slate-800 text-xs font-semibold text-center select-none;
  max-width: 6rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.badge-count {
  @apply select-none;
  color: rgba(100, 116, 139, 0.8);
  font-size: 0.65rem;
}

.list-view {
  display: flex;
  flex-direction: column;
}

.list-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 150ms ease, box-shadow 150ms ease, opacity 150ms ease;
}

.list-row:hover { background: #f1f5f9; }

.list-row.is-selected {
  background: #e8eef8;
  box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.08);
}

.list-row.is-disabled {
  opacity: 0.45;
}

.list-pick {
  width: 26px;
  height: 26px;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 2px solid rgba(15, 23, 42, 0.85);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.94);
  color: #ffffff;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.12);
  padding: 0;
  cursor: pointer;
  transition: transform 140ms ease, background 140ms ease, border-color 140ms ease;
}

.list-pick:hover:not(:disabled) {
  transform: scale(1.04);
}

.list-pick:disabled {
  cursor: not-allowed;
}

.list-row.is-selected .list-pick {
  border-color: #0f172a;
  background: #0f172a;
}

.list-pick__mark {
  font-size: 0.8rem;
  font-weight: 700;
  line-height: 1;
}

.list-thumb-wrap {
  position: relative;
  width: 50px;
  height: 50px;
  flex-shrink: 0;
  border-radius: 6px;
  overflow: hidden;
  background: #e2e8f0;
}

.list-thumb-wrap--cover-picking {
  box-shadow: inset 0 0 0 2px rgba(15, 23, 42, 0.26);
}

.list-cover-badge {
  top: 6px;
  right: 6px;
  min-width: 34px;
  height: 18px;
  padding: 0 0.35rem;
  font-size: 0.54rem;
}

.list-thumb-skeleton {
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, #e2e8f0 25%, #f1f5f9 50%, #e2e8f0 75%);
  background-size: 200% 100%;
  animation: skeleton-wave 1.4s ease-in-out infinite;
}

.list-thumb-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.list-main {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
}

.list-title-row {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  min-width: 0;
  width: 100%;
}

.list-type-pill {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 2.4rem;
  height: 1.55rem;
  padding: 0 0.55rem;
  border-radius: 999px;
  background: #e2e8f0;
  color: #334155;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.list-name {
  flex: 1;
  min-width: 0;
  font-size: 0.875rem;
  color: #334155;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.page-pagination-host {
  padding-top: 0.12rem;
}

.page-pagination-host--selection {
  padding-bottom: 0.08rem;
}

@media (orientation: landscape) {
  .selection-grid {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }
}

@media (orientation: portrait) {
  .selection-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.8rem;
  }
}

.page--paged .selection-island {
  position: absolute;
  right: 1.5rem;
  bottom: 4.25rem;
}
</style>
