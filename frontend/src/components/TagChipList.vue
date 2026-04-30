<template>
  <div class="tag-chip-list" :class="{ 'tag-chip-list--compact': compact }">
    <span
      v-for="tag in sortedTags"
      :key="tag.id || tag.name"
      class="tag-chip"
      :style="chipStyle(tag)"
      :title="tag.description || ''"
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
import { normalizeTagColors } from '../utils/tagColors'

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
      const { color, borderColor, backgroundColor } = normalizeTagColors(tag)

      return {
        '--tag-chip-color': color,
        '--tag-chip-border-color': borderColor,
        '--tag-chip-bg': backgroundColor,
      }
    },
  },
}
</script>
