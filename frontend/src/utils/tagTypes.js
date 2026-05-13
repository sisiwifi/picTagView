export const TAG_TYPE_OPTIONS = [
  { value: 'normal', label: '普通标签' },
  { value: 'artist', label: '作者标签' },
  { value: 'copyright', label: '作品标签' },
  { value: 'character', label: '角色标签' },
  { value: 'series', label: '系列标签' },
]

export function isValidTagType(value) {
  const normalizedValue = String(value || '').trim().toLowerCase()
  return TAG_TYPE_OPTIONS.some(option => option.value === normalizedValue)
}

export function normalizeTagTypeValue(value, fallback = 'normal') {
  const normalizedValue = String(value || '').trim().toLowerCase()
  if (isValidTagType(normalizedValue)) {
    return normalizedValue
  }
  return String(fallback || 'normal').trim().toLowerCase() || 'normal'
}

export function getTagTypeOption(value) {
  const normalizedValue = normalizeTagTypeValue(value)
  return TAG_TYPE_OPTIONS.find(option => option.value === normalizedValue) || TAG_TYPE_OPTIONS[0]
}

export function getTagTypeLabel(value) {
  return getTagTypeOption(value).label
}