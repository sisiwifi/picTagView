export const API_BASE = 'http://127.0.0.1:8000'

export const TOP_LEVEL_PAGE_STANDARD = Object.freeze({
  thumbEdgePx: 400,
  searchDebounceMs: 260,
  searchResultLimit: 120,
})

export const TOP_LEVEL_NAV_ITEMS = Object.freeze([
  { path: '/', label: '主页', icon: '🏠' },
  { path: '/search', label: '搜索', icon: '🔎', matchPrefixes: ['/search/results'] },
  { path: '/tags', label: '标签总览', icon: '🏷️', matchPrefixes: ['/tags/'] },
  { path: '/gallery', label: '图库管理', icon: '🖼️', matchPrefixes: ['/gallery/'] },
  { path: '/calendar', label: '日期视图', icon: '📅', matchPrefixes: ['/calendar/'] },
  { path: '/favorites', label: '收藏', icon: '⭐', matchPrefixes: ['/favorites/'] },
  { path: '/settings', label: '设置', icon: '⚙️', matchPrefixes: ['/settings/'] },
])

const SEARCH_TAG_PREFIX = /^tag\s*:/i
const SEARCH_FILENAME_PREFIX = /^name\s*:/i
const SEARCH_FILE_PREFIX = /^file\s*:/i
const SEARCH_IMPORTED_PREFIX = /^import\s*:/i
const SEARCH_CREATED_PREFIX = /^create\s*:/i
const DATETIME_RANGE_SEPARATOR = '~'
const DATETIME_TEXT_RE = /^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})$/

function padDateSegment(value) {
  return String(value).padStart(2, '0')
}

function toIsoLikeDateTime(date) {
  return [
    `${date.getFullYear()}-${padDateSegment(date.getMonth() + 1)}-${padDateSegment(date.getDate())}`,
    `${padDateSegment(date.getHours())}:${padDateSegment(date.getMinutes())}:${padDateSegment(date.getSeconds())}`,
  ].join(' ')
}

function toLocalIsoParameter(date) {
  return [
    `${date.getFullYear()}-${padDateSegment(date.getMonth() + 1)}-${padDateSegment(date.getDate())}`,
    `${padDateSegment(date.getHours())}:${padDateSegment(date.getMinutes())}:${padDateSegment(date.getSeconds())}`,
  ].join('T')
}

function parseDateTimeText(rawValue) {
  const normalized = String(rawValue || '').trim()
  const matched = DATETIME_TEXT_RE.exec(normalized)
  if (!matched) return null

  const [, yearText, monthText, dayText, hourText, minuteText, secondText] = matched
  const year = Number(yearText)
  const month = Number(monthText)
  const day = Number(dayText)
  const hour = Number(hourText)
  const minute = Number(minuteText)
  const second = Number(secondText)
  const date = new Date(year, month - 1, day, hour, minute, second)
  if (
    Number.isNaN(date.getTime())
    || date.getFullYear() !== year
    || date.getMonth() !== month - 1
    || date.getDate() !== day
    || date.getHours() !== hour
    || date.getMinutes() !== minute
    || date.getSeconds() !== second
  ) {
    return null
  }
  return date
}

function buildTimeModeResult(mode, queryText, hint, extra = {}) {
  return {
    mode,
    normalizedQuery: queryText,
    canonicalQuery: queryText,
    hint,
    validationError: '',
    quickHash: String(extra.quickHash || '').trim(),
    startAt: extra.startAt || '',
    endAt: extra.endAt || '',
    timeField: extra.timeField || '',
    displayToken: extra.displayToken || '',
  }
}

function parseTimeRangeMode(mode, rawText) {
  const timeField = mode === 'imported_at' ? 'imported_at' : 'file_created_at'
  const hint = mode === 'imported_at' ? '按导入时间范围搜索' : '按创建时间范围搜索'
  const normalized = String(rawText || '').trim()
  const segments = normalized.split(DATETIME_RANGE_SEPARATOR).map(segment => segment.trim())
  if (segments.length !== 2 || !segments[0] || !segments[1]) {
    return {
      ...buildTimeModeResult(mode, normalized, hint, { timeField }),
      validationError: '时间范围格式应为 YYYY-MM-DD HH:mm:ss~YYYY-MM-DD HH:mm:ss',
    }
  }

  const startDate = parseDateTimeText(segments[0])
  const endDate = parseDateTimeText(segments[1])
  if (!startDate || !endDate) {
    return {
      ...buildTimeModeResult(mode, normalized, hint, { timeField }),
      validationError: '时间范围格式应为 YYYY-MM-DD HH:mm:ss~YYYY-MM-DD HH:mm:ss',
    }
  }
  if (startDate.getTime() > endDate.getTime()) {
    return {
      ...buildTimeModeResult(mode, normalized, hint, { timeField }),
      validationError: '时间范围起点不能晚于终点',
    }
  }

  const startAt = toLocalIsoParameter(startDate)
  const endAt = toLocalIsoParameter(endDate)
  const canonicalRange = `${toIsoLikeDateTime(startDate)}${DATETIME_RANGE_SEPARATOR}${toIsoLikeDateTime(endDate)}`
  return buildTimeModeResult(mode, canonicalRange, hint, {
    startAt,
    endAt,
    timeField,
  })
}

function buildFileModeResult(rawValue, options = {}) {
  const normalizedQuery = String(rawValue || '').replace(SEARCH_FILE_PREFIX, '').trim()
  const quickHash = String(options?.quickHash || '').trim()
  return {
    mode: 'file',
    normalizedQuery,
    canonicalQuery: normalizedQuery ? `file:${normalizedQuery}` : 'file:',
    hint: '按所选文件的 Quick Hash 搜索',
    validationError: quickHash ? '' : '文件搜索需要先点击相机按钮选择一张本地图片。',
    quickHash,
    startAt: '',
    endAt: '',
    timeField: '',
    displayToken: normalizedQuery,
  }
}

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

export function detectSearchMode(rawValue, options = {}) {
  const value = String(rawValue || '').trim()
  if (!value) {
    return {
      mode: 'auto',
      normalizedQuery: '',
      canonicalQuery: '',
      hint: '输入文件名、Tag、文件或时间范围',
      validationError: '',
      quickHash: '',
      startAt: '',
      endAt: '',
      timeField: '',
      displayToken: '',
    }
  }

  if (SEARCH_FILENAME_PREFIX.test(value)) {
    return {
      mode: 'filename',
      normalizedQuery: value.replace(SEARCH_FILENAME_PREFIX, '').trim(),
      canonicalQuery: `name:${value.replace(SEARCH_FILENAME_PREFIX, '').trim()}`,
      hint: '仅按文件名搜索',
      validationError: '',
      quickHash: '',
      startAt: '',
      endAt: '',
      timeField: '',
      displayToken: '',
    }
  }

  if (value.startsWith('$')) {
    return {
      mode: 'filename',
      normalizedQuery: value.slice(1).trim(),
      canonicalQuery: `name:${value.slice(1).trim()}`,
      hint: '仅按文件名搜索',
      validationError: '',
      quickHash: '',
      startAt: '',
      endAt: '',
      timeField: '',
      displayToken: '',
    }
  }

  if (SEARCH_TAG_PREFIX.test(value)) {
    return {
      mode: 'tag',
      normalizedQuery: value.replace(SEARCH_TAG_PREFIX, '').trim(),
      canonicalQuery: `tag:${value.replace(SEARCH_TAG_PREFIX, '').trim()}`,
      hint: '按 Tag 搜索',
      validationError: '',
      quickHash: '',
      startAt: '',
      endAt: '',
      timeField: '',
      displayToken: '',
    }
  }

  if (value.startsWith('#')) {
    return {
      mode: 'tag',
      normalizedQuery: value.slice(1).trim(),
      canonicalQuery: `tag:${value.slice(1).trim()}`,
      hint: '按 Tag 搜索',
      validationError: '',
      quickHash: '',
      startAt: '',
      endAt: '',
      timeField: '',
      displayToken: '',
    }
  }

  if (SEARCH_FILE_PREFIX.test(value)) {
    return buildFileModeResult(value, options)
  }

  if (SEARCH_IMPORTED_PREFIX.test(value)) {
    return parseTimeRangeMode('imported_at', value.replace(SEARCH_IMPORTED_PREFIX, '').trim())
  }

  if (SEARCH_CREATED_PREFIX.test(value)) {
    return parseTimeRangeMode('file_created_at', value.replace(SEARCH_CREATED_PREFIX, '').trim())
  }

  return {
    mode: 'auto',
    normalizedQuery: value,
    canonicalQuery: value,
    hint: '默认同时匹配文件名与 Tag',
    validationError: '',
    quickHash: '',
    startAt: '',
    endAt: '',
    timeField: '',
    displayToken: '',
  }
}

export function buildSearchRequestParams(rawValue, options = {}) {
  const modeInfo = detectSearchMode(rawValue, options)
  const params = new URLSearchParams()
  if (modeInfo.normalizedQuery) {
    params.set('q', modeInfo.normalizedQuery)
  }
  if (modeInfo.mode) {
    params.set('mode', modeInfo.mode)
  }
  if (modeInfo.quickHash) {
    params.set('quick_hash', modeInfo.quickHash)
  }
  if (modeInfo.startAt) {
    params.set('start_at', modeInfo.startAt)
  }
  if (modeInfo.endAt) {
    params.set('end_at', modeInfo.endAt)
  }
  return { modeInfo, params }
}

export function formatSearchDateTime(value) {
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return toIsoLikeDateTime(date)
}

export function buildTimeRangeQuery(fieldType, startValue, endValue) {
  const mode = fieldType === 'file_created_at' ? 'create' : 'import'
  const startText = formatSearchDateTime(startValue)
  const endText = formatSearchDateTime(endValue)
  if (!startText || !endText) return ''
  return `${mode}:${startText}${DATETIME_RANGE_SEPARATOR}${endText}`
}

export function formatSearchModeLabel(mode) {
  switch (mode) {
    case 'file':
      return '本地文件 / Quick Hash'
    case 'filename':
      return '文件名'
    case 'imported_at':
      return '导入时间'
    case 'file_created_at':
      return '创建时间'
    case 'tag':
      return 'Tag'
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
    case 'imported_at':
      return '导入时间'
    case 'file_created_at':
      return '创建时间'
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

export function buildBrowseLocation(mediaRelPath, options = {}) {
  const normalized = String(mediaRelPath || '').replace(/\\/g, '/').trim()
  if (!normalized) return null

  const parts = normalized.split('/').filter(Boolean)
  if (parts.length < 3 || parts[0] !== 'media') {
    return null
  }

  const group = encodeURIComponent(parts[1])
  const albumSegments = parts.slice(2, -1).map(segment => encodeURIComponent(segment))
  const query = {}
  const focusId = Number(options?.focusId)
  if (Number.isInteger(focusId) && focusId > 0) {
    query.focus = String(focusId)
  }
  if (normalized) {
    query.focusPath = normalized
  }
  if (!albumSegments.length) {
    return Object.keys(query).length
      ? { path: `/calendar/${group}`, query }
      : `/calendar/${group}`
  }
  const path = `/calendar/${group}/${albumSegments.join('/')}`
  return Object.keys(query).length ? { path, query } : path
}

export function shortenQuickHash(value) {
  const normalized = String(value || '').trim()
  if (!normalized) return ''
  if (normalized.length <= 14) return normalized
  return `${normalized.slice(0, 8)}...${normalized.slice(-4)}`
}