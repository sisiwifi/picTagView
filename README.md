# picTagView

本地图片管理系统，当前实现基于 FastAPI + SQLModel + SQLite + Vue 3。项目已经从基础导入页演进为一套完整的本地图库工作流：导入、刷新、日期与相册浏览、标签总览与标签二级浏览、收藏夹浏览、单输入搜索、主分类管理、回收站、缩略图缓存队列，以及图片元数据编辑。

## 当前能力

| 模块 | 当前实现 |
| --- | --- |
| 导入与去重 | Gallery 页按文件夹分批导入，后端按 `media/YYYY-MM/` 写入；同批次内完成哈希去重、相册链维护、图片主分类写入，以及可选的文件名自动打标 |
| 日期与相册浏览 | `CalendarOverview` 展示月份总览；`BrowsePage` 负责月份列表与相册层级浏览，数据来自 `/api/dates/*` 与 `/api/albums/*` |
| 标签系统 | 标签总览页支持按首字母分组、Top10 排行、草稿预占、编辑、删除、JSON 导入导出；标签二级页复用 `BrowsePage`，数据来自 `/api/tags/{tag_id}/images` |
| 收藏夹 | 收藏总览页展示全部可见收藏夹；收藏二级页复用 `BrowsePage`，支持批量添加/移除图片与手动选择封面 |
| 搜索 | 一级搜索页支持单输入检索，自动识别文件名、Tag 与图片路径；路径模式会先定位源图片，再按 `quick_hash` 查找同图 |
| 选择模式与详情 | `BrowsePage` 内支持多选、详情浮层、Tag 菜单、收藏菜单；`PATCH /api/images/metadata` 可直接修改文件名、主分类和创建时间 |
| 主分类 | 图片只保留一个生效主分类；默认主分类固定为 `id=1`，主分类设置页支持增删改、启停和批量操作 |
| 回收站 | 支持图片或相册移入回收站、还原、彻底删除、清空；回收站页复用 `BrowsePage` 的统一壳和选择态 |
| 缓存与预览修复 | `backend/temp/` 保存月份封面/临时缩略图，`backend/data/cache/` 保存浏览缓存缩略图；前端通过共享缓存队列按需生成并轮询结果 |

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
| `/` | `HomePage.vue` | 首页统计 |
| `/search` | `SearchPage.vue` | 单输入搜索 |
| `/tags` | `TagOverviewPage.vue` | 标签总览 |
| `/tags/:tagId` | `BrowsePage.vue` | 标签二级浏览 |
| `/gallery` | `GalleryPage.vue` | 导入与全量刷新 |
| `/calendar` | `CalendarOverview.vue` | 日期总览 |
| `/calendar/:group` | `BrowsePage.vue` | 月份浏览 |
| `/calendar/:group/:albumPath+` | `BrowsePage.vue` | 相册层级浏览 |
| `/favorites` | `FavoritesPage.vue` | 收藏夹总览 |
| `/favorites/:collectionId` | `BrowsePage.vue` | 收藏夹二级浏览 |
| `/settings` | `SettingsPage.vue` | 设置页 |
| `/settings/categories` | `CategorySettingsPage.vue` | 主分类管理 |
| `/trash` | `BrowsePage.vue` | 回收站浏览 |

`BrowsePage.vue` 通过 `browseContract` 在 `calendar`、`collection`、`tag`、`trash` 四种模式之间切换，统一复用布局、分页/滚动配置、选择态、详情浮层和预览修复流程。更细的契约说明见 `frontend/commonBrowsePage.md`。

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
│   ├── README.md               # 前端说明
│   └── commonBrowsePage.md     # 统一浏览页契约说明
├── media/                      # 已入库媒体目录
├── trash/                      # 回收站物理目录
└── build/start_project.bat     # 一键启动脚本
```

首次启动时，`backend/app/core/config.py` 会自动创建 `backend/data`、`backend/temp`、`media`、`trash` 等运行时目录。

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

## 当前运行约定

- 前端多个文件内直接写死 `API_BASE = 'http://127.0.0.1:8000'`，切换后端端口时需要同步修改代码。
- 页面配置由 `backend/data/app_settings.json` 持久化，当前包含：
  - 浏览缓存缩略图短边尺寸
  - 月份封面尺寸
  - 页面浏览模式与滚动窗口范围
  - 文件名自动打标设置 `tag_match_setting`
- 文件名自动打标已经接入导入流程和手动文件名匹配接口，但当前前端设置页还没有图形化配置入口；如需调整，只能通过后端 API 或 `app_settings.json`。
- 标签草稿通过 `POST /api/tags/draft` 预占，草稿标签会被列表、导出和打标接口过滤；保存时通过 `PATCH /api/tags/{id}` 转正。

## 文档索引

- [后端 API 与服务说明](backend/api_services.md)
- [后端技术说明](backend/techReadme.md)
- [前端技术说明](frontend/README.md)
- [统一浏览页契约](frontend/commonBrowsePage.md)
