# picTagView Backend API & Services Document

本文档说明后端服务分层、路由拆分结构以及各 API 的实现位置。

## 1. 服务分层

- 路由层：app/api/routes.py 与 app/api/routers/*.py
- 公共 API 工具：app/api/common.py
- 业务服务层：app/services/*.py

### 1.1 主要服务

- app/services/import_service.py
  - import_files(files, last_modified_times, created_times)
  - refresh_library()
  - rebuild_hash_index()
  - recalculate_album_counts()
  - 说明：该文件是稳定门面，具体实现拆分在下列子模块
- app/services/imports/pipeline.py
  - import_files(...)
  - 负责导入批处理、预去重、并行处理编排、DB 串行写入
- app/services/imports/maintenance.py
  - refresh_library()
  - recalculate_album_counts()
  - 负责库修复、孤儿清理、相册计数与封面重算
- app/services/imports/hash_index.py
  - load/save/lookup/add/rebuild hash index
- app/services/imports/helpers.py
  - 路径转换、文件时间、缩略图条目处理、mime/尺寸/quick_hash 等通用工具
- app/services/parallel_processor.py
  - process_from_paths(entries, temp_dir)
  - process_from_bytes(entries, temp_dir)
  - process_hash_only_from_bytes(entries)
- app/services/cache_thumb_service.py
  - generate_cache_thumbs_progressively(entries, cache_dir, on_complete)
- app/services/app_settings_service.py
  - load_app_settings()/save_app_settings()
  - get_cache_thumb_short_side_px()/set_cache_thumb_short_side_px()
  - get_month_cover_size_px()/set_month_cover_size_px()
  - 说明：统一持久化 app_settings.json（包含看图器偏好与缓存缩略图短边设置）
- app/services/viewer_service.py
  - collect_image_viewers(extensions)
  - get_preferred_viewer_id() / set_preferred_viewer_id()
  - launch_with_preferred_viewer(command_template, file_path)
  - ensure_viewer_icon(viewer)

## 2. 路由组织

- app/api/routes.py
  - 仅作为聚合入口，统一 include 子路由。
- app/api/routers/basic.py
  - GET /
  - POST /api/import
  - GET /api/images/count
  - POST /api/admin/refresh
- app/api/routers/dates.py
  - GET /api/dates
  - GET /api/dates/{date_group}/items
- app/api/routers/albums.py
  - GET /api/albums/by-path/{album_path:path}
  - GET /api/albums/{album_id}
- app/api/routers/images.py
  - GET /api/images/{image_id}/open
- app/api/routers/system.py
  - GET /api/system/cache-thumb-setting
  - POST /api/system/cache-thumb-setting
  - GET /api/system/month-cover-setting
  - POST /api/system/month-cover-setting
  - GET /api/system/viewer-info
  - GET /api/system/image-viewers
  - GET /api/system/viewer-preference
  - POST /api/system/viewer-preference
- app/api/routers/cache.py
  - DELETE /api/cache
  - POST /api/thumbnails/cache
  - GET /api/thumbnails/cache/status/{task_id}
- app/api/routers/tags.py
  - GET /api/tags
  - GET /api/tags/{tag_id}
  - POST /api/tags
  - PATCH /api/tags/{tag_id}
  - DELETE /api/tags/{tag_id}
  - GET /api/tags/export/json
  - POST /api/tags/import/json

## 3. API 说明

### 3.1 基础接口

- GET /
  - 实现：app/api/routers/basic.py
  - 用途：健康检查
  - 返回：{"status": "ok"}

- POST /api/import
  - 实现：app/api/routers/basic.py，调用 app/services/import_service.py
  - 参数：files, last_modified_json, created_time_json
  - 返回：{"imported": [...], "skipped": [...]}

- GET /api/images/count
  - 实现：app/api/routers/basic.py
  - 返回：{"count": int}

- POST /api/admin/refresh
  - 实现：app/api/routers/basic.py，调用 app/services/import_service.py
  - 用途：触发库修复与缩略图补齐
  - 模式：支持 mode=quick|full（默认 quick）
    - quick：路径对账 + 相册关系维护 + 缩略图/元数据补齐
    - full：在 quick 基础上额外扫描 media 并收编未入库图片，更新哈希索引

### 3.2 日期与相册接口

- GET /api/dates
  - 实现：app/api/routers/dates.py
  - 用途：返回按年月分组的汇总和封面信息

- GET /api/dates/{date_group}/items
  - 实现：app/api/routers/dates.py
  - 用途：返回某年月下的直图与子相册
  - 说明：子相册条目中包含 `album_path` 字段（即 Album.path，如 `2024-07/vacation`），前端用于构建 `/calendar/:group/:albumPath+` 路由

- GET /api/albums/by-path/{album_path:path}
  - 实现：app/api/routers/albums.py
  - 用途：通过相册物理路径查询相册详情（前端路由 `/calendar/:group/:albumPath+` 使用）
  - 参数：album_path 为相对于 media 根的相册路径，如 `2024-07/vacation/day1`
  - 返回：与 GET /api/albums/{album_id} 相同的 AlbumDetailResponse
  - 说明：Album.path 字段有数据库索引，查询高效

- GET /api/albums/{album_id}
  - 实现：app/api/routers/albums.py
  - 用途：返回相册详情、祖先面包屑、子相册与直图
  - 说明：响应体中 `album.date_group`（YYYY-MM）与 `album.path` 供前端面包屑与返回导航使用；条目中 `album_path` 字段提供子相册的物理路径用于 URL 构建

### 3.3 系统集成接口

- GET /api/images/{image_id}/open
  - 实现：app/api/routers/images.py，调用 app/services/viewer_service.py
  - 用途：在本机系统中打开原图

- GET /api/system/viewer-info
  - 实现：app/api/routers/system.py
  - 用途：返回系统默认看图软件与应用内偏好

- GET /api/system/cache-thumb-setting
  - 实现：app/api/routers/system.py
  - 用途：读取缓存缩略图短边配置（单位 px）
  - 返回：`{ short_side_px, default_short_side_px, min_short_side_px, max_short_side_px }`

- POST /api/system/cache-thumb-setting
  - 实现：app/api/routers/system.py
  - Body：`{ short_side_px: int }`
  - 用途：更新缓存缩略图短边配置（仅影响后续生成到 `data/cache/` 的缩略图）
  - 说明：前端设置页保存后会调用 `DELETE /api/cache` 清空缓存，随后按新尺寸重建

- GET /api/system/month-cover-setting
  - 实现：app/api/routers/system.py
  - 用途：读取月份封面尺寸配置（单位 px）
  - 返回：`{ size_px, default_size_px, min_size_px, max_size_px }`

- POST /api/system/month-cover-setting
  - 实现：app/api/routers/system.py
  - Body：`{ size_px: int }`
  - 用途：更新月份封面尺寸（影响 `temp/` 内月份封面与后续导入生成规则）
  - 说明：前端设置页保存后会调用 `DELETE /api/cache` 清空缓存，随后按新尺寸重建

- GET /api/system/image-viewers
  - 实现：app/api/routers/system.py
  - 用途：扫描可用看图程序（Windows）

- GET /api/system/viewer-preference
  - 实现：app/api/routers/system.py
  - 用途：读取应用内偏好看图程序

- POST /api/system/viewer-preference
  - 实现：app/api/routers/system.py
  - 用途：设置应用内偏好看图程序

### 3.4 缓存接口

- DELETE /api/cache
  - 实现：app/api/routers/cache.py
  - 用途：清理 temp 与 cache 文件，并清理 DB 中失效缩略图引用

- POST /api/thumbnails/cache
  - 实现：app/api/routers/cache.py，生成逻辑调用 app/services/cache_thumb_service.py
  - 用途：异步启动缓存缩略图生成任务
  - 说明：短边尺寸来自 `app_settings.json` 的 `cache_thumb_short_side_px`（默认 600）
  - 返回：{"task_id": "<uuid>"}

- GET /api/thumbnails/cache/status/{task_id}
  - 实现：app/api/routers/cache.py
  - 用途：轮询任务状态与新增缓存缩略图 URL

### 3.5 标签接口

- GET /api/tags
  - 实现：app/api/routers/tags.py
  - 参数：ids（逗号分隔 ID 列表，批量查）、category（过滤）、type（标签种类过滤）、q（名称模糊搜索）、limit/offset（分页）
  - 用途：列出/搜索/批量查询 Tag；前端展示图片标签时通过 ids 参数批量拉取

- GET /api/tags/{tag_id}
  - 实现：app/api/routers/tags.py
  - 用途：获取单个 Tag 完整详情

- POST /api/tags
  - 实现：app/api/routers/tags.py
  - Body：`{ name, display_name, type, description, category, created_by, metadata }`
  - 用途：手动创建新 Tag；name 会自动规范化为小写

- PATCH /api/tags/{tag_id}
  - 实现：app/api/routers/tags.py
  - Body：`{ display_name?, type?, description?, category?, metadata? }`
  - 用途：更新 Tag 属性（name 不可修改）

- DELETE /api/tags/{tag_id}
  - 实现：app/api/routers/tags.py
  - 用途：删除 Tag（物理删除，不软删）

- GET /api/tags/export/json
  - 实现：app/api/routers/tags.py
  - 用途：将全库 Tag 导出为 JSON 文件（前端设置页点击"导出 JSON"触发下载）
  - 响应头包含 Content-Disposition: attachment; filename="tags_export.json"

- POST /api/tags/import/json
  - 实现：app/api/routers/tags.py
  - Body：`{ tags: [...], on_conflict: "skip"|"overwrite" }`
  - 用途：批量导入 Tag；on_conflict=skip（默认）跳过同名，overwrite 覆盖可更新字段
  - 返回：`{ imported, updated, skipped, errors }`

## 4. 业务数据库汇总

本项目所有持久化数据存储在同一 SQLite 文件（路径由 `app/core/config.py` 的 `DB_PATH` 配置，默认 `backend/db.sqlite`）。

| 表名 | 对应模型 | 主要作用 |
|---|---|---|
| `imageasset` | `ImageAsset` (`app/models/image_asset.py`) | 图片媒体资产主表；存储哈希、路径、尺寸、日期分组、缩略图条目、关联 Tag ID 数组等全量元数据 |
| `album` | `Album` (`app/models/album.py`) | 树形相册结构；存储相册名称、层级路径、封面、照片计数、日期分组 |
| `album_image` | `AlbumImage` (`app/models/album_image.py`) | 相册-图片显式多对多关联表；用于查询某相册下的直图成员，替代按 `ImageAsset.album` JSON 扫描，并由导入与重算流程同步维护 |
| `pathsoftdelete` | `PathSoftDelete` (`app/models/soft_delete.py`) | 软删除日志表（路径级）；以 target_path 为准控制图片或相册的可见性，实体本身不删除 |
| `tag` | `Tag` (`app/models/tag.py`) | 标签库；存储标准化名称、展示名称、分类、使用次数、来源、元信息等，`ImageAsset.tags` 存储该表的 id 列表 |

附加文件：
- `MEDIA_DIR/.hash_index.json`：哈希索引缓存（非 SQLite），用于导入时 O(1) 去重，详见服务层 `hash_index.py`。

## 5. 约定

- thumb_url 表示 temp 预览图路径。
- cache_thumb_url 表示按需生成的 cache 预览图路径。
- 相册导航使用 public_id，不依赖数据库自增主键。
- 软删除可见性由 path_soft_delete.target_path 判定（路径级可见性）。
