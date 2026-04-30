# picTagView Backend API 与服务说明

本文档按“路由层 -> 服务层 -> 当前协议细节”说明后端实现，内容以 `backend/app/api/routers/*.py` 与 `backend/app/services/*.py` 的当前代码为准。

## 1. 分层概览

| 层级 | 位置 | 当前职责 |
| --- | --- | --- |
| 路由聚合 | `app/api/routes.py` | 注册 `basic`、`categories`、`dates`、`albums`、`images`、`collections`、`search`、`system`、`cache`、`tags`、`trash` |
| 路由实现 | `app/api/routers/*.py` | 解析请求、校验参数、组织响应、调用服务 |
| 通用 API 工具 | `app/api/common.py` | 预览 URL 解析、路径归一化、`media_path` 选择、请求级缩略图可用性索引 |
| 数据模型与 schema | `app/models/*.py`、`app/api/schemas.py` | 定义实体结构、请求体和响应模型 |
| 服务层 | `app/services/*.py`、`app/services/imports/*.py` | 导入、刷新、分类、封面、回收站、查看器、Tag 匹配、缓存缩略图、收藏夹等业务逻辑 |

## 2. 路由清单

### 2.1 基础与导入

| 文件 | 端点 | 当前行为 |
| --- | --- | --- |
| `basic.py` | `GET /` | 健康检查，返回 `{"status": "ok"}` |
| `basic.py` | `POST /api/import` | 接收 `files`、`last_modified_json`、`created_time_json`、`category_id`，调用导入流水线 |
| `basic.py` | `GET /api/images/count` | 返回库中 `ImageAsset` 总数 |
| `basic.py` | `POST /api/admin/refresh` | 触发 `quick` 或 `full` 刷新；支持 `repair_cache + image_ids/trash_entry_ids` 的定向预览修复 |

### 2.2 浏览与媒体操作

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

### 2.3 Tag、收藏与搜索

| 文件 | 端点 | 当前行为 |
| --- | --- | --- |
| `tags.py` | `GET /api/tags` | 列出非草稿 Tag；支持 `ids`、`q`、`type`、`sort_by`、分页 |
| `tags.py` | `GET /api/tags/{tag_id}` | 读取单个非草稿 Tag |
| `tags.py` | `GET /api/tags/{tag_id}/images` | 返回该 Tag 下的可见图片列表，供标签二级页使用 |
| `tags.py` | `POST /api/tags/draft` | 预占隐藏草稿 Tag |
| `tags.py` | `POST /api/tags` | 新建正式 Tag |
| `tags.py` | `PATCH /api/tags/{tag_id}` | 更新 Tag；如果目标是草稿，会在这里转正 |
| `tags.py` | `DELETE /api/tags/{tag_id}` | 删除 Tag；草稿与正式 Tag 都走这个接口 |
| `tags.py` | `GET /api/tags/export/json` | 导出 JSON |
| `tags.py` | `POST /api/tags/import/json` | 导入 JSON，支持 `skip` / `overwrite` 冲突策略 |
| `images.py` | `POST /api/images/tags/filename-match` | 按文件名匹配 Tag，可只预览或直接回写 |
| `images.py` | `POST /api/images/tags/apply` | 对图片批量追加、替换或移除 Tag |
| `collections.py` | `GET /api/collections` | 返回全部顶层、且当前仍有可见图片的收藏夹 |
| `collections.py` | `GET /api/collections/{collection_id}` | 按 `Collection.public_id` 返回收藏夹详情 |
| `collections.py` | `POST /api/collections/search` | 为收藏菜单提供候选收藏夹与命中统计 |
| `collections.py` | `POST /api/collections/apply` | 批量把图片添加、移除或保留在收藏夹中；不存在时可创建收藏夹 |
| `collections.py` | `POST /api/collections/{collection_id}/cover` | 设置手动收藏封面 |
| `search.py` | `GET /api/search/images` | 单输入搜索，支持 `auto`、`filename`、`tag`、`path` |

### 2.4 分类、缓存、系统与回收站

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
- 后端会先校验 `category_id` 是否存在，再进入导入流水线。
- 如果 `tag_match_setting.enabled=true`，导入批次会在同一数据库事务内按文件名自动匹配 Tag，并以 `append_unique` 方式追加到图片 `tags`。
- 导入期只会为本批次真正新增关联的 Tag 刷新 `last_used_at` 并增量同步 `usage_count`。

### 4.2 图片元数据编辑

- `PATCH /api/images/metadata` 当前支持三种更新：
  - `name`
  - `category_id`
  - `file_created_at`
- 多选时不允许改文件名。
- 传入 `file_created_at` 后，如果月份变化，后端会把文件物理移动到新的 `media/YYYY-MM/...` 目录。
- 如果一张图片有多个 `media_path` 实例，前端应通过 `media_rel_path` 精确指定目标实例。

### 4.3 Tag 协议

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

### 4.4 收藏夹协议

- 收藏夹详情和封面接口都使用 `Collection.public_id`，不是数值主键。
- `POST /api/collections/search` 的核心用途不是全文搜索，而是为“当前选中图片”返回候选收藏夹与命中统计。
- `POST /api/collections/apply` 接收 `image_actions`，每个条目包含：
  - `image_id`
  - `action`，当前使用 `add`、`remove`、`keep`
- 如果未传现有 `collection_id`，后端会按标题创建或复用同名收藏夹。

### 4.5 搜索协议

- `GET /api/search/images` 支持 `auto`、`filename`、`tag`、`path`。
- `auto` 模式下：
  - 看起来像图片路径时，会转为 `path`
  - 否则会转为混合搜索 `mixed`
- 路径模式先定位源图片，再按 `quick_hash` 返回同图图片，因此结果里可能同时含：
  - 源路径命中
  - `quick_hash` 命中

### 4.6 缓存缩略图队列协议

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

### 4.7 页面配置与自动打标设置

- `page_config` 当前持久化在 `backend/data/app_settings.json`，包含：
  - `browse_mode`: `scroll | paged`
  - `scroll_window_size`: `40-200`，步长 20，默认 100
- `tag_match_setting` 当前也持久化在 `app_settings.json`，包含：
  - `enabled`
  - `noise_tokens`
  - `min_token_length`
  - `drop_numeric_only`
- 后端已经提供 `GET/POST /api/system/tag-match-setting`，但当前前端设置页还没有实际入口。

### 4.8 回收站协议

- `POST /api/trash/move` 的请求项字段是：
  - `type`
  - `image_id`
  - `media_rel_path`
  - `album_path`
- 回收站恢复会复用导入/刷新链路重建数据库和相册统计。
- `POST /api/trash/reconcile` 用于进入回收站后的轻量对账与预览修复，不替代完整刷新。
