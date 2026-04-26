<template>
  <div v-if="normalizedTotalPages > 1 || showPageSizeSelector" class="page-pagination">
    <div class="page-pagination__meta">
      <span class="page-pagination__summary">第 {{ normalizedCurrentPage }} / {{ normalizedTotalPages }} 页</span>
    </div>

    <div class="page-pagination__body">
      <div class="page-pagination__controls">
        <button
          class="page-pagination__btn"
          type="button"
          :disabled="normalizedCurrentPage <= 1"
          @click="emitPage(normalizedCurrentPage - 1)"
        >上一页</button>

        <template v-for="token in pageTokens" :key="token.key">
          <span v-if="token.type === 'ellipsis'" class="page-pagination__ellipsis">…</span>
          <button
            v-else
            class="page-pagination__page"
            :class="{ 'is-active': token.value === normalizedCurrentPage }"
            type="button"
            :disabled="token.value === normalizedCurrentPage"
            @click="emitPage(token.value)"
          >{{ token.value }}</button>
        </template>

        <button
          class="page-pagination__btn"
          type="button"
          :disabled="normalizedCurrentPage >= normalizedTotalPages"
          @click="emitPage(normalizedCurrentPage + 1)"
        >下一页</button>
      </div>

      <form class="page-pagination__jump" @submit.prevent="submitPageInput">
        <span class="page-pagination__jump-label">跳转到</span>
        <input
          v-model.trim="pageInputValue"
          class="page-pagination__jump-input"
          type="number"
          inputmode="numeric"
          min="1"
          :max="normalizedTotalPages"
          aria-label="输入页码"
        />
        <button class="page-pagination__btn page-pagination__btn--jump" type="submit">跳转</button>
      </form>

      <label v-if="showPageSizeSelector" class="page-pagination__size">
        <span class="page-pagination__size-label">每页</span>
        <select class="page-pagination__select" :value="pageSize" @change="onPageSizeChange">
          <option v-for="option in normalizedPageSizeOptions" :key="option" :value="option">{{ option }}</option>
        </select>
      </label>
    </div>
  </div>
</template>

<script>
function clampPage(value, totalPages) {
  const normalizedTotalPages = Math.max(1, Number(totalPages) || 1)
  const normalizedValue = Number(value) || 1
  return Math.min(Math.max(1, normalizedValue), normalizedTotalPages)
}

export default {
  name: 'PagePaginationBar',

  data() {
    return {
      pageInputValue: '1',
    }
  },

  props: {
    currentPage: {
      type: Number,
      default: 1,
    },
    totalPages: {
      type: Number,
      default: 1,
    },
    pageSize: {
      type: Number,
      default: null,
    },
    pageSizeOptions: {
      type: Array,
      default: () => [],
    },
  },

  computed: {
    normalizedTotalPages() {
      return Math.max(1, Number(this.totalPages) || 1)
    },

    normalizedCurrentPage() {
      return clampPage(this.currentPage, this.normalizedTotalPages)
    },

    normalizedPageSizeOptions() {
      return this.pageSizeOptions
        .map(option => Number(option))
        .filter(option => Number.isInteger(option) && option > 0)
    },

    showPageSizeSelector() {
      return this.pageSize !== null && this.normalizedPageSizeOptions.length > 0
    },

    pageTokens() {
      const totalPages = this.normalizedTotalPages
      const currentPage = this.normalizedCurrentPage
      if (totalPages <= 7) {
        return Array.from({ length: totalPages }, (_value, index) => ({
          type: 'page',
          value: index + 1,
          key: `page-${index + 1}`,
        }))
      }

      const anchorPages = Array.from(new Set([
        1,
        currentPage - 1,
        currentPage,
        currentPage + 1,
        totalPages,
      ]))
        .filter(page => page >= 1 && page <= totalPages)
        .sort((left, right) => left - right)

      const tokens = []
      for (const page of anchorPages) {
        const previousPage = tokens.length ? tokens[tokens.length - 1].value : null

        if (previousPage !== null) {
          const gap = page - previousPage
          if (gap === 2) {
            const bridgedPage = previousPage + 1
            tokens.push({ type: 'page', value: bridgedPage, key: `page-${bridgedPage}` })
          } else if (gap > 2) {
            tokens.push({ type: 'ellipsis', key: `ellipsis-${previousPage}-${page}` })
          }
        }

        tokens.push({ type: 'page', value: page, key: `page-${page}` })
      }

      return tokens
    },
  },

  watch: {
    normalizedCurrentPage: {
      immediate: true,
      handler(nextPage) {
        this.pageInputValue = String(nextPage)
      },
    },
  },

  methods: {
    emitPage(nextPage) {
      const normalizedPage = clampPage(nextPage, this.normalizedTotalPages)
      if (normalizedPage === this.normalizedCurrentPage) return
      this.$emit('update:page', normalizedPage)
    },

    submitPageInput() {
      const nextPage = Number.parseInt(this.pageInputValue, 10)
      if (!Number.isInteger(nextPage)) {
        this.pageInputValue = String(this.normalizedCurrentPage)
        return
      }

      const normalizedPage = clampPage(nextPage, this.normalizedTotalPages)
      this.pageInputValue = String(normalizedPage)
      this.emitPage(normalizedPage)
    },

    onPageSizeChange(event) {
      const nextPageSize = Number.parseInt(String(event?.target?.value || ''), 10)
      if (!Number.isInteger(nextPageSize) || nextPageSize <= 0) return
      this.$emit('update:pageSize', nextPageSize)
    },
  },
}
</script>

<style scoped lang="css">
.page-pagination {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.56rem 0.72rem;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 14px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.96));
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
}

.page-pagination__meta {
  display: flex;
  align-items: center;
  min-width: 0;
}

.page-pagination__summary {
  color: #0f172a;
  font-size: 0.76rem;
  font-weight: 700;
  white-space: nowrap;
}

.page-pagination__body {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
  flex: 1 1 auto;
}

.page-pagination__controls {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 0.25rem;
}

.page-pagination__btn,
.page-pagination__page,
.page-pagination__select {
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.94);
  color: #334155;
  font-size: 0.74rem;
  font-weight: 700;
  transition: background 140ms ease, color 140ms ease, border-color 140ms ease, box-shadow 140ms ease;
}

.page-pagination__btn,
.page-pagination__page {
  min-width: 2.15rem;
  height: 1.9rem;
  padding: 0 0.56rem;
  cursor: pointer;
}

.page-pagination__btn:hover:not(:disabled),
.page-pagination__page:hover:not(:disabled),
.page-pagination__select:hover:not(:disabled) {
  border-color: rgba(59, 130, 246, 0.22);
  background: #eff6ff;
  color: #0f172a;
}

.page-pagination__page.is-active {
  border-color: rgba(37, 99, 235, 0.2);
  background: #dbeafe;
  color: #1d4ed8;
  cursor: default;
}

.page-pagination__btn:disabled,
.page-pagination__page:disabled,
.page-pagination__select:disabled {
  opacity: 0.42;
  cursor: not-allowed;
}

.page-pagination__ellipsis {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.15rem;
  color: #94a3b8;
  font-size: 0.86rem;
  font-weight: 700;
}

.page-pagination__size {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  color: #64748b;
  font-size: 0.7rem;
  font-weight: 700;
}

.page-pagination__jump {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.page-pagination__jump-label {
  color: #64748b;
  font-size: 0.7rem;
  font-weight: 700;
  white-space: nowrap;
}

.page-pagination__jump-input {
  width: 4.2rem;
  height: 1.9rem;
  padding: 0 0.56rem;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.94);
  color: #0f172a;
  font-size: 0.74rem;
  font-weight: 700;
}

.page-pagination__jump-input:focus {
  outline: none;
  border-color: rgba(37, 99, 235, 0.35);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.page-pagination__btn--jump {
  min-width: 3rem;
}

.page-pagination__size-label {
  white-space: nowrap;
}

.page-pagination__select {
  min-width: 4.7rem;
  height: 1.9rem;
  padding: 0 0.56rem;
  cursor: pointer;
  appearance: none;
}

@media (max-width: 640px) {
  .page-pagination {
    padding: 0.5rem 0.6rem;
  }

  .page-pagination__body {
    justify-content: flex-start;
  }

  .page-pagination__controls {
    justify-content: flex-start;
  }
}
</style>
