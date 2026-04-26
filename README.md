# picTagView

本地图片管理系统，基于 FastAPI + SQLModel + SQLite + Vue 3。

当前版本已经演进为一套完整的本地图库工作流：导入、去重、日期浏览、相册浏览、选择模式批处理、标签元数据编辑、主分类管理、独立回收站，以及多级缩略图缓存与刷新修复。

---

## 功能概览

| 模块 | 当前能力 |
| --- | --- |
| 导入与去重 | 支持文件夹导入，按日期写入 `media/YYYY-MM/`；维护 SHA-256 与 quick hash；刷新和恢复链路复用相同去重规则 |
| 日期与相册浏览 | 支持 CalendarOverview、按月份浏览、按相册路径浏览；相册显示状态、计数与封面由可见图片派生 |
| 页面配置与分页浏览 | 设置页可切换“滚动浏览 / 分页浏览”；BrowsePage 与 TrashPage 会在瀑布流、选择网格与列表（Browse）下按当前视口高度自动分页，并在缩放后尽量保持当前首张可见图附近 |
| 选择模式 | 支持瀑布流 / 网格 / 列表切换、窗口化渲染、Ctrl/Shift 多选、拖选、详情浮层与批量操作；右下角操作岛在窄屏下保持单行紧凑布局，并可向页面边缘收拢 |
| 信息区切换 | 选择模式下点击卡片底部信息区，可在文件名和 Tag 显示之间切换；Tag 采用当前 chip 样式，单行横向排列，超出隐藏并保留隐藏滚动条的横向滚动 |
| 标签系统 | 支持最近使用标签、搜索已有标签、自动文件名匹配、新增/编辑标签、标签 JSON 导入导出 |
| 标签编辑 | 支持真实预占 `public_id`、`name` 格式校验、`type` 下拉、Tag 预览、7 个预设配色，以及 HEX8 + HSV + 透明度取色 |
| 主分类 | 图片主分类由 `Category` 管理，支持默认分类回退、启用/停用、使用计数同步与配置页管理 |
| 回收站 | 支持图片/相册移入回收站、批量还原、彻底删除、清空回收站；回收站页复用选择模式与详情浮层交互 |
| 缩略图与缓存 | 使用 `backend/temp/` 管理月份封面/临时预览，使用 `backend/data/cache/` 管理浏览缓存缩略图 |
| 刷新与修复 | 支持库刷新、孤立数据清理、缺失预览补齐、未入库媒体收编、哈希索引重建 |

---

## 技术栈

### 后端

| 组件 | 说明 |
| --- | --- |
| FastAPI | REST API 与应用入口 |
| SQLModel / SQLAlchemy | 模型、查询与事务 |
| SQLite | 本地数据库，默认在 `backend/data/app.db` |
| OpenCV / numpy | 图像读取、尺寸识别、缩略图生成 |
| Uvicorn | 本地开发服务器 |

### 前端

| 组件 | 说明 |
| --- | --- |
| Vue 3 | 响应式 UI |
| Vue Router | 页面路由 |
| Tailwind CSS v3 | 样式基础设施 |
| Vue CLI | 开发、构建与 lint |

---

## 当前目录结构

```text
picTagView_main/
├── backend/                         # 后端服务
│   ├── app/                         # FastAPI 应用主体
│   │   ├── api/                     # API 定义层
│   │   │   ├── common.py            # 通用接口参数与工具
│   │   │   ├── routes.py            # 汇总并注册全部路由
│   │   │   ├── schemas.py           # 请求与响应数据结构
│   │   │   └── routers/             # 按功能拆分的接口路由
│   │   │       ├── albums.py        # 相册浏览与目录相关接口
│   │   │       ├── basic.py         # 导入、刷新、基础图片接口
│   │   │       ├── cache.py         # 浏览缓存与缩略图队列接口
│   │   │       ├── categories.py    # 主分类配置与统计接口
│   │   │       ├── dates.py         # 日期总览与月份浏览接口
│   │   │       ├── images.py        # 图片详情、批量操作接口
│   │   │       ├── system.py        # 系统设置与查看器配置接口
│   │   │       ├── tags.py          # Tag 查询、编辑、导入导出接口
│   │   │       └── trash.py         # 回收站浏览与恢复接口
│   │   ├── core/                    # 核心配置
│   │   │   └── config.py            # 应用配置与环境变量读取
│   │   ├── db/                      # 数据库连接
│   │   │   └── session.py           # Session 与引擎初始化
│   │   ├── models/                  # 数据模型
│   │   │   ├── album.py             # 相册节点模型
│   │   │   ├── album_image.py       # 相册与图片关联模型
│   │   │   ├── category.py          # 主分类模型
│   │   │   ├── image_asset.py       # 图片资源主表
│   │   │   ├── soft_delete.py       # 软删除相关基础字段
│   │   │   ├── tag.py               # 标签模型
│   │   │   └── trash_entry.py       # 回收站条目模型
│   │   ├── services/                # 业务服务层
│   │   │   ├── app_settings_service.py      # 应用设置读写
│   │   │   ├── cache_thumb_service.py       # 缓存缩略图管理
│   │   │   ├── category_service.py          # 主分类业务逻辑
│   │   │   ├── file_scanner.py              # 文件扫描与识别
│   │   │   ├── hash_service.py              # 哈希计算与去重
│   │   │   ├── import_service.py            # 导入流程封装
│   │   │   ├── parallel_processor.py        # 并行处理调度
│   │   │   ├── thumbnail_service.py         # 缩略图生成
│   │   │   ├── trash_service.py             # 回收站处理
│   │   │   ├── viewer_service.py            # 查看器与打开路径逻辑
│   │   │   ├── visible_album_service.py     # 可见相册与封面派生
│   │   │   └── imports/                     # 导入子流程拆分
│   │   │       ├── helpers.py               # 导入辅助函数
│   │   │       ├── hash_index.py            # 哈希索引维护
│   │   │       ├── maintenance.py           # 刷新与修复维护
│   │   │       └── pipeline.py              # 导入主流水线
│   │   ├── __init__.py               # 后端应用包标记
│   │   └── main.py                   # 应用入口
│   ├── data/                         # 运行时数据
│   │   ├── app.db                    # SQLite 数据库文件
│   │   ├── app_settings.json         # 应用设置持久化文件
│   │   ├── cache/                    # 浏览缓存缩略图目录
│   │   └── viewer_icons/             # 查看器图标资源
│   ├── scripts/                      # 维护脚本目录
│   ├── temp/                         # 临时文件与封面缓存
│   ├── tests/                        # 后端测试
│   ├── api_services.md               # API 与服务层说明
│   ├── Dockerfile                    # 后端容器构建文件
│   ├── requirements.txt              # Python 依赖列表
│   └── techReadme.md                 # 后端技术说明文档
├── build/                            # 启动脚本目录
│   └── start_project.bat             # 一键启动脚本
├── frontend/                         # 前端工程
│   ├── public/                       # 静态公开资源
│   ├── src/                          # 前端源码
│   │   ├── assets/                   # 样式与字体资源
│   │   │   ├── fonts/                # 字体文件
│   │   │   ├── tag-chips.css         # Tag chip 样式
│   │   │   └── tailwind.css          # Tailwind 基础样式入口
│   │   ├── components/               # 通用组件
│   │   │   ├── ActionProgressOverlay.vue   # 长操作进度遮罩
│   │   │   ├── BreadcrumbHeader.vue        # 面包屑标题栏
│   │   │   ├── CategoryFormDialog.vue      # 主分类编辑弹窗
│   │   │   ├── ConfirmationDialog.vue      # 确认对话框
│   │   │   ├── FolderImportDialog.vue      # 文件夹导入弹窗
│   │   │   ├── LoadingSpinner.vue          # 加载动画组件
│   │   │   ├── MediaItemCard.vue           # 媒体卡片
│   │   │   ├── PagePaginationBar.vue       # 通用分页条
│   │   │   ├── SelectionDetailOverlay.vue   # 选择详情浮层
│   │   │   ├── Sidebar.vue                 # 侧边栏导航
│   │   │   ├── TagChipList.vue             # Tag chip 列表
│   │   │   ├── TagColorPicker.vue          # Tag 颜色选择器
│   │   │   ├── TagFormDialog.vue           # Tag 编辑弹窗
│   │   │   ├── TagImportDialog.vue         # Tag 导入弹窗
│   │   │   ├── TagMenuDialog.vue           # 批量 Tag 菜单
│   │   │   ├── ThumbCard.vue               # 缩略图卡片
│   │   │   └── TrashPageHeader.vue         # 回收站页头部
│   │   ├── pages/                    # 页面视图
│   │   │   ├── BrowsePage.vue        # 月份 / 相册浏览主页面
│   │   │   ├── CalendarOverview.vue  # 日期总览页
│   │   │   ├── CategorySettingsPage.vue    # 主分类设置页
│   │   │   ├── EmptyPage.vue        # 空状态占位页
│   │   │   ├── GalleryPage.vue      # 导入与图库入口页
│   │   │   ├── HomePage.vue         # 首页概览
│   │   │   ├── SettingsPage.vue     # 系统设置页
│   │   │   └── TrashPage.vue        # 回收站页
│   │   ├── router/                  # 路由配置
│   │   │   └── index.js             # 路由入口
│   │   ├── utils/                   # 前端工具函数
│   │   │   ├── pageConfig.js        # 页面浏览模式设置工具
│   │   │   └── tagColors.js         # Tag 颜色处理工具
│   │   ├── App.vue                  # 根组件
│   │   └── main.js                  # 前端入口
│   ├── package.json                 # 前端脚本与依赖配置
│   ├── package-lock.json            # 依赖锁定文件
│   ├── postcss.config.js            # PostCSS 配置
│   ├── tailwind.config.js           # Tailwind 配置
│   └── vue.config.js               # Vue CLI 配置
├── media/                            # 导入后的媒体目录
├── trash/                            # 回收站目录
└── README.md                         # 项目说明文档
```

> `media/` 与 `trash/` 是运行时目录，会随着实际导入内容与用户操作持续变化。

---

## 后端模块概览

### API 层

- `backend/app/api/routes.py`
  - 聚合所有业务 router。
- `backend/app/api/routers/basic.py`
  - 导入、刷新、图片元信息等基础接口。
- `backend/app/api/routers/dates.py`
  - 日期总览与月份浏览接口。
- `backend/app/api/routers/albums.py`
  - 相册路径浏览、层级读取与打开目录。
- `backend/app/api/routers/images.py`
  - 图片打开、批量打 tag、文件名匹配等接口。
- `backend/app/api/routers/tags.py`
  - Tag 查询、创建、编辑、导入导出与草稿预占接口。
- `backend/app/api/routers/categories.py`
  - 主分类配置与计数维护接口。
- `backend/app/api/routers/cache.py`
  - 浏览缓存缩略图 generation 队列。
- `backend/app/api/routers/system.py`
  - 应用设置、页面浏览模式与查看器设置等系统接口。
- `backend/app/api/routers/trash.py`
  - 回收站浏览、移动、还原与硬删除接口。

### 数据模型

- `ImageAsset`
  - 图片主表，保存哈希、尺寸、`media_path`、`tags`、`album` 等核心信息。
- `Album`
  - 树形相册节点。
- `AlbumImage`
  - 相册与图片的关联表。
- `Tag`
  - 标签标准名、展示名、类型、描述与显色元数据。
- `Category`
  - 图片主分类配置。
- `TrashEntry`
  - 回收站条目与 payload 元数据。

### 服务层

- `services/imports/pipeline.py`
  - 导入主流程。
- `services/imports/maintenance.py`
  - 刷新、收编与修复逻辑。
- `services/imports/hash_index.py`
  - 哈希索引缓存维护。
- `services/parallel_processor.py`
  - 并行处理图像、哈希与缩略图。
- `services/cache_thumb_service.py` / `services/thumbnail_service.py`
  - 缩略图生成与缓存策略。
- `services/visible_album_service.py`
  - 相册可见性、派生计数与封面逻辑。
- `services/trash_service.py`
  - 删除到回收站、还原与彻底删除。
- `services/app_settings_service.py`
  - 应用设置持久化到 `backend/data/app_settings.json`，包括缓存尺寸、月份封面尺寸、文件名匹配配置与页面浏览模式。

---

## 前端模块概览

### 页面

- `HomePage.vue`
  - 首页摘要。
- `GalleryPage.vue`
  - 导入、刷新与任务入口。
- `CalendarOverview.vue`
  - 日期总览页。
- `BrowsePage.vue`
  - 月份/相册浏览主页面，也是选择模式、Tag 菜单和标签编辑的核心页面；支持滚动浏览与分页浏览两种模式。
- `CategorySettingsPage.vue`
  - 主分类配置页。
- `SettingsPage.vue`
  - 系统设置、页面配置、标签导入导出、查看器配置等。
- `TrashPage.vue`
  - 回收站主页面；支持滚动浏览与分页浏览两种模式。

### 组件

- `MediaItemCard.vue`
  - 选择模式卡片，支持文件名 / Tag chip 切换。
- `SelectionDetailOverlay.vue`
  - 选择详情浮层与快捷操作入口。
- `TagMenuDialog.vue`
  - 批量挂 tag 菜单。
- `TagFormDialog.vue`
  - 标签新增 / 编辑弹窗。
- `TagColorPicker.vue`
  - HEX8 + HSV + 透明度取色器。
- `TagChipList.vue`
  - 统一 Tag chip 渲染。
- `TagImportDialog.vue`
  - 标签 JSON 导入弹窗。
- `CategoryFormDialog.vue`
  - 主分类新建 / 编辑弹窗。
- `ConfirmationDialog.vue`
  - 确认弹窗。
- `ActionProgressOverlay.vue`
  - 长操作进度遮罩。

### 共享资源

- `frontend/src/utils/tagColors.js`
  - 标签颜色归一化、HEX8 与 HSV 转换、alpha 处理。
- `frontend/src/assets/tag-chips.css`
  - Tag chip 基础样式。

---

## 标签颜色约定

- 工程内统一使用 HEX8 表示颜色：`#RRGGBBAA`。
- `border_color` 同时作为 Tag 文字颜色。
- `background_color` 允许独立透明度。
- 后端会兼容旧的 `rgba(...)` 或短十六进制输入，但写入和返回时统一归一为大写 HEX8。

---

## 启动方式

### 前置条件

- Python 依赖安装到仓库根目录 `.venv`
- 前端依赖安装在 `frontend/node_modules`
- Windows 环境下推荐直接使用仓库内虚拟环境启动后端

### 安装依赖

```powershell
# 仓库根目录
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

Set-Location frontend
npm install
```

### 一键启动

```powershell
build\start_project.bat
```

这个脚本会：

- 使用仓库根目录 `.venv` 启动后端 `uvicorn`
- 启动前端 `npm run serve`

### 手动启动

```powershell
# 后端
Set-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```powershell
# 前端
Set-Location frontend
npm run serve
```

默认开发地址：

- 后端：`http://127.0.0.1:8000`
- 前端：`http://127.0.0.1:8080`

---

## 测试与验证

### 后端测试

```powershell
# 仓库根目录
.\.venv\Scripts\python.exe -m pytest backend\tests
```

### 前端静态检查与构建

```powershell
Set-Location frontend
npm run lint
npm run build
```

---

## 补充文档

- `backend/techReadme.md`
  - 更细的后端模型、接口与业务说明。
- `backend/api_services.md`
  - 服务层与 API 职责摘要。

---

## 当前实现说明

这份 README 以当前工作区真实结构为准，不再描述旧版单文件 routes、失效的 `comp/groupByDate` 目录，或后端按固定色盘自动分配 Tag 颜色的旧行为。