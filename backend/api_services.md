# picTagView Backend API & Services Document

本文档说明后端服务分层、路由拆分结构以及各 API 的实现位置。

## 1. 服务分层

- 路由层：app/api/routes.py 与 app/api/routers/*.py
- 公共 API 工具：app/api/common.py
- 业务服务层：app/services/*.py

### 1.1 主要服务

- app/services/import_service.py
  - import_files(files, last_modified_times, created_times, category_id=None)
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
  - generate_cache_thumb_entry(key, file_path, cache_dir)
  - generate_cache_thumbs_progressively(entries, cache_dir, on_complete)
  - 说明：缓存缩略图 worker 数量会按 CPU 核数动态确定，默认保留 2 个核心给系统并设置 8 个 worker 上限
- app/services/trash_service.py
  - list_trash_items()
  - move_targets_to_trash(items)
  - restore_trash_entries(entry_ids)
  - hard_delete_trash_entries(entry_ids)
  - clear_trash()
  - 说明：负责回收站条目查询、移动到回收站、还原、彻底删除与清空回收站
- app/services/category_service.py
  - ensure_default_category()
  - resolve_category_id()
  - sync_category_usage_counts()
  - reassign_category_references()
  - 说明：维护受控主分类、默认主分类、初始化回填、批量启用 / 停用与删除回退
- app/services/app_settings_service.py
  - load_app_settings()/save_app_settings()
  - get_cache_thumb_short_side_px()/set_cache_thumb_short_side_px()
  - get_month_cover_size_px()/set_month_cover_size_px()
  - get_page_config()/set_page_config()
  - get_tag_match_setting()/set_tag_match_setting()
  - 说明：统一持久化 app_settings.json（包含缓存缩略图短边、月份封面尺寸、文件名匹配配置与页面浏览模式）
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
  - POST /api/images/tags/filename-match
  - POST /api/images/tags/apply
- app/api/routers/trash.py
  - GET /api/trash/items
  - POST /api/trash/move
  - POST /api/trash/restore
  - POST /api/trash/hard-delete
  - DELETE /api/trash
- app/api/routers/system.py：`GET /api/system/cache-thumb-setting`、`POST /api/system/cache-thumb-setting`、`GET /api/system/month-cover-setting`、`POST /api/system/month-cover-setting`、`GET /api/system/page-config`、`POST /api/system/page-config`、`GET /api/system/tag-match-setting`、`POST /api/system/tag-match-setting`、`GET /api/system/viewer-info`、`GET /api/system/image-viewers`、`GET /api/system/viewer-preference`、`POST /api/system/viewer-preference`
- app/api/routers/cache.py
  - DELETE /api/cache
  - POST /api/thumbnails/cache
  - GET /api/thumbnails/cache/status/{task_id}
- app/api/routers/categories.py
  - GET /api/categories
  - POST /api/categories
  - PATCH /api/categories/{category_id}
  - DELETE /api/categories/{category_id}
  - POST /api/categories/bulk
- app/api/routers/tags.py
  - GET /api/tags
  - GET /api/tags/{tag_id}
  - POST /api/tags/draft
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
  - 参数：files, last_modified_json, created_time_json, category_id
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
  - Body（可选）：`{ repair_cache?: bool, image_ids?: number[], trash_entry_ids?: number[] }`；当 `repair_cache=true` 时，后端会只修复目标图片或回收站条目的 cache 预览，并把最新缩略图路径/哈希回写元数据

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
  - 性能补充：该接口会在单次请求内各扫描一次 `backend/temp/` 与 `backend/data/cache/`，构建缩略图可用性索引；后续每个条目的 `thumb_url` / `cache_thumb_url` 解析只做内存 membership 判断，不再逐条调用 `exists()`

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
  - 性能补充：该接口与日期接口共享同一套请求级预览索引策略，避免在子相册封面和直属图片遍历时对每个条目重复执行磁盘存在性检查

### 3.3 图片与系统集成接口

- GET /api/images/meta
  - 实现：app/api/routers/images.py
  - 参数：`ids=1,2,3`（逗号分隔图片 ID）
  - 用途：批量回填图片元数据、缩略图地址、`media_paths` 与 `category_id`
  - 说明：主要供详情浮层或旧列表数据补齐字段；`media_paths` 也为更精细的文件实例操作提供兜底信息

- GET /api/images/{image_id}/open
  - 实现：app/api/routers/images.py，调用 app/services/viewer_service.py
  - 用途：在本机系统中打开原图
  - 参数：可选 `path` 查询参数；若提供，则必须命中该图片的某个 `media_path` 实例，否则返回 404

- POST /api/images/tags/filename-match
  - 实现：app/api/routers/images.py
  - 用途：按文件名批量匹配 Tag，并按选项回写图片 tags
  - Body：`{ image_ids, apply, merge_mode, include_tokens }`
  - 匹配规则：按空格分词，不拆分下划线 `_`；支持噪声词、最小长度、纯数字 token 过滤
  - 返回：逐图片匹配详情、回写前后 tag id、公共标签集合与 `multi_display`

- POST /api/images/tags/apply
  - 实现：app/api/routers/images.py
  - 用途：把指定 Tag 批量回写到图片 tags（用于详情浮层 Tag 菜单确认操作）
  - Body：`{ image_ids, tag_ids, merge_mode }`
  - merge_mode：`append_unique`（默认，去重追加）| `replace`（覆盖为指定 tag 列表）| `remove`（从已选图片中移除指定 tag）
  - 返回：逐图片回写前后 tag id、公共标签集合与 `multi_display`
  - 说明：当 merge_mode 为 `append_unique` / `replace` 时，会刷新相关 Tag 的 `last_used_at`；并同步受影响 Tag 的 `usage_count`

### 3.4 回收站接口

- GET /api/trash/items
  - 实现：app/api/routers/trash.py，调用 app/services/trash_service.py
  - 用途：列出回收站条目，供 TrashPage 瀑布流与选择态使用
  - 说明：仅返回当前可显示条目，不再在列表请求中同步执行轻量对账；缺失 cache 的补齐由前端在首屏后通过定向 quick refresh 或 `POST /api/trash/reconcile` 静默触发
  - 返回：`{ items: [...] }`，条目包含类型、名称、预览图、原路径、图片尺寸与 Tag ID 列表；`category_id` 仅在图片条目上返回
  - 前端约定：TrashPage 常规卡片只消费 `cache_thumb_url` / `thumb_url`，并在缺失时显示骨架；`trash_media_url` 只在详情层缩略图失败时作为原图兜底，不再作为常规浏览路径

- POST /api/trash/reconcile
  - 实现：app/api/routers/trash.py，调用 app/services/trash_service.py
  - 用途：对回收站执行轻量对账，清理已丢失 payload 的 `TrashEntry`，并补齐仍存在条目的 `preview_path` / `preview_cache_path` 引用
  - 返回：`{ changed: bool, total_items: int }`

### 3.4b 主分类接口

- GET /api/categories
  - 实现：app/api/routers/categories.py
  - 用途：列出全部主分类，并同步返回 `{image}` 使用计数
  - 说明：接口会确保默认主分类存在，默认项固定为 `id=1`

- POST /api/categories
  - 实现：app/api/routers/categories.py
  - Body：`{ name, display_name, description, is_active? }`
  - 用途：创建主分类；`name` 只允许小写字母、数字与下划线

- PATCH /api/categories/{category_id}
  - 实现：app/api/routers/categories.py
  - 用途：更新主分类名称、显示名、说明或启用状态
  - 说明：默认主分类不可编辑

- DELETE /api/categories/{category_id}
  - 实现：app/api/routers/categories.py
  - 用途：删除主分类，并把引用该分类的图片与图片回收站条目回退到默认主分类

- POST /api/categories/bulk
  - 实现：app/api/routers/categories.py
  - Body：`{ action: activate|deactivate|delete, ids: [...] }`
  - 用途：批量启用、停用或删除主分类；主分类配置页的管理模式通过该接口驱动右下角按钮岛与移除操作

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

- GET /api/system/page-config
  - 实现：app/api/routers/system.py
  - 用途：读取页面浏览模式配置
  - 返回：`{ browse_mode, default_browse_mode, scroll_window_size, default_scroll_window_size }`，当前支持 `scroll` 与 `paged`

- POST /api/system/page-config
  - 实现：app/api/routers/system.py
  - Body：`{ browse_mode: "scroll" | "paged", scroll_window_size?: 40|60|80|100|120|140|160|180|200 }`
  - 用途：保存页面浏览模式，供 BrowsePage 与 TrashPage 统一切换滚动浏览 / 分页浏览，并持久化滚动模式下的窗口范围
  - 说明：前端仍会根据页面方向切换瀑布流样式；该接口只持久化滚动 / 分页模式与窗口范围本身，不保存横竖屏布局偏好。

- GET /api/system/tag-match-setting
  - 实现：app/api/routers/system.py
  - 用途：读取文件名匹配 Tag 的过滤配置
  - 返回：`{ enabled, noise_tokens, min_token_length, drop_numeric_only, sort_mode }`

- POST /api/system/tag-match-setting
  - 实现：app/api/routers/system.py
  - Body：`{ enabled, noise_tokens, min_token_length, drop_numeric_only }`
  - 用途：保存文件名匹配 Tag 的过滤配置

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
  - 用途：把当前页面当前 generation 的缓存缩略图请求提交到共享队列
  - Body：兼容旧格式 `{"image_ids": [...]}`；BrowsePage / CalendarOverview 现使用新格式：
    - `ordered_image_ids`: 前端按优先级排好的图片 ID 列表
    - `generation`: 当前页面代次，新 generation 会覆盖同一 `page_token` 的旧 generation
    - `page_token`: 当前页面逻辑标识，如某个 BrowsePage 路径
    - `sort_signature`: 当前排序签名，便于日志与排障
    - `direction`: 当前滚动方向（`forward` / `backward` / `none`）
    - `anchor_image_id` / `anchor_item_key` / `anchor_offset`: 当前缓存锚点与视觉锚点信息
  - 说明：短边尺寸来自 `app_settings.json` 的 `cache_thumb_short_side_px`（默认 600）；同一 `page_token` 下未启动的旧任务会直接丢弃，已启动 worker 允许完成，但结果只会回流到当前仍需要该图片的 generation
  - 返回：`{"task_id": "<uuid>", "generation": <int>}`

- GET /api/thumbnails/cache/status/{task_id}
  - 实现：app/api/routers/cache.py
  - 参数：可选 `cursor=<int>`，用于增量轮询
  - 用途：轮询任务状态与本次 cursor 之后新增的缓存缩略图 URL
  - 返回：`{ status, items, next_cursor, generation }`

### 3.7 标签接口

- GET /api/tags
  - 实现：app/api/routers/tags.py
  - 参数：ids（逗号分隔 ID 列表，批量查）、type（标签种类过滤）、q（名称模糊搜索）、sort_by（`name_asc` / `last_used_desc`）、limit/offset（分页）；历史 `category_id` / `category` 参数仍可传入但已忽略
  - 用途：列出/搜索/批量查询 Tag；前端展示图片标签时通过 ids 参数批量拉取
  - 补充：`sort_by=last_used_desc&limit=5` 可用于获取最近使用标签
  - 性能补充：总数统计已改为数据库 `COUNT(*)` 查询，避免批量 ids 请求时先全量取回记录再在 Python 内计数

- GET /api/tags/{tag_id}
  - 实现：app/api/routers/tags.py
  - 用途：获取单个 Tag 完整详情

- POST /api/tags/draft
  - 实现：app/api/routers/tags.py
  - Body：`{ type?, metadata? }`
  - 用途：预占真实 `id/public_id` 并创建隐藏草稿 Tag；草稿不会出现在 `/api/tags` 列表、导出、最近使用与图片打标相关接口中

- POST /api/tags
  - 实现：app/api/routers/tags.py
  - Body：`{ name, display_name, type, description, created_by, metadata }`
  - 用途：手动创建新 Tag；name 会自动规范化为小写

- PATCH /api/tags/{tag_id}
  - 实现：app/api/routers/tags.py
  - Body：`{ name?, display_name?, type?, description?, created_by?, metadata? }`
  - 用途：更新 Tag 属性；若目标是隐藏草稿 Tag，则同一接口也承担“转正”流程

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

- Tag 显色元数据
  - 写入位置：`Tag.metadata.color`、`Tag.metadata.border_color`、`Tag.metadata.background_color`
  - 维护方式：由 Tag 创建、更新或导入时显式提供；后端不再按固定规则自动分配或回写颜色
  - 消费方式：前端从 Tag 元数据读取显色字段并渲染 tag chip

## 4. 业务数据库汇总

本项目所有持久化数据存储在同一 SQLite 文件（路径由 `app/core/config.py` 的 `DB_PATH` 配置，默认 `backend/data/app.db`）。

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
- `/api/dates/*` 与 `/api/albums/*` 在返回列表时，会先按请求构建 temp/cache 目录文件名索引，再解析 `thumb_url` / `cache_thumb_url`；对外行为保持“只有文件实际存在才返回 URL”，但避免了逐项 `exists()` 带来的界面首开延迟。
- TrashPage 条目会优先复用 `thumb_url` / `cache_thumb_url`；若只有 trash payload，则通过 `/trash-media/...` 作为预览回退。
- TrashPage header 左侧提供“返回”按钮；选择态右下角操作岛包含“详情 / 还原 / 删除 / 全选 / 取消选择”。当同时存在相册与图片时，“全选”沿用类型锁定逻辑，通过二级按钮选择“相册 / 图片”。
- BrowsePage 的“删除到回收站”和 TrashPage 的“还原 / 删除 / 清空回收站”都应使用应用内居中确认弹窗，不再依赖浏览器原生提示框。
- TrashPage 与 BrowsePage 保持一致的视觉锚点策略：瀑布流和选择态切换时，优先恢复当前首屏条目到第一排附近，而不是简单回到顶部。
- TrashPage 的瀑布流布局也采用精确宽度 key 的内存缓存；若回收站条目缺失 `width/height`，才在图片加载后批量回填尺寸，避免每张图触发一次全量重排。
- BrowsePage 的普通模式与选择模式都应优先显示 cache/temp 缩略图；若缓存尚未生成，则显示骨架占位并沿用 `/api/thumbnails/cache` 的异步生成链路，而不是把原图当作常态展示源。
- BrowsePage 与 TrashPage 的照片墙会随页面方向自动切换：横屏保持等高 justified flow，竖屏切换为等宽 masonry；分页模式允许单页只出现少量图片，只要行数、列数与锚点恢复稳定即可。
- `/api/dates/*` 与 `/api/albums/*` 的图片条目现在还会返回 `file_size`、`imported_at`、`file_created_at`，供选择模式详情浮层直接展示，不需要额外请求单图详情接口。
- `/api/dates/*` 与 `/api/albums/*` 的图片条目现在还会返回 `media_index` 与 `media_rel_path`；前端调用 `/api/images/{image_id}/open` 时应优先传入 `path=media_rel_path`，而不是默认取 `media_path[0]`。
- `/api/dates/*` 与 `/api/albums/*` 的相册条目现在还会返回 `photo_count` 与 `created_at`，供相册选择详情浮层显示“图片数量”和相册创建时间。
- `GET /api/images/meta?ids=1,2,3` 用于按需回填图片元数据；当前主要供 BrowsePage 在详情浮层打开时，为旧列表数据或缺字段条目补齐 `file_size`、`imported_at`、`file_created_at`、`tags` 与缩略图地址。
- `GET /api/albums/open-by-path/{album_path:path}` 用于在系统文件管理器中打开相册目录；当前由 BrowsePage 在相册详情浮层点击“查看相册”时调用。
- BrowsePage 的“大缩略图”照片墙应优先消费 `/api/dates/*` 与 `/api/albums/*` 返回的 `width` / `height` 初始化布局；前端 `onload` 仅在元数据缺失时做异常兜底回填，不再把图片实际加载当作常态排布来源。
- BrowsePage 当前仅对列表模式与选择模式启用窗口化渲染，借此减少 DOM 数量与选择态下的重排压力；“大缩略图”照片墙仍保留全量渲染，但会按“页面标识 + 排序签名 + 精确容器宽度 + 布局指纹”缓存 `justifiedRows` 结果，降低反复重算的成本。
- BrowsePage 现把“视觉锚点”和“缓存锚点”拆开：视觉锚点用于浏览态 / 选择态切换时把同一内容恢复到新布局首排内，缓存锚点用于向 `/api/thumbnails/cache` 发送 generation 请求；普通照片墙优先请求“缓存锚点 + 当前首排 + 前后 N 张”，其中 `N` 由 `scroll_window_size` 决定，可选 `40-200`，默认 `100`。
- 缓存缩略图请求不再为每次滚动单独开启一组后台批处理，而是统一进入共享 worker 队列；前端通过 `cursor` 增量轮询，只拉取新的完成项。
- BrowsePage 的选择逻辑现已扩展到列表显示：列表模式可通过长按进入选择态，并继续使用与卡片选择界面相同的 Ctrl/Shift、多选与统一选择符号；该行为仅是前端交互扩展，不新增后端接口。
- BrowsePage 选择模式的详情浮层只使用 cache/temp 缩略图做预览，不把原图当作弹层内展示源；弹层尺寸由主视图区当前可视宽高共同约束，左侧图片区内的缩略图按原图比例自适应显示；多选时左侧预览列表需可滚动且隐藏滚动条，右下保留删除占位按钮；若选中图片则主操作继续复用 `/api/images/{image_id}/open`，若选中相册则主操作改为调用 `/api/albums/open-by-path/{album_path:path}` 打开目录。
- BrowsePage 详情浮层打开时会锁定页面滚动，避免滚轮、空白区拖动或中键自动滚动穿透到底层页面。
- BrowsePage 操作岛中的“全选”在同时存在相册与图片时应通过点击展开二级按钮，不依赖 hover，这样桌面与移动端都能稳定选择“相册 / 图片”两类全选动作。
- 相册导航使用 public_id，不依赖数据库自增主键。
- 普通浏览不再依赖路径级软删除过滤；删除后目标会从 `media/` 物理移入 `trash/`，回收站列表直接基于 `TrashEntry` 渲染。
- BrowsePage 选择模式默认只使用浏览接口返回的 `tags` id 列表；真正的 Tag 名称解析通过 `/api/tags?ids=...` 按需批量完成，不在 `/api/dates/*` 与 `/api/albums/*` 内联展开。
