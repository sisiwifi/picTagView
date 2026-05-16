# picTagView

本地图片管理系统，当前实现基于 FastAPI + SQLModel + SQLite + Vue 3。项目已经从基础导入页演进为一套完整的本地图库工作流：导入、刷新、日期与相册浏览、标签总览与标签二级浏览、收藏夹浏览、单输入搜索、主分类管理、回收站、缩略图缓存队列，以及图片元数据编辑。

## 当前能力

| 模块 | 当前实现 |
| --- | --- |
| 导入与去重 | Gallery 页按文件夹分批导入，后端按 `media/YYYY-MM/` 写入；同批次内完成哈希去重、相册链维护、图片主分类写入，以及可选的文件名自动打标 |
| 主页 | `/` 顶层页现在显示两个精确统计卡和一面连续滚动的 Tag 墙：图片总数按当前显示主分类过滤，Tag 总数保持全局；下方标签墙按显示主分类内的可见图片重新统计 Tag 使用量，并为每个 Tag 选择尽量轮换的代表图，以更简洁的居中封面卡片形式展示 |
| 图库管理 | `/gallery` 作为父页，同时展示“最近导入”和“图库总览”两条一级缩略图预览；recent 直接读取最近一次导入或 full-refresh 收编得到的成功图片全集，一级预览优先显示最新图片；普通缩略图直接打开只读详情，最后一格以图片承载“查看全部”跳转；当 `media` 根目录存在孤立图片或孤立相册时，导入卡片会提示刷新媒体库，且仅在导入或刷新进行中每 2 秒静默刷新 recent 预览 |
| 日期与相册浏览 | `CalendarOverview` 展示月份总览；`BrowsePage` 负责月份列表与相册层级浏览，数据来自 `/api/dates/*` 与 `/api/albums/*` |
| 标签系统 | 标签总览页支持按首字母分组、分组内按 name 过滤、固定页头、Top10 排行、草稿预占、编辑与删除；删除正式 Tag 时会在同一事务里同步解除图片关联。设置页还提供内部“管理标签”二级面板，支持列筛选、表格勾选、Shift 连选、样式预览、行内编辑、分页、批量新增和批量删除；标签二级页复用 `BrowsePage`，数据来自 `/api/tags/{tag_id}/images` |
| 收藏夹 | 收藏总览页展示全部可见收藏夹；收藏二级页复用 `BrowsePage`，支持批量添加/移除图片与手动选择封面 |
| 搜索 | 一级搜索页支持单输入检索、按图搜索和时间范围辅助输入，并以局部虚拟化网格预览当前视口附近结果；完整结果进入 `/search/results`，自动识别文件名、Tag、图片路径、quick hash 同图搜索以及导入/创建时间范围 |
| 选择模式与详情 | `BrowsePage` 内支持统一筛选面板、多选、详情浮层、Tag 菜单、收藏菜单；详情浮层会以图片自身快照继续承载当前编辑，不会因本地筛选失配立即清空，关闭详情后才统一刷新主网格；标签栏新增“↺”可把缺失的 `tag.name` 同步到文件名；`PATCH /api/images/metadata` 可直接修改文件名、主分类和创建时间 |
| 主分类 | 图片只保留一个生效主分类；默认主分类固定为 `id=1`，主分类设置页支持增删改、启停和批量操作 |
| 回收站 | 支持图片或相册移入回收站、还原、彻底删除、清空；回收站页复用 `BrowsePage` 的统一壳和选择态 |
| 缓存与预览修复 | `backend/temp/` 保存月份封面/临时缩略图，`backend/data/cache/` 保存浏览缓存缩略图；前端通过共享缓存队列按需生成并轮询结果 |
| 动图处理 | GIF、动态 WEBP 等多帧图片在导入、刷新和缓存生成时统一抽取首帧生成预览，并写入 `is_animated + animation_meta`；其中 `animation_meta` 只在动图时保存 `frame_count / format`，一级卡片、`BrowsePage` 卡片/列表和详情浮层会显示 `GIF` / `WEBP` 标记 |

## 架构概览

### 后端

- 入口：`backend/app/main.py`
- 框架：FastAPI
- ORM：SQLModel / SQLAlchemy
- 数据库：SQLite，默认文件为 `backend/data/app.db`
- 静态挂载：
  - `/thumbnails` -> `backend/temp`
  - `/cache` -> `backend/data/cache`
  - `/media` -> `media`
  - `/trash-media` -> `trash`
  - `/viewer-icons` -> `backend/data/viewer_icons`

### 前端

- 工程：Vue CLI + Vue 3 + Vue Router
- 样式：Tailwind CSS
- 网络：页面直接使用 `fetch` 调后端 API
- 当前约定：前端直接连接 `http://127.0.0.1:8000`，没有配置 `devServer.proxy`

## 顶层页面与路由

| 路由 | 组件 | 说明 |
| --- | --- | --- |
| `/` | `HomePage.vue` | 主页仪表板：两张精确统计卡 + 可见 Tag 连续滚动标签墙 |
| `/search` | `SearchPage.vue` | 单输入搜索与一级预览 |
| `/search/results` | `BrowsePage.vue` | 完整搜索结果二级浏览，`browseContract = 'search-results'` |
| `/tags` | `TagOverviewPage.vue` | 标签总览，页头固定在主滚动区顶部 |
| `/tags/:tagId` | `BrowsePage.vue` | 标签二级浏览 |
| `/gallery` | `GalleryPage.vue` | 图库管理父页：导入、刷新、最近导入预览、图库总览预览 |
| `/gallery/recent` | `BrowsePage.vue` | 最近导入二级浏览 |
| `/gallery/recent/:group/:albumPath+` | `BrowsePage.vue` | 最近导入中的相册层级浏览 |
| `/gallery/all` | `BrowsePage.vue` | 图库总览二级浏览 |
| `/gallery/all/:group/:albumPath+` | `BrowsePage.vue` | 图库总览中的相册层级浏览 |
| `/calendar` | `CalendarOverview.vue` | 日期总览 |
| `/calendar/:group` | `BrowsePage.vue` | 月份浏览 |
| `/calendar/:group/:albumPath+` | `BrowsePage.vue` | 相册层级浏览 |
| `/favorites` | `FavoritesPage.vue` | 收藏夹总览 |
| `/favorites/:collectionId` | `BrowsePage.vue` | 收藏夹二级浏览 |
| `/settings` | `SettingsPage.vue` | 设置页 |
| `/settings/categories` | `CategorySettingsPage.vue` | 主分类管理 |
| `/trash` | `BrowsePage.vue` | 回收站浏览 |

`BrowsePage.vue` 通过 `browseContract` 在 `calendar`、`search-results`、`gallery-recent`、`gallery-all`、`collection`、`tag`、`trash` 七种模式之间切换，统一复用布局、分页/滚动配置、默认 header 筛选面板、选择态、详情浮层和预览修复流程。更细的契约说明见 `frontend/commonBrowsePage.md`。

## 目录说明

```text
picTagView_main/
├── backend/                    # FastAPI 后端
│   ├── app/                    # API、模型、服务与配置
│   ├── data/                   # app.db、app_settings.json、cache、viewer_icons
│   ├── temp/                   # 月份封面与临时缩略图
│   ├── tests/                  # 后端测试
│   ├── api_services.md         # API 与服务层说明
│   └── techReadme.md           # 后端技术说明
├── frontend/                   # Vue 前端
│   ├── src/pages/              # 顶层页与 BrowsePage
│   ├── src/components/         # 通用组件与对话框
│   ├── src/utils/              # 页面契约、页面配置、颜色工具
│   ├── Frontend_README.md      # 前端说明
│   └── commonBrowsePage.md     # 统一浏览页契约说明
├── media/                      # 已入库媒体目录
├── trash/                      # 回收站物理目录
└── build/start_project.bat     # 一键启动脚本
```

首次启动时，`backend/app/core/config.py` 会自动创建 `backend/data`、`backend/temp`、`backend/data/cache`、`backend/data/viewer_icons`、`media`、`trash` 等运行时目录。

## 启动与开发

### 1. 安装依赖

项目的批处理脚本约定后端虚拟环境位于仓库根目录 `.venv`。

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -r backend\requirements.txt

cd frontend
npm install
cd ..
```

### 2. 一键启动

```powershell
build\start_project.bat
```

脚本会：

1. 使用根目录 `.venv` 启动后端 `uvicorn app.main:app --reload`
2. 检查后端健康接口 `http://127.0.0.1:8000/`
3. 启动前端 `npm run serve`

### 3. 手动启动

```powershell
cd backend
..\.venv\Scripts\python -m uvicorn app.main:app --reload
```

```powershell
cd frontend
npm run serve
```

默认地址：

- 后端：`http://127.0.0.1:8000`
- 前端：`http://localhost:8080`

## 便携打包

仓库内提供了一个 Windows 便携打包脚本：[build/package_portable.py](build/package_portable.py)。它会先构建前端，再把后端代码、前端静态产物和便携 Python 运行时组装成一个可搬运的 ZIP。

这个 ZIP 只包含程序本身，不包含 `media`、`backend/temp`、`backend/data/cache`、数据库等运行内容；用户解压后首次启动时，程序会自动创建这些运行目录。

便携包现在会额外把 `build/tags_export.json` 复制到压缩包根目录的 `tags_export.json`。它只作为可选导入源保留，首次启动不会自动导入；如需使用，请在程序内按需手动导入。

打包脚本默认直接使用当前项目 `.venv` 对应的 Python 基座和已安装依赖生成便携运行时；如果你已经准备好了现成的便携 Python 运行时目录，也可以放到 `build\runtime\python` 或通过 `PORTABLE_PYTHON_DIR` 指定，然后执行：

```powershell
build\package_portable.bat
```

也可以直接调用：

```powershell
python build\package_portable.py --runtime-python-dir D:\path\to\portable-python
```

打包后的目录会包含 `start.vbs` 和 `start.bat`。推荐双击 `start.vbs` 进行静默启动；`start.bat` 作为兼容入口会转调到同一个静默启动器。启动后会以独立管理窗口打开前端界面，不再弹出前后端 CLI 窗口。

解压后的根目录还会包含 `config.json`，当前可通过 `backend_port` 配置后端端口。关闭这个独立管理窗口后，启动器会同步停止后端服务。

## 当前运行约定

- 前端的 API 基址现在统一从 `runtime-config.js` 读取：开发环境默认指向 `http://127.0.0.1:8000`，便携包在启动时会把它改成同源地址；`HomePage.vue`、`BrowsePage.vue`、`SettingsPage.vue`、`CategorySettingsPage.vue`、`CalendarOverview.vue` 等页面都已经收口到 `topLevelPageConvention.js` 暴露的共享 `API_BASE`。
- `POST /api/admin/refresh?mode=full` 现在会先扫描并收编 `media` 根目录下不符合 `media/YYYY-MM/...` 结构的孤立图片和孤立相册，再做全库路径对账与补元数据；图库管理页通过 `GET /api/admin/orphan-media-status` 决定是否提示“媒体库存在孤立文件，请刷新媒体库”。
- 页面配置由 `backend/data/app_settings.json` 持久化，当前包含：
  - 浏览缓存缩略图短边尺寸
  - 月份封面尺寸
  - 页面浏览模式与滚动窗口范围
  - 文件名自动打标设置 `tag_match_setting`
- 搜索当前采用两段式交互：`/search` 只负责输入、模式识别和一级预览，完整结果列表复用 `BrowsePage.vue` 挂在 `/search/results?q=...`。
- 文件名自动打标已经接入导入流程和手动文件名匹配接口，但当前前端设置页还没有图形化配置入口；如需调整，只能通过后端 API 或 `app_settings.json`。
- 标签草稿通过 `POST /api/tags/draft` 预占，草稿标签会被列表、导出和打标接口过滤；保存时通过 `PATCH /api/tags/{id}` 转正。
- 删除正式 Tag 时，后端会在同一数据库事务中同步清理 `ImageAsset.tags` 里的对应 id；设置页“管理标签”面板支持批量删除，删除前必须输入 8 位随机确认码。
- 设置页标签管理除了导出标签 / 导入标签 / 管理标签三枚纵向按钮，还提供内部二级面板：默认全量加载全部 Tag，可切到分页模式；表格支持列级筛选、样式预览和行末编辑；批量新增使用固定尺寸的表格式弹窗，逐行填写 `name / display_name / description / type`，并按 7 组 chip 样式预设自动轮换默认值。
- 标签表单在 `name` 为空、格式非法或与现有标签重复时，会同时给出字段错误态和提交按钮附近的禁用原因提示，而不是只禁用确认按钮。
- 多帧图片当前统一以首帧作为 temp/cache 预览来源；前端不会再把 GIF 原文件直接拿来充当主卡片预览，只会在原图查看时交给系统查看器或浏览器按既有行为打开原文件。

## 文档索引

- [后端 API 与服务说明](backend/api_services.md)
- [后端技术说明](backend/techReadme.md)
- [前端技术说明](frontend/Frontend_README.md)
- [统一浏览页契约](frontend/commonBrowsePage.md)
