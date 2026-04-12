# picTagView Backend 技术说明书

## 1. 项目位置
- `D:\project2025\Python_Projects\picTagView\backend`

## 2. 后端架构概览
- 框架：FastAPI
- ORM：SQLModel（基于 SQLAlchemy）
- 数据库：SQLite（文件路径由 `app/core/config.py` 配置）
- 静态文件：FastAPI `StaticFiles` 挂载 `MEDIA_DIR` 与 `TEMP_DIR`，分别用于原图/缩略图访问
- 并行：`concurrent.futures` 的 `ProcessPoolExecutor` + `ThreadPoolExecutor`，用于哈希与缩略图生成

## 3. 主要模块说明

### 3.1 `app/main.py`
- 入口文件，创建应用 `create_app()`：
  - `init_db()`（初始化/建表/迁移）
  - CORS 配置为 `*`
  - 挂载 `
  /thumbnails` -> `TEMP_DIR`
  - 挂载 `/media` -> `MEDIA_DIR`
  - 注册路由 `app.include_router(api_router)`

### 3.2 `app/api/routes.py` + `app/api/routers/*`
- 路由聚合入口：`app/api/routes.py` 只负责 `include_router`。
- 业务按职责拆分到子路由模块：
  - `app/api/routers/basic.py`：`GET /`、`POST /api/import`、`GET /api/images/count`、`POST /api/admin/refresh`
  - `app/api/routers/dates.py`：`GET /api/dates`、`GET /api/dates/{date_group}/items`
  - `app/api/routers/albums.py`：`GET /api/albums/{album_id}`
  - `app/api/routers/images.py`：`GET /api/images/{image_id}/open`
  - `app/api/routers/system.py`：`/api/system/*` 相关接口
  - `app/api/routers/cache.py`：`DELETE /api/cache`、`/api/thumbnails/cache*`
- 共享查询与路径工具在 `app/api/common.py`：软删除过滤、缩略图 URL 解析、存储路径解析。

补充（2026-04）：
- `GET /api/dates/{date_group}/items` 与 `GET /api/albums/{album_id}` 的条目模型新增 `sort_ts`（Unix 秒级时间戳，可为空）。
- `sort_ts` 生成规则：
  - 图片条目：优先 `file_created_at`，回退 `imported_at`，再回退 `created_at`。
  - 相册条目：优先 `updated_at`，回退 `created_at`。
- 前端据此支持“Date/Alpha 排序字段切换 + 升降序切换”。
- 前端排序规则补充：相册项与图片项分组独立排序（各自按 Date/Alpha 与升降序），最终始终保持“相册在前，图片在后”。
- 前端交互补充：排序字段选择器由滑块改为 `select`（`Date`/`Alpha`），升降序箭头按钮独立放在选择框外侧。
- 前端结构补充：日期详情页与相册页的 header 已统一为面包屑样式，并组件化为 `frontend/src/components/BreadcrumbHeader.vue`，用于复用“返回按钮 + 面包屑 + 项目数 + 排序控件 + 右侧扩展操作区”。
- 返回与面包屑导航行为：
  - 相册面包屑结构：日期视图 › YYYY-MM › 祖先相册… › 当前相册。
  - 月份节点（YYYY-MM）是可点击链接，目标为 `/calendar?group=YYYY-MM`。
  - 日期视图页在数据加载完成后自动恢复到对应月份详情，随后清除 query 参数（路径不变，不触发组件重建）。
  - 返回按钮语义统一为"目录上一级"：日期详情页返回月份网格；相册页优先返回父相册，无父相册则带月份参数回到日期视图。
  - 月份上下文优先级：`route.query.group` › `album.date_group` › `album.path` 中的 YYYY-MM。
  - 关键架构约束：`App.vue` 路由组件使用 `:key="route.path"` 而非 `fullPath`，确保 query 参数变化不会销毁并重建组件，避免导航恢复死循环。
- **页面切换过渡动画**：
  - `App.vue` 中 `<router-view>` 使用 `<Transition name="page" mode="out-in">` 包裹路由组件，跨路由切换（日期视图 ↔ 相册视图、不同相册层级间）均有淡入淡出动画（离开 110ms、进入 160ms），消除瞬间"闪动"感。
  - `BreadcrumbHeader.vue` 中面包屑 `<nav>` 通过 `:key="crumbsKey"` 绑定路径签名，外层 `<Transition name="bc-fade" mode="out-in">` 在路径节点变化时触发淡入淡出（离开 80ms、进入 160ms）。
  - `DateViewPage.vue` 内部月份→详情切换使用 `t-forward`/`t-back` 命名过渡（缩放 + 位移），月份网格使用 `.grid-wrapper--fading` 实现淡出配合。
- 默认策略：
  - 日期视图详情（非相册视图）默认 `Date` 升序。
  - 相册视图默认 `Alpha` 升序。

### 3.3 `app/services/import_service.py`（门面）
- 对外稳定入口：
  - `import_files(files, last_modified_times, created_times)`
  - `refresh_library()`
  - `rebuild_hash_index()`
  - `recalculate_album_counts()`
- 该文件仅做兼容导出；实现已拆到 `app/services/imports/*`。

### 3.3a `app/services/imports/pipeline.py`
- 导入主流程（批处理与去重核心）
- `import_files(files, last_modified_times, created_times)`：
  - 解析上传路径（兼容 `webkitRelativePath`），`_parse_relative_path` 返回 `(subdir_chain, filename)`
  - 过滤非图片，由扩展名判断
  - 维护目录级 `date_group`，按子目录最早时间分组（格式 `YYYY-MM`）
  - 导入前加载哈希索引缓存 `.hash_index.json`，用于 O(1) 去重查找
  - 子目录链 → 自动创建 Album 树（`_ensure_album_chain`），所有嵌套层级继承顶层 `date_group`
  - 去重策略：相同哈希在相册内 → 保留并添加 album 关系；直传重复 → 跳过
  - 导入结束后保存哈希索引并释放内存
  - 批次读取文件内容（`IMPORT_BATCH_SIZE=50`）
  - 线程池并行 `process_from_bytes` 只为"每月封面所需图片"生成 temp 缩略图
  - 其他图片调用 `process_hash_only_from_bytes`（`_compute_hash_only` worker）：并行完成 SHA-256 + xxhash + **cv2.imdecode 尺寸读取**，不生成缩略图
  - DB 串行写入循环中仅使用已并行得到的宽高，不再在主线程调用 cv2（性能优化方案 A）
  - 导入不中断行为：前端在开始导入时会设置全局标记 `window.__ptvImporting = true`（见 `frontend/src/pages/GalleryPage.vue`），导入结束时恢复为 `false`。
  - 前端刷新策略变更（路由切换相关）：项目已移除“路由切换自动触发全库刷新”的行为，`frontend/src/router/index.js` 不再在每次路由变更时发起后台 `POST /api/admin/refresh`。当前前端刷新策略为：
    - 仅在 Gallery 页面由用户点击的“刷新”按钮触发完整的 `POST /api/admin/refresh?mode=full`（保留为手动触发的全库修复/补齐与新文件收编）。
    - 切换到首页（`/`）时仅请求 `GET /api/images/count`，用于刷新并显示库总数的统计信息。
    - 在 Gallery 与 DateView（日历）页面，前端会对缩略图加载错误（例如 `404`）做出响应：当页面检测到应从 `TEMP_DIR` 读取的缩略图缺失且对应媒体文件存在时，会立即（无延迟）调用 `POST /api/admin/refresh` 以让后端补齐缺失的 temp 缩略图；刷新完成后前端会重新拉取相关数据并使用缓存击穿（例如追加时间戳）来重新加载刚生成的缩略图并更新显示。该策略避免了路由切换时与导入并发造成的冲突，同时将自动修复控制在真正发生缺失时触发。
  - 文件时间规则：取创建时间与修改时间最小值，回刷到导入文件，并记录到元数据
  - 写入 `ImageAsset`（`quick_hash`、尺寸、mime、tags/thumbs 等扩展字段）

### 3.3b `app/services/imports/maintenance.py`
- 维护/修复工作流：
- `refresh_library()`：
  - 支持 `mode=quick|full`（默认 `quick`）
  - 三阶段执行：
    1) 路径对账与关系修复：清理失效 `media_path`、重建 `ImageAsset.album`、维护 `Album` 表并处理非相册唯一实例冲突
    2) 缩略图与元数据修复：补齐代表图所需 400×400 temp 缩略图及缺失元数据
    3) `full` 模式下收编新文件：扫描 `MEDIA_DIR` 中未入库图片，按导入规则做 hash 去重并写回索引
  - 清理 orphan cache（无对应媒体记录的 `*_cache.webp`）
- `recalculate_album_counts()`：重算 `photo_count` / `subtree_photo_count` 与封面；同时清空并完整重建 `album_image` 关联表。

### 3.3c `app/services/imports/hash_index.py`
- 哈希索引缓存子模块：
  - `load_hash_index()` / `save_hash_index()`
  - `lookup_hash_index()` / `lookup_quick_hash()`
  - `add_to_hash_index()` / `rebuild_hash_index()`

### 3.3d `app/services/imports/helpers.py`
- 导入与维护公共工具：
  - 路径转换：`to_project_relative`、`resolve_stored_path`
  - 文件时间：`apply_file_times`、`set_windows_creation_time`
  - 缩略图条目：`required_thumb_entry`、`upsert_thumb`、`has_required_thumb`
  - 媒体基础能力：`quick_hash_from_bytes`、`mime_from_name`、`image_dimensions_from_*`

### 3.4 `app/services/parallel_processor.py`
- 图片处理核心，提供两种 API：
  - `process_from_paths(entries, temp_dir)`：磁盘到磁盘，使用 `ProcessPoolExecutor`（适合大量文件读取）
  - `process_from_bytes(entries, temp_dir)`：字节到磁盘，使用 `ThreadPoolExecutor`（适合已加载数据、避免进程间 IPC）
- 关键实现 `_process_from_path` / `_process_from_bytes`：
  - 计算 SHA-256 hash
  - 基于 `opencv-python`/`numpy` decode 并中心裁剪缩放到 `400×400`，保存 `temp_dir/{hash}.webp`（WebP 格式）
  - 误码处理 `decode_failed`、异常情况返回错误
- `_compute_hash_only`（线程池 worker）：
  - 计算 SHA-256 + xxhash（quick_hash）**并同时用 cv2.imdecode 获取图片宽高**
  - 将 cv2 解码移入并行阶段，避免在 DB 串行写入循环中执行 cv2（约 230 ms/张），消除主要性能瓶颈
  - 解码失败时宽高返回 `None`，import_service 保留 fallback 调用进行补偿

### 3.4b `app/services/viewer_service.py`
- 系统看图程序集成逻辑（原先在路由层）：
  - 读取/写入 `app_settings.json` 中的偏好看图程序
  - Windows 注册表枚举图片关联程序与默认程序
  - 解析并提取程序图标（输出到 `VIEWER_ICON_DIR`）
  - 启动偏好看图程序打开图片（失败回退系统默认）

### 3.4c `app/services/app_settings_service.py`
- 应用设置持久化服务：
  - 统一读写 `data/app_settings.json`
  - 提供缓存缩略图短边配置：
    - `get_cache_thumb_short_side_px()`（默认 600）
    - `set_cache_thumb_short_side_px(value)`（限制范围 100~4000）
  - 提供月份封面尺寸配置：
    - `get_month_cover_size_px()`（默认 400）
    - `set_month_cover_size_px(value)`（限制范围 100~2000）
  - 该配置被 `cache_thumb_service` 在生成 `data/cache/*.webp` 时使用
  - `parallel_processor` 会使用月份封面尺寸配置生成 `temp/*.webp`

### 3.5 `app/models/image_asset.py`
- 数据模型 `ImageAsset`：
  - `id` (int): 主键
  - `original_path` (str): 导入时的原始相对/上传路径，带索引
  - `full_filename` (str | null): 文件名
  - `file_hash` (str): SHA-256 散列，唯一索引，用于去重
  - `quick_hash` (str | null): 快速哈希（xxhash64 或回退），用于快速比对
  - `thumbs` (JSON array): 详细的缩略图条目数组，每项包含 `type`/`path`/`width`/`height`/`mime_type`/`generated_at`
  - `media_path` (JSON array of str): 存放在 `MEDIA_DIR` 下的原图相对路径列表；一张图可在多个相册中存储多个副本
  - `date_group` (str | null): 年-月分组，格式 `YYYY-MM`，用于前端日期视图索引
  - `file_created_at` (datetime | null): 文件原始创建时间（如可用）
  - `imported_at` (datetime): 导入时间
  - `width` / `height` / `file_size` / `mime_type`: 媒体元信息
  - `category` (str): 可选分类
  - `tags` (JSON array of int): 关联的 Tag ID 整数列表，如 `[23, 45, 91]`；前端查询标签详情时通过 `/api/tags?ids=23,45,91` 批量获取
  - `album` (JSON array of arrays): 所属相册路径，每个内层数组是从根相册到叶相册的 `public_id` 完整路径，如 `[["album_1", "album_3"], ["album_5"]]`（保留用于兼容；实际查询已通过 `album_image` 关联表完成）
  - `collection` (JSON array): 所属收藏集信息，数据结构待定，默认空数组
  - `created_at` (datetime): 记录创建时间

### 3.5b `app/models/album.py`
- 数据模型 `Album`（树形相册结构）：
  - `id` (int): 主键自增
  - `public_id` (str): 外部暴露标识，格式 `album_{id}`，唯一索引
  - `title` (str): 相册名称（可重复，取自子目录名）
  - `description` (str | null): 描述
  - `path` (str): 媒体目录下的完整路径，格式 `{date_group}/{subdir1}/{subdir2}`，用于唯一定位
  - `category` (str | null): 分类
  - `is_leaf` (bool): 是否为叶节点相册（无子相册）
  - `parent_id` (int | null): 父相册 ID（顶层相册为 null）
  - `cover` (JSON dict | null): 封面信息 `{photo_id, thumb_path, filename, updated_at}`，按文件名字母序选取最早文件
  - `photo_count` (int): 直属照片数
  - `subtree_photo_count` (int): 含所有子相册的总照片数
  - `sort_mode` (str): 排序模式 `alpha`（默认）/ `date` / `manual`
  - `settings` / `stats` (JSON dict): 扩展设置与统计
  - `date_group` (str | null): 所有嵌套层级继承顶层的 `date_group`
  - `created_at` / `updated_at`: 时间戳

### 3.5c `app/models/soft_delete.py`
- 数据模型 `PathSoftDelete`（独立软删除表）：
  - `id` (int): 主键
  - `entity_type` (str): 目标类型，当前为 `image` 或 `album`
  - `owner_id` (int | null): 关联的 `ImageAsset.id` 或 `Album.id`
  - `target_path` (str): 被删除的规范化路径；图片对应具体的 `media_path` 条目，相册对应 `Album.path`
  - `deleted_at` (datetime): 删除时间戳
  - `created_at` (datetime): 记录创建时间

说明：当前查询层通过 `path_soft_delete` 过滤可见项，`ImageAsset` 与 `Album` 本身不再保存 `deleted_at` 字段。
补充：可见性以 `target_path` 为准做路径级判定，不再仅以 `owner_id` 做整实体屏蔽。

### 3.5d 哈希索引缓存（`.hash_index.json`）
- 文件位置：`MEDIA_DIR/.hash_index.json`
- 格式：`{"file_hash": image_id, ...}` 的 JSON 对象
- 用途：导入时快速去重查询，避免逐条 DB 查询
- 生命周期（由 `app/services/imports/hash_index.py` 管理）：
  - 导入开始时加载到内存
  - 导入过程中新增/更新条目
  - 导入结束后序列化回磁盘
  - `refresh_library()` 结束时完整重建

示例: 以下为从数据库抽取的一个 `ImageAsset` 记录示例，展示了字段实际存储形态：

```json
{
"id": 123,
"original_path": "photos/vacation/img001.jpg",
"full_filename": "img001.jpg",
"file_hash": "c3c006a821fe9087d1506cadb12c03c2e8bb5b65aba8ef9ca2251643798e97d3",
"quick_hash": "c3c006a821fe9087",
"thumbs": [
{
"type": "webp",
"path": "backend/temp/c3c006a821fe9087d1506cadb12c03c2e8bb5b65aba8ef9ca2251643798e97d3.webp",
"width": 400,
"height": 400,
"mime_type": "image/webp",
"generated_at": "2026-03-20T10:00:00.000000"
},
{
"type": "webp",
"path": "backend/data/cache/c3c006a821fe9087d1506cadb12c03c2e8bb5b65aba8ef9ca2251643798e97d3_cache.webp",
"width": 600,
"height": 450,
"mime_type": "image/webp",
"generated_at": "2026-03-20T10:05:00.000000"
}
],
"media_path": ["media/2025-03/img001.jpg"],
"date_group": "2025-03",
"file_created_at": "2025-03-15 12:34:00.000000",
"imported_at": "2026-03-20T09:59:00.000000",
"created_at": "2026-03-20 09:59:00.000000",
"width": 4000,
"height": 3000,
"file_size": 3421123,
"mime_type": "image/jpeg",
"category": "",
"tags": [23, 45, 91],
"album": [["album_1", "album_3"]],
"collection": []
}
```

说明：`thumbs` 字段通常以 JSON 存储在 SQLite 中（`SQLModel` 使用 `JSON` 列），`thumb_path` 与 `thumbs[*].path` 可为相对路径或工程内路径，外部访问时会由路由解析为 `/thumbnails/...`。
`tags` 字段存储整数 ID 列表，而非文字字符串；前端需显示标签名称时通过批量查询接口 `/api/tags?ids=...` 获取对应 `Tag` 记录。

### 3.5e `app/models/album_image.py`
- 数据模型 `AlbumImage`（相册-图片显式关联表）：
  - `id` (int): 主键自增
  - `album_id` (int): 关联 `Album.id`，建有索引 `ix_album_image_album_id`
  - `image_id` (int): 关联 `ImageAsset.id`，建有索引 `ix_album_image_image_id`
  - `sort_order` (int): 排序权重，默认 0
  - `created_at` (datetime): 记录创建时间
- 唯一约束：`(album_id, image_id)` 联合唯一，防止重复关联
- 用途：替代以往遍历全量 `ImageAsset.album` JSON 的方式，通过索引 JOIN 快速定位相册内图片，显著降低相册视图与日期视图的 I/O 与 CPU 开销。
- 数据维护：
  - 导入流程 (`pipeline.py`) 在写入 `ImageAsset.album` 的同时双写 `album_image` 行
  - `recalculate_album_counts()` 会先清空再完整重建 `album_image` 数据
  - `refresh_library(mode=full)` 收编新文件时同步写入
  - 首次部署可通过 `scripts/backfill_album_image.py` 从现有数据回填

### 3.5f `app/models/tag.py`
- 数据模型 `Tag`（标签库）：
  - `id` (int): 主键自增
  - `public_id` (str): 对外稳定标识符，格式 `tag_{id}`，唯一索引；写入 DB 后由系统自动回填
  - `name` (str): 规范化名称，全小写英文，数据库唯一约束，最大 256 字节
  - `display_name` (str): 前端展示名称，默认与 name 相同
  - `type` (str): 标签种类，取值为 `normal` / `artist` / `artwork` / `series`，默认 `normal`
  - `description` (str | null): 描述，最大 1024 字节
  - `category` (str | null): 分类，与其他实体保持一致
  - `usage_count` (int): 缓存字段，表示当前有多少张图片关联了该 Tag，由写入侧维护
  - `last_used_at` (str | null): Tag 最后被关联或访问的时间，格式 `YYYYMMDDHHMMSS`
  - `metadata_` (JSON dict): 存储为数据库列 `metadata`，可扩展扩展字段，结构如下：
    - `schema_version` (int): Tag 元信息版本号，当前为 1
    - `color` (str): 展示颜色，十六进制如 `#FF9900`
    - `created_via` (str): 创建来源，合法值见下表
    - `ui_hint` (dict): 前端 UI 展示提示，如 `{"badge": "city", "promote": true}`
    - `notes` (str): 备注，默认留空
  - `created_at` (datetime): 记录创建时间（UTC）
  - `created_by` (str): 创建者，主控生成为 `admin`，导入为 `import`
  - `updated_at` (datetime): 最后更新时间（UTC）

  **`type` 合法值说明：**

  | 值 | 含义 |
  |---|---|
  | `normal` | 普通标签 |
  | `artist` | 作者/创作者标签 |
  | `copyright` | 作品标签 |
  | `character` | 人物标签 |
  | `series` | 系列标签 |

**`created_via` 合法值说明：**

| 值 | 含义 |
|---|---|
| `manual` | 人工创建 |
| `auto:filename` | 从文件名自动提取 |
| `import` | 从外部数据导入 |
| `merge` | 由合并操作产生 |
| `split` | 由拆分操作产生 |
| `sync` | 外部同步生成 |
| `migration` | 由旧数据迁移生成 |

### 3.6 `app/db/session.py`
- `engine`：`sqlite:///{DB_PATH}`
- `init_db()`：建表 + 迁移字段（`media_path/date_group`）
- `get_session()`：返回 `Session(engine)`

## 3.7 业务数据库汇总

本项目所有持久化数据均存储在同一个 SQLite 文件（路径由 `app/core/config.py` 中的 `DB_PATH` 配置，默认 `backend/db.sqlite`）。

| 表名 | 对应模型 | 主要作用 |
|---|---|---|
| `imageasset` | `ImageAsset` (`app/models/image_asset.py`) | 图片媒体资产主表；存储哈希、路径、尺寸、日期分组、缩略图条目、关联 Tag ID 数组等全量元数据 |
| `album` | `Album` (`app/models/album.py`) | 树形相册结构；存储相册名称、层级路径、封面、照片计数、日期分组 |
| `pathsoftdelete` | `PathSoftDelete` (`app/models/soft_delete.py`) | 软删除日志表（路径级）；以 `target_path` 为准控制图片或相册的可见性，实体本身不删除 |
| `album_image` | `AlbumImage` (`app/models/album_image.py`) | 相册-图片显式多对多关联表；通过索引 JOIN 替代全表扫描，加速相册与日期视图查询 |
| `tag` | `Tag` (`app/models/tag.py`) | 标签库；存储标准化名称、展示名称、分类、使用次数、来源、元信息等，`ImageAsset.tags` 存储该表的 `id` 外键 |

附加文件：
- `MEDIA_DIR/.hash_index.json`：哈希索引缓存（非 SQLite），用于导入时 O(1) 去重，详见 §3.3d。

## 4. 核心业务流程
1. 用户前端上传图像文件列表
2. `/api/import` 解析 `last_modified_json`，并发处理图像哈希/缩略图
3. 记录写入数据库并保存到 `MEDIA_DIR`（按 `date_group`/子目录组织）
4. 前端调用 `/api/dates` 和 `/api/dates/{date_group}/items` 构建图库视图
5. 管理端 `/api/admin/refresh` 保持一致性（支持 `quick/full`）

补充：
- 设置页可通过 `GET/POST /api/system/cache-thumb-setting` 管理缓存缩略图短边尺寸。
- 设置页可通过 `GET/POST /api/system/month-cover-setting` 管理月份封面尺寸。
- 当尺寸保存成功后，前端会调用 `DELETE /api/cache` 清空 `data/cache/` 与 `temp/`，后续缓存缩略图按新尺寸重新生成。

## 5. 配置与外部依赖
- `app/core/config.py`（含 `MEDIA_DIR`, `TEMP_DIR`, `DB_PATH`）
- `backend/requirements.txt`（依赖）
  - fastapi: REST API 框架
  - uvicorn: ASGI 服务器
  - sqlmodel: ORM + 数据模型，封装 SQLAlchemy
  - sqlalchemy: 底层 SQL 映射与事务支持
  - python-multipart: 上传处理
  - opencv-python: 图像读取、缩放、裁剪
  - numpy: 数组处理（OpenCV 依赖）
  - pydantic: FastAPI 校验与序列化（间接使用）
  - pytest / httpx（若有测试需求）

### 5.1 系统交互与性能要点
- 导入流程分成 3 个阶段（元数据、时间分组、批次并行/数据库序列）
- `IMPORT_BATCH_SIZE=20`：避免一次性内存占满，通过分批读取并处理减少压力
- 并行调用逻辑
  - `process_from_bytes`（线程池，适合来自前端上传的流式字节）
  - `process_from_paths`（进程池，适合本地磁盘批量扫描）
- 软删除查询规则
  - `ImageAsset` 和 `Album` 的可见性由 `path_soft_delete` 决定，而不是各自表内的 `deleted_at`
  - 恢复操作本质上是删除对应的 `path_soft_delete` 记录
- 缩略图缓存策略
  - **导入缩略图**（月份封面）：仅对每月代表图生成 `TEMP_DIR/{file_hash}.webp`，400×400 方形裁剪
  - **缓存展示缩略图**（相册内浏览）：按需生成 `CACHE_DIR/{file_hash}_cache.webp`，最短边 600，保持原始比例
  - 重复上传同 hash 文件时不会重复写缩略图
- 目录组织：
  - 原图存储：`MEDIA_DIR/<date_group>/[top_subdir/]...`（`YYYY-MM`）
  - 生成 `date_group` 规则：
    - 直传文件按 `last_modified` 生成
    - 有子目录按 `subdir` 最早时间生成

### 5.2 数据库设计与迁移
- 表结构升级逻辑：`app/db/session.py` 的 `_migrate_db` 支持无痛增列，防止旧 schema 掉链
- 唯一约束：`file_hash` 唯一，作为去重核心；`original_path` 保留原始输入路径；`album_image(album_id, image_id)` 联合唯一
- 索引：`original_path`, `file_hash`, `date_group`, `album_image.album_id`, `album_image.image_id` 用于高效查询

## 6. 运行与调试
1. 进入 `backend` 目录
2. 使用项目虚拟环境安装依赖 `..\.venv\Scripts\python.exe -m pip install -r requirements.txt`
3. 启动服务 `..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
4. API 说明：
   - `GET /` 健康检查
   - `POST /api/import` 多文件上传（`files` + 可选 `last_modified_json`）
  - `POST /api/admin/refresh?mode=quick|full` 修复库状态（默认 `quick`）
   - `GET /api/images/count` 计数
   - `GET /api/dates` 列出年月分组
   - `GET /api/dates/{date_group}/items` 列直图/子相册

## 7. 常见问题与排查
1. `upload_images` 返回错误或空结果
   - 检查客户端 `last_modified_json` 是否为合法 JSON 数组
   - 检查文件扩展名是否在 `IMAGE_EXTS` 中（`.jpg .jpeg .png .webp .gif .tiff .bmp`）
   - 查 `backend` 日志，有无 `decode_failed` 或 OpenCV 异常
2. 缩略图缺失
  - 日期视图封面图来自 `TEMP_DIR`（400×400）；相册内图优先来自 `CACHE_DIR`
  - 检查 `media_path` 是否为有效相对路径（由项目根解析）
  - `refresh` API 仅补齐“每月代表图”的 temp 缩略图，不会全量重建 temp
3. `media_path` 对应文件不存在
   - 触发 `POST /api/admin/refresh` 清理孤儿并补全新文件为 `repaired`
   - 手动检查 `MEDIA_DIR` 文件名及权限
4. SQLite 锁和并发问题
   - SQLite 并发写有限，API 在 `import_files` 以及 `refresh_library` 内为每条处理单次 commit，减少锁竞争
   - 避免多个 `refresh` 并行调用
5. 运行报 `ModuleNotFoundError: No module named 'cv2'`
   - 执行 `pip install opencv-python`；建议加 `opencv-python-headless`（不依赖 GUI）

## 8. 重要路径和命名规则
- 媒体目录：`MEDIA_DIR` = 例如 `backend/media`（可配置）
- 临时缩略图：`TEMP_DIR` = 例如 `backend/temp`
- 相册缓存缩略图：`CACHE_DIR` = 例如 `backend/data/cache`
- 数据库路径：`DB_PATH` = 例如 `backend/db.sqlite`
- `date_group` 规则：`YYYY-MM`（如 `2024-07`），用于前端按年/月分组

---