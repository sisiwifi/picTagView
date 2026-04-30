export const API_BASE = 'http://127.0.0.1:8000'

export const TOP_LEVEL_PAGE_STANDARD = Object.freeze({
  thumbEdgePx: 400,
  searchDebounceMs: 260,
  searchResultLimit: 120,
})

export const TOP_LEVEL_NAV_ITEMS = Object.freeze([
  { path: '/', label: '主页', icon: '🏠' },
  { path: '/search', label: '搜索', icon: '🔎' },
  { path: '/tags', label: '标签总览', icon: '🏷️' },
  { path: '/gallery', label: '图库管理', icon: '🖼️' },
  { path: '/calendar', label: '日期视图', icon: '📅', matchPrefixes: ['/calendar/'] },
  { path: '/favorites', label: '收藏', icon: '⭐' },
  { path: '/settings', label: '设置', icon: '⚙️', matchPrefixes: ['/settings/'] },
])

const SEARCH_PATH_PREFIX = /^path\s*:/i
const SEARCH_TAG_PREFIX = /^tag\s*:/i
const IMAGE_SUFFIX_RE = /\.(jpg|jpeg|png|webp|gif|bmp|tif|tiff|avif)$/i

export function topLevelPageVars() {
  return {
    '--top-level-thumb-edge': `${TOP_LEVEL_PAGE_STANDARD.thumbEdgePx}px`,
  }
}

export function isTopLevelRouteActive(currentPath, targetPath) {
  const item = TOP_LEVEL_NAV_ITEMS.find(entry => entry.path === targetPath)
  if (!item) {
    return currentPath === targetPath
  }
  if (currentPath === item.path) {
    return true
  }
  return Array.isArray(item.matchPrefixes)
    ? item.matchPrefixes.some(prefix => currentPath.startsWith(prefix))
    : false
}

export function detectSearchMode(rawValue) {
  const value = String(rawValue || '').trim()
  if (!value) {
    return { mode: 'auto', normalizedQuery: '', hint: '输入文件名、tag 或图片路径' }
  }

  if (SEARCH_TAG_PREFIX.test(value)) {
    return {
      mode: 'tag',
      normalizedQuery: value.replace(SEARCH_TAG_PREFIX, '').trim(),
      hint: '按 Tag 搜索',
    }
  }

  if (SEARCH_PATH_PREFIX.test(value)) {
    return {
      mode: 'path',
      normalizedQuery: value.replace(SEARCH_PATH_PREFIX, '').trim(),
      hint: '按图片路径解析 quick hash 搜索',
    }
  }

  if (value.startsWith('#')) {
    return {
      mode: 'tag',
      normalizedQuery: value.slice(1).trim(),
      hint: '按 Tag 搜索',
    }
  }

  const normalizedPath = String(value).replace(/\\/g, '/').trim()
  if (normalizedPath.startsWith('media/') || normalizedPath.toLowerCase().includes('/media/') || (normalizedPath.includes('/') && IMAGE_SUFFIX_RE.test(normalizedPath))) {
    return {
      mode: 'path',
      normalizedQuery: normalizedPath,
      hint: '按图片路径解析 quick hash 搜索',
    }
  }

  return {
    mode: 'auto',
    normalizedQuery: value,
    hint: '默认同时匹配文件名与 Tag',
  }
}

export function formatSearchModeLabel(mode) {
  switch (mode) {
    case 'filename':
      return '文件名'
    case 'tag':
      return 'Tag'
    case 'path':
      return '路径 / Quick Hash'
    case 'mixed':
    case 'auto':
    default:
      return '文件名 / Tag'
  }
}

export function formatMatchedByLabel(value) {
  switch (value) {
    case 'filename':
      return '文件名'
    case 'tag':
      return 'Tag'
    case 'quick_hash':
      return 'Quick Hash'
    case 'path':
      return '源路径'
    default:
      return value || '匹配'
  }
}

export function resolvePreviewUrl(item) {
  if (!item) return ''
  if (item.cache_thumb_url) return `${API_BASE}${item.cache_thumb_url}`
  if (item.thumb_url) return `${API_BASE}${item.thumb_url}`
  return ''
}

export function buildOriginalMediaUrl(mediaRelPath) {
  if (!mediaRelPath) return ''
  const normalized = String(mediaRelPath).replace(/^\/+/, '')
  return `${API_BASE}/${normalized}`
}

export function buildBrowseLocation(mediaRelPath) {
  const normalized = String(mediaRelPath || '').replace(/\\/g, '/').trim()
  if (!normalized) return null

  const parts = normalized.split('/').filter(Boolean)
  if (parts.length < 3 || parts[0] !== 'media') {
    return null
  }

  const group = encodeURIComponent(parts[1])
  const albumSegments = parts.slice(2, -1).map(segment => encodeURIComponent(segment))
  if (!albumSegments.length) {
    return `/calendar/${group}`
  }
  return `/calendar/${group}/${albumSegments.join('/')}`
}

export function shortenQuickHash(value) {
  const normalized = String(value || '').trim()
  if (!normalized) return ''
  if (normalized.length <= 14) return normalized
  return `${normalized.slice(0, 8)}...${normalized.slice(-4)}`
}