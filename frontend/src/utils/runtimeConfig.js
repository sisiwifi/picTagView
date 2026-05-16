export const DEFAULT_API_BASE = 'http://127.0.0.1:8000'

export function resolveApiBase() {
  if (typeof window !== 'undefined') {
    const injectedBase = window.__PTV_API_BASE__
    if (typeof injectedBase === 'string' && injectedBase.trim()) {
      return injectedBase.trim().replace(/\/$/, '')
    }
  }

  return DEFAULT_API_BASE
}