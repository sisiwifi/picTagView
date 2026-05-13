# picTagView Frontend 技术说明书

本文档描述前端的当前页面结构、路由、共享浏览壳和运行约定，内容以 `frontend/src` 下的现行代码为准。

## 1. 项目位置与技术栈

- 项目目录：`D:\Python_projects\picTagView_main\frontend`
- 框架：Vue 3
- 路由：Vue Router 4
- 样式：Tailwind CSS
- 构建：Vue CLI 5
- 网络：原生 `fetch`

## 2. 目录结构

```text
frontend/
├── public/
├── src/
│   ├── App.vue
│   ├── main.js
│   ├── router/index.js
│   ├── assets/
│   ├── components/
│   ├── pages/
│   └── utils/
├── package.json
├── vue.config.js
└── README.md
```

关键目录当前分工：

- `src/pages/`：一级页、`BrowsePage.vue`、`TagOverviewPage.vue`、设置页等
- `src/components/`：详情浮层、Tag/收藏菜单、分页条、主分类和确认弹窗等
- `src/utils/commonBrowsePage.js`：统一浏览页契约
- `src/utils/pageConfig.js`：页面浏览模式读写与本地缓存
- `src/pages/topLevelPageConvention.js`：顶层页导航、统一搜索输入逻辑和顶层缩略图约定

## 3. 当前路由

| 路由 | 组件 | 说明 |
| --- | --- | --- |
| `/` | `HomePage.vue` | 主页仪表板：精确统计卡 + 连续滚动的可见 Tag 墙 |
| `/search` | `SearchPage.vue` | 单输入搜索、本地文件搜图、时间范围过滤与一级虚拟化预览 |
| `/search/results` | `BrowsePage.vue` | 完整搜索结果二级浏览，`browseContract = 'search-results'`，支持复用 `q` 与 `quick_hash` |
| `/tags` | `TagOverviewPage.vue` | 标签总览与编辑入口，页头固定在主滚动区顶部 |
| `/tags/:tagId` | `BrowsePage.vue` | 标签二级浏览，`browseContract = 'tag'` |
| `/gallery` | `GalleryPage.vue` | 图库管理父页，包含导入、刷新、最近导入预览、图库总览预览，`meta.keepAlive = true` |
| `/gallery/recent` | `BrowsePage.vue` | 最近导入二级浏览，`browseContract = 'gallery-recent'` |
| `/gallery/recent/:group/:albumPath+` | `BrowsePage.vue` | 最近导入中的相册层级浏览，仍使用 `browseContract = 'gallery-recent'` |
| `/gallery/all` | `BrowsePage.vue` | 图库总览二级浏览，`browseContract = 'gallery-all'` |
| `/gallery/all/:group/:albumPath+` | `BrowsePage.vue` | 图库总览中的相册层级浏览，仍使用 `browseContract = 'gallery-all'` |
| `/calendar` | `CalendarOverview.vue` | 日期总览 |
| `/calendar/:group` | `BrowsePage.vue` | 月份浏览 |
| `/calendar/:group/:albumPath+` | `BrowsePage.vue` | 相册层级浏览 |
| `/favorites` | `FavoritesPage.vue` | 收藏夹总览 |
| `/favorites/:collectionId` | `BrowsePage.vue` | 收藏夹二级浏览，`browseContract = 'collection'` |
| `/settings` | `SettingsPage.vue` | 设置页 |
| `/settings/categories` | `CategorySettingsPage.vue` | 主分类配置 |
| `/trash` | `BrowsePage.vue` | 回收站浏览，`browseContract = 'trash'` |

说明：

- `BrowsePage.vue` 在多个路由间通过 `meta.reuseKey = 'browse'` 复用实例。
- `GalleryPage.vue` 通过 `meta.keepAlive = true` 保留导入中的本地状态和队列。

## 4. 主要页面与交互

### 4.0 `HomePage.vue`

- 当前首页不再只是单个图片计数卡片，而是一个独立顶层仪表板。
- 顶部两张卡片分别显示精确统计值：
  - 按显示主分类过滤后的图片总数，点击进入 `/gallery/all`
  - 全局非草稿 Tag 总数，点击进入 `/tags`
- 下方标签墙通过 `GET /api/home/overview` 分页读取：
  - 仅统计显示主分类中的可见图片
  - 按 Tag 的可见图片数降序排列
  - 卡片点击进入 `/tags/:tagId`
- 标签墙使用本地虚拟化连续滚动网格，只渲染视口附近的方形卡片，并在接近底部时继续懒加载下一批 Tag。
- Tag 卡片采用更简洁的纯封面覆盖文案布局：移除额外角标和底部信息面板，主标题放大并居中，描述保持小号文字但同样居中。
- 当全部可见 Tag 都加载完成时，首页只显示一个会自动消失的浮动提示，而不再在底部长期占用一行状态位。
- 首页使用 `localStorage` 维护最近展示过的封面图片 id；每次进入首页时会把这段 history 传给后端，尽量为每个 Tag 换一批代表图，只在候选确实不足时才允许重复。
- 对于缺失 temp/cache 预览的代表图，首页会复用现有 targeted preview repair 链路：先调用 `POST /api/admin/refresh?mode=quick` 请求指定 image id 的预览修复，再通过 `GET /api/images/meta` 回填新的缩略图地址。

### 4.1 `GalleryPage.vue`

- 使用 `FolderImportDialog.vue` 管理多行文件夹导入。
- 每一行导入任务都可以单独指定主分类。
- 当前按 `50` 张图片分块上传到 `POST /api/import`，并用 `recent_import_mode = replace/append` 把同一次前端导入重新聚合成 recent 快照；recent 一级页优先读取后端快照中的 `successful_image_ids`。
- 导入过程中支持“停止导入”，通过 `AbortController` 中止当前请求并停止后续批次。
- `/gallery` 父页会在导入卡片下方展示“最近导入”和“图库总览”两条一级预览带：
  - 普通缩略图只显示图片本身，不叠加名称，也不额外加暗色遮罩
  - 如果总数超过当前展示容量，最后一格会复用顺序中的下一张图片作为跳转卡，而不是空白占位块
  - 点击普通缩略图打开只读详情浮层，点击最后一格或“查看全部”进入二级列表页
- 一级预览卡片会在封面资源来自 GIF / 动态 WEBP 时显示 `GIF` / `WEBP` 小标记；详情浮层沿用同一标记。
- 导入状态、进度和结果提示恢复为按需展开的紧凑反馈区，不再在页面空闲时预留固定大块空白。
- 页面激活时会检查月份缩略图缺失，并在需要时静默触发 `POST /api/admin/refresh`。

### 4.2 `SearchPage.vue`

- 是当前顶层搜索入口，而不是直接把全部结果放进 `BrowsePage.vue`。
- 输入框通过 `detectSearchMode()` 自动识别：
  - 普通文本 -> 文件名 / Tag 混合搜索
  - `name:xxx` 或 `$xxx` -> 文件名 搜索
  - `tag:xxx` 或 `#xxx` -> Tag 搜索
  - `file:xxx` -> 本地图片 quick hash 搜索；正常入口是点击输入框右侧“按图搜索”按钮上传单张图片，由前端自动写回 `file:文件名`
  - `import:YYYY-MM-DD HH:mm:ss~YYYY-MM-DD HH:mm:ss` -> 导入时间范围搜索
  - `create:YYYY-MM-DD HH:mm:ss~YYYY-MM-DD HH:mm:ss` -> 创建时间范围搜索
- 输入框右侧提供两个辅助入口：
  - “按图搜索”按钮：使用与页面其他操作一致的扁平圆角按钮样式，打开单文件选择框，调用 `POST /api/search/by-file`，并把 quick hash 搜索结果同步回搜索框与路由
  - “时间范围”按钮：使用与页面其他操作一致的扁平圆角按钮样式，打开 `SearchTimeRangeDialog.vue`，辅助生成 `import:` / `create:` 查询串
- 一级页不再固定只展示前 `3` 行，而是使用连续滚动的局部虚拟化网格；页面只渲染视口附近约 `3` 行加少量 overscan 的卡片。
- 搜索详情浮层中的“主分类”会显示分类名称；“匹配方式”会按搜索语义显示为“按文件搜索 / 文件名匹配 / 标签匹配 / 按导入时间搜索 / 按创建时间搜索”。
- 搜索主结果卡片只使用 temp/cache 缩略图作为预览来源；缺失时先显示占位，再通过 targeted refresh 拉起缩略图修复，不再用原图作为主预览兜底；修复后仍失败时进入“预览不可用”终态，避免无限加载。
- 如果搜索结果对应的是多帧图片，卡片和详情浮层会显示 `GIF` / `WEBP` 标记；标记依赖后端返回的 `is_animated + animation_meta`，其中 `animation_meta.format` 只在动图时返回，而不是前端自行猜文件后缀。
- 点击“查看全部”后，会带着 `q` 查询参数进入 `/search/results`；如果当前是 `file:` 搜索，还会一并带上 `quick_hash`，完整结果列表交给 `BrowsePage.vue` 的 `search-results` 契约处理。

### 4.3 `TagOverviewPage.vue`

- 当前不是占位页，而是完整的标签总览页。
- 页面顶栏固定在主滚动区顶部，长列表滚动时仍保留“增加标签 / 编辑标签”和统计摘要。
- 主要能力：
  - 按 `tag.name` 首字母分组
  - 每个字母分组支持局部 `name` 筛选，以及按内容高度折叠 / 展开
  - 侧栏展示使用次数 Top 10 和最近使用 Top 10
  - 新建标签时先调用 `/api/tags/draft`
  - `TagFormDialog.vue` 在 `name` 为空、格式非法或与现有标签重复时，会同时显示字段错误态和提交按钮附近的禁用原因提示
  - 编辑模式下支持直接打开 Tag 表单与删除确认；删除提示会明确说明“同步解除图片关联”，实际删除由后端统一事务完成
- 非编辑模式点击 Tag 会进入 `/tags/:tagId` 的二级浏览页。

### 4.4 `FavoritesPage.vue`

- 当前不是占位页，而是收藏夹总览页。
- 页面调用 `GET /api/collections` 获取可见收藏夹。
- 如果封面图片还没有缓存缩略图，会主动启动 `/api/thumbnails/cache` 队列并轮询状态。

### 4.5 `SettingsPage.vue`

- 当前已接入的设置项：
  - 浏览缓存缩略图尺寸
  - 月份封面尺寸
  - 页面浏览模式与滚动窗口范围
  - Tag JSON 导入导出
  - 内部“管理标签”二级面板：表格查看 `序号 / id / name / display_name / description / type / 样式预览`，支持列筛选、勾选、Shift 连选、Ctrl/Cmd + A 全选当前视图、分页切换、行末编辑、批量新增与批量删除
  - 图片查看器偏好
  - 主分类管理入口
  - 回收站入口
  - 夜间模式占位按钮
- 当前仍是占位的入口：
  - 夜间模式
- `SettingsPage.vue` 内部当前有两个二级面板状态：
  - `activePanel = 'tag-manager'`：标签管理面板，默认全量加载全部 Tag，也可切到分页模式；支持按列筛选、样式预览与行末编辑；批量删除需输入 8 位随机确认码；批量新增使用固定尺寸的三级弹窗表格，逐行填写 `name / display_name / description / type`，并按 7 组 chip 样式预设自动轮换默认值
  - `activePanel = 'tag-filter'`：保留的占位子面板，入口按钮当前仍被注释，不会在用户界面里显示
- 注意：后端已有 `/api/system/tag-match-setting`，但设置页目前没有实际 UI 去编辑它。

### 4.6 `BrowsePage.vue`

- 是当前最核心的共享浏览壳。
- 通过 `browseContract` 切换七类数据源：
  - `calendar`
  - `search-results`
  - `gallery-recent`
  - `gallery-all`
  - `collection`
  - `tag`
  - `trash`
- 当前复用的能力包括：
  - 面包屑页头
  - 默认 header 内置的统一筛选面板
  - 选择模式
  - 详情浮层
  - Tag 菜单与收藏菜单
  - 滚动/分页浏览模式
  - 预览修复与缓存缩略图生成
- BrowsePage 的网格卡片、列表缩略图和详情浮层会统一显示 GIF / 动态 WEBP 标记；数据源来自各浏览接口和 `/api/images/meta` 的同一组动图元信息字段。
- 所有 BrowsePage 路由的默认 header 都会提供一个“筛选”按钮，点击后打开带遮罩的二级筛选面板，并在面板打开期间锁定页面滚动。
- 当前筛选完全是前端本地过滤，基于当前路由已加载到页面的完整数据集重新计算可见条目，不额外请求新的 browse API 参数。
- 筛选维度固定为：标签、主分类、文件名、文件类型、导入时间、创建时间、文件大小。其中标签块优先级最高，展示当前视图出现过的全部标签，使用 Tag chip 呈现；未选标签会置灰，悬停可看 description。
- 标签筛选支持多选 OR；“无标签”会与普通标签做并集；主分类按当前页面出现过的分类多选；文件类型按扩展名多选；时间与大小支持只填单侧；筛选状态只保留在当前页面实例，不写入路由 query 或本地缓存。
- 相册项不参与筛选并始终保留，所以混合相册/图片的浏览页会只筛图片，不会把相册导航节点一起过滤掉。

更细的契约字段见 `commonBrowsePage.md`。

- `gallery-recent` 与 `gallery-all` 在相册模式下不再跳入 `/calendar/...`，而是保留在 `/gallery/...` 路由空间内，面包屑和返回行为也随之留在图库管理体系中。

## 5. 顶层导航与搜索约定

`src/pages/topLevelPageConvention.js` 当前负责：

- 顶层导航项 `TOP_LEVEL_NAV_ITEMS`
- 顶层缩略图边长约定 `thumbEdgePx = 400`
- 搜索模式识别：
  - `name:xxx` 或 `$xxx` -> 文件名搜索
  - `tag:xxx` 或 `#xxx` -> Tag 搜索
  - `file:xxx` -> 本地文件 / quick hash 搜索
  - `import:开始~结束` -> 导入时间范围搜索
  - `create:开始~结束` -> 创建时间范围搜索
  - 看起来像 `media/...` 的路径 -> 后端兼容路径搜索
  - 其他情况 -> 文件名 / Tag 混合搜索
- 搜索一级页使用连续滚动虚拟化预览；完整结果挂在 `/search/results`，并沿用顶层“搜索”导航高亮。
- 搜索结果显示文案映射
- 搜索请求参数生成与 `file` / 时间范围参数归一化
- 顶层页公用 CSS 变量

## 6. 统一浏览页契约

`src/utils/commonBrowsePage.js` 当前导出：

- `getCommonBrowsePageContract(contractName)`
- `normalizeBrowseItems(rawItems, contractName)`

已实现契约：

- `calendar`
- `search-results`
- `gallery-recent`
- `gallery-all`
- `collection`
- `tag`
- `trash`

各契约负责：

- 默认排序
- 面包屑
- 页头扩展动作
- 选择态按钮岛动作
- 详情浮层按钮策略
- 数据源请求
- 数据归一化
- 预览修复后的刷新策略

页面布局、选择状态、详情浮层状态、Tag/收藏菜单状态仍由 `BrowsePage.vue` 自己维护，不在契约内部。

## 7. 与后端的当前约定

### 7.1 API 地址

当前前端并没有通过代理访问后端，而是多处直接写死：

```js
const API_BASE = 'http://127.0.0.1:8000'
```

这类常量目前出现在：

- `src/pages/topLevelPageConvention.js`
- `src/utils/commonBrowsePage.js`
- `src/utils/pageConfig.js`
- `src/pages/BrowsePage.vue`
- `src/pages/SettingsPage.vue`
- `src/pages/CategorySettingsPage.vue`
- `src/pages/CalendarOverview.vue`

如果后端端口变化，需要同步修改这些位置。

其中 `HomePage.vue` 已改为复用 `topLevelPageConvention.js` 暴露的共享 `API_BASE`，不再单独维护一份常量。

### 7.2 页面配置

`src/utils/pageConfig.js` 当前与后端约定：

- `browse_mode`: `scroll | paged`
- `scroll_window_size`: `40, 60, ..., 200`

这些配置会作用到所有复用 `BrowsePage.vue` 的契约页，包括搜索结果、标签、收藏、图库、日期和回收站。

工具模块会：

- 从 `GET /api/system/page-config` 拉取配置
- 通过 `POST /api/system/page-config` 保存配置
- 在浏览器 `localStorage` 中缓存配置
- 保存后广播 `ptv:page-config-updated`

### 7.3 预览与缓存

- `FavoritesPage`、`CalendarOverview` 和 `BrowsePage` 都会使用 `POST /api/thumbnails/cache` 与 `GET /api/thumbnails/cache/status/{task_id}`。
- 当前前端使用了后端支持的 `page_token + generation + cursor` 协议。
- 共享浏览页的主卡片缺预览修复改为契约开关控制；`calendar`、`gallery-recent`、`gallery-all`、`collection`、`tag` 会自动调用 `POST /api/admin/refresh` 做定向修复。
- 上述非搜索契约在 targeted repair 结束后仍无预览时，会回退到卡片内原图；`search-results` 保持不回退，只显示终态提示。
- 多帧图片的 temp/cache 预览统一使用后端抽取的首帧，因此前端不再需要为 GIF 单独走原图兜底路径；原图查看行为继续沿用各页面既有的系统查看器 / 浏览器策略。

## 8. 构建与运行

### 8.1 安装依赖

```powershell
cd frontend
npm install
```

### 8.2 开发模式

```powershell
npm run serve
```

默认访问地址为 `http://localhost:8080`。

### 8.3 生产构建

```powershell
npm run build
```

### 8.4 Lint

```powershell
npm run lint
```

## 9. 当前注意事项

- 前端依赖后端先启动，否则大部分页面会直接请求失败。
- 当前 `vue.config.js` 没有启用代理配置。
- `GalleryPage` 的保活依赖 `App.vue` 保持 `KeepAlive` 容器常驻；如果后续调整路由渲染结构，需要特别注意这一点。
- 设置页只有 Tag JSON 导入导出，没有图形化的文件名自动打标设置入口；内部 `Tag过滤` 子面板目前仍是未开放的占位结构。
