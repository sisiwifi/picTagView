# picTagView Backend API 与服务说明

本文档按“路由层 -> 服务层 -> 当前协议细节”说明后端实现，内容以 `backend/app/api/routers/*.py` 与 `backend/app/services/*.py` 的当前代码为准。

## 1. 分层概览

| 层级 | 位置 | 当前职责 |
| --- | --- | --- |
| 路由聚合 | `app/api/routes.py` | 注册 `basic`、`categories`、`dates`、`gallery`、`home`、`albums`、`images`、`collections`、`search`、`system`、`cache`、`tags`、`trash` |
| 路由实现 | `app/api/routers/*.py` | 解析请求、校验参数、组织响应、调用服务 |
| 通用 API 工具 | `app/api/common.py` | 预览 URL 解析、路径归一化、`media_path` 选择、请求级缩略图可用性索引 |
| 数据模型与 schema | `app/models/*.py`、`app/api/schemas.py` | 定义实体结构、请求体和响应模型 |
| 服务层 | `app/services/*.py`、`app/services/imports/*.py` | 导入、刷新、分类、封面、回收站、查看器、Tag 匹配、缓存缩略图、收藏夹等业务逻辑 |

## 2. 路由清单

### 2.1 基础与导入

| 文件 | 端点 | 当前行为 |
| --- | --- | --- |
| `basic.py` | `GET /` | 健康检查，返回 `{"status": "ok"}` |
| `basic.py` | `POST /api/import` | 接收 `files`、`last_modified_json`、`created_time_json`、`category_id`、`recent_import_mode`，调用导入流水线 |
| `basic.py` | `GET /api/images/count` | 返回库中 `ImageAsset` 总数 |
| `home.py` | `GET /api/home/overview` | 返回主页所需的统计卡与标签墙分页数据：`visible_image_count` 按显示主分类过滤，`global_tag_count` 保持全局；标签墙按可见图片重新统计 Tag 使用量，并接受 `exclude_image_ids` 来尽量避开最近展示过的代表图 |
| `basic.py` | `POST /api/admin/refresh` | 触发 `quick` 或 `full` 刷新；当 `mode=quick` 且请求体里 `repair_cache=true` 并带 `image_ids` 或 `trash_entry_ids` 时，会走 targeted-only 轻路径做定向预览修复，不再顺带执行全库维护 |

### 2.2 图库管理聚合

| 文件 | 端点 | 当前行为 |
| --- | --- | --- |
| `gallery.py` | `GET /api/gallery/recent/overview` | 返回 recent 快照中“最近一批成功导入图片全集”的一级预览列表与总数 |
| `gallery.py` | `GET /api/gallery/all/overview` | 返回全部可见图片拉平后的一级预览列表与总数 |
| `gallery.py` | `GET /api/gallery/recent/items` | 返回最近导入二级页所需的“相册在前 + 直图在后”混合列表 |
| `gallery.py` | `GET /api/gallery/all/items` | 返回图库总览二级页所需的“相册在前 + 直图在后”混合列表 |

### 2.3 浏览与媒体操作

| 文件 | 端点 | 当前行为 |
| --- | --- | --- |
| `dates.py` | `GET /api/dates` | 返回年月总览和月份代表图 |
| `dates.py` | `GET /api/dates/{date_group}/items` | 返回某月份下的顶层相册与直图混合列表 |
| `albums.py` | `GET /api/albums/by-path/{album_path:path}` | 按物理相册路径取详情 |
| `albums.py` | `GET /api/albums/open-by-path/{album_path:path}` | 在系统文件管理器中打开相册目录 |
| `albums.py` | `GET /api/albums/{album_id}` | 按 `Album.public_id` 取详情 |
| `albums.py` | `POST /api/albums/{album_id}/cover` | 设置手动相册封面 |
| `images.py` | `GET /api/images/meta` | 批量读取图片元数据与 `media_paths` |
| `images.py` | `PATCH /api/images/metadata` | 修改文件名、主分类、创建时间；必要时移动文件到新的月份目录 |
| `images.py` | `GET /api/images/{image_id}/open` | 打开图片；可用 `path` 精确指定某个 `media_path` 实例 |

### 2.4 Tag、收藏与搜索

| 文件 | 端点 | 当前行为 |
| --- | --- | --- |
| `tags.py` | `GET /api/tags` | 列出非草稿 Tag；支持 `ids`、`q`、`type`、`sort_by`、分页 |
| `tags.py` | `GET /api/tags/{tag_id}` | 读取单个非草稿 Tag |
| `tags.py` | `GET /api/tags/{tag_id}/images` | 返回该 Tag 下的可见图片列表，供标签二级页使用 |
| `tags.py` | `POST /api/tags/draft` | 预占隐藏草稿 Tag |
| `tags.py` | `POST /api/tags` | 新建正式 Tag |
| `tags.py` | `POST /api/tags/bulk-create` | 批量新增正式 Tag；整批校验 `name / type / 重复 / 颜色元数据`，任一行失败则整批回滚，并返回 `row_errors` |
| `tags.py` | `PATCH /api/tags/{tag_id}` | 更新 Tag；如果目标是草稿，会在这里转正 |
| `tags.py` | `DELETE /api/tags/{tag_id}` | 删除单个 Tag；草稿与正式 Tag 都走这个接口，正式 Tag 删除时会同步解除图片关联 |
| `tags.py` | `POST /api/tags/bulk-delete` | 批量删除 Tag，并在同一事务里从图片 `tags` 列表中移除对应 id |
| `tags.py` | `GET /api/tags/export/json` | 导出 JSON |
| `tags.py` | `POST /api/tags/import/json` | 导入 JSON，支持 `skip` / `overwrite` 冲突策略 |
| `images.py` | `POST /api/images/tags/filename-match` | 按文件名匹配 Tag，可只预览或直接回写 |
| `images.py` | `POST /api/images/tags/apply` | 对图片批量追加、替换或移除 Tag |
| `collections.py` | `GET /api/collections` | 返回全部顶层、且当前仍有可见图片的收藏夹 |
| `collections.py` | `GET /api/collections/{collection_id}` | 按 `Collection.public_id` 返回收藏夹详情 |
| `collections.py` | `POST /api/collections/search` | 为收藏菜单提供候选收藏夹与命中统计 |
| `collections.py` | `POST /api/collections/apply` | 批量把图片添加、移除或保留在收藏夹中；不存在时可创建收藏夹 |
| `collections.py` | `POST /api/collections/{collection_id}/cover` | 设置手动收藏封面 |
| `search.py` | `GET /api/search/images` | 单输入搜索，支持 `auto`、`filename`、`tag`、`path`、`file`、`imported_at`、`file_created_at`；可结合 `quick_hash`、`start_at`、`end_at` 返回匹配元数据 |
| `search.py` | `POST /api/search/by-file` | 上传单张本地图片，按其 quick hash 反查同图结果，并返回统一搜索响应 |

### 2.5 分类、缓存、系统与回收站

| 文件 | 端点 | 当前行为 |
| --- | --- | --- |
| `categories.py` | `GET /api/categories` | 返回全部主分类并同步 `usage_count` |
| `categories.py` | `POST /api/categories` | 新建主分类 |
| `categories.py` | `PATCH /api/categories/{category_id}` | 更新主分类；默认主分类不可编辑 |
| `categories.py` | `DELETE /api/categories/{category_id}` | 删除主分类并把引用回退到默认主分类 |
| `categories.py` | `POST /api/categories/bulk` | 批量启用、停用或删除主分类 |
| `cache.py` | `DELETE /api/cache` | 清空 `backend/temp` 与 `backend/data/cache`，并清理数据库中过期缩略图记录 |
| `cache.py` | `POST /api/thumbnails/cache` | 启动共享缓存缩略图队列 |
| `cache.py` | `GET /api/thumbnails/cache/status/{task_id}` | 按 `cursor` 增量轮询缓存任务结果 |
| `system.py` | `GET/POST /api/system/cache-thumb-setting` | 浏览缓存缩略图尺寸配置 |
| `system.py` | `GET/POST /api/system/month-cover-setting` | 月份封面尺寸配置 |
| `system.py` | `GET/POST /api/system/page-config` | 浏览模式与滚动窗口范围配置 |
| `system.py` | `GET/POST /api/system/tag-match-setting` | 文件名自动打标配置 |
| `system.py` | `GET /api/system/viewer-info` | 当前系统默认查看器与应用内偏好 |
| `system.py` | `GET /api/system/image-viewers` | 枚举可用查看器并返回图标 |
| `system.py` | `GET/POST /api/system/viewer-preference` | 读取与设置应用内默认查看器 |
| `trash.py` | `GET /api/trash/items` | 返回回收站条目 |
| `trash.py` | `POST /api/trash/reconcile` | 对账并修复回收站条目 |
| `trash.py` | `POST /api/trash/move` | 把图片或相册移入回收站 |
| `trash.py` | `POST /api/trash/restore` | 还原回收站条目 |
| `trash.py` | `POST /api/trash/hard-delete` | 彻底删除回收站条目 |
| `trash.py` | `DELETE /api/trash` | 清空回收站 |

## 3. 关键服务模块

| 模块 | 当前职责 |
| --- | --- |
| `services/import_service.py` | 导入与刷新门面，兼容旧引用 |
| `services/imports/pipeline.py` | 导入批处理、哈希去重、相册链创建、主分类写入、导入期自动打标 |
| `services/imports/maintenance.py` | `quick/full` 刷新、路径对账、缺失预览修复、未入库图片收编 |
| `services/imports/hash_index.py` | `.hash_index.json` 的加载、查询和重建 |
| `services/imports/helpers.py` | 路径归一化、文件时间回写、缩略图条目更新等辅助函数 |
| `services/image_frame_service.py` | 多帧图片首帧提取、动图识别、尺寸与帧数元数据归一化 |
| `services/recent_import_service.py` | 维护“最近一批成功导入图片”的快照，支持按 replace/append 聚合同一前端导入会话 |
| `services/parallel_processor.py` | 并行哈希、尺寸识别与月份封面生成 |
| `services/cache_thumb_service.py` | 生成 `data/cache/*.webp` 浏览缓存缩略图 |
| `services/thumbnail_service.py` | 缩略图生成底层逻辑 |
| `services/category_service.py` | 默认主分类、主分类校验、使用计数同步、引用回退 |
| `services/tag_match_service.py` | 文件名分词、Tag 匹配、Tag 排序、`last_used_at` 与 `usage_count` 更新 |
| `services/collection_service.py` | 收藏夹创建/查找、候选列表、增删图片、封面选择、统计刷新 |
| `services/cover_service.py` | 相册/收藏手动封面 payload 读写 |
| `services/visible_album_service.py` | 依据当前可见图片推导相册可见性、封面与计数 |
| `services/trash_service.py` | 回收站列表、移入、还原、硬删除、清空、对账 |
| `services/viewer_service.py` | Windows 查看器枚举、图标提取、应用内默认查看器启动 |
| `services/app_settings_service.py` | `app_settings.json` 读写，持久化页面、缩略图和自动打标配置 |

## 4. 当前协议细节

### 4.1 导入协议

- `POST /api/import` 使用 `multipart/form-data`。
- 当前前端会传：
  - `files`
  - `last_modified_json`
  - `created_time_json`
  - `category_id`
  - `recent_import_mode`
- 后端会先校验 `category_id` 是否存在，再进入导入流水线。
- `recent_import_mode` 当前有两种语义：
  - `replace`：开始一次新的“最近导入”会话，重置旧快照
  - `append`：把后续批次合并到当前快照，解决前端分块上传导致的 recent 只显示最后一批问题
- `RecentImportOperation.successful_image_ids` 当前是 recent 一级页的主数据源，记录该前端导入流程里所有成功导入的图片 id；旧的 `preview_image_ids` 仅保留兼容用途。
- 如果 `tag_match_setting.enabled=true`，导入批次会在同一数据库事务内按文件名自动匹配 Tag，并以 `append_unique` 方式追加到图片 `tags`。
- 导入期只会为本批次真正新增关联的 Tag 刷新 `last_used_at` 并增量同步 `usage_count`。
- GIF、动态 WEBP 等多帧图片会在导入阶段统一抽取首帧生成 temp 缩略图与尺寸元数据，同时写入 `ImageAsset.is_animated + animation_meta`；其中 `animation_meta` 只在动图时保存 `frame_count / format`。

### 4.2 图库管理聚合协议

- `GET /api/gallery/recent/overview` 与 `GET /api/gallery/all/overview` 都返回：
  - `scope`
  - `total`
  - `items`
- 一级页 overview 只返回图片预览条目，不返回相册节点；recent overview 优先读取 `successful_image_ids`，而不是旧的 preview 兼容字段。
- `GET /api/gallery/recent/items` 与 `GET /api/gallery/all/items` 返回 `DateItem` 风格的混合列表，继续复用 `BrowsePage`：
  - 相册节点在前
  - 直图节点在后
  - 两类节点都沿用现有日期视图的排序与详情协议
- 日期、相册、收藏、搜索、图库 overview/item 接口现在都会把动图元数据一并返回给前端，用于统一显示 `GIF` / `WEBP` 标记。

### 4.2.1 主页聚合协议

- `GET /api/home/overview` 当前接收：
  - `limit`
  - `offset`
  - `exclude_image_ids`，允许通过重复 query 参数传多个 image id
- 返回体分两块：
  - `stats.visible_image_count`：按 `Category.is_active` 过滤后的可见图片总数
  - `stats.global_tag_count`：全局非草稿 Tag 总数
  - `stats.visible_tag_count`：当前显示主分类范围内真正命中的 Tag 数
  - `tag_wall.items[*]`：`tag` 元数据、`visible_usage_count` 和 `cover`
- `tag_wall.items[*].cover` 是主页方卡直接可消费的图片结构，包含：`id`、`thumb_url`、`cache_thumb_url`、`media_rel_path`、`width/height`、`is_animated + animation_meta`。
- 代表图选择规则：优先避开本次请求传入的 `exclude_image_ids`，其次避免同一批返回中的多个 Tag 重复使用同一张图；只有当某个 Tag 的候选图片确实不足时，才回退为重复图。

### 4.3 图片元数据编辑

- `PATCH /api/images/metadata` 当前支持三种更新：
  - `name`
  - `category_id`
  - `file_created_at`
- 多选时不允许改文件名；这是 `PATCH /api/images/metadata` 的后端 `400` 硬校验，前端只是同步禁用对应 UI。
- 传入 `file_created_at` 后，如果月份变化，后端会把文件物理移动到新的 `media/YYYY-MM/...` 目录，并保留原有子目录链；如果目标目录已存在同名文件，会自动预留一个唯一文件名后再落盘。
- 如果一张图片有多个 `media_path` 实例，前端应通过 `media_rel_path` 精确指定目标实例。

### 4.4 Tag 协议

- 草稿 Tag 通过 `created_by = system:draft-reserve` 标记。
- 草稿不会出现在：
  - `GET /api/tags`
  - `GET /api/tags/{id}`
  - `GET /api/tags/export/json`
  - 图片 Tag 批量应用逻辑
- 前端新建标签的实际链路是：
  1. `POST /api/tags/draft`
  2. 弹窗编辑
  3. `PATCH /api/tags/{id}` 保存并转正
  4. 取消时 `DELETE /api/tags/{id}` 删除草稿
- 正式 Tag 删除协议现在统一为“删标签 + 解关联”：
  - `DELETE /api/tags/{id}` 与 `POST /api/tags/bulk-delete` 都会在同一事务中单次扫描 `ImageAsset`，从 `ImageAsset.tags` 中移除目标 tag id，再删除 Tag 记录。
  - 删除响应不会删除图片本身，只会清理 Tag 实体和图片上的标签引用。
  - 批量删除返回 `deleted_tag_ids`、`deleted_count`、`detached_image_count`、`detached_reference_count`、`missing_ids`，供设置页表格管理面板使用。
- `POST /api/tags/bulk-create` 约定：
  - 请求体使用 `tags` 数组，每行当前接收 `name`、`display_name`、`description`、`type`、`metadata`
  - 后端会逐行校验 `type ∈ {normal, artist, copyright, character, series}`，并在写入后自动补全 `public_id`
  - 任一行 `name` 非法、`type` 非法、同批重复、与数据库重复，或 `metadata` 颜色非法时，整批返回 `400`，并通过 `row_errors[*].row_index/field/message` 描述错误

### 4.5 收藏夹协议

- 收藏夹详情和封面接口都使用 `Collection.public_id`，不是数值主键。
- `POST /api/collections/search` 的核心用途不是全文搜索，而是为“当前选中图片”返回候选收藏夹与命中统计。
- `POST /api/collections/apply` 接收 `image_actions`，每个条目包含：
  - `image_id`
  - `action`，当前使用 `add`、`remove`、`keep`
- 如果未传现有 `collection_id`，后端会按标题创建或复用同名收藏夹。

### 4.6 搜索协议

- `GET /api/search/images` 现在支持：
  - `auto`
  - `filename`
  - `tag`
  - `path`
  - `file`
  - `imported_at`
  - `file_created_at`
- `auto` 模式下：
  - 看起来像图片路径时，会转为 `path`
  - 否则会转为混合搜索 `mixed`
- 各模式的额外参数约定：
  - `file`：前端传 `q=文件名`、`mode=file`，并额外传 `quick_hash`
  - `imported_at`：前端传 `q=开始时间~结束时间`、`mode=imported_at`，并额外传 `start_at`、`end_at`
  - `file_created_at`：前端传 `q=开始时间~结束时间`、`mode=file_created_at`，并额外传 `start_at`、`end_at`
- `POST /api/search/by-file` 使用 `multipart/form-data` 上传单个 `file`，后端会计算 quick hash，再复用 `file` 模式返回统一的 `SearchImageResponse`。
- 前端一级搜索页默认使用有限结果；`/search/results` 二级页会把 `limit=0` 传给后端，以拉取完整结果集。
- 返回体当前包含：
  - `requested_mode` / `resolved_mode`
  - `total`
  - `source_media_rel_path`
  - `quick_hash`
  - `included_tags`
  - `items[*].matched_by`
  - `items[*].matched_tags`
- `matched_by` 目前可能出现：
  - `filename`
  - `tag`
  - `path`
  - `quick_hash`
  - `imported_at`
  - `file_created_at`
- 路径模式依然保留给后端兼容逻辑；文件模式会直接按传入的 `quick_hash` 返回同图图片，因此结果里可能同时含：
  - 源路径命中
  - `quick_hash` 命中

### 4.7 缓存缩略图队列协议

- `POST /api/thumbnails/cache` 当前请求体定义在 `app/api/schemas.py::CacheRequest`。
- 可用字段：
  - `image_ids`
  - `ordered_image_ids`
  - `generation`
  - `page_token`
  - `sort_signature`
  - `direction`
  - `anchor_image_id`
  - `anchor_item_key`
  - `anchor_offset`
- 现有行为：
  - 已存在的缓存缩略图会立即放进返回流
  - 同一个 `page_token` 的新 `generation` 会替换旧页面任务
  - 状态接口通过 `cursor` 返回新增完成项，而不是每次全量返回
- 浏览缓存缩略图对多帧图片也统一使用首帧，不再依赖 OpenCV 直接解码整段 GIF/WEBP 原始文件。

### 4.8 页面配置与自动打标设置

- `page_config` 当前持久化在 `backend/data/app_settings.json`，包含：
  - `browse_mode`: `scroll | paged`
  - `scroll_window_size`: `40-200`，步长 20，默认 100
- `tag_match_setting` 当前也持久化在 `app_settings.json`，包含：
  - `enabled`
  - `noise_tokens`
  - `min_token_length`
  - `drop_numeric_only`
  - `sort_mode`，当前固定为 `name_asc`
- 后端已经提供 `GET/POST /api/system/tag-match-setting`，但当前前端设置页还没有实际入口。

### 4.9 回收站协议

- `TrashEntry.entry_key` 是每个回收站条目的不透明唯一键，不等同于数据库自增 `id`；当前主要用于生成物理 payload 路径前缀，并作为前端回收站条目的稳定 key。
- 当前回收站 payload 默认平铺保存为 `trash/{entry_key}__{payload_name}`；对账与清理逻辑仍兼容早期 `trash/entries/{entry_key}/payload/` 目录结构。
- 图片移入回收站时会一并保留 `original_path`、`original_date_group`、`category_id`、`tags`、`imported_at`、`file_created_at` 等恢复所需元数据；列表接口会把这些字段继续返回给前端。
- `POST /api/trash/move` 的请求项字段是：
  - `type`
  - `image_id`
  - `media_rel_path`
  - `album_path`
- 回收站恢复会复用导入/刷新链路重建数据库和相册统计。
- `POST /api/trash/reconcile` 用于进入回收站后的轻量对账与预览修复，不替代完整刷新。
