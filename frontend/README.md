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
| `/` | `HomePage.vue` | 首页统计 |
| `/search` | `SearchPage.vue` | 单输入搜索 |
| `/tags` | `TagOverviewPage.vue` | 标签总览与编辑入口 |
| `/tags/:tagId` | `BrowsePage.vue` | 标签二级浏览，`browseContract = 'tag'` |
| `/gallery` | `GalleryPage.vue` | 导入与刷新，`meta.keepAlive = true` |
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

### 4.1 `GalleryPage.vue`

- 使用 `FolderImportDialog.vue` 管理多行文件夹导入。
- 每一行导入任务都可以单独指定主分类。
- 当前按 `50` 张图片分块上传到 `POST /api/import`。
- 导入过程中支持“停止导入”，通过 `AbortController` 中止当前请求并停止后续批次。
- 页面激活时会检查月份缩略图缺失，并在需要时静默触发 `POST /api/admin/refresh`。

### 4.2 `TagOverviewPage.vue`

- 当前不是占位页，而是完整的标签总览页。
- 主要能力：
  - 按 `tag.name` 首字母分组
  - 侧栏展示使用次数 Top 10 和最近使用 Top 10
  - 新建标签时先调用 `/api/tags/draft`
  - 编辑模式下支持直接打开 Tag 表单与删除确认
- 非编辑模式点击 Tag 会进入 `/tags/:tagId` 的二级浏览页。

### 4.3 `FavoritesPage.vue`

- 当前不是占位页，而是收藏夹总览页。
- 页面调用 `GET /api/collections` 获取可见收藏夹。
- 如果封面图片还没有缓存缩略图，会主动启动 `/api/thumbnails/cache` 队列并轮询状态。

### 4.4 `SettingsPage.vue`

- 当前已接入的设置项：
  - 浏览缓存缩略图尺寸
  - 月份封面尺寸
  - 页面浏览模式与滚动窗口范围
  - Tag JSON 导入导出
  - 图片查看器偏好
  - 主分类管理入口
  - 回收站入口
- 当前仍是占位的入口：
  - 夜间模式
  - `Tag过滤` 二级页
- 注意：后端已有 `/api/system/tag-match-setting`，但设置页目前没有实际 UI 去编辑它。

### 4.5 `BrowsePage.vue`

- 是当前最核心的共享浏览壳。
- 通过 `browseContract` 切换四类数据源：
  - `calendar`
  - `collection`
  - `tag`
  - `trash`
- 当前复用的能力包括：
  - 面包屑页头
  - 选择模式
  - 详情浮层
  - Tag 菜单与收藏菜单
  - 滚动/分页浏览模式
  - 预览修复与缓存缩略图生成

更细的契约字段见 `commonBrowsePage.md`。

## 5. 顶层导航与搜索约定

`src/pages/topLevelPageConvention.js` 当前负责：

- 顶层导航项 `TOP_LEVEL_NAV_ITEMS`
- 顶层缩略图边长约定 `thumbEdgePx = 400`
- 搜索模式识别：
  - `tag:xxx` 或 `#xxx` -> Tag 搜索
  - `path:...` 或看起来像 `media/...` 的路径 -> 路径搜索
  - 其他情况 -> 文件名 / Tag 混合搜索
- 搜索结果显示文案映射
- 顶层页公用 CSS 变量

## 6. 统一浏览页契约

`src/utils/commonBrowsePage.js` 当前导出：

- `getCommonBrowsePageContract(contractName)`
- `normalizeBrowseItems(rawItems, contractName)`

已实现契约：

- `calendar`
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
- 多个页面文件内的本地常量

如果后端端口变化，需要同步修改这些位置。

### 7.2 页面配置

`src/utils/pageConfig.js` 当前与后端约定：

- `browse_mode`: `scroll | paged`
- `scroll_window_size`: `40, 60, ..., 200`

工具模块会：

- 从 `GET /api/system/page-config` 拉取配置
- 通过 `POST /api/system/page-config` 保存配置
- 在浏览器 `localStorage` 中缓存配置
- 保存后广播 `ptv:page-config-updated`

### 7.3 预览与缓存

- `FavoritesPage` 和 `BrowsePage` 都会使用 `POST /api/thumbnails/cache` 与 `GET /api/thumbnails/cache/status/{task_id}`。
- 当前前端使用了后端支持的 `page_token + generation + cursor` 协议。
- 浏览页检测到预览缺失时，会调用 `POST /api/admin/refresh` 做定向修复，而不是盲目全量刷新。

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
- 设置页只有 Tag JSON 导入导出，没有图形化的文件名自动打标设置入口。
