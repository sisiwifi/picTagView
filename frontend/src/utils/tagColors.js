const HEX_PATTERN = /^#?(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/
const RGBA_PATTERN = /^rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})(?:\s*,\s*([0-9]*\.?[0-9]+))?\s*\)$/i

export function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

function expandShortHex(value) {
  return value
    .split('')
    .map(component => `${component}${component}`)
    .join('')
}

function normalizeAlphaByte(value) {
  if (typeof value === 'string' && /^[0-9a-fA-F]{2}$/.test(value.trim())) {
    return value.trim().toUpperCase()
  }
  const numberValue = Number(value)
  if (!Number.isFinite(numberValue)) return 'FF'
  return clamp(Math.round(numberValue), 0, 255).toString(16).padStart(2, '0').toUpperCase()
}

function parseRgbMatch(value) {
  const matched = RGBA_PATTERN.exec(String(value || '').trim())
  if (!matched) return ''
  const red = clamp(Number(matched[1]), 0, 255)
  const green = clamp(Number(matched[2]), 0, 255)
  const blue = clamp(Number(matched[3]), 0, 255)
  const alphaRaw = matched[4] == null ? 1 : Number(matched[4])
  const alpha = clamp(Number.isFinite(alphaRaw) ? alphaRaw : 1, 0, 1)
  return `#${red.toString(16).padStart(2, '0')}${green.toString(16).padStart(2, '0')}${blue.toString(16).padStart(2, '0')}${Math.round(alpha * 255).toString(16).padStart(2, '0')}`.toUpperCase()
}

export function tryNormalizeHex8(value, options = {}) {
  const { defaultAlpha = 'FF' } = options
  const raw = String(value || '').trim()
  if (!raw) {
    return { valid: true, value: '' }
  }

  const rgbaHex = parseRgbMatch(raw)
  if (rgbaHex) {
    return { valid: true, value: rgbaHex }
  }

  if (!HEX_PATTERN.test(raw)) {
    return { valid: false, value: '' }
  }

  const hex = raw.startsWith('#') ? raw.slice(1) : raw
  let expanded = ''
  if (hex.length === 3) {
    expanded = `${expandShortHex(hex)}${normalizeAlphaByte(defaultAlpha)}`
  } else if (hex.length === 4) {
    expanded = expandShortHex(hex)
  } else if (hex.length === 6) {
    expanded = `${hex}${normalizeAlphaByte(defaultAlpha)}`
  } else {
    expanded = hex
  }

  return { valid: true, value: `#${expanded}`.toUpperCase() }
}

export function normalizeHex8(value, options = {}) {
  return tryNormalizeHex8(value, options).value
}

export function parseHex8(value, options = {}) {
  const { fallback = '#64748BFF', defaultAlpha = 'FF' } = options
  const normalized = normalizeHex8(value, { defaultAlpha }) || normalizeHex8(fallback, { defaultAlpha: 'FF' })
  return {
    hex: normalized,
    red: Number.parseInt(normalized.slice(1, 3), 16),
    green: Number.parseInt(normalized.slice(3, 5), 16),
    blue: Number.parseInt(normalized.slice(5, 7), 16),
    alpha: Number.parseInt(normalized.slice(7, 9), 16),
  }
}

export function rgbHex(value, options = {}) {
  const normalized = normalizeHex8(value, options)
  return normalized ? normalized.slice(0, 7) : ''
}

export function withAlpha(value, alphaValue, options = {}) {
  const normalized = normalizeHex8(value, { defaultAlpha: 'FF', ...options })
  if (!normalized) return ''
  return `${normalized.slice(0, 7)}${normalizeAlphaByte(alphaValue)}`
}

export function isSameRgb(left, right) {
  const leftRgb = rgbHex(left)
  const rightRgb = rgbHex(right)
  return Boolean(leftRgb && rightRgb && leftRgb === rightRgb)
}

export function alphaByteToPercent(alphaByte) {
  const numeric = clamp(Number(alphaByte), 0, 255)
  return Math.round((numeric / 255) * 100)
}

export function percentToAlphaByte(percent) {
  const numeric = clamp(Number(percent), 0, 100)
  return Math.round((numeric / 100) * 255)
}

export function rgbToHsv(red, green, blue) {
  const r = clamp(Number(red), 0, 255) / 255
  const g = clamp(Number(green), 0, 255) / 255
  const b = clamp(Number(blue), 0, 255) / 255
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  const delta = max - min

  let hue = 0
  if (delta !== 0) {
    if (max === r) {
      hue = 60 * (((g - b) / delta) % 6)
    } else if (max === g) {
      hue = 60 * (((b - r) / delta) + 2)
    } else {
      hue = 60 * (((r - g) / delta) + 4)
    }
  }
  if (hue < 0) hue += 360

  const saturation = max === 0 ? 0 : (delta / max) * 100
  const value = max * 100
  return {
    hue,
    saturation,
    value,
  }
}

export function hsvToRgb(hue, saturation, value) {
  const normalizedHue = ((Number(hue) % 360) + 360) % 360
  const normalizedSaturation = clamp(Number(saturation), 0, 100) / 100
  const normalizedValue = clamp(Number(value), 0, 100) / 100
  const chroma = normalizedValue * normalizedSaturation
  const x = chroma * (1 - Math.abs(((normalizedHue / 60) % 2) - 1))
  const match = normalizedValue - chroma

  let red = 0
  let green = 0
  let blue = 0

  if (normalizedHue < 60) {
    red = chroma
    green = x
  } else if (normalizedHue < 120) {
    red = x
    green = chroma
  } else if (normalizedHue < 180) {
    green = chroma
    blue = x
  } else if (normalizedHue < 240) {
    green = x
    blue = chroma
  } else if (normalizedHue < 300) {
    red = x
    blue = chroma
  } else {
    red = chroma
    blue = x
  }

  return {
    red: Math.round((red + match) * 255),
    green: Math.round((green + match) * 255),
    blue: Math.round((blue + match) * 255),
  }
}

export function hex8ToHsv(value, options = {}) {
  const { red, green, blue, alpha, hex } = parseHex8(value, options)
  const hsv = rgbToHsv(red, green, blue)
  return {
    ...hsv,
    alpha,
    hex,
  }
}

export function hsvToHex8(hue, saturation, value, alpha = 255) {
  const { red, green, blue } = hsvToRgb(hue, saturation, value)
  return `#${red.toString(16).padStart(2, '0')}${green.toString(16).padStart(2, '0')}${blue.toString(16).padStart(2, '0')}${normalizeAlphaByte(alpha)}`.toUpperCase()
}

export function normalizeTagColors(rawTag, options = {}) {
  const { fallbackColor = '#334155FF', fallbackBackgroundAlpha = '66' } = options
  const metadata = rawTag?.metadata && typeof rawTag.metadata === 'object' ? rawTag.metadata : {}
  const color = normalizeHex8(
    typeof rawTag?.color === 'string' ? rawTag.color : (typeof metadata.color === 'string' ? metadata.color : ''),
    { defaultAlpha: 'FF' }
  ) || normalizeHex8(fallbackColor, { defaultAlpha: 'FF' })
  const borderColor = normalizeHex8(
    typeof rawTag?.border_color === 'string' ? rawTag.border_color : (typeof metadata.border_color === 'string' ? metadata.border_color : ''),
    { defaultAlpha: 'FF' }
  ) || color
  const backgroundColor = normalizeHex8(
    typeof rawTag?.background_color === 'string' ? rawTag.background_color : (typeof metadata.background_color === 'string' ? metadata.background_color : ''),
    { defaultAlpha: 'FF' }
  ) || withAlpha(borderColor, fallbackBackgroundAlpha)

  return {
    color,
    borderColor,
    backgroundColor,
  }
}