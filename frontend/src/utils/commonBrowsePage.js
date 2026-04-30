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

  return {
    ...rawItem,
    type,
    name,
    count: Number(rawItem?.count ?? rawItem?.photo_count ?? 0) || 0,
    sort_ts: Number(rawItem?.sort_ts) || toUnixSeconds(rawItem?.file_created_at || rawItem?.imported_at || rawItem?.created_at),
    stable_key: stableKey,
    layout_key: rawItem?.id || rawItem?.public_id || rawItem?.album_path || rawItem?.media_rel_path || stableKey,
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

  return {
    ...rawItem,
    type,
    name,
    public_id: type === 'album' ? (rawItem?.public_id || rawItem?.entry_key || String(rawItem?.id || '')) : rawItem?.public_id,
    count: Number(rawItem?.count ?? rawItem?.photo_count ?? 0) || 0,
    sort_ts: Number(rawItem?.sort_ts) || toUnixSeconds(rawItem?.file_created_at || rawItem?.imported_at || rawItem?.created_at),
    stable_key: stableKey,
    layout_key: rawItem?.entry_key || rawItem?.id || stableKey,
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

const calendarContract = {
  name: 'calendar',
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
  if (contractName === 'trash') return trashContract
  if (contractName === 'collection') return collectionContract
  return calendarContract
}

export function normalizeBrowseItems(rawItems, contractName = 'calendar') {
  return getCommonBrowsePageContract(contractName).normalizeItems(rawItems)
}