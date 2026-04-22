<template>
  <Teleport to="body">
    <Transition name="folder-import-fade">
      <div v-if="visible" class="folder-import-mask" @click.self="$emit('close')">
        <section class="folder-import-dialog" role="dialog" aria-modal="true" aria-label="导入图片文件夹">
          <header class="folder-import-dialog__header">
            <div>
              <h3 class="folder-import-dialog__title">导入图片文件夹</h3>
              <p class="folder-import-dialog__subtitle">可先加入多个文件夹，再分别设置主分类后顺序导入。</p>
            </div>
            <button class="folder-import-dialog__close" type="button" :disabled="busy" @click="$emit('close')">关闭</button>
          </header>

          <div class="folder-import-layout">
            <div class="folder-import-board">
              <div class="folder-import-table-wrap">
                <table v-if="rows.length" class="folder-import-table">
                  <thead>
                    <tr>
                      <th>路径</th>
                      <th>主分类</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="row in rows"
                      :key="row.id"
                      class="folder-import-row"
                      :class="{ 'is-selected': selectedIds.includes(row.id) }"
                      @click="$emit('toggle-row', row.id)"
                    >
                      <td>
                        <div class="folder-import-path-cell">
                          <span class="folder-import-path-cell__mark">{{ selectedIds.includes(row.id) ? '●' : '○' }}</span>
                          <div>
                            <div class="folder-import-path">{{ row.label }}</div>
                            <div class="folder-import-meta">{{ row.imageCount }} 张图片 / {{ row.fileCount }} 个文件</div>
                          </div>
                        </div>
                      </td>
                      <td>
                        <select
                          class="folder-import-select"
                          :disabled="busy"
                          :value="row.categoryValue"
                          @click.stop
                          @change="$emit('update-category', { rowId: row.id, value: $event.target.value })"
                        >
                          <option value="auto">Auto（暂未实现）</option>
                          <option
                            v-for="category in categories"
                            :key="category.id"
                            :value="String(category.id)"
                          >
                            {{ category.display_name || category.name || `#${category.id}` }}
                          </option>
                        </select>
                      </td>
                    </tr>
                  </tbody>
                </table>

                <div v-else class="folder-import-empty">
                  尚未添加文件夹。点击右侧“添加行”开始。
                </div>
              </div>
            </div>

            <aside class="folder-import-actions">
              <div class="folder-import-actions__top">
                <button class="folder-import-side-btn" type="button" :disabled="busy" @click="$emit('add-row')">添加行</button>
                <button class="folder-import-side-btn folder-import-side-btn--danger" type="button" :disabled="busy || !selectedIds.length" @click="$emit('delete-selected')">删除行</button>
              </div>

              <div class="folder-import-actions__bottom">
                <button class="folder-import-main-btn folder-import-main-btn--accent" type="button" :disabled="busy || !rows.length" @click="$emit('confirm')">
                  {{ busy ? '导入中…' : '导入' }}
                </button>
                <button class="folder-import-main-btn folder-import-main-btn--ghost" type="button" :disabled="busy" @click="$emit('close')">取消</button>
              </div>
            </aside>
          </div>

          <p v-if="error" class="folder-import-feedback folder-import-feedback--error">{{ error }}</p>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script>
export default {
  name: 'FolderImportDialog',
  props: {
    visible: { type: Boolean, default: false },
    busy: { type: Boolean, default: false },
    rows: { type: Array, default: () => [] },
    categories: { type: Array, default: () => [] },
    selectedIds: { type: Array, default: () => [] },
    error: { type: String, default: '' },
  },
  emits: ['add-row', 'close', 'confirm', 'delete-selected', 'toggle-row', 'update-category'],
}
</script>

<style scoped lang="css">
.folder-import-mask {
  position: fixed;
  inset: 0;
  z-index: 120;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: rgba(15, 23, 42, 0.34);
  backdrop-filter: blur(8px);
}

.folder-import-dialog {
  width: min(100%, 1060px);
  border: 1px solid rgba(226, 232, 240, 0.92);
  border-radius: 30px;
  padding: 1.35rem;
  background:
    radial-gradient(circle at top left, rgba(191, 219, 254, 0.72), transparent 35%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
  box-shadow: 0 30px 80px rgba(15, 23, 42, 0.24);
}

.folder-import-dialog__header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.folder-import-dialog__title {
  margin: 0;
  color: #0f172a;
  font-size: 1.12rem;
  font-weight: 800;
}

.folder-import-dialog__subtitle {
  margin: 0.4rem 0 0;
  color: #64748b;
  font-size: 0.84rem;
  line-height: 1.6;
}

.folder-import-dialog__close {
  border: 0;
  background: transparent;
  color: #64748b;
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
}

.folder-import-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 160px;
  gap: 1.2rem;
  margin-top: 1.2rem;
}

.folder-import-board {
  min-width: 0;
}

.folder-import-table-wrap {
  min-height: 420px;
  border: 1px solid rgba(148, 163, 184, 0.26);
  border-radius: 22px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.84);
}

.folder-import-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.folder-import-table th,
.folder-import-table td {
  border-bottom: 1px solid rgba(203, 213, 225, 0.8);
  padding: 0.9rem 1rem;
  text-align: left;
  vertical-align: middle;
}

.folder-import-table th {
  color: #334155;
  font-size: 0.8rem;
  font-weight: 800;
  background: rgba(248, 250, 252, 0.92);
}

.folder-import-table th:first-child,
.folder-import-table td:first-child {
  width: 76%;
  border-right: 1px solid rgba(203, 213, 225, 0.8);
}

.folder-import-row {
  cursor: pointer;
  transition: background 150ms ease;
}

.folder-import-row:hover {
  background: rgba(241, 245, 249, 0.74);
}

.folder-import-row.is-selected {
  background: rgba(219, 234, 254, 0.8);
}

.folder-import-path-cell {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
}

.folder-import-path-cell__mark {
  color: #0f172a;
  font-size: 0.92rem;
  line-height: 1.2;
}

.folder-import-path {
  color: #0f172a;
  font-size: 0.88rem;
  font-weight: 700;
  word-break: break-all;
}

.folder-import-meta {
  margin-top: 0.28rem;
  color: #64748b;
  font-size: 0.74rem;
}

.folder-import-select {
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.34);
  border-radius: 14px;
  padding: 0.72rem 0.8rem;
  background: rgba(255, 255, 255, 0.94);
  color: #0f172a;
  font-size: 0.84rem;
}

.folder-import-empty {
  min-height: 420px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  color: #94a3b8;
  font-size: 0.86rem;
  text-align: center;
}

.folder-import-actions {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 1rem;
}

.folder-import-actions__top,
.folder-import-actions__bottom {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.folder-import-side-btn,
.folder-import-main-btn {
  border: 0;
  cursor: pointer;
  transition: transform 150ms ease, opacity 150ms ease, box-shadow 150ms ease, background 150ms ease;
}

.folder-import-side-btn:hover,
.folder-import-main-btn:hover {
  transform: translateY(-1px);
}

.folder-import-side-btn {
  width: 100%;
  min-height: 56px;
  border-radius: 18px;
  padding: 0.88rem 0.95rem;
  background: rgba(255, 255, 255, 0.94);
  color: #0f172a;
  font-size: 0.92rem;
  font-weight: 800;
  text-align: center;
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.3);
}

.folder-import-side-btn--danger {
  color: #991b1b;
}

.folder-import-main-btn {
  width: 100%;
  min-height: 56px;
  border-radius: 18px;
  padding: 0.9rem 1rem;
  font-size: 0.96rem;
  font-weight: 800;
}

.folder-import-main-btn--accent {
  background: linear-gradient(135deg, #0f766e, #0f766e 35%, #0f172a);
  color: #fff;
  box-shadow: 0 16px 32px rgba(15, 23, 42, 0.16);
}

.folder-import-main-btn--ghost {
  background: rgba(226, 232, 240, 0.88);
  color: #334155;
}

.folder-import-feedback {
  margin: 1rem 0 0;
  border-radius: 16px;
  padding: 0.8rem 0.95rem;
  font-size: 0.82rem;
  font-weight: 700;
}

.folder-import-feedback--error {
  background: rgba(254, 226, 226, 0.9);
  color: #991b1b;
}

.folder-import-side-btn:disabled,
.folder-import-main-btn:disabled,
.folder-import-select:disabled,
.folder-import-dialog__close:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
}

.folder-import-fade-enter-active,
.folder-import-fade-leave-active {
  transition: opacity 180ms ease;
}

.folder-import-fade-enter-from,
.folder-import-fade-leave-to {
  opacity: 0;
}

@media (max-width: 900px) {
  .folder-import-layout {
    grid-template-columns: 1fr;
  }

  .folder-import-actions {
    flex-direction: row;
    align-items: stretch;
  }

  .folder-import-actions__top {
    flex-direction: row;
  }

  .folder-import-actions__bottom {
    flex: 1;
  }
}

@media (max-width: 640px) {
  .folder-import-dialog {
    padding: 1rem;
    border-radius: 24px;
  }

  .folder-import-dialog__header {
    flex-direction: column;
  }

  .folder-import-table th,
  .folder-import-table td {
    padding: 0.78rem 0.72rem;
  }

  .folder-import-actions {
    flex-direction: column;
  }

  .folder-import-actions__top {
    flex-direction: row;
  }

  .folder-import-side-btn {
    align-self: auto;
  }
}
</style>