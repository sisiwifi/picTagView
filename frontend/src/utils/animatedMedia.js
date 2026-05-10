function normalizeFrameCount(value) {
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed < 1) return 1
  return Math.max(1, Math.floor(parsed))
}

function resolveRawAnimationMeta(rawItem) {
  if (rawItem?.animation_meta && typeof rawItem.animation_meta === 'object') {
    return rawItem.animation_meta
  }
  if (rawItem?.frame_count != null || rawItem?.animation_format) {
    return {
      frame_count: rawItem?.frame_count,
      format: rawItem?.animation_format,
    }
  }
  return null
}

export function normalizeAnimationFormat(value) {
  const normalized = String(value || '').trim().toUpperCase()
  return normalized || ''
}

export function normalizeAnimatedFields(rawItem) {
  const rawAnimationMeta = resolveRawAnimationMeta(rawItem)
  const frameCount = normalizeFrameCount(rawAnimationMeta?.frame_count ?? rawItem?.frame_count)
  const isAnimated = Boolean(rawItem?.is_animated) || frameCount > 1
  const animationFormat = isAnimated
    ? normalizeAnimationFormat(rawAnimationMeta?.format ?? rawAnimationMeta?.animation_format ?? rawItem?.animation_format)
    : ''
  const animationMeta = isAnimated
    ? {
        frame_count: frameCount,
        format: animationFormat || null,
      }
    : null
  return {
    is_animated: isAnimated,
    animation_meta: animationMeta,
    frame_count: isAnimated ? frameCount : 1,
    animation_format: animationFormat,
  }
}

export function resolveAnimatedBadgeLabel(rawItem) {
  const { is_animated: isAnimated, animation_format: animationFormat } = normalizeAnimatedFields(rawItem)
  if (!isAnimated) return ''
  if (animationFormat === 'GIF' || animationFormat === 'WEBP') {
    return animationFormat
  }
  return ''
}