# picTagView Backend API & Services Document

本文档整理了 picTagView 后端所有可用的 REST API 以及内部核心处理服务的位置、用途与调用方法。

## 1. 核心服务 (Services)

核心业务逻辑全部隔离在 `app/services/` 目录下，并被 `app/api/routes.py` 或互相调用。

### 1.1 并发与哈希服务
- **位置**：`app/services/parallel_processor.py` 和 `app/services/hash_service.py`
- **用途**：处理繁重的 CPU 密集型任务，主要进行图片解码（OpenCV）、图片裁剪与哈希计算。
- **核心方法**：
  - `process_from_paths(entries, temp_dir, max_workers)`：基于外部路径利用多进程 `ProcessPoolExecutor` 并发生成缩略图，避免大量图片数据跨进程序列化，适合已存在磁盘的图片的二次处理。
  - `process_from_bytes(entries, temp_dir, max_workers)`：利用 `ThreadPoolExecutor` 并发处理内存中的图片，适合直接在上传、读取文件时边解析边执行。利用 OpenCV 与 hashlib 会释放 GIL 的特性实现高吞吐。
  - `process_hash_only_from_bytes(entries, max_workers)`：专注于仅求得图片的 `sha256` 散列，不提取缩略图。

### 1.2 缓存缩略图生成服务
- **位置**：`app/services/cache_thumb_service.py`
- **用途**：负责相册页面按需动态生成的（即浏览器请求但未命中缓存时触发）短边 600px 的 WebP 预览缩略图。
- **核心方法**：
  - `generate_cache_thumbs_progressively(entries, cache_dir, on_complete)`：通过多线程流式生成缓存缩略图，使得前端可以收到逐步加载的视觉反馈。

### 1.3 导入与刷新服务
- **位置**：`app/services/import_service.py`
- **用途**：管理新图片导入与媒体库定期清理校验，更新图片的元数据信息，如创建时间、标签、宽高、QuickHash 等。
- **核心方法**：
  - `import_files(files, last_modified_times, created_times)`：多阶段进行图片处理。Phase1 提取上传队列的元信息，Phase2 根据修改日期提取 `date_group` 并仅为一个分组打最新缩略图，Phase3 基于并行框架 `parallel_processor` 执行运算并更新 SQLModel 数据库及写入物理位置 (`media/`)。
  - `refresh_library()`：数据一致性自检。Step0 删除无主的 Cache 图片；Step1 删除物理文件确实已丢失的数据库记录；Step2 保证所有月份分组必须存在至少一张 400x400 的封面 Temp 缩略图；Step3 回填遗漏的快哈希和分辨率。

### 1.4 缩略图创建基础服务
- **位置**：`app/services/thumbnail_service.py`
- **用途**：供特殊单张图片读取或遗留调用的纯同步 1:1 裁剪创建函数。
- **核心方法**：
  - `create_thumbnail_from_bytes(content, file_hash)`：用 OpenCV 裁剪 1:1，直接写入 `TEMP_DIR`。

---

## 2. API 接口 (Routes)

所有的 REST API 由 FastAPI 提供，路由集中注册于 `backend/app/api/routes.py`（大多数路由）；具体实现逻辑有时会委托到 `backend/app/services/` 下的服务函数（例如 `import_service.py`, `parallel_processor.py`, `cache_thumb_service.py`）。
本地基础路径默认为：`http://127.0.0.1:8000`。

### 2.1 基础与基础运维 API

#### `GET /`
- 实现位置：`backend/app/api/routes.py`
- **用途**：健康检查。
- **返回**：`{"status": "ok"}`。

#### `GET /api/images/count`
- 实现位置：`backend/app/api/routes.py` （函数 `images_count()`）
- **用途**：快速获取数据库中所有图片的计数。
- **返回**：`{"count": <int>}`。

- 实现位置：`backend/app/api/routes.py`（调用 `app/services/import_service.import_files`）
- **用途**：导入前端上传的高清照片原始文件。支持 FormData 解析前端传回来的文件流和文件相关的时间。
- **参数 (FormData)**：
  - `files`：多文件上传 (`UploadFile`)
  - `last_modified_json`：与 files 对应的上次修改时间数组 (JSON string，可选)
  - `created_time_json`：与 files 对应的文件创建时间数组 (JSON string，可选)
- **返回**：`{"imported": ["file1.jpg", ...], "skipped": [...]}`。

#### `POST /api/admin/refresh`
- 实现位置：`backend/app/api/routes.py`（路由直接调用 `import_service.refresh_library()`）
- **用途**：触发文件清理与图库元数据、缩略图同步扫描修复。
- **返回**：`{"pruned": <int>, "total_images": <int>, "cache_deleted": <int>, "regenerated": <int>}`。

---

### 2.2 相册视图 API

#### `GET /api/dates`
- 实现位置：`backend/app/api/routes.py`（函数 `dates_view()`）
- **用途**：获取全量按年-月份分组（`date_group`）聚类的相册大纲列表，以及当前月份首选展示的封面图片 URL。
- **返回**：
  ```json
  {
    "years": [
      {
        "year": 2025,
        "months": [
          {
            "group": "2025-03",
            "year": 2025,
            "month": 3,
            "count": 12,
            "thumb_url": "/thumbnails/xxxxx.webp"
          }
        ]
      }
    ]
  }
  ```

#### `GET /api/dates/{date_group}/items`
- 实现位置：`backend/app/api/routes.py`（函数 `date_group_items()`）
- **用途**：获取某个特定月份组（如 `2025-03`）里面的具体照片或者子相册（目录）。
- **参数 (Path)**：`date_group`，如 `2025-03`。
- **返回**：包含 `date_group` 和 `items`。`items` 类型分为 `image`（直接在根组下）或 `album`（有子目录）。

---

### 2.3 查看原图与操作系统集成 API

#### `GET /api/images/{image_id}/open`
- 实现位置：`backend/app/api/routes.py`（函数 `open_image()`）
- **用途**：触发在服务端当前运行设备的操作系统内，使用系统或指定的默认图片浏览器打开此张图片的原图。
- **返回**：`{"status": "ok", "mode": "preferred"|"system", "viewer_id": "..."}`。

#### `GET /api/system/viewer-info`
- 实现位置：`backend/app/api/routes.py`（函数 `viewer_info()`）
- **用途**：获取当前操作系统的全局默认看图软件和 App 内指定看图软件的信息。
- **返回**：`{"viewer": "...", "preferred_viewer_id": null, "system_viewer": "..."}`。

#### `GET /api/system/image-viewers`
- 实现位置：`backend/app/api/routes.py`（函数 `image_viewers()`）
- **用途**：扫描 Windows 注册表，返回操作系统内所有已安装且能打开主流图片的程序。
- **返回**：包含应用列表（含注册表 ProgID、名称、类型、提取并代理好的程序图标 URL）、偏好选择情况。

#### `GET /api/system/viewer-preference`
- **用途**：获取配置在本应用范围的偏好看图软件 ID。

#### `POST /api/system/viewer-preference`
- **用途**：设置并保存应用内打开图片的默认程序到配置文件中。
- **请求体 (JSON)**：`{"viewer_id": "xxx.ProgID" | ""}`，空字符串意味着跟随系统。

---

### 2.4 缩略图缓存管理 API

#### `DELETE /api/cache`
- 实现位置：`backend/app/api/routes.py`（函数 `delete_cache` / 删除逻辑位于 routes.py）
- **用途**：清除 `temp/` 及 `data/cache/` 这两处的缩略图存放位置所有已缓存文件，并移除数据库内丢失记录的字段清理，强制重新触发刷新。
- **返回**：`{"temp_deleted": <int>, "cache_deleted": <int>, "error": null}`。

#### `POST /api/thumbnails/cache`
- 实现位置：`backend/app/api/routes.py`（路由 + 后台任务协调；实际生成由 `app/services/cache_thumb_service.py` 实现并在 routes.py 中被调用）
- **用途**：通知后端异步为所提供的特定全量图片 ID 生成 600px 尺寸长列表模式的缓存缩略图。
- **请求体 (JSON)**：`{"image_ids": [1, 2, 3, ...]}`。
- **返回**：`{"task_id": "<uuid>"}` 返回用于轮询的任务 ID。

#### `GET /api/thumbnails/cache/status/{task_id}`
- 实现位置：`backend/app/api/routes.py`（状态轮询路由，返回 `_task_store` 中的运行状态）
- **用途**：通过给定的 task_id 轮询当前批量大图转缓存缩略图进度的进度及新生成的资源 URL 列表。
- **返回**：
  ```json
  {
    "status": "running" | "done" | "error",
    "items": [
      {
        "id": 1,
        "cache_thumb_url": "/cache/xxxxx_cache.webp"
      }
    ]
  }
  ```
