# Common Browse Page 模板契约

本文档定义前端统一浏览壳的开发范式。目标是让所有“图片 / 相册浏览页”都复用同一套页面壳、布局、选择、详情和预览修复主流程，只通过页面契约、数据源和数据适配器注入差异。

当前基线实现：

- 页面壳：`frontend/src/pages/BrowsePage.vue`
- 详情浮层：`frontend/src/components/SelectionDetailOverlay.vue`
- 三级动作菜单：`frontend/src/components/TagMenuDialog.vue`、`frontend/src/components/CollectionMenuDialog.vue`
- 页面契约与适配器：`frontend/src/utils/commonBrowsePage.js`

## 1. 总体分层

统一浏览页由 4 层组成：

1. 路由上下文
2. 页面契约
3. 数据源
4. 数据适配器

### 1.1 路由上下文

路由上下文只负责“我现在在哪”和“这个页面属于哪种浏览模式”，不负责业务动作。

约定：

- `route.meta.browseContract`：决定当前页面使用哪种页面契约
- `route.meta.reuseKey`：决定是否复用 `BrowsePage` 实例
- `route.params`：负责位置参数，例如 `group`、`albumPath`、`collectionId`

示例：

```js
{
  path: '/favorites/:collectionId',
  name: 'browse-collection',
  component: BrowsePage,
  meta: {
    reuseKey: 'browse',
    browseContract: 'collection',
  },
}
```

### 1.2 页面契约

页面契约负责当前页面的策略差异：

- 默认排序
- 面包屑
- 页头扩展按钮
- 按钮岛动作
- 详情浮层按钮
- 详情浮层外接的三级菜单入口（例如 Tag / 收藏）
- 页头动作触发的附加交互模式（例如“选择封面”）
- 元数据编辑权限
- 主动作与危险动作
- 预览修复后的收尾策略

页面契约不直接持有布局状态，也不直接操作 DOM。

补充：Tag 菜单与收藏菜单虽然都从 `BrowsePage.vue` 发起，但它们不属于页面契约本身的内部状态。页面契约只负责决定“当前页面有没有这个入口”；真正的菜单状态、搜索、提交与局部 UI 回写都由 `BrowsePage.vue` 管理。

### 1.3 数据源

数据源只负责拿原始数据包，不负责归一化、不负责排序、不负责展示字段。

例如：

- calendar 模式：
  - `GET /api/dates/:group/items`
  - `GET /api/albums/by-path/:path`
- collection 模式：
  - `GET /api/collections/:collectionId`
- trash 模式：
  - `GET /api/trash/items`

### 1.4 数据适配器

数据适配器把各自页面的数据源结果转换成统一 item。

这是整套模板的核心。未来新增页面时，优先新增适配器和页面契约，不再复制页面实现。

## 2. 统一 item 契约

所有模式最终都必须归一化为统一 item。

最低必填字段如下：

| 字段 | 说明 |
| --- | --- |
| `stable_key` | 页面级稳定 key，用于选择、详情、锚点恢复 |
| `layout_key` | 布局级 key，用于宽高缓存和布局指纹 |
| `type` | `image` 或 `album` |
| `name` | 统一展示名称 |
| `cache_thumb_url` | 主预览 URL |
| `thumb_url` | 次级预览 URL |
| `preview_original_url` | 详情层原始预览回退 URL |
| `sort_ts` | 标准时间排序值，完全对齐现有 BrowsePage 的排序语义 |
| `count` | 相册数量字段，图片可为 `0` |
| `width` / `height` | 尺寸字段 |
| `file_size` | 文件大小 |
| `imported_at` | 导入时间 |
| `file_created_at` | 图片创建时间 |
| `created_at` | 记录创建时间或相册创建时间 |
| `category_id` | 主分类 |
| `tags` | Tag ID 列表 |
| `editable` | 当前 item 的元数据编辑能力 |

`editable` 约定如下：

```js
editable: {
  name: true | false,
  category: true | false,
  tags: true | false,
  createdAt: true | false,
}
```

## 3. sortValue 规范

统一 item 的时间排序值必须与现有 `BrowsePage` 对齐，不再为不同页面单独定义“另一套排序语义”。

约定：

- 统一使用 `sort_ts`
- `sort_ts` 是秒级 Unix 时间戳
- 页面壳只认 `sortBy = date | alpha` 和 `sortDir = asc | desc`
- adapter 负责把原始数据映射成 `sort_ts`

## 4. 详情浮层策略对象

详情浮层由 `SelectionDetailOverlay.vue` 承载，页面差异通过策略对象注入。

### 4.1 元数据权限

四个编辑入口只保留两种状态：

- 允许修改
- 隐藏

策略对象：

```js
metadataPermissions: {
  name: true | false,
  category: true | false,
  tags: true | false,
  createdAt: true | false,
}
```

### 4.2 底部两个按钮

两个按钮全部必填。

约定：

- 第一个按钮：`primary`
- 第二个按钮：`secondary`
- 若页面没有真实第二动作，可配置成“取消”

策略对象：

```js
{
  primaryActionLabel: '查看原图',
  primaryActionTone: 'accent',
  canOpenPrimaryAction: true,
  primaryActionDisabled: false,

  secondaryActionLabel: '移入回收站',
  secondaryActionTone: 'danger',
  secondaryActionDisabled: false,
}
```

色调建议：

- `accent`
- `danger`
- `neutral`
- `ghost`

### 4.3 可选三级菜单入口

`SelectionDetailOverlay.vue` 除两个底部主按钮外，还可以在右侧追加独立图标入口，例如收藏星标。

约定：

- 图标按钮本身只负责触发事件，不直接管理菜单状态
- 菜单组件通过 `Teleport` 作为详情浮层之上的三级窗口挂载
- 当前实现中：
  - Tag 入口放在字段区的 `TagChipList` 加号按钮
  - 收藏入口放在详情浮层底部动作区右侧的镂空五角星按钮

## 5. 页头与按钮岛规范

### 5.1 页头

统一复用 `BreadcrumbHeader.vue`。

规则：

- 页头只负责展示和布局
- 额外功能按钮通过默认 slot 注入
- 页头不再为某个页面维护单独组件
- 如果页面支持容器级动作，例如相册/收藏夹“选择封面”，统一由页面契约在 `buildHeaderActions(vm)` 中注入按钮，具体模式状态仍由 `BrowsePage.vue` 管理

例如回收站的“清空回收站”按钮，就是通过 header slot 注入，而不是再建一个独立的回收站页头组件。

### 5.2 按钮岛

选择态右下角按钮岛分为两部分：

1. 页面契约提供的动作按钮
2. 通用的“全选 / 取消选择”

按钮配置示例：

```js
[
  {
    key: 'details',
    label: '详情',
    handler: 'openSelectionDetailsFromIsland',
    className: '',
    disabled: !vm.selectedCount || vm.actionBusy,
  },
  {
    key: 'collect',
    label: '收藏',
    handler: 'openCollectionMenu',
    className: '',
    disabled: !vm.canOpenCollectionMenu || vm.actionBusy,
  },
  {
    key: 'restore',
    label: '还原',
    handler: 'restoreSelection',
    className: '',
    disabled: !vm.selectedCount || vm.actionBusy,
  },
  {
    key: 'hard-delete',
    label: '删除',
    handler: 'hardDeleteSelection',
    className: 'selection-island__btn--danger',
    disabled: !vm.selectedCount || vm.actionBusy,
  },
]
```

## 6. 生命周期钩子规范

统一浏览页的生命周期钩子如下。

### 6.1 beforeLoad(ctx)

进入页面或路由变化时执行。

职责：

- 清理 selection
- 清理详情浮层
- 清理轮询 / 缩略图任务状态
- 清理预览失败标记
- 清理浮层与滚动锁
- 是否保留视图锚点由页面契约决定

### 6.2 loadItems(ctx)

只负责从当前数据源获取原始数据包。

不允许做：

- 排序
- item 归一化
- 页面展示字段拼接
- DOM 计算

### 6.3 normalizeItems(rawItems, ctx)

将原始数据归一化为统一 item。

这是未来所有虚拟浏览页的核心入口。

## 7. 可复用菜单约定

BrowsePage 当前有两类可复用三级菜单：

1. `TagMenuDialog.vue`
2. `CollectionMenuDialog.vue`

两者都遵循同一约定：

- 菜单由 `BrowsePage.vue` 统一持有 `visible / busy / query / suggestions / error` 等状态
- 详情浮层和选择态按钮岛都只能发起“打开菜单”的动作，不各自维护一套状态
- 关闭详情浮层、退出选择态或清空选择时，相关菜单需要一并关闭，避免页面残留悬浮状态

职责：

- 生成 `stable_key`
- 生成 `layout_key`
- 统一 `type`
- 统一 `name`
- 映射预览 URL
- 映射 `sort_ts`
- 映射尺寸 / 数量 / 元数据字段
- 映射 `editable`

### 6.4 afterLoad(items, ctx)

负责把已归一化的数据接入页面壳。

典型职责：

- 排序
- cache URL 索引
- 标签映射
- 主分类映射
- 布局指纹生成
- 必要的静默修复

### 6.5 openPrimary(item, ctx)

详情层主按钮行为。

示例：

- calendar：打开原图 / 打开相册
- collection：打开原图
- trash：还原

### 6.6 dangerAction(selection, ctx)

详情层第二按钮或批量危险动作。

示例：

- calendar：移入回收站
- trash：硬删除

### 6.7 afterAction(result, ctx)

动作执行后的统一收尾策略。

遵循当前 `BrowsePage` 的原则：

- 能局部回写就局部回写
- 需要重排时局部重排
- 必须换数据源或上下文时再整页重载

### 6.8 silentRepair(ctx)

仅在必要模式启用。

职责：

- 404 预览补齐
- quick refresh
- generation / 队列修复
- 轻量 reconcile

### 6.9 onRouteChange(ctx)

决定：

- 是否复用 `BrowsePage`
- 是否保留锚点
- 是否完整重载

### 6.10 onResize(ctx) / onScroll(ctx)

只处理布局与可视窗口同步。

不允许掺杂：

- 数据源获取逻辑
- adapter 逻辑
- 业务动作

### 6.11 onUnmount(ctx)

统一清理：

- 定时器
- 轮询
- 事件监听
- 滚动锁
- 预览修复队列
- 浮层状态

## 7. 当前页面契约接口

当前实际实现位于 `frontend/src/utils/commonBrowsePage.js`，建议页面契约至少暴露以下成员：

```js
{
  name,
  emptyState,
  defaultSort(vm),
  buildCrumbs(vm),
  buildHeaderActions(vm),
  buildSelectionActions(vm),
  buildDetailPolicy(vm),
  loadItems(vm),
  normalizeItems(rawItems, vm),
  afterLoad(vm),
  back(vm),
  openItem(vm, item),
  openPrimary(vm, item),
  updateCover(vm, item),
  runSecondaryAction(vm),
  previewRepairPayloadKey,
  afterPreviewRepair(vm, repairIds),
}
```

## 8. 后端数据库设计建议

前端统一浏览模板依赖后端把“浏览用信息”和“业务原始信息”稳定提供出来。

### 8.1 live 浏览

live 浏览主要来自：

- `imageasset`
- `album`
- `album_image`

建议后端对 browse 接口稳定输出：

- `type`
- `id`
- `public_id`
- `name`
- `album_path`
- `media_rel_path`
- `cache_thumb_url`
- `thumb_url`
- `sort_ts`
- `width`
- `height`
- `file_size`
- `imported_at`
- `file_created_at`
- `created_at`
- `category_id`
- `tags`
- `photo_count`

### 8.2 trash 浏览

trash 浏览主要依赖：

- `trash_entry`

当前后端模型可参考：

- `backend/app/models/trash_entry.py`

`trash_entry` 至少需要稳定承载：

- `id`
- `entry_key`
- `entity_type`
- `display_name`
- `original_path`
- `trash_path`
- `preview_path`
- `preview_thumb_path`
- `preview_cache_path`
- `file_hash`
- `width`
- `height`
- `file_size`
- `mime_type`
- `category_id`
- `imported_at`
- `file_created_at`
- `photo_count`
- `tags`
- `created_at`

建议 trash browse 接口额外输出前端直接可用字段：

- `cache_thumb_url`
- `thumb_url`
- `trash_media_url`
- `sort_ts`

这样 adapter 就只负责归一化，不必再在页面层拼 URL。

## 9. 数据适配器设计建议

数据适配器应该是纯函数，职责单一。

示例：

```js
function normalizeTrashItem(rawItem) {
  const type = rawItem.entity_type === 'album' ? 'album' : 'image'
  return {
    ...rawItem,
    type,
    name: rawItem.display_name || rawItem.name || '未命名',
    stable_key: `${type}:${rawItem.entry_key || rawItem.id}`,
    layout_key: rawItem.entry_key || rawItem.id,
    cache_thumb_url: rawItem.cache_thumb_url || rawItem.preview_cache_path || '',
    thumb_url: rawItem.thumb_url || rawItem.preview_thumb_path || rawItem.preview_path || '',
    preview_original_url: rawItem.trash_media_url || rawItem.preview_path || '',
    sort_ts: rawItem.sort_ts,
    editable: {
      name: false,
      category: false,
      tags: false,
      createdAt: false,
    },
  }
}
```

要求：

- adapter 内不访问 DOM
- adapter 内不直接触发 fetch
- adapter 内不做页面跳转
- adapter 只做归一化映射

## 10. 新页面开发步骤

后续新增浏览页时，按下面顺序开发：

1. 明确路由上下文
2. 新增数据源接口
3. 编写 adapter，把原始数据转成统一 item
4. 新增页面契约，决定按钮、详情、动作和修复策略
5. 将路由指向 `BrowsePage.vue`
6. 只在必要时补充专用静默修复钩子

不再允许复制一个新的 `XXXPage.vue` 来维护另一套布局、选择、详情和虚拟化逻辑。

## 11. 当前已落地的契约

当前已实现三个模式：

- `calendar`
- `collection`
- `trash`

其中：

- `calendar` 负责 live browse
- `collection` 负责收藏夹二级 browse，并复用 BrowsePage 的选择、详情、Tag/收藏菜单与封面选择模式
- `trash` 负责回收站 browse

二者共用同一 `BrowsePage.vue` 壳，只通过页面契约和 adapter 分流。