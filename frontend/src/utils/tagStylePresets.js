export const TAG_STYLE_PRESETS = [
  { id: 'preset-red', label: '红色', borderColor: '#FF0000FF', backgroundColor: '#FF000066' },
  { id: 'preset-orange', label: '橙色', borderColor: '#FF6600FF', backgroundColor: '#FF660066' },
  { id: 'preset-yellow', label: '金黄', borderColor: '#C9A600FF', backgroundColor: '#FFFF0024' },
  { id: 'preset-green', label: '绿色', borderColor: '#00B84AFF', backgroundColor: '#00FF0029' },
  { id: 'preset-blue', label: '蓝色', borderColor: '#1E90FFFF', backgroundColor: '#1E90FF66' },
  { id: 'preset-purple', label: '紫色', borderColor: '#8A2BE2FF', backgroundColor: '#8A2BE266' },
  { id: 'preset-pink', label: '粉色', borderColor: '#FF1493FF', backgroundColor: '#FF149366' },
]

export function getTagStylePresetById(presetId) {
  const normalizedId = String(presetId || '')
  return TAG_STYLE_PRESETS.find(preset => preset.id === normalizedId) || TAG_STYLE_PRESETS[0]
}

export function getCycledTagStylePreset(index = 0) {
  if (!TAG_STYLE_PRESETS.length) return null
  const normalizedIndex = Number.isInteger(index) && index >= 0 ? index : 0
  return TAG_STYLE_PRESETS[normalizedIndex % TAG_STYLE_PRESETS.length]
}

export function buildTagStyleMetadata(presetId, metadata = null) {
  const preset = getTagStylePresetById(presetId)
  const sourceMetadata = metadata && typeof metadata === 'object' && !Array.isArray(metadata) ? metadata : {}
  return {
    schema_version: Number.isInteger(sourceMetadata.schema_version) ? sourceMetadata.schema_version : 1,
    created_via: typeof sourceMetadata.created_via === 'string' && sourceMetadata.created_via.trim() ? sourceMetadata.created_via.trim() : 'manual',
    ui_hint: sourceMetadata.ui_hint && typeof sourceMetadata.ui_hint === 'object' && !Array.isArray(sourceMetadata.ui_hint) ? { ...sourceMetadata.ui_hint } : {},
    notes: typeof sourceMetadata.notes === 'string' ? sourceMetadata.notes : '',
    color: preset.borderColor,
    border_color: preset.borderColor,
    background_color: preset.backgroundColor,
  }
}