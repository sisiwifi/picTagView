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

### 3.2 `app/api/routes.py`
- API 路由定义：
  - `GET /`：健康检查
  - `POST /api/import`：批量上传图片，调用 `import_service.import_files`
  - `GET /api/images/count`：总图像数量
  - `POST /api/admin/refresh`：修复/重建库，调用 `import_service.refresh_library`
  - `GET /api/dates`：按年份/月份汇总（基于 `ImageAsset.date_group`）
  - `GET /api/dates/{date_group}/items`：获取某月内容（直图+子相册表示）

### 3.3 `app/services/import_service.py`
- 核心导入与库修复逻辑
- `import_files(files, last_modified_times)`：
  - 解析上传路径（兼容 `webkitRelativePath`）
  - 过滤非图片，由扩展名判断
  - 维护目录级 `date_group`，按子目录最早时间分组
  - 批次读取文件内容（`IMPORT_BATCH_SIZE=20`）
  - 线程池并行 `process_from_bytes` 生成 `file_hash` 与 `thumb_path`
  - 去重（`file_hash` 唯一）与修复缺失图像/缩略图
  - 写入 `ImageAsset`（包含 `original_path`、`file_hash`、`thumb_path`、`media_path`、`date_group`）

- `refresh_library()`：
  - 清理 DB 中 orphan 记录（媒体文件丢失，删缩略图、删记录）
  - 扫描全量 `MEDIA_DIR` 真实文件
  - 并行 `process_from_paths` 重新生成 hash/thumb
  - 修复/新增数据库记录
  - 返回 `pruned/repaired/errors`

### 3.4 `app/services/parallel_processor.py`
- 图片处理核心，提供两种 API：
  - `process_from_paths(entries, temp_dir)`：磁盘到磁盘，使用 `ProcessPoolExecutor`（适合大量文件读取）
  - `process_from_bytes(entries, temp_dir)`：字节到磁盘，使用 `ThreadPoolExecutor`（适合已加载数据、避免进程间 IPC）
- 关键实现 `_process_from_path` / `_process_from_bytes`：
  - 计算 SHA-256 hash
  - 基于 `opencv-python`/`numpy` decode 并中心裁剪缩放到 `800×800`，保存 `temp_dir/{hash}.webp`（WebP 格式）
  - 误码处理 `decode_failed`、异常情况返回错误

### 3.5 `app/models/image_asset.py`
- 数据模型 `ImageAsset`：
  - `id` int 主键
  - `original_path` 索引
  - `file_hash` 索引唯一
  - `thumb_path`
  - `media_path` 可空
  - `date_group` 可空索引（`yyyy-m`）
  - `created_at`

### 3.6 `app/db/session.py`
- `engine`：`sqlite:///{DB_PATH}`
- `init_db()`：建表 + 迁移字段（`media_path/date_group`）
- `get_session()`：返回 `Session(engine)`

## 4. 核心业务流程
1. 用户前端上传图像文件列表
2. `/api/import` 解析 `last_modified_json`，并发处理图像哈希/缩略图
3. 记录写入数据库并保存到 `MEDIA_DIR`（按 `date_group`/子目录组织）
4. 前端调用 `/api/dates` 和 `/api/dates/{date_group}/items` 构建图库视图
5. 管理端 `/api/admin/refresh` 保持一致性（丢文件修复、更新 DB）

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
- 缩略图缓存策略
  - **导入缩略图**（月份封面）：`TEMP_DIR/{file_hash}.webp`，800×800 方形裁剪，1:1 展示
  - **缓存展示缩略图**（相册内浏览）：`CACHE_DIR/{file_hash}_cache.webp`，400px 短边缩放，保持原始比例
  - 重复上传同 hash 文件时不会重复写缩略图
- 目录组织：
  - 原图存储：`MEDIA_DIR/<date_group>/[top_subdir/]...`（`<year>-<month>`）
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
   - `POST /api/admin/refresh` 修复库状态
   - `GET /api/images/count` 计数
   - `GET /api/dates` 列出年月分组
   - `GET /api/dates/{date_group}/items` 列直图/子相册

## 7. 常见问题与排查
1. `upload_images` 返回错误或空结果
   - 检查客户端 `last_modified_json` 是否为合法 JSON 数组
   - 检查文件扩展名是否在 `IMAGE_EXTS` 中（`.jpg .jpeg .png .webp .gif .tiff .bmp`）
   - 查 `backend` 日志，有无 `decode_failed` 或 OpenCV 异常
2. 缩略图缺失
   - 确认 `TEMP_DIR` 写权限
   - 检查 `process_from_bytes` / `process_from_paths` 是否成功返回 `thumb_path`
   - `refresh` API 自动修复丢失缩略图（同 `imageasset` hash 记录）
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
- 数据库路径：`DB_PATH` = 例如 `backend/db.sqlite`
- `date_group` 规则：`YYYY-M`（如 `2024-7`），用于前端按年/月分组

---