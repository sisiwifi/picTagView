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
    - 仅在 Gallery 页面由用户点击的“刷新”按钮触发完整的 `POST /api/admin/refresh`（保留为手动触发的全库修复/补齐）。
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
- `recalculate_album_counts()`：重算 `photo_count` / `subtree_photo_count` 与封面。

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
  - `category` (str) / `tags` (JSON array): 可选的分类与标签
  - `album` (JSON array of arrays): 所属相册路径，每个内层数组是从根相册到叶相册的 `public_id` 完整路径，如 `[["album_1", "album_3"], ["album_5"]]`
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
"tags": [],
"album": [["album_1", "album_3"]],
"collection": []
}
```

说明：`thumbs` 字段通常以 JSON 存储在 SQLite 中（`SQLModel` 使用 `JSON` 列），`thumb_path` 与 `thumbs[*].path` 可为相对路径或工程内路径，外部访问时会由路由解析为 `/thumbnails/...`。

### 3.6 `app/db/session.py`
- `engine`：`sqlite:///{DB_PATH}`
- `init_db()`：建表 + 迁移字段（`media_path/date_group`）
- `get_session()`：返回 `Session(engine)`

## 4. 核心业务流程
1. 用户前端上传图像文件列表
2. `/api/import` 解析 `last_modified_json`，并发处理图像哈希/缩略图
3. 记录写入数据库并保存到 `MEDIA_DIR`（按 `date_group`/子目录组织）
4. 前端调用 `/api/dates` 和 `/api/dates/{date_group}/items` 构建图库视图
5. 管理端 `/api/admin/refresh` 保持一致性（支持 `quick/full`）

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
- 唯一约束：`file_hash` 唯一，作为去重核心；`original_path` 保留原始输入路径
- 索引：`original_path`, `file_hash`, `date_group` 用于高效查询

## 6. 运行与调试
1. 进入 `backend` 目录
2. 安装依赖 `pip install -r requirements.txt`
3. 启动服务 `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
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