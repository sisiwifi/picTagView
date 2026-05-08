<template>
  <div class="tag-chip-list" :class="{ 'tag-chip-list--compact': compact }">
    <component
      v-for="tag in sortedTags"
      :key="tag.id || tag.name"
      :is="clickable ? 'button' : 'span'"
      class="tag-chip"
      :class="{ 'tag-chip--interactive': clickable }"
      :style="chipStyle(tag)"
      :title="tag.description || ''"
      :type="clickable ? 'button' : null"
      @click="handleTagClick(tag)"
    >
      {{ tag.display_name || tag.name || '' }}
    </component>
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
  emits: ['add-click', 'tag-click'],
  props: {
    tags: {
      type: Array,
      default: () => [],
    },
    clickable: {
      type: Boolean,
      default: false,
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
    handleTagClick(tag) {
      if (!this.clickable) return
      this.$emit('tag-click', tag)
    },
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
