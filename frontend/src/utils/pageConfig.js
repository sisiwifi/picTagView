const API_BASE = 'http://127.0.0.1:8000'
const STORAGE_KEY = 'ptv.pageConfig'

export const PAGE_CONFIG_UPDATED_EVENT = 'ptv:page-config-updated'
export const PAGE_BROWSE_MODE_SCROLL = 'scroll'
export const PAGE_BROWSE_MODE_PAGED = 'paged'
export const PAGE_SCROLL_WINDOW_OPTIONS = Object.freeze([40, 60, 80, 100, 120, 140, 160, 180, 200])

export const DEFAULT_PAGE_CONFIG = Object.freeze({
  browseMode: PAGE_BROWSE_MODE_SCROLL,
  scrollWindowSize: 100,
})

function normalizeBrowseMode(value) {
  return value === PAGE_BROWSE_MODE_PAGED ? PAGE_BROWSE_MODE_PAGED : PAGE_BROWSE_MODE_SCROLL
}

function normalizeScrollWindowSize(value) {
  const numericValue = Number.parseInt(String(value ?? ''), 10)
  if (PAGE_SCROLL_WINDOW_OPTIONS.includes(numericValue)) {
    return numericValue
  }
  return DEFAULT_PAGE_CONFIG.scrollWindowSize
}

export function normalizePageConfig(rawConfig) {
  const browseMode = normalizeBrowseMode(
    rawConfig?.browse_mode || rawConfig?.browseMode || DEFAULT_PAGE_CONFIG.browseMode,
  )
  const scrollWindowSize = normalizeScrollWindowSize(
    rawConfig?.scroll_window_size || rawConfig?.scrollWindowSize || DEFAULT_PAGE_CONFIG.scrollWindowSize,
  )

  return {
    browseMode,
    scrollWindowSize,
  }
}

function writeCachedPageConfig(config) {
  if (typeof window === 'undefined' || !window.localStorage) return
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
  } catch {
    // ignore local cache persistence failures
  }
}

function dispatchPageConfigUpdated(config) {
  if (typeof window === 'undefined' || typeof window.dispatchEvent !== 'function') return
  window.dispatchEvent(new CustomEvent(PAGE_CONFIG_UPDATED_EVENT, { detail: config }))
}

export function getCachedPageConfig() {
  if (typeof window === 'undefined' || !window.localStorage) {
    return { ...DEFAULT_PAGE_CONFIG }
  }

  try {
    const rawText = window.localStorage.getItem(STORAGE_KEY)
    if (!rawText) return { ...DEFAULT_PAGE_CONFIG }
    return normalizePageConfig(JSON.parse(rawText))
  } catch {
    return { ...DEFAULT_PAGE_CONFIG }
  }
}

export async function fetchPageConfig() {
  const res = await fetch(`${API_BASE}/api/system/page-config`)
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`)
  }

  const config = normalizePageConfig(await res.json())
  writeCachedPageConfig(config)
  return config
}

export async function savePageConfig(nextConfig) {
  const normalized = normalizePageConfig(nextConfig)
  const res = await fetch(`${API_BASE}/api/system/page-config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      browse_mode: normalized.browseMode,
      scroll_window_size: normalized.scrollWindowSize,
    }),
  })

  if (!res.ok) {
    const payload = await res.json().catch(() => ({}))
    throw new Error(payload.detail || `HTTP ${res.status}`)
  }

  const savedConfig = normalizePageConfig(await res.json())
  writeCachedPageConfig(savedConfig)
  dispatchPageConfigUpdated(savedConfig)
  return savedConfig
}
