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
  - GET /api/albums/{album_id}
- app/api/routers/images.py
  - GET /api/images/{image_id}/open
- app/api/routers/system.py
  - GET /api/system/viewer-info
  - GET /api/system/image-viewers
  - GET /api/system/viewer-preference
  - POST /api/system/viewer-preference
- app/api/routers/cache.py
  - DELETE /api/cache
  - POST /api/thumbnails/cache
  - GET /api/thumbnails/cache/status/{task_id}

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

### 3.2 日期与相册接口

- GET /api/dates
  - 实现：app/api/routers/dates.py
  - 用途：返回按年月分组的汇总和封面信息

- GET /api/dates/{date_group}/items
  - 实现：app/api/routers/dates.py
  - 用途：返回某年月下的直图与子相册

- GET /api/albums/{album_id}
  - 实现：app/api/routers/albums.py
  - 用途：返回相册详情、祖先面包屑、子相册与直图

### 3.3 系统集成接口

- GET /api/images/{image_id}/open
  - 实现：app/api/routers/images.py，调用 app/services/viewer_service.py
  - 用途：在本机系统中打开原图

- GET /api/system/viewer-info
  - 实现：app/api/routers/system.py
  - 用途：返回系统默认看图软件与应用内偏好

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
  - 返回：{"task_id": "<uuid>"}

- GET /api/thumbnails/cache/status/{task_id}
  - 实现：app/api/routers/cache.py
  - 用途：轮询任务状态与新增缓存缩略图 URL

## 4. 约定

- thumb_url 表示 temp 预览图路径。
- cache_thumb_url 表示按需生成的 cache 预览图路径。
- 相册导航使用 public_id，不依赖数据库自增主键。
- 软删除可见性由 path_soft_delete 表过滤。
