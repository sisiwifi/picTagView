<template>
  <div class="tag-chip-list" :class="{ 'tag-chip-list--compact': compact }">
    <span
      v-for="tag in sortedTags"
      :key="tag.id || tag.name"
      class="tag-chip"
      :style="chipStyle(tag)"
      :title="tag.name || ''"
    >
      {{ tag.display_name || tag.name || '' }}
    </span>
    <button
      v-if="showAddButton"
      class="tag-chip tag-chip--add"
      type="button"
      :disabled="addDisabled"
      title="添加标签"
      @click="$emit('add-click')"
    >
      +
    </button>
  </div>
</template>

<script>
function normalizeHexColor(input) {
  const raw = String(input || '').trim()
  if (!raw) return ''
  const withPrefix = raw.startsWith('#') ? raw : `#${raw}`
  const shortHex = /^#[0-9a-fA-F]{3}$/
  const longHex = /^#[0-9a-fA-F]{6}$/
  if (longHex.test(withPrefix)) return withPrefix
  if (!shortHex.test(withPrefix)) return ''
  const r = withPrefix[1]
  const g = withPrefix[2]
  const b = withPrefix[3]
  return `#${r}${r}${g}${g}${b}${b}`
}

function hexToRgba(hexColor, alpha = 0.4) {
  const normalized = normalizeHexColor(hexColor)
  if (!normalized) return 'rgba(100, 116, 139, 0.4)'
  const r = Number.parseInt(normalized.slice(1, 3), 16)
  const g = Number.parseInt(normalized.slice(3, 5), 16)
  const b = Number.parseInt(normalized.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

export default {
  name: 'TagChipList',
  emits: ['add-click'],
  props: {
    tags: {
      type: Array,
      default: () => [],
    },
    compact: {
      type: Boolean,
      default: true,
    },
    showAddButton: {
      type: Boolean,
      default: false,
    },
    addDisabled: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    sortedTags() {
      return [...this.tags].sort((left, right) => {
        const leftName = String(left?.name || '').toLowerCase()
        const rightName = String(right?.name || '').toLowerCase()
        return leftName.localeCompare(rightName)
      })
    },
  },
  methods: {
    chipStyle(tag) {
      const metadataColor = normalizeHexColor(tag?.color || '')
      const metadataBorderColor = normalizeHexColor(tag?.border_color || '')
      const metadataBackgroundColor = String(tag?.background_color || '').trim()

      const color = metadataColor || '#334155'
      const borderColor = metadataBorderColor || color
      const backgroundColor = metadataBackgroundColor || hexToRgba(color, 0.4)

      return {
        '--tag-chip-color': color,
        '--tag-chip-border-color': borderColor,
        '--tag-chip-bg': backgroundColor,
      }
    },
  },
}
</script>
