# Common Browse Page 契约说明

本文档对应 `frontend/src/utils/commonBrowsePage.js` 的当前实现，描述 `BrowsePage.vue` 如何通过页面契约切换 `calendar`、`search-results`、`gallery-recent`、`gallery-all`、`collection`、`tag`、`trash` 七种浏览模式。

## 1. 目标

当前统一浏览壳的职责是：

- 复用同一套页面布局
- 复用同一套页头筛选面板与遮罩交互
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
- `search-results`
- `gallery-recent`
- `gallery-all`
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
| `is_animated / animation_meta` | 后端返回的动图元信息；`animation_meta` 只在动图时包含 `frame_count / format`，用于共享卡片与详情浮层的状态展示 |
| `animated_badge_label` | 前端根据动图元信息归一化出的显式标记，目前只会是 `GIF` / `WEBP` 或空字符串 |
| `preview_original_url` | 图片详情层原图 URL，来自 `media_rel_path` |
| `editable` | 图片可编辑 `name/category/tags/createdAt`，相册不可编辑 |

### 3.2 `search-results`

搜索结果条目走 `normalizeSearchItem()`，内部会先复用 `normalizeCalendarItem()`，再补充搜索专有字段：

- 仅生成 `image` 条目，不包含相册节点
- 保留后端返回的 `matched_by`
- 保留后端返回的 `matched_tags`
- 同样保留后端返回的动图元信息，并归一化成 `animated_badge_label`
- `search-results` 不再把原图当作主预览兜底；当 temp/cache 缩略图都缺失时，页面先显示骨架，再复用 targeted preview repair 链路异步补图

### 3.3 `trash`

回收站条目走 `normalizeTrashItem()`，和普通浏览最大的区别是：

- `stable_key` 优先使用 `entry_key`
- 预览 URL 优先使用回收站自身字段：
  - `cache_thumb_url`
  - `thumb_url`
  - `trash_media_url`
- `editable` 全部为 `false`
- 当前回收站条目也会走同一套动图字段归一化流程，但因为后端暂未给回收站列表补充动图元信息，所以 badge 结果通常为空

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
| `autoRepairMissingPreview` | 是否在主卡片缺预览时自动批量加入 targeted repair |
| `allowOriginalPreviewFallback` | targeted repair 结束后，是否允许主卡片回退到卡片内原图 |
| `updateCover(vm, item)` | 可选，仅日历相册和收藏夹支持 |

## 5. 当前七个契约

| 契约 | 数据源 | 默认排序 | 页头动作 | 主动作 / 次动作 | 预览修复 key |
| --- | --- | --- | --- | --- | --- |
| `calendar` | `/api/dates/{group}/items` 或 `/api/albums/by-path/{path}` | 月份页 `date asc`；相册页 `alpha asc` | 相册模式下可进入“选择封面” | `查看原图/查看相册` + `移入回收站` | `image_ids` |
| `search-results` | `/api/search/images?...&limit=0`，由统一搜索参数生成器补齐 `mode`，必要时带 `quick_hash/start_at/end_at` | `alpha asc` | 无 | `查看原图` + `移入回收站` | `image_ids` |
| `gallery-recent` | `/api/gallery/recent/items` | `date asc` | 无 | 图片 `查看原图`、相册 `打开目录` + `移入回收站` | `image_ids` |
| `gallery-all` | `/api/gallery/all/items` | `date asc` | 无 | 图片 `查看原图`、相册 `打开目录` + `移入回收站` | `image_ids` |
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

### 6.2 `search-results`

- 数据源来自 `/api/search/images`，查询参数的主入口仍是当前路由的 `q`；当一级页是 `file:` 搜索时，还会额外读取路由里的 `quick_hash`。
- 契约会先用统一的 `buildSearchRequestParams()` 生成搜索参数，再以 `limit=0` 请求完整结果集。
- 面包屑结构固定为“搜索 -> 当前查询词”。
- 条目只包含图片，不包含相册节点；点击卡片主体会先打开详情浮层，而不是直接打开原图。
- 主预览优先使用 temp/cache 缩略图；如果当前渲染项缺失缩略图，契约页会把对应 image id 批量送入现有 preview repair 队列，后台异步修复后再通过 `/api/images/meta` 回填。
- `search-results` 不启用主卡片原图兜底；修复后仍拿不到预览时，卡片进入终态提示而不是无限骨架。
- 返回行为会回到 `/search`，并保留原始 `q`；如果当前是 `file:` 搜索，也会一并保留 `quick_hash`，保证一级页与二级页结果一致。

### 6.3 `gallery-recent` / `gallery-all`

- 两个契约都从 `/gallery` 父页进入，面包屑固定为“图库管理 -> 当前子页”。
- 当进入相册层级时，路由保持在 `/gallery/recent/:group/:albumPath+` 或 `/gallery/all/:group/:albumPath+`，不再跳回 `/calendar/...`。
- 数据格式沿用 `DateItem`，因此二级页继续复用日期视图的选择态、详情浮层与预览修复链路。
- 条目允许同时包含：
  - 顶层相册节点
  - 顶层直图节点
- 排序约定与日期视图的二级页保持一致：相册在前，图片在后，两类节点各自按时间/名称规则排序。
- 主卡片缺少 temp/cache 缩略图时会自动加入 targeted repair；修复结束后仍无预览时，回退到卡片内原图，不再永久显示骨架。
- 返回行为固定留在 gallery 体系内：相册页先回当前 gallery 子页上一级，相册根页再回 `/gallery`。

### 6.4 `collection`

- 面包屑固定为“收藏 -> 当前收藏夹”。
- 条目只包含图片，没有相册节点。
- 点击图片和详情主动作都走系统打开图片。
- 收藏夹页同样支持手动封面，接口为 `/api/collections/{public_id}/cover`。
- 主卡片缺预览时会自动复用 targeted repair；修复结束后仍无缩略图时，回退为卡片内原图。

### 6.5 `tag`

- 面包屑固定为“标签总览 -> 当前标签”。
- 页头额外动作只有“编辑标签”。
- 浏览信息并不直接使用后端相册结构，而是把 `/api/tags/{id}/images` 返回的 `tag` 元数据包装成一个“浏览容器信息”。
- 主卡片缺预览时同样会自动加入 targeted repair；修复结束后可回退卡片内原图。

### 6.6 `trash`

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
- 统一筛选面板状态，以及基于完整数据集的前端本地过滤
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
- `search-results` 复用了 `normalizeCalendarItem()` 的图片字段，但额外保留了搜索匹配元数据，并使用路由查询参数而不是路径参数驱动数据加载。
- `trash` 使用独立的 `normalizeTrashItem()`，因为回收站的预览和主动作逻辑与普通浏览完全不同。
- 所有 `BrowsePage.vue` 契约页都会在默认 header 右侧额外挂出统一的“筛选”按钮；它不是 contract 自定义动作，而是共享浏览壳自带能力。
- 当前筛选完全在前端本地完成，作用于每个契约加载到页面后的完整数据集；筛选状态只保留在当前页面实例内，不写回路由 query，也不落本地缓存。
- 筛选维度固定为：标签、主分类、文件名、文件类型、导入时间、创建时间、文件大小。其中标签块永远排在最上方，并使用 Tag chip 展示当前视图中出现过的全部标签；description 通过悬停提示显示。
- 标签筛选支持多选 OR；“无标签”与普通标签做并集；主分类按当前页面出现过的 category_id 多选；文件类型按当前视图图片项出现过的扩展名多选；时间与大小都支持只填单侧形成开区间。
- 筛选面板里的标签名称与 description 由共享 Tag lookup 延迟补齐，拉取范围基于完整 `sourceItems` 而不是当前已筛出的 `items`；因此即使图片刚被打上新标签，悬停提示也会在同页内及时刷新。
- 筛选只作用于图片条目；相册条目不参与筛选并始终保留，所以混合相册/图片页面不会因为筛选而把导航性的相册卡片全部隐藏。
- 预览缺失自动修复与主卡片原图回退已经改成契约开关控制，而不是写死在单个页面分支里。
- 共享浏览壳当前约定：卡片、列表缩略图与详情浮层都只依赖归一化后的动图字段决定是否显示 `GIF` / `WEBP` 标记，不再自行判断文件后缀。
- `previewRepairPayloadKey` 当前只有两种：
  - 普通浏览相关：`image_ids`
  - 回收站：`trash_entry_ids`
- `normalizeBrowseItems()` 只是对 `getCommonBrowsePageContract(...).normalizeItems(...)` 的轻封装，不会做额外业务处理。
