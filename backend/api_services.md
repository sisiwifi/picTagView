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
- app/services/trash_service.py
  - list_trash_items()
  - move_targets_to_trash(items)
  - restore_trash_entries(entry_ids)
  - hard_delete_trash_entries(entry_ids)
  - clear_trash()
  - 说明：负责回收站条目查询、移动到回收站、还原、彻底删除与清空回收站
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
  - GET /api/albums/open-by-path/{album_path:path}
  - GET /api/albums/{album_id}
- app/api/routers/images.py
  - GET /api/images/meta
  - GET /api/images/{image_id}/open
- app/api/routers/trash.py
  - GET /api/trash/items
  - POST /api/trash/move
  - POST /api/trash/restore
  - POST /api/trash/hard-delete
  - DELETE /api/trash
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
  - 说明补充：图片条目额外返回 `media_index` 与 `media_rel_path`，用于前端稳定指向当前列表所对应的具体 `media_path` 实例，避免一图多路径时误开到首个实例
  - 说明补充：图片条目额外返回 `tags: list[int]`，供前端选择模式在需要时做 Tag 文本显示；该接口本身不 join Tag 表，保持主查询轻量
  - 元数据补充：图片条目与相册条目都会返回 `width` / `height`；相册项的宽高来自其封面图片，用于前端在“大缩略图”照片墙中稳定初始化行布局
  - 缩略图补充：`cache_thumb_url` 仅在 `data/cache/` 中已有缓存缩略图时返回，不再把原图路径作为常规回退值；前端应在缺失时显示骨架并通过 `/api/thumbnails/cache` 触发生成

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
  - 说明补充：直属图片条目同样返回 `media_index` 与 `media_rel_path`，用于在相册内打开正确的文件实例
  - 说明补充：直属图片条目同样返回 `tags: list[int]`，前端仅在用户显式切换到 Tag 视图时再批量解析为文本
  - 元数据补充：图片条目返回原图 `width` / `height`；子相册条目返回封面图 `width` / `height`，以便前端优先使用后端元数据预估卡片宽高比
  - 缩略图补充：直属图片条目遵循与日期接口一致的缓存策略，仅在缓存文件实际存在时返回 `cache_thumb_url`

### 3.3 图片与系统集成接口

- GET /api/images/meta
  - 实现：app/api/routers/images.py
  - 参数：`ids=1,2,3`（逗号分隔图片 ID）
  - 用途：批量回填图片元数据、缩略图地址与 `media_paths`
  - 说明：主要供详情浮层或旧列表数据补齐字段；`media_paths` 也为更精细的文件实例操作提供兜底信息

- GET /api/images/{image_id}/open
  - 实现：app/api/routers/images.py，调用 app/services/viewer_service.py
  - 用途：在本机系统中打开原图
  - 参数：可选 `path` 查询参数；若提供，则必须命中该图片的某个 `media_path` 实例，否则返回 404

### 3.4 回收站接口

- GET /api/trash/items
  - 实现：app/api/routers/trash.py，调用 app/services/trash_service.py
  - 用途：列出回收站条目，供 TrashPage 瀑布流与选择态使用
  - 说明：返回前会先执行一次批量轻量对账，清除已丢失 payload 的 `TrashEntry`，并为仍存在的条目成批补齐 `preview_path` 与 `temp/*.webp`；不再在进入页面时逐条强制生成 `data/cache/*.webp`
  - 返回：`{ items: [...] }`，条目包含类型、名称、预览图、原路径、图片尺寸、Tag ID 列表等

- POST /api/trash/move
  - 实现：app/api/routers/trash.py，调用 app/services/trash_service.py
  - Body：`{ items: [{ type, image_id?, media_rel_path?, album_path? }, ...] }`
  - 用途：把选中的图片或相册从 `media/` 移入 `trash/` 并创建 `TrashEntry`
  - 说明：相册删除按整棵目录树处理；图片删除按具体 `media_rel_path` 实例处理
  - 存储说明：新条目直接扁平存放为 `trash/<entry_key>__<原名>`，不再额外创建 `entries/<entry_key>/payload/` 深层目录

- POST /api/trash/restore
  - 实现：app/api/routers/trash.py，调用 app/services/trash_service.py
  - Body：`{ entry_ids: [1, 2, 3] }`
  - 用途：将回收站条目恢复到 `media/`，并复用导入/刷新链路重新建库
  - 说明：相册重名时自动追加 `_1`、`_2` 等后缀；图片恢复继续遵循现有 hash 去重与导入策略；相册恢复优先走轻量哈希收编，减少同步缩略图生成带来的阻塞

- POST /api/trash/hard-delete
  - 实现：app/api/routers/trash.py，调用 app/services/trash_service.py
  - Body：`{ entry_ids: [1, 2, 3] }`
  - 用途：物理删除回收站 payload，并清理对应 `TrashEntry`

- DELETE /api/trash
  - 实现：app/api/routers/trash.py，调用 app/services/trash_service.py
  - 用途：清空整个回收站，物理删除所有 payload

### 3.5 系统集成接口

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

### 3.6 缓存接口

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

### 3.7 标签接口

- GET /api/tags
  - 实现：app/api/routers/tags.py
  - 参数：ids（逗号分隔 ID 列表，批量查）、category（过滤）、type（标签种类过滤）、q（名称模糊搜索）、limit/offset（分页）
  - 用途：列出/搜索/批量查询 Tag；前端展示图片标签时通过 ids 参数批量拉取
  - 性能补充：总数统计已改为数据库 `COUNT(*)` 查询，避免批量 ids 请求时先全量取回记录再在 Python 内计数

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
| `trashentry` | `TrashEntry` (`app/models/trash_entry.py`) | 回收站条目表；记录回收站内图片/相册的原路径、trash payload、预览信息与恢复所需元数据 |
| `tag` | `Tag` (`app/models/tag.py`) | 标签库；存储标准化名称、展示名称、分类、使用次数、来源、元信息等，`ImageAsset.tags` 存储该表的 id 列表 |

附加文件：
- `MEDIA_DIR/.hash_index.json`：哈希索引缓存（非 SQLite），用于导入时 O(1) 去重，详见服务层 `hash_index.py`。

## 5. 约定

- thumb_url 表示 temp 预览图路径。
- cache_thumb_url 表示按需生成的 cache 预览图路径。
- TrashPage 条目会优先复用 `thumb_url` / `cache_thumb_url`；若只有 trash payload，则通过 `/trash-media/...` 作为预览回退。
- TrashPage header 左侧提供“返回”按钮；选择态右下角操作岛包含“详情 / 还原 / 删除 / 全选 / 取消选择”。当同时存在相册与图片时，“全选”沿用类型锁定逻辑，通过二级按钮选择“相册 / 图片”。
- BrowsePage 的“删除到回收站”和 TrashPage 的“还原 / 删除 / 清空回收站”都应使用应用内居中确认弹窗，不再依赖浏览器原生提示框。
- BrowsePage 的普通模式与选择模式都应优先显示 cache/temp 缩略图；若缓存尚未生成，则显示骨架占位并沿用 `/api/thumbnails/cache` 的异步生成链路，而不是把原图当作常态展示源。
- `/api/dates/*` 与 `/api/albums/*` 的图片条目现在还会返回 `file_size`、`imported_at`、`file_created_at`，供选择模式详情浮层直接展示，不需要额外请求单图详情接口。
- `/api/dates/*` 与 `/api/albums/*` 的图片条目现在还会返回 `media_index` 与 `media_rel_path`；前端调用 `/api/images/{image_id}/open` 时应优先传入 `path=media_rel_path`，而不是默认取 `media_path[0]`。
- `/api/dates/*` 与 `/api/albums/*` 的相册条目现在还会返回 `photo_count` 与 `created_at`，供相册选择详情浮层显示“图片数量”和相册创建时间。
- `GET /api/images/meta?ids=1,2,3` 用于按需回填图片元数据；当前主要供 BrowsePage 在详情浮层打开时，为旧列表数据或缺字段条目补齐 `file_size`、`imported_at`、`file_created_at`、`tags` 与缩略图地址。
- `GET /api/albums/open-by-path/{album_path:path}` 用于在系统文件管理器中打开相册目录；当前由 BrowsePage 在相册详情浮层点击“查看相册”时调用。
- BrowsePage 的“大缩略图”照片墙应优先消费 `/api/dates/*` 与 `/api/albums/*` 返回的 `width` / `height` 初始化布局；前端 `onload` 只作为缺失元数据时的兜底修正，不应再把图片实际加载当作首选布局来源。
- BrowsePage 当前仅对列表模式与选择模式启用窗口化渲染，借此减少 DOM 数量与选择态下的重排压力；“大缩略图”照片墙保持原有全量渲染与滚动锚点策略不变。
- BrowsePage 的选择逻辑现已扩展到列表显示：列表模式可通过长按进入选择态，并继续使用与卡片选择界面相同的 Ctrl/Shift、多选与统一选择符号；该行为仅是前端交互扩展，不新增后端接口。
- BrowsePage 选择模式的详情浮层只使用 cache/temp 缩略图做预览，不把原图当作弹层内展示源；弹层尺寸由主视图区当前可视宽高共同约束，左侧图片区内的缩略图按原图比例自适应显示；多选时左侧预览列表需可滚动且隐藏滚动条，右下保留删除占位按钮；若选中图片则主操作继续复用 `/api/images/{image_id}/open`，若选中相册则主操作改为调用 `/api/albums/open-by-path/{album_path:path}` 打开目录。
- BrowsePage 详情浮层打开时会锁定页面滚动，避免滚轮、空白区拖动或中键自动滚动穿透到底层页面。
- BrowsePage 操作岛中的“全选”在同时存在相册与图片时应通过点击展开二级按钮，不依赖 hover，这样桌面与移动端都能稳定选择“相册 / 图片”两类全选动作。
- 相册导航使用 public_id，不依赖数据库自增主键。
- 普通浏览不再依赖路径级软删除过滤；删除后目标会从 `media/` 物理移入 `trash/`，回收站列表直接基于 `TrashEntry` 渲染。
- BrowsePage 选择模式默认只使用浏览接口返回的 `tags` id 列表；真正的 Tag 名称解析通过 `/api/tags?ids=...` 按需批量完成，不在 `/api/dates/*` 与 `/api/albums/*` 内联展开。
