# picTagView Frontend 技术说明书

## 1. 项目位置
- `D:\Python_projects\picTagView_main\frontend`

## 2. 技术栈
- Vue 3（Vue CLI 项目）
- Vue Router（页面导航）
- Fetch API（当前代码未引入 Axios，页面内直接请求后端 API）
- Tailwind CSS（样式工具类）
- ES6+ JavaScript
- Node.js + npm（构建与脚本运行）

## 3. 目录结构
```text
frontend/
├── public/
├── src/
│   ├── App.vue
│   ├── main.js
│   ├── router/
│   │   └── index.js
│   ├── assets/
│   │   ├── tailwind.css
│   │   └── tag-chips.css
│   ├── components/
│   │   ├── BreadcrumbHeader.vue
│   │   ├── LoadingSpinner.vue
│   │   ├── MediaItemCard.vue
│   │   ├── PagePaginationBar.vue
│   │   ├── SelectionDetailOverlay.vue
│   │   ├── Sidebar.vue
│   │   ├── TagChipList.vue
│   │   ├── TagColorPicker.vue
│   │   ├── TagFormDialog.vue
│   │   ├── TagImportDialog.vue
│   │   ├── TagMenuDialog.vue
│   │   ├── ThumbCard.vue
│   │   └── TrashPageHeader.vue
│   ├── utils/
│   │   ├── pageConfig.js
│   │   └── tagColors.js
│   └── pages/
│       ├── HomePage.vue
│       ├── GalleryPage.vue
│       ├── CalendarOverview.vue
│       ├── BrowsePage.vue
│       ├── CategorySettingsPage.vue
│       ├── EmptyPage.vue
│       ├── SettingsPage.vue
│       └── TrashPage.vue
└── vue.config.js
```

## 4. 主要功能说明
### 4.1 上传与导入
- `GalleryPage` 提供多行文件夹导入 UI，可为每一行单独选择主分类
- 调用 `POST /api/import`
- 使用 `FormData` 传递 `files`、`last_modified_json`、`created_time_json`、`category_id`
- 前端会把根目录直下文件与首层嵌套子目录分别按每批 50 个文件拆分后顺序上传
- 导入进行中会显示“停止导入”按钮；点击后会中止当前前端请求，并停止继续提交后续批次，当前及未完成的文件夹会保留在导入表单中便于继续导入
- `/gallery` 路由启用 `meta.keepAlive`，切换到其他页面时不会销毁导入队列；返回后继续显示当前进度与停止按钮状态

### 4.2 日历总览
- `CalendarOverview` 获取 `GET /api/dates`
- 按 `year -> month` 做嵌套显示
- 点击月组进入 `/calendar/{date_group}` 浏览页

### 4.3 展示图库内容
- `BrowsePage` 调用 `GET /api/dates/{date_group}/items` 或 `GET /api/albums/by-path/{album_path:path}`
- 直图显示 `ThumbCard`，子目录显示相册封面并支持物理路径继续下钻
- 同时消费 `GET /api/system/page-config` 的浏览方式设置；当模式为 `paged` 时，瀑布流、列表和选择网格都会按当前视口高度分页，列表页支持每页 `10 / 20 / 50 / 100`；当模式为 `scroll` 时，还会读取固定窗口范围 `40 / 60 / ... / 200`，默认 `100`
- 瀑布流会随页面方向自动切换：横屏继续使用等高 justified flow，竖屏切换为 2 列等宽 masonry；分页模式也沿用同一套方向规则
- 浏览缓存缩略图通过 `POST /api/thumbnails/cache` 与 `GET /api/thumbnails/cache/status/{task_id}` 渐进生成和轮询；当 cache/temp 预览本身返回 `404` 时，BrowsePage 会立即触发带目标 `image_ids` 的 `POST /api/admin/refresh?mode=quick` 并回填最新 `cache_thumb_url`
- 选择模式详情浮层中的 Tag 使用 `TagChipList` 渲染，显色来自后端返回的 Tag 元数据字段，统一为 HEX8：
   - `color`
   - `border_color`
   - `background_color`
- 选择模式详情浮层中的文件名 / 主分类编辑会直接把 `PATCH /api/images/metadata` 返回的增量结果回写到当前 `items`；不会因为这两类修改重新调用整页列表接口或清空缩略图。
- 创建时间修改也不再触发整页重载：若图片仍属于当前 `date_group` 或当前相册路径，只做本地字段更新与重排；若已移出当前视图，则只从当前列表局部移除并刷新排布。

### 4.4 回收站浏览与页面配置
- `TrashPage` 调用 `GET /api/trash/items`
- 与 `BrowsePage` 共用 `PagePaginationBar` 和 `pageConfig.js`
- 当设置页切到“分页浏览”时，回收站瀑布流与选择网格也会分页，并在窗口缩放后按当前首个可见项重新定位页码；当设置页保持“滚动浏览”时，会使用同一份窗口范围配置做可见区前后预修复
- 回收站照片墙同样按页面方向切换布局：横屏使用等高 justified flow，竖屏使用 2 列等宽 masonry；页面不会插入额外空占位元素
- 回收站卡片常规浏览只消费 `cache_thumb_url` / `thumb_url`；若预览缺失则先显示骨架，再静默触发目标 `trash_entry_ids` 的 quick refresh。`/trash-media/...` 只在详情层缩略图失败时作为少量兜底原图使用
- TrashPage 首屏会先显示当前可展示条目，再异步调用 `POST /api/trash/reconcile` 做轻量对账；若对账结果改变列表，前端会在保留锚点的前提下静默刷新

### 4.5 文件名分析回写 Tag
- 前端保留文件名分析回写能力，可调用 `POST /api/images/tags/filename-match`
- 支持批量图片分析并回写 tags，前端会即时刷新当前选择项的标签显示
- 多选显示规则：优先显示公共标签；没有公共标签但存在差异时显示 `various`

### 4.6 Tag 菜单手动回写
- 选择模式详情浮层的 Tag 区末尾提供 `+` 按钮，点击后弹出 Tag 标签菜单
- 菜单顶部“现有标签”在多选时显示所选图片的公共标签，右侧 `x` 按钮可移除该标签
- 菜单输入框为空时，固定高度建议容器显示最近使用的 5 个标签（`last_used_at` 最新）
- 菜单输入框有内容时按 `name` 与 `display_name` 搜索，建议项显示 `display_name`
- 每条建议右侧提供 `+` 与笔形按钮：`+` 先写入当前弹层草稿，笔形按钮可打开标签元数据编辑弹窗
- “添加新标签”会先调用 `POST /api/tags/draft` 预占真实 `id/public_id`，再进入标签表单弹窗；取消时删除草稿，保存时通过 `PATCH /api/tags/{id}` 转正
- 标签表单弹窗支持 `name` 正则校验、`type` 下拉选择、Tag 预览、7 个预设配色，以及 HEX8 + HSV + 透明度取色器
- 菜单底部保留“添加新标签（预留）”入口，原“编辑标签”位置改为“自动标签”按钮
- “自动标签”在菜单内调用 `POST /api/images/tags/filename-match` 做预分析并合并到草稿，不会立即回写
- 菜单右下角提供“取消 / 确定”：
   - 取消或右上角关闭：丢弃草稿，不改动任何图片标签
   - 确定：对所有变更图片调用 `POST /api/images/tags/apply`（`merge_mode=replace`）一次性提交

### 4.7 管理与重建
- 交互按钮触发 `POST /api/admin/refresh`
- 后端当前返回 `{ mode, pruned, total_images, cache_deleted, regenerated, new_ingested, hash_conflicts, non_album_deduped, cleaned_paths }`

## 5. 前端路由说明 (`router/index.js`)
- `/` -> `HomePage`
- `/tags` -> `EmptyPage`
- `/gallery` -> `GalleryPage`（`meta.keepAlive = true`，保留导入页面实例）
- `/calendar` -> `CalendarOverview`
- `/calendar/:group` -> `BrowsePage`
- `/calendar/:group/:albumPath+` -> `BrowsePage`
- `/settings` -> `SettingsPage`
- `/settings/categories` -> `CategorySettingsPage`
- `/trash` -> `TrashPage`

* `App.vue` 会保持 `KeepAlive` 容器常驻，再单独渲染非保活路由；当前仅 `GalleryPage` 依赖该机制来保留导入状态，避免从 `/gallery` 切到普通页面时被意外卸载

* 两个 browse 路由共享 `meta.reuseKey = 'browse'`，用于复用同一个 `BrowsePage` 组件实例

* 具体文件中有嵌套路由、组件复用与参数处理

## 6. 构建与运行
### 6.1 安装依赖
```
cd frontend
npm install
```

### 6.2 开发模式
```
npm run serve
```
默认访问：http://localhost:8080

### 6.3 生产打包
```
npm run build
```
打包输出：`dist/`

### 6.4 Lint
```
npm run lint
```

## 7. 关键配置
- 当前页面组件与 `src/utils/pageConfig.js` 直接把 `API_BASE` 写为 `http://127.0.0.1:8000`
- `vue.config.js` 当前仅开启 `transpileDependencies`，未配置 `devServer.proxy`
- 前端当前是直连后端，不依赖本地代理；如果后端端口变化，需要同步更新 `API_BASE`
- `tailwind.config.js`：Tailwind 主题/路径

## 8. 常见问题与排查
1. 页面白屏或组件样式异常
   - 检查 `npm install` 是否成功，依赖缺失（如 `vue`, `vue-router`, `tailwindcss`）
   - 检查浏览器控制台 JS 错误
2. API 请求失败（跨域/404）
   - 确认后端 `uvicorn` 运行并端口正确
   - 确认页面内的 `API_BASE` 仍指向 `http://127.0.0.1:8000`
   - 如果你自行改为代理模式，再检查 `vue.config.js` 的 `devServer.proxy`
3. 上传消耗时间过长、卡顿
   - 可能是本地资源读取或后端处理较多，建议分批次上传
   - 检查后端 `import_files` 进度与日志
4. 缩略图不显示
   - 确认后端 `POST /api/import` 成功返回
   - 月份 / temp 缩略图 URL 形如 `/thumbnails/{hash}.webp`
   - 浏览 cache 缩略图 URL 形如 `/cache/{hash}_cache.webp`
   - 确保 `backend/temp` 或 `backend/data/cache` 中存在对应文件
5. 404 在 /calendar/{date_group} 或更深层相册路径
   - 确认日期组和相册路径在后端存在
   - 检查浏览页是否能正确解析 `album_path`

## 9. 补充说明
- 前端对后端 API 的依赖关系：
   - `/api/categories` 用于导入页主分类下拉、浏览页详情补充和主分类设置页
   - `/api/dates` 用于年月树
   - `/api/dates/{date_group}/items` 用于日历内容
   - `/api/albums/by-path/{album_path:path}` 用于物理路径相册详情
   - `/api/images/count` 可用于统计呈现
   - `/api/images/meta` 用于详情浮层补齐文件元数据
   - `/api/images/tags/filename-match` 用于文件名分析与 Tag 草稿预匹配
   - `/api/images/tags/apply` 用于标签菜单手动批量添加、覆盖或移除标签
   - `/api/tags/draft` 用于预占隐藏草稿 Tag
   - `/api/tags?sort_by=last_used_desc&limit=5` 用于输入为空时加载最近使用标签
   - `/api/tags/export/json` 与 `/api/tags/import/json` 用于设置页的 Tag JSON 导入导出
   - `/api/trash/items`、`/api/trash/reconcile`、`/api/trash/restore`、`/api/trash/hard-delete`、`DELETE /api/trash` 用于回收站页面
   - `/api/thumbnails/cache` 与 `/api/thumbnails/cache/status/{task_id}` 用于浏览缓存缩略图异步生成
   - `DELETE /api/cache` 用于设置页清理 temp/cache 缩略图
   - `/api/system/cache-thumb-setting` 与 `/api/system/month-cover-setting` 用于设置页尺寸配置
   - `/api/system/page-config` 用于读取/保存滚动浏览与分页浏览模式，以及滚动模式窗口范围
   - `/api/admin/refresh?mode=quick` 支持按 `image_ids` 或 `trash_entry_ids` 做目标 cache 修复
   - `/api/system/tag-match-setting` 用于读取/保存文件名匹配过滤配置
   - `/api/system/image-viewers` 与 `/api/system/viewer-preference` 用于设置页看图器偏好
- `ThumbCard` 负责显示缩略图，统一尺寸对齐
- `Sidebar` 负责导航历史分组与用户操作按钮

---
