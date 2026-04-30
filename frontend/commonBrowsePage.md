# Common Browse Page 契约说明

本文档对应 `frontend/src/utils/commonBrowsePage.js` 的当前实现，描述 `BrowsePage.vue` 如何通过页面契约切换 `calendar`、`collection`、`tag`、`trash` 四种浏览模式。

## 1. 目标

当前统一浏览壳的职责是：

- 复用同一套页面布局
- 复用选择模式、详情浮层、Tag 菜单和收藏菜单
- 复用分页/滚动浏览模式
- 复用缓存缩略图修复与轮询
- 只把“每个页面真正不同的地方”下沉到契约对象

当前基线实现：

- 页面壳：`frontend/src/pages/BrowsePage.vue`
- 契约实现：`frontend/src/utils/commonBrowsePage.js`
- 详情浮层：`frontend/src/components/SelectionDetailOverlay.vue`
- 三级菜单：`TagMenuDialog.vue`、`CollectionMenuDialog.vue`

## 2. 导出 API

`commonBrowsePage.js` 当前导出两个入口：

- `getCommonBrowsePageContract(contractName = 'calendar')`
- `normalizeBrowseItems(rawItems, contractName = 'calendar')`

支持的契约名：

- `calendar`
- `collection`
- `tag`
- `trash`

## 3. 统一 item 归一化

### 3.1 `calendar` / `collection` / `tag`

这三类最终都走 `normalizeCalendarItem()`，当前会统一出以下核心字段：

| 字段 | 当前来源 / 含义 |
| --- | --- |
| `type` | `image` 或 `album` |
| `name` | 展示名 |
| `count` | 相册图片数 |
| `sort_ts` | 排序时间戳；没有就从时间字段回退计算 |
| `stable_key` | 页面级稳定 key；图片优先用 `media_rel_path`，相册优先用 `public_id/album_path` |
| `layout_key` | 布局缓存 key |
| `preview_original_url` | 图片详情层原图 URL，来自 `media_rel_path` |
| `editable` | 图片可编辑 `name/category/tags/createdAt`，相册不可编辑 |

### 3.2 `trash`

回收站条目走 `normalizeTrashItem()`，和普通浏览最大的区别是：

- `stable_key` 优先使用 `entry_key`
- 预览 URL 优先使用回收站自身字段：
  - `cache_thumb_url`
  - `thumb_url`
  - `trash_media_url`
- `editable` 全部为 `false`

## 4. 契约接口

每个契约对象当前都围绕下面这些能力组织：

| 字段 / 方法 | 作用 |
| --- | --- |
| `name` | 契约名 |
| `emptyState` | 空状态图标与文案 |
| `defaultSort(vm)` | 默认排序字段与方向 |
| `buildCrumbs(vm)` | 构造面包屑 |
| `buildHeaderActions(vm)` | 页头右侧动作 |
| `buildSelectionActions(vm)` | 选择态按钮岛动作 |
| `buildDetailPolicy(vm)` | 详情浮层的权限与主次动作 |
| `loadItems(vm)` | 拉取原始数据包 |
| `normalizeItems(rawItems)` | 把原始数据转成统一 item |
| `afterLoad(vm)` | 页面拿到数据后的附加逻辑 |
| `back(vm)` | 返回行为 |
| `openItem(vm, item)` | 点击卡片主体时的行为 |
| `openPrimary(vm, item)` | 详情浮层主动作 |
| `runSecondaryAction(vm)` | 详情浮层次动作 |
| `previewRepairPayloadKey` | 预览修复请求使用的字段名 |
| `afterPreviewRepair(vm, repairIds)` | 预览修复后的收尾逻辑 |
| `updateCover(vm, item)` | 可选，仅日历相册和收藏夹支持 |

## 5. 当前四个契约

| 契约 | 数据源 | 默认排序 | 页头动作 | 主动作 / 次动作 | 预览修复 key |
| --- | --- | --- | --- | --- | --- |
| `calendar` | `/api/dates/{group}/items` 或 `/api/albums/by-path/{path}` | 月份页 `date asc`；相册页 `alpha asc` | 相册模式下可进入“选择封面” | `查看原图/查看相册` + `移入回收站` | `image_ids` |
| `collection` | `/api/collections/{collectionPublicId}` | `date asc` | 可进入“选择封面” | `查看原图` + `移入回收站` | `image_ids` |
| `tag` | `/api/tags/{tagId}/images` | `date desc` | `编辑标签` | `查看原图` + `移入回收站` | `image_ids` |
| `trash` | `/api/trash/items` | `date desc` | `清空回收站` | `还原` + `删除` | `trash_entry_ids` |

## 6. 各契约的当前行为细节

### 6.1 `calendar`

- 面包屑结构为“日期视图 -> 月份 -> 相册层级”。
- 点击相册会继续进入 `/calendar/:group/:albumPath+`。
- 点击图片会调用 `/api/images/{id}/open?path=...`。
- 相册详情层的主动作不是打开图片，而是调用 `/api/albums/open-by-path/{album_path}` 打开磁盘目录。
- 在相册模式下，页头会显示“选择封面”按钮，并通过 `/api/albums/{public_id}/cover` 保存封面。

### 6.2 `collection`

- 面包屑固定为“收藏 -> 当前收藏夹”。
- 条目只包含图片，没有相册节点。
- 点击图片和详情主动作都走系统打开图片。
- 收藏夹页同样支持手动封面，接口为 `/api/collections/{public_id}/cover`。

### 6.3 `tag`

- 面包屑固定为“标签总览 -> 当前标签”。
- 页头额外动作只有“编辑标签”。
- 浏览信息并不直接使用后端相册结构，而是把 `/api/tags/{id}/images` 返回的 `tag` 元数据包装成一个“浏览容器信息”。

### 6.4 `trash`

- 面包屑只有“回收站”。
- 点击条目不会直接打开原图，而是打开回收站详情浮层。
- 详情层没有任何元数据编辑入口。
- `afterLoad(vm)` 中会执行：
  - 分类标签加载
  - Tag 标签加载
  - `triggerSilentRepair()` 静默对账
- 返回逻辑优先 `router.back()`；如果浏览器历史不足，则回到 `/settings`。

## 7. `BrowsePage.vue` 自己负责的状态

以下内容当前不属于契约，而由 `BrowsePage.vue` 自己维护：

- 排布模式与布局缓存
- 选择状态与多选逻辑
- 详情浮层显隐与滚动锁
- Tag 菜单状态
- 收藏菜单状态
- 缩略图缓存轮询状态
- 预览失败记录与修复触发时机
- 分类名称和 Tag 文本的延迟加载

这意味着新增浏览模式时，优先新增契约和数据适配器，而不是复制一份新的浏览页组件。

## 8. 当前实现上的重要约定

- `collection` 与 `tag` 复用了 `normalizeCalendarItem()`，因此它们和普通月页的图片条目字段保持一致。
- `trash` 使用独立的 `normalizeTrashItem()`，因为回收站的预览和主动作逻辑与普通浏览完全不同。
- `previewRepairPayloadKey` 当前只有两种：
  - 普通浏览相关：`image_ids`
  - 回收站：`trash_entry_ids`
- `normalizeBrowseItems()` 只是对 `getCommonBrowsePageContract(...).normalizeItems(...)` 的轻封装，不会做额外业务处理。
