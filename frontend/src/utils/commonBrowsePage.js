import { buildSearchRequestParams, formatSearchModeLabel } from '../pages/topLevelPageConvention'
import { normalizeAnimatedFields, resolveAnimatedBadgeLabel } from './animatedMedia'

const API_BASE = 'http://127.0.0.1:8000'

function toUnixSeconds(value) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.floor(value)
  }
  if (!value) return 0
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return 0
  return Math.floor(parsed.getTime() / 1000)
}

function normalizeCalendarItem(rawItem) {
  const type = rawItem?.type === 'album' ? 'album' : 'image'
  const name = rawItem?.name || rawItem?.full_filename || '未命名'
  const stableKey = type === 'album'
    ? `album:${rawItem?.public_id || rawItem?.album_path || rawItem?.id || name}`
    : `image:${rawItem?.media_rel_path || rawItem?.id || name}`
  const animatedFields = normalizeAnimatedFields(rawItem)

  return {
    ...rawItem,
    ...animatedFields,
    type,
    name,
    count: Number(rawItem?.count ?? rawItem?.photo_count ?? 0) || 0,
    sort_ts: Number(rawItem?.sort_ts) || toUnixSeconds(rawItem?.file_created_at || rawItem?.imported_at || rawItem?.created_at),
    stable_key: stableKey,
    layout_key: rawItem?.id || rawItem?.public_id || rawItem?.album_path || rawItem?.media_rel_path || stableKey,
    animated_badge_label: resolveAnimatedBadgeLabel(rawItem),
    preview_original_url: type === 'image' && rawItem?.media_rel_path
      ? `/media/${String(rawItem.media_rel_path).replace(/\\/g, '/')}`
      : '',
    editable: {
      name: type === 'image' && Number.isInteger(rawItem?.id),
      category: type === 'image' && Number.isInteger(rawItem?.id),
      tags: type === 'image' && Number.isInteger(rawItem?.id),
      createdAt: type === 'image' && Number.isInteger(rawItem?.id),
    },
  }
}

function normalizeTrashItem(rawItem) {
  const type = rawItem?.entity_type === 'album' ? 'album' : 'image'
  const name = rawItem?.display_name || rawItem?.name || '未命名'
  const stableKey = `${type}:${rawItem?.entry_key || rawItem?.id || name}`
  const previewCacheUrl = rawItem?.cache_thumb_url || rawItem?.preview_cache_path || ''
  const previewThumbUrl = rawItem?.thumb_url || rawItem?.preview_thumb_path || rawItem?.preview_path || ''
  const previewOriginalUrl = rawItem?.trash_media_url || rawItem?.preview_path || ''
  const animatedFields = normalizeAnimatedFields(rawItem)

  return {
    ...rawItem,
    ...animatedFields,
    type,
    name,
    public_id: type === 'album' ? (rawItem?.public_id || rawItem?.entry_key || String(rawItem?.id || '')) : rawItem?.public_id,
    count: Number(rawItem?.count ?? rawItem?.photo_count ?? 0) || 0,
    sort_ts: Number(rawItem?.sort_ts) || toUnixSeconds(rawItem?.file_created_at || rawItem?.imported_at || rawItem?.created_at),
    stable_key: stableKey,
    layout_key: rawItem?.entry_key || rawItem?.id || stableKey,
    animated_badge_label: resolveAnimatedBadgeLabel(rawItem),
    cache_thumb_url: previewCacheUrl,
    thumb_url: previewThumbUrl,
    preview_original_url: previewOriginalUrl,
    editable: {
      name: false,
      category: false,
      tags: false,
      createdAt: false,
    },
  }
}

function buildCalendarCrumbs(vm) {
  const crumbs = [
    { label: '日期视图', title: '日期视图', to: '/calendar' },
  ]

  if (!vm.isAlbumMode) {
    crumbs.push({ label: vm.dateGroup, current: true })
    return crumbs
  }

  crumbs.push({
    label: vm.dateGroup,
    title: vm.dateGroup,
    to: `/calendar/${vm.dateGroup}`,
  })

  const segments = vm.albumPath.split('/').filter(Boolean)
  for (let index = 0; index < segments.length; index += 1) {
    const segment = segments[index]
    const isLast = index === segments.length - 1
    const segPath = segments.slice(0, index + 1).join('/')
    const ancestorTitle = vm.getAncestorTitle(index, segment)
    if (isLast) {
      crumbs.push({
        label: vm.bcLabel(vm.albumInfo?.title || segment),
        title: vm.albumInfo?.title || segment,
        current: true,
      })
      continue
    }
    crumbs.push({
      label: vm.bcLabel(ancestorTitle),
      title: ancestorTitle,
      to: `/calendar/${vm.dateGroup}/${segPath}`,
    })
  }

  return crumbs
}

function buildSelectionAction(key, label, handler, options = {}) {
  return {
    key,
    label,
    handler,
    className: options.className || '',
    disabled: Boolean(options.disabled),
  }
}

function buildCoverHeaderAction(vm) {
  return {
    key: 'pick-cover',
    label: vm.coverPickerMode ? '取消选择封面' : '选择封面',
    handler: 'toggleCoverPicker',
    className: vm.coverPickerMode ? 'browse-header__action--active' : '',
    disabled: !vm.canPickContainerCover || vm.actionBusy,
  }
}

function buildCalendarLikeSelectionActions(vm) {
  return [
    buildSelectionAction('details', '详情', 'openSelectionDetailsFromIsland', {
      disabled: !vm.selectedCount || vm.actionBusy,
    }),
    buildSelectionAction('collect', '收藏', 'openCollectionMenu', {
      disabled: !vm.canOpenCollectionMenu || vm.actionBusy,
    }),
  ]
}

function buildCalendarLikeDetailPolicy(vm) {
  return {
    metadataPermissions: {
      name: vm.canEditSelectionName,
      category: vm.canEditSelectionCategory,
      tags: vm.canOpenTagMenu,
      createdAt: vm.canEditSelectionCreatedAt,
    },
    primaryActionLabel: vm.selectionDetailType === 'album' ? '查看相册' : '查看原图',
    primaryActionTone: 'accent',
    canOpenPrimaryAction: vm.canOpenPrimaryActionFromDetails && !vm.actionBusy,
    primaryActionDisabled: vm.actionBusy,
    secondaryActionLabel: '移入回收站',
    secondaryActionTone: 'danger',
    secondaryActionDisabled: vm.actionBusy,
  }
}

function openImageItem(item) {
  if (!Number.isInteger(item?.id)) return
  const pathSuffix = item.media_rel_path ? `?path=${encodeURIComponent(item.media_rel_path)}` : ''
  fetch(`${API_BASE}/api/images/${item.id}/open${pathSuffix}`).catch(() => {})
}

function normalizeCollectionItem(rawItem) {
  return normalizeCalendarItem(rawItem)
}

function buildCollectionCrumbs(vm) {
  return [
    { label: '收藏', title: '收藏', to: '/favorites' },
    {
      label: vm.bcLabel(vm.albumInfo?.title || '收藏夹'),
      title: vm.albumInfo?.title || '收藏夹',
      current: true,
    },
  ]
}

function buildTagCrumbs(vm) {
  return [
    { label: '标签总览', title: '标签总览', to: '/tags' },
    {
      label: vm.bcLabel(vm.albumInfo?.title || '标签'),
      title: vm.albumInfo?.title || '标签',
      current: true,
    },
  ]
}

function buildTagHeaderActions(vm) {
  return [
    {
      key: 'edit-tag',
      label: '编辑标签',
      handler: 'editCurrentBrowseTag',
      disabled: !Number.isInteger(vm.currentBrowseTagId) || vm.tagMenuBusy || vm.tagFormSaving || vm.actionBusy,
    },
  ]
}

function buildTagBrowseInfo(tag, itemCount = 0) {
  if (!tag || !Number.isInteger(tag?.id)) {
    return null
  }

  const title = String(tag?.display_name || tag?.name || `#${tag.id}`)
  return {
    id: tag.id,
    public_id: String(tag?.public_id || ''),
    title,
    description: String(tag?.description || ''),
    name: String(tag?.name || ''),
    display_name: title,
    type: String(tag?.type || 'normal'),
    usage_count: Number(tag?.usage_count || 0),
    last_used_at: String(tag?.last_used_at || ''),
    metadata: tag?.metadata && typeof tag.metadata === 'object' ? tag.metadata : {},
    photo_count: Number(itemCount || 0),
  }
}

function getSearchQuery(vm) {
  return String(vm?.$route?.query?.q || '').trim()
}

function getSearchQuickHash(vm) {
  return String(vm?.$route?.query?.quick_hash || '').trim()
}

function buildSearchCrumbs(vm) {
  const rawQuery = getSearchQuery(vm)
  const quickHash = getSearchQuickHash(vm)
  const searchQuery = {}
  if (rawQuery) {
    searchQuery.q = rawQuery
  }
  if (quickHash) {
    searchQuery.quick_hash = quickHash
  }
  return [
    {
      label: '搜索',
      title: '搜索',
      to: rawQuery || quickHash ? { path: '/search', query: searchQuery } : '/search',
    },
    {
      label: vm.bcLabel(rawQuery || '搜索结果'),
      title: rawQuery || '搜索结果',
      current: true,
    },
  ]
}

function buildSearchBrowseInfo(rawQuery, resolvedMode, itemCount = 0) {
  return {
    title: rawQuery ? `搜索：${rawQuery}` : '搜索结果',
    description: rawQuery ? `模式：${formatSearchModeLabel(resolvedMode)} · ${Number(itemCount || 0)} 条结果` : '',
    photo_count: Number(itemCount || 0),
  }
}

function normalizeSearchItem(rawItem) {
  return normalizeCalendarItem({
    ...rawItem,
    type: 'image',
    full_filename: rawItem?.name || rawItem?.full_filename || '未命名',
    matched_tags: Array.isArray(rawItem?.matched_tags) ? rawItem.matched_tags : [],
    matched_by: Array.isArray(rawItem?.matched_by) ? rawItem.matched_by : [],
  })
}

function getGalleryScopeBasePath(contractName) {
  return contractName === 'gallery-all' ? '/gallery/all' : '/gallery/recent'
}

function buildGalleryAlbumRoute(contractName, albumPath) {
  const normalized = String(albumPath || '').replace(/\\/g, '/').trim()
  if (!normalized) return getGalleryScopeBasePath(contractName)
  const parts = normalized.split('/').filter(Boolean)
  if (parts.length < 2) return getGalleryScopeBasePath(contractName)
  const group = encodeURIComponent(parts[0])
  const nestedAlbumPath = parts.slice(1).map(segment => encodeURIComponent(segment)).join('/')
  return `${getGalleryScopeBasePath(contractName)}/${group}/${nestedAlbumPath}`
}

function buildGalleryCrumbs(vm, title) {
  const rootPath = getGalleryScopeBasePath(vm.pageContractName)
  const crumbs = [
    { label: '图库管理', title: '图库管理', to: '/gallery' },
  ]

  if (!vm.isAlbumMode) {
    crumbs.push({ label: title, title, current: true })
    return crumbs
  }

  crumbs.push({ label: title, title, to: rootPath })

  const segments = vm.albumPath.split('/').filter(Boolean)
  for (let index = 0; index < segments.length; index += 1) {
    const segment = segments[index]
    const isLast = index === segments.length - 1
    const ancestorTitle = vm.getAncestorTitle(index, segment)
    if (isLast) {
      crumbs.push({
        label: vm.bcLabel(vm.albumInfo?.title || segment),
        title: vm.albumInfo?.title || segment,
        current: true,
      })
      continue
    }
    crumbs.push({
      label: vm.bcLabel(ancestorTitle),
      title: ancestorTitle,
      to: `${rootPath}/${encodeURIComponent(vm.dateGroup)}/${segments.slice(0, index + 1).map(part => encodeURIComponent(part)).join('/')}`,
    })
  }

  return crumbs
}

function backFromGalleryScope(vm) {
  const rootPath = getGalleryScopeBasePath(vm.pageContractName)
  if (!vm.isAlbumMode) {
    vm.$router.push('/gallery')
    return
  }

  const segments = vm.albumPath.split('/').filter(Boolean)
  if (segments.length > 1) {
    const parentPath = segments.slice(0, -1).map(segment => encodeURIComponent(segment)).join('/')
    vm.$router.push(`${rootPath}/${encodeURIComponent(vm.dateGroup)}/${parentPath}`)
    return
  }

  vm.$router.push(rootPath)
}

function openGalleryScopedItem(vm, item) {
  if (!item) return
  if (item.type === 'album') {
    if (item.album_path) {
      vm.$router.push(buildGalleryAlbumRoute(vm.pageContractName, item.album_path))
    }
    return
  }
  openImageItem(item)
}

function openGalleryScopedPrimary(_vm, item) {
  if (!item) return
  if (item.type === 'album') {
    if (!item.album_path) return
    fetch(`${API_BASE}/api/albums/open-by-path/${encodeURI(item.album_path)}`).catch(() => {})
    return
  }
  openImageItem(item)
}

const calendarContract = {
  name: 'calendar',
  autoRepairMissingPreview: true,
  allowOriginalPreviewFallback: true,
  emptyState: {
    icon: '📂',
    text: '此页面尚无内容。',
  },
  defaultSort(vm) {
    return {
      sortBy: vm.isAlbumMode ? 'alpha' : 'date',
      sortDir: 'asc',
    }
  },
  buildCrumbs(vm) {
    return buildCalendarCrumbs(vm)
  },
  buildHeaderActions(vm) {
    return vm.canPickContainerCover ? [buildCoverHeaderAction(vm)] : []
  },
  buildSelectionActions(vm) {
    return buildCalendarLikeSelectionActions(vm)
  },
  buildDetailPolicy(vm) {
    return buildCalendarLikeDetailPolicy(vm)
  },
  async loadItems(vm) {
    const url = vm.isAlbumMode
      ? `${API_BASE}/api/albums/by-path/${encodeURI(vm.fullAlbumPath)}`
      : `${API_BASE}/api/dates/${vm.dateGroup}/items`
    const res = await fetch(url)
    if (!res.ok) {
      return { items: [], album: null }
    }
    const data = await res.json()
    return {
      items: Array.isArray(data?.items) ? data.items : [],
      album: data?.album || null,
    }
  },
  normalizeItems(rawItems) {
    return (rawItems || []).map(item => normalizeCalendarItem(item))
  },
  afterLoad(vm) {
    vm.ensureCategoryLabelsLoaded()
    if (vm.selectionInfoMode === 'tags') {
      vm.ensureTagLabelsLoaded()
    }
  },
  back(vm) {
    if (vm.isAlbumMode) {
      const segments = vm.albumPath.split('/').filter(Boolean)
      if (segments.length > 1) {
        const parentPath = segments.slice(0, -1).join('/')
        vm.$router.push(`/calendar/${vm.dateGroup}/${parentPath}`)
      } else {
        vm.$router.push(`/calendar/${vm.dateGroup}`)
      }
      return
    }
    vm.$router.push('/calendar')
  },
  openItem(vm, item) {
    if (!item) return
    if (item.type === 'album') {
      if (item.album_path) {
        vm.$router.push(`/calendar/${item.album_path}`)
      } else if (item.public_id) {
        const base = vm.isAlbumMode
          ? `/calendar/${vm.dateGroup}/${vm.albumPath}`
          : `/calendar/${vm.dateGroup}`
        vm.$router.push(`${base}/${encodeURIComponent(item.name)}`)
      }
      return
    }
    openImageItem(item)
  },
  openPrimary(vm, item) {
    if (!item) return
    if (item.type === 'album') {
      if (!item.album_path) return
      fetch(`${API_BASE}/api/albums/open-by-path/${encodeURI(item.album_path)}`).catch(() => {})
      return
    }
    this.openItem(vm, item)
  },
  async updateCover(vm, item) {
    if (!vm.isAlbumMode || !vm.albumInfo?.public_id || !Number.isInteger(item?.id)) {
      throw new Error('当前页面不支持设置封面')
    }

    const res = await fetch(`${API_BASE}/api/albums/${encodeURIComponent(vm.albumInfo.public_id)}/cover`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_id: item.id }),
    })
    if (!res.ok) {
      const payload = await res.json().catch(() => ({}))
      throw new Error(payload.detail || `HTTP ${res.status}`)
    }
    return res.json()
  },
  runSecondaryAction(vm) {
    vm.moveSelectedToTrash()
  },
  previewRepairPayloadKey: 'image_ids',
  async afterPreviewRepair(vm, repairIds) {
    await vm.refreshPreviewMetadata(repairIds)
  },
}

const collectionContract = {
  name: 'collection',
  autoRepairMissingPreview: true,
  allowOriginalPreviewFallback: true,
  emptyState: {
    icon: '☆',
    text: '当前收藏夹暂无可见图片。',
  },
  defaultSort() {
    return {
      sortBy: 'date',
      sortDir: 'asc',
    }
  },
  buildCrumbs(vm) {
    return buildCollectionCrumbs(vm)
  },
  buildHeaderActions(vm) {
    return vm.canPickContainerCover ? [buildCoverHeaderAction(vm)] : []
  },
  buildSelectionActions(vm) {
    return buildCalendarLikeSelectionActions(vm)
  },
  buildDetailPolicy(vm) {
    return buildCalendarLikeDetailPolicy(vm)
  },
  async loadItems(vm) {
    const res = await fetch(`${API_BASE}/api/collections/${encodeURIComponent(vm.collectionPublicId)}`)
    if (!res.ok) {
      return { items: [], album: null }
    }
    const data = await res.json()
    return {
      items: Array.isArray(data?.items) ? data.items : [],
      album: data?.collection || null,
    }
  },
  normalizeItems(rawItems) {
    return (rawItems || []).map(item => normalizeCollectionItem(item))
  },
  afterLoad(vm) {
    vm.ensureCategoryLabelsLoaded()
    if (vm.selectionInfoMode === 'tags') {
      vm.ensureTagLabelsLoaded()
    }
  },
  back(vm) {
    vm.$router.push('/favorites')
  },
  openItem(_vm, item) {
    openImageItem(item)
  },
  openPrimary(_vm, item) {
    openImageItem(item)
  },
  async updateCover(vm, item) {
    if (!vm.collectionPublicId || !Number.isInteger(item?.id)) {
      throw new Error('当前页面不支持设置封面')
    }

    const res = await fetch(`${API_BASE}/api/collections/${encodeURIComponent(vm.collectionPublicId)}/cover`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_id: item.id }),
    })
    if (!res.ok) {
      const payload = await res.json().catch(() => ({}))
      throw new Error(payload.detail || `HTTP ${res.status}`)
    }
    return res.json()
  },
  runSecondaryAction(vm) {
    vm.moveSelectedToTrash()
  },
  previewRepairPayloadKey: 'image_ids',
  async afterPreviewRepair(vm, repairIds) {
    await vm.refreshPreviewMetadata(repairIds)
  },
}

const tagContract = {
  name: 'tag',
  autoRepairMissingPreview: true,
  allowOriginalPreviewFallback: true,
  emptyState: {
    icon: '🏷',
    text: '当前标签下暂无可见图片。',
  },
  defaultSort() {
    return {
      sortBy: 'date',
      sortDir: 'desc',
    }
  },
  buildCrumbs(vm) {
    return buildTagCrumbs(vm)
  },
  buildHeaderActions(vm) {
    return buildTagHeaderActions(vm)
  },
  buildSelectionActions(vm) {
    return buildCalendarLikeSelectionActions(vm)
  },
  buildDetailPolicy(vm) {
    return buildCalendarLikeDetailPolicy(vm)
  },
  async loadItems(vm) {
    if (!Number.isInteger(vm.currentBrowseTagId)) {
      return { items: [], album: null }
    }

    const res = await fetch(`${API_BASE}/api/tags/${encodeURIComponent(vm.currentBrowseTagId)}/images`)
    if (!res.ok) {
      return { items: [], album: null }
    }

    const data = await res.json()
    const items = Array.isArray(data?.items) ? data.items : []
    return {
      items,
      album: buildTagBrowseInfo(data?.tag, items.length),
    }
  },
  normalizeItems(rawItems) {
    return (rawItems || []).map(item => normalizeCollectionItem(item))
  },
  afterLoad(vm) {
    vm.ensureCategoryLabelsLoaded()
    if (vm.selectionInfoMode === 'tags') {
      vm.ensureTagLabelsLoaded()
    }
  },
  back(vm) {
    vm.$router.push('/tags')
  },
  openItem(_vm, item) {
    openImageItem(item)
  },
  openPrimary(_vm, item) {
    openImageItem(item)
  },
  runSecondaryAction(vm) {
    vm.moveSelectedToTrash()
  },
  previewRepairPayloadKey: 'image_ids',
  async afterPreviewRepair(vm, repairIds) {
    await vm.refreshPreviewMetadata(repairIds)
  },
}

const galleryRecentContract = {
  name: 'gallery-recent',
  autoRepairMissingPreview: true,
  allowOriginalPreviewFallback: true,
  emptyState: {
    icon: '🕘',
    text: '最近导入为空。',
  },
  defaultSort(vm) {
    return {
      sortBy: vm.isAlbumMode ? 'alpha' : 'date',
      sortDir: 'asc',
    }
  },
  buildCrumbs(vm) {
    return buildGalleryCrumbs(vm, '最近导入')
  },
  buildHeaderActions() {
    return []
  },
  buildSelectionActions(vm) {
    return buildCalendarLikeSelectionActions(vm)
  },
  buildDetailPolicy(vm) {
    return buildCalendarLikeDetailPolicy(vm)
  },
  async loadItems(vm) {
    const url = vm.isAlbumMode
      ? `${API_BASE}/api/albums/by-path/${encodeURI(vm.fullAlbumPath)}`
      : `${API_BASE}/api/gallery/recent/items`
    const res = await fetch(url)
    if (!res.ok) {
      return { items: [], album: null }
    }
    const data = await res.json()
    return {
      items: Array.isArray(data?.items) ? data.items : [],
      album: data?.album || null,
    }
  },
  normalizeItems(rawItems) {
    return (rawItems || []).map(item => normalizeCalendarItem(item))
  },
  afterLoad(vm) {
    vm.ensureCategoryLabelsLoaded()
    if (vm.selectionInfoMode === 'tags') {
      vm.ensureTagLabelsLoaded()
    }
  },
  back(vm) {
    backFromGalleryScope(vm)
  },
  openItem(vm, item) {
    openGalleryScopedItem(vm, item)
  },
  openPrimary(vm, item) {
    openGalleryScopedPrimary(vm, item)
  },
  runSecondaryAction(vm) {
    vm.moveSelectedToTrash()
  },
  previewRepairPayloadKey: 'image_ids',
  async afterPreviewRepair(vm, repairIds) {
    await vm.refreshPreviewMetadata(repairIds)
  },
}

const searchResultsContract = {
  name: 'search-results',
  autoRepairMissingPreview: true,
  emptyState: {
    icon: '🔎',
    text: '当前搜索暂无结果。',
  },
  defaultSort() {
    return {
      sortBy: 'alpha',
      sortDir: 'asc',
    }
  },
  buildCrumbs(vm) {
    return buildSearchCrumbs(vm)
  },
  buildHeaderActions() {
    return []
  },
  buildSelectionActions(vm) {
    return buildCalendarLikeSelectionActions(vm)
  },
  buildDetailPolicy(vm) {
    return buildCalendarLikeDetailPolicy(vm)
  },
  async loadItems(vm) {
    const rawQuery = getSearchQuery(vm)
    const quickHash = getSearchQuickHash(vm)
    if (!rawQuery) {
      return {
        items: [],
        album: buildSearchBrowseInfo('', 'auto', 0),
      }
    }

    const { modeInfo, params } = buildSearchRequestParams(rawQuery, { quickHash })
    if (!modeInfo.normalizedQuery || modeInfo.validationError) {
      return {
        items: [],
        album: buildSearchBrowseInfo(rawQuery, modeInfo.mode, 0),
      }
    }

    params.set('limit', '0')
    const res = await fetch(`${API_BASE}/api/search/images?${params.toString()}`)
    if (!res.ok) {
      return {
        items: [],
        album: buildSearchBrowseInfo(rawQuery, modeInfo.mode, 0),
      }
    }

    const data = await res.json()
    const items = Array.isArray(data?.items) ? data.items : []
    return {
      items,
      album: buildSearchBrowseInfo(rawQuery, data?.resolved_mode || modeInfo.mode, Number(data?.total || items.length || 0)),
    }
  },
  normalizeItems(rawItems) {
    return (rawItems || []).map(item => normalizeSearchItem(item))
  },
  afterLoad(vm) {
    vm.ensureCategoryLabelsLoaded()
    if (vm.selectionInfoMode === 'tags') {
      vm.ensureTagLabelsLoaded()
    }
  },
  back(vm) {
    const rawQuery = getSearchQuery(vm)
    const quickHash = getSearchQuickHash(vm)
    const query = {}
    if (rawQuery) {
      query.q = rawQuery
    }
    if (quickHash) {
      query.quick_hash = quickHash
    }
    vm.$router.push({
      path: '/search',
      query,
    })
  },
  openItem(vm, item) {
    const index = vm.items.findIndex(candidate => candidate?.stable_key === item?.stable_key)
    if (index >= 0) {
      vm.onReservedDetailsClick(vm.items[index], index)
      return
    }
    openImageItem(item)
  },
  openPrimary(_vm, item) {
    openImageItem(item)
  },
  runSecondaryAction(vm) {
    vm.moveSelectedToTrash()
  },
  previewRepairPayloadKey: 'image_ids',
  async afterPreviewRepair(vm, repairIds) {
    await vm.refreshPreviewMetadata(repairIds)
  },
}

const galleryAllContract = {
  name: 'gallery-all',
  autoRepairMissingPreview: true,
  allowOriginalPreviewFallback: true,
  emptyState: {
    icon: '🖼',
    text: '图库中暂无可见内容。',
  },
  defaultSort(vm) {
    return {
      sortBy: vm.isAlbumMode ? 'alpha' : 'date',
      sortDir: 'asc',
    }
  },
  buildCrumbs(vm) {
    return buildGalleryCrumbs(vm, '图库总览')
  },
  buildHeaderActions() {
    return []
  },
  buildSelectionActions(vm) {
    return buildCalendarLikeSelectionActions(vm)
  },
  buildDetailPolicy(vm) {
    return buildCalendarLikeDetailPolicy(vm)
  },
  async loadItems(vm) {
    const url = vm.isAlbumMode
      ? `${API_BASE}/api/albums/by-path/${encodeURI(vm.fullAlbumPath)}`
      : `${API_BASE}/api/gallery/all/items`
    const res = await fetch(url)
    if (!res.ok) {
      return { items: [], album: null }
    }
    const data = await res.json()
    return {
      items: Array.isArray(data?.items) ? data.items : [],
      album: data?.album || null,
    }
  },
  normalizeItems(rawItems) {
    return (rawItems || []).map(item => normalizeCalendarItem(item))
  },
  afterLoad(vm) {
    vm.ensureCategoryLabelsLoaded()
    if (vm.selectionInfoMode === 'tags') {
      vm.ensureTagLabelsLoaded()
    }
  },
  back(vm) {
    backFromGalleryScope(vm)
  },
  openItem(vm, item) {
    openGalleryScopedItem(vm, item)
  },
  openPrimary(vm, item) {
    openGalleryScopedPrimary(vm, item)
  },
  runSecondaryAction(vm) {
    vm.moveSelectedToTrash()
  },
  previewRepairPayloadKey: 'image_ids',
  async afterPreviewRepair(vm, repairIds) {
    await vm.refreshPreviewMetadata(repairIds)
  },
}

const trashContract = {
  name: 'trash',
  emptyState: {
    icon: '🗑',
    text: '回收站为空。',
  },
  defaultSort() {
    return {
      sortBy: 'date',
      sortDir: 'desc',
    }
  },
  buildCrumbs() {
    return [{ label: '回收站', title: '回收站', current: true }]
  },
  buildHeaderActions(vm) {
    return [
      {
        key: 'clear-trash',
        label: '清空回收站',
        handler: 'clearTrash',
        className: 'browse-header__action browse-header__action--danger',
        disabled: vm.actionBusy || !vm.totalCount,
      },
    ]
  },
  buildSelectionActions(vm) {
    return [
      buildSelectionAction('details', '详情', 'openSelectionDetailsFromIsland', {
        disabled: !vm.selectedCount || vm.actionBusy,
      }),
      buildSelectionAction('restore', '还原', 'restoreSelection', {
        disabled: !vm.selectedCount || vm.actionBusy,
      }),
      buildSelectionAction('hard-delete', '删除', 'hardDeleteSelection', {
        className: 'selection-island__btn--danger',
        disabled: !vm.selectedCount || vm.actionBusy,
      }),
    ]
  },
  buildDetailPolicy(vm) {
    return {
      metadataPermissions: {
        name: false,
        category: false,
        tags: false,
        createdAt: false,
      },
      primaryActionLabel: '还原',
      primaryActionTone: 'accent',
      canOpenPrimaryAction: vm.selectedCount > 0 && !vm.actionBusy,
      primaryActionDisabled: vm.actionBusy,
      secondaryActionLabel: '删除',
      secondaryActionTone: 'danger',
      secondaryActionDisabled: vm.actionBusy,
    }
  },
  async loadItems() {
    const res = await fetch(`${API_BASE}/api/trash/items`)
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`)
    }
    const data = await res.json()
    return {
      items: Array.isArray(data?.items) ? data.items : [],
      album: null,
    }
  },
  normalizeItems(rawItems) {
    return (rawItems || []).map(item => normalizeTrashItem(item))
  },
  afterLoad(vm) {
    vm.ensureCategoryLabelsLoaded()
    vm.ensureTagLabelsLoaded()
    void vm.triggerSilentRepair()
  },
  back(vm) {
    if (typeof window !== 'undefined' && window.history.length > 1) {
      vm.$router.back()
      return
    }
    vm.$router.push('/settings')
  },
  openItem(vm, item) {
    const index = vm.items.findIndex(candidate => candidate?.stable_key === item?.stable_key)
    if (index >= 0) {
      vm.onReservedDetailsClick(vm.items[index], index)
    }
  },
  openPrimary(vm) {
    vm.restoreSelection()
  },
  runSecondaryAction(vm) {
    vm.hardDeleteSelection()
  },
  previewRepairPayloadKey: 'trash_entry_ids',
  async afterPreviewRepair(vm) {
    await vm.reloadContractItemsPreservingAnchor({
      preserveSelection: true,
      reopenDetails: vm.selectionDetailsOpen,
      runAfterLoad: false,
    })
  },
}

export function getCommonBrowsePageContract(contractName = 'calendar') {
  if (contractName === 'search-results') return searchResultsContract
  if (contractName === 'gallery-recent') return galleryRecentContract
  if (contractName === 'gallery-all') return galleryAllContract
  if (contractName === 'trash') return trashContract
  if (contractName === 'collection') return collectionContract
  if (contractName === 'tag') return tagContract
  return calendarContract
}

export function normalizeBrowseItems(rawItems, contractName = 'calendar') {
  return getCommonBrowsePageContract(contractName).normalizeItems(rawItems)
}