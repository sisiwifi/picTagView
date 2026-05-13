# picTagView Backend 技术说明书

本文档描述当前后端结构、运行时目录、核心模块和开发约定，内容以 `backend/app` 下的现行代码为准。

## 1. 项目位置

- 后端目录：`D:\Python_projects\picTagView_main\backend`
- 应用入口：`backend/app/main.py`

## 2. 技术栈与运行时目录

### 2.1 技术栈

- Web 框架：FastAPI
- ORM：SQLModel / SQLAlchemy
- 数据库：SQLite
- 多媒体处理：OpenCV、numpy
- 开发服务器：Uvicorn
- 上传解析：python-multipart
- 快速哈希：xxhash

### 2.2 路径来源

`app/core/config.py` 当前没有环境变量分支，而是直接按仓库结构计算路径：

| 常量 | 当前值 |
| --- | --- |
| `BASE_DIR` | `backend` |
| `PROJECT_ROOT` | 仓库根目录 |
| `DATA_DIR` | `backend/data` |
| `TEMP_DIR` | `backend/temp` |
| `CACHE_DIR` | `backend/data/cache` |
| `VIEWER_ICON_DIR` | `backend/data/viewer_icons` |
| `MEDIA_DIR` | `media` |
| `TRASH_DIR` | `trash` |
| `DB_PATH` | `backend/data/app.db` |

模块导入时会自动确保这些目录存在。

## 3. 应用启动流程

`app/main.py` 的 `create_app()` 当前做了下面几件事：

1. 调用 `init_db()` 初始化数据库
2. 创建 `FastAPI(title="picTagView Backend", version="0.1.0")`
3. 配置全开放 CORS
4. 挂载静态目录：
   - `/thumbnails` -> `TEMP_DIR`
   - `/cache` -> `CACHE_DIR`
   - `/media` -> `MEDIA_DIR`
   - `/trash-media` -> `TRASH_DIR`
   - `/viewer-icons` -> `VIEWER_ICON_DIR`
5. 注册 `app/api/routes.py` 聚合出的全部 API 路由

## 4. 路由结构

`app/api/routes.py` 当前注册的 router 顺序如下：

1. `basic_router`
2. `categories_router`
3. `dates_router`
4. `gallery_router`
5. `home_router`
6. `albums_router`
7. `images_router`
8. `collections_router`
9. `search_router`
10. `system_router`
11. `cache_router`
12. `tags_router`
13. `trash_router`

这意味着当前后端已经包含：

- 导入与刷新
- 日期与相册浏览
- 图片元数据编辑
- Tag 查询、草稿、新增、编辑、导入导出、Tag 二级浏览
- 收藏夹总览、详情、封面与批量应用
- 搜索
- 系统设置与查看器集成
- 缓存缩略图队列
- 主分类管理
- 回收站管理

## 5. 核心子系统

### 5.1 导入与刷新

- `services/import_service.py` 是兼容门面。
- 真正的导入和维护逻辑位于 `services/imports/`：
  - `pipeline.py`：导入批处理、哈希去重、相册链维护、图片主分类赋值、导入期文件名自动打标
  - `maintenance.py`：`quick/full` 刷新、路径对账、缺失预览修复、未入库媒体收编
  - `hash_index.py`：哈希索引缓存
  - `helpers.py`：文件时间、路径与缩略图辅助工具
- `services/image_frame_service.py` 负责统一识别多帧图片，并把 GIF、动态 WEBP 等文件的首帧转换为后续 temp/cache 预览使用的 OpenCV 图像。

当前导入规则的关键点：

- 图片按时间归入 `media/YYYY-MM/`
- 子目录会创建树形 `Album`
- 图片只保留一个主分类，优先使用导入请求给出的 `category_id`
- 同批次导入会在一个事务内完成写库、关联和自动打标
- 前端一次导入会被拆成多个上传批次；后端通过 `RecentImportOperation` 快照与 `recent_import_mode = replace/append` 把这些批次重新聚合成一次“最近导入操作”，并在 `successful_image_ids` 中保存整批成功导入图片全集；recent 一级页优先读取这一字段，旧的 `preview_image_ids` 仅保留兼容用途。
- 多帧图片不会再把原始动图直接交给缩略图链路处理，而是统一提取首帧，写入 `ImageAsset.is_animated + animation_meta`；其中 `animation_meta` 只在动图时保存 `frame_count / format`，供 overview、BrowsePage 和详情浮层显示状态标记。

### 5.1.1 图库管理聚合

- `gallery.py` 为 `/gallery` 父页提供两类聚合数据：
  - `recent/*`：最近一次导入操作的一级预览和二级混合列表
  - `all/*`：图库总览的一级预览和二级混合列表
- 一级 overview 只返回图片条目，供父页渲染方形缩略图带。
- 二级 items 继续复用日期视图的“相册优先 + 直图随后”约定，避免单独维护一套浏览语义。

### 5.1.2 首页聚合

- `home.py` 为 `/` 顶层页提供专用聚合接口 `GET /api/home/overview`。
- 主页聚合建立在现有的可见图片体系之上：
  - 图片总数来自 `get_active_category_ids() + list_visible_assets()`
  - Tag 墙只统计这些可见图片真正关联到的非草稿 Tag
- 主页的统计口径被刻意拆开：
  - `visible_image_count` 跟随显示主分类
  - `global_tag_count` 保持全局非草稿总量
- 代表图选择会同时考虑当前请求携带的最近展示图片 id 列表、当前分页批次内已选过的代表图 id，以及 temp/cache 预览是否可用。
- 这使首页可以在不写数据库状态的前提下，通过前端 `localStorage` 尽量轮换每次进入主页时的 Tag 代表图。

### 5.2 浏览与可见性

- `dates.py`、`albums.py` 不直接把所有相册都返回给前端，而是依赖 `visible_album_service.py` 根据“当前可见图片”推导相册可见性、封面和数量。
- 相册是否可见，不再取决于相册自身的主分类字段，而取决于子树中是否还有可见图片。
- 日期、相册、Tag、收藏、回收站这些浏览接口都会带上缩略图信息、宽高、排序时间和 `tags` ID 列表。
- 日期、相册、收藏、图库 overview、搜索和图片元信息接口现在额外返回动图元数据，前端只对 `GIF` / `WEBP` 显式打标，其他多帧格式先保留内部识别能力。

### 5.3 Tag 与搜索

- `tags.py` 负责 Tag CRUD、草稿占位、导入导出和 Tag 二级浏览。
- `tags.py` 现在还提供批量新增与批量删除接口，供设置页内部的标签管理面板使用。
- 草稿 Tag 使用 `created_by = system:draft-reserve` 标记，并在查询与导出时过滤。
- 删除正式 Tag 的实现已经统一到同一条事务路径：无论是总览页单删、设置页批删，还是取消草稿后的清理，后端都会在一次数据库事务里先扫描 `ImageAsset.tags` 并移除目标 id，再删除 Tag 记录；不会逐个 Tag 做多次提交，也不会删除图片本身。
- 批量新增采用整批校验、整批写入：先校验 `name`、`type`、同批重复、数据库重复和颜色元数据，再统一 `flush -> public_id -> commit`；如果任一行失败则整批回滚，并把 `row_errors` 返回给前端高亮对应行。
- `tag_match_service.py` 封装文件名分词、Tag 匹配、Tag 排序和计数更新；导入流程与图片页“自动标签”共用这一套逻辑。
- `search.py` 现在支持 `filename`、`tag`、`path`、`file`、`imported_at`、`file_created_at` 六类显式搜索，以及 `auto -> mixed/path` 解析；其中 `file` 通过 `quick_hash` 找到同图图片，时间模式通过 `start_at/end_at` 做区间过滤。
- 搜索响应当前同时服务 `SearchPage.vue` 一级虚拟化预览和 `/search/results` 完整列表，返回体包含 `requested_mode`、`resolved_mode`、`included_tags`、`matched_by`、`matched_tags` 等前端渲染所需元数据；前端顶层页提供“按图搜索”和“时间范围”两个辅助入口来生成对应查询。
- 搜索 UI 的主预览现在优先使用 temp/cache 缩略图，不再拿原图作为主卡片兜底；当搜索结果缺失缩略图时，前端会复用现有 `POST /api/admin/refresh?mode=quick` + `/api/images/meta` 的 targeted repair 链路，后台异步生成并回填预览元数据。
- `POST /api/admin/refresh` 在 targeted preview repair 场景下已经做了轻路径分流：当 `mode=quick` 且请求体带 `repair_cache=true` 和 `image_ids` / `trash_entry_ids` 时，后端会直接修复指定条目的缩略图与缓存引用，不再先执行全库路径对账、缓存目录清理、月份代表图补缩略图、hash index 全量重建或相册计数重算。

### 5.4 收藏夹与封面

- `collection_service.py` 负责收藏夹创建、查找、候选列表、批量添加/移除和统计刷新。
- 收藏封面与相册封面都支持手动设置，相关 payload 由 `cover_service.py` 维护。
- 收藏详情与封面接口都使用 `public_id` 字符串，而不是数值主键。

### 5.5 主分类

- 当前主分类体系只落在图片上，不再落在相册和 Tag 上。
- `category_service.py` 负责：
  - 默认主分类保证存在
  - 名称校验
  - 使用计数同步
  - 删除时引用回退
- 默认主分类固定为 `id=1`，且不可编辑、不可删除。

### 5.6 回收站

- `trash_service.py` 负责图片或相册移入回收站、列出条目、还原、彻底删除和清空。
- 每个 `TrashEntry` 都有一个独立的 `entry_key`；当前物理 payload 默认按 `trash/{entry_key}__{payload_name}` 平铺保存，前端也会把它当作回收站条目的稳定 key 使用。
- 还原流程不会手工拼接数据库记录，而是尽量复用导入/刷新链路重新建库。
- `POST /api/trash/reconcile` 提供轻量对账和预览修复能力，供前端进入回收站后静默调用。

### 5.7 缓存缩略图队列

- `cache.py` 在路由层维护共享任务表、页面 token、generation 和增量游标。
- `cache_thumb_service.py` 负责实际生成 `backend/data/cache/*.webp`。
- 队列当前特性：
  - 同页新 generation 会取代旧页面任务
  - 已有缓存立即返回
  - 状态接口通过 `cursor` 增量返回新完成项
  - 任务完成后会把缓存缩略图写回 `ImageAsset.thumbs`
- 对 GIF、动态 WEBP 等多帧图片，缓存队列也与导入链保持一致，统一使用首帧生成 WebP 缓存，不再依赖动图原始字节的逐处 OpenCV 解码。

### 5.8 查看器与系统设置

- `viewer_service.py` 主要服务于 Windows：
  - 枚举可用图片查看器
  - 解析系统默认查看器
  - 生成查看器图标
  - 以应用内偏好查看器打开图片
- `app_settings_service.py` 当前持久化到 `backend/data/app_settings.json` 的设置包括：
  - 浏览缓存缩略图短边尺寸
  - 月份封面尺寸
  - 页面浏览模式与滚动窗口范围（`40-200`，步长 `20`）
  - 文件名自动打标设置（`enabled`、`noise_tokens`、`min_token_length`、`drop_numeric_only`，返回体额外带固定 `sort_mode = name_asc`）

## 6. 数据模型摘要

| 模型 | 当前角色 |
| --- | --- |
| `ImageAsset` | 图片主表，保存哈希、宽高、`media_path`、`tags`、`category_id`、时间、缩略图信息与 `is_animated + animation_meta`；`animation_meta` 只在动图时保存 `frame_count / format` |
| `Album` | 相册树节点，保存路径、标题、封面和统计 |
| `AlbumImage` | 相册与图片关系表 |
| `RecentImportOperation` | 最近一次导入操作快照，记录整批成功导入图片全集，以及 recent 二级页需要的图片 / 顶层相册集合 |
| `Tag` | Tag 元数据、颜色、描述、`usage_count`、`last_used_at` |
| `Category` | 图片主分类 |
| `Collection` | 收藏夹 |
| `CollectionImage` | 收藏夹与图片关系表 |
| `TrashEntry` | 回收站条目与恢复所需 payload |

## 7. 开发与运行

### 7.1 安装依赖

```powershell
python -m venv ..\.venv
..\.venv\Scripts\python -m pip install --upgrade pip
..\.venv\Scripts\python -m pip install -r requirements.txt
```

或者直接在仓库根目录执行：

```powershell
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
```

### 7.2 启动开发服务

```powershell
..\.venv\Scripts\python -m uvicorn app.main:app --reload
```

也可以从仓库根目录使用 `build/start_project.bat` 同时启动前后端。

## 8. 当前约定与注意事项

- 前端默认直连 `http://127.0.0.1:8000`，后端端口变化时需要同步更新前端代码。
- `backend/data/app.db` 是当前默认数据库文件，仓库运行期间会持续变化。
- 图片元数据编辑里的“多选不能改文件名”不是只靠前端收敛交互，而是 `/api/images/metadata` 的后端硬校验；多选请求如果同时带 `name` 会直接返回 `400`。
- 文件名自动打标配置 API 已存在，但前端设置页尚未接入对应 UI；设置页内部虽然保留了 `Tag过滤` 占位子面板结构，但入口按钮当前未开放。
- 草稿 Tag 属于正常数据库记录，只是通过 `created_by` 被隐藏；调试数据库时要注意区分。
