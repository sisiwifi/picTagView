# picTagView Backend 技术说明书

本文档描述当前后端结构、运行时目录、核心模块和开发约定，内容以 `backend/app` 下的现行代码为准。

## 1. 项目位置

- 后端目录：`D:\Python_projects\picTagView_main\backend`
- 应用入口：`backend/app/main.py`

## 2. 技术栈与运行时目录

### 2.1 技术栈

- Web 框架：FastAPI
- ORM：SQLModel / SQLAlchemy
- 数据库：SQLite
- 多媒体处理：OpenCV、numpy
- 开发服务器：Uvicorn
- 上传解析：python-multipart
- 快速哈希：xxhash

### 2.2 路径来源

`app/core/config.py` 当前没有环境变量分支，而是直接按仓库结构计算路径：

| 常量 | 当前值 |
| --- | --- |
| `BASE_DIR` | `backend` |
| `PROJECT_ROOT` | 仓库根目录 |
| `DATA_DIR` | `backend/data` |
| `TEMP_DIR` | `backend/temp` |
| `CACHE_DIR` | `backend/data/cache` |
| `VIEWER_ICON_DIR` | `backend/data/viewer_icons` |
| `MEDIA_DIR` | `media` |
| `TRASH_DIR` | `trash` |
| `DB_PATH` | `backend/data/app.db` |

模块导入时会自动确保这些目录存在。

## 3. 应用启动流程

`app/main.py` 的 `create_app()` 当前做了下面几件事：

1. 调用 `init_db()` 初始化数据库
2. 创建 `FastAPI(title="picTagView Backend", version="0.1.0")`
3. 配置全开放 CORS
4. 挂载静态目录：
   - `/thumbnails` -> `TEMP_DIR`
   - `/cache` -> `CACHE_DIR`
   - `/media` -> `MEDIA_DIR`
   - `/trash-media` -> `TRASH_DIR`
   - `/viewer-icons` -> `VIEWER_ICON_DIR`
5. 注册 `app/api/routes.py` 聚合出的全部 API 路由

## 4. 路由结构

`app/api/routes.py` 当前注册的 router 顺序如下：

1. `basic_router`
2. `categories_router`
3. `dates_router`
4. `albums_router`
5. `images_router`
6. `collections_router`
7. `search_router`
8. `system_router`
9. `cache_router`
10. `tags_router`
11. `trash_router`

这意味着当前后端已经包含：

- 导入与刷新
- 日期与相册浏览
- 图片元数据编辑
- Tag 查询、草稿、新增、编辑、导入导出、Tag 二级浏览
- 收藏夹总览、详情、封面与批量应用
- 搜索
- 系统设置与查看器集成
- 缓存缩略图队列
- 主分类管理
- 回收站管理

## 5. 核心子系统

### 5.1 导入与刷新

- `services/import_service.py` 是兼容门面。
- 真正的导入和维护逻辑位于 `services/imports/`：
  - `pipeline.py`：导入批处理、哈希去重、相册链维护、图片主分类赋值、导入期文件名自动打标
  - `maintenance.py`：`quick/full` 刷新、路径对账、缺失预览修复、未入库媒体收编
  - `hash_index.py`：哈希索引缓存
  - `helpers.py`：文件时间、路径与缩略图辅助工具

当前导入规则的关键点：

- 图片按时间归入 `media/YYYY-MM/`
- 子目录会创建树形 `Album`
- 图片只保留一个主分类，优先使用导入请求给出的 `category_id`
- 同批次导入会在一个事务内完成写库、关联和自动打标

### 5.2 浏览与可见性

- `dates.py`、`albums.py` 不直接把所有相册都返回给前端，而是依赖 `visible_album_service.py` 根据“当前可见图片”推导相册可见性、封面和数量。
- 相册是否可见，不再取决于相册自身的主分类字段，而取决于子树中是否还有可见图片。
- 日期、相册、Tag、收藏、回收站这些浏览接口都会带上缩略图信息、宽高、排序时间和 `tags` ID 列表。

### 5.3 Tag 与搜索

- `tags.py` 负责 Tag CRUD、草稿占位、导入导出和 Tag 二级浏览。
- 草稿 Tag 使用 `created_by = system:draft-reserve` 标记，并在查询与导出时过滤。
- `tag_match_service.py` 封装文件名分词、Tag 匹配、Tag 排序和计数更新；导入流程与图片页“自动标签”共用这一套逻辑。
- `search.py` 支持 `filename`、`tag`、`path` 三类搜索，并在路径模式下额外按 `quick_hash` 找到同图图片。

### 5.4 收藏夹与封面

- `collection_service.py` 负责收藏夹创建、查找、候选列表、批量添加/移除和统计刷新。
- 收藏封面与相册封面都支持手动设置，相关 payload 由 `cover_service.py` 维护。
- 收藏详情与封面接口都使用 `public_id` 字符串，而不是数值主键。

### 5.5 主分类

- 当前主分类体系只落在图片上，不再落在相册和 Tag 上。
- `category_service.py` 负责：
  - 默认主分类保证存在
  - 名称校验
  - 使用计数同步
  - 删除时引用回退
- 默认主分类固定为 `id=1`，且不可编辑、不可删除。

### 5.6 回收站

- `trash_service.py` 负责图片或相册移入回收站、列出条目、还原、彻底删除和清空。
- 还原流程不会手工拼接数据库记录，而是尽量复用导入/刷新链路重新建库。
- `POST /api/trash/reconcile` 提供轻量对账和预览修复能力，供前端进入回收站后静默调用。

### 5.7 缓存缩略图队列

- `cache.py` 在路由层维护共享任务表、页面 token、generation 和增量游标。
- `cache_thumb_service.py` 负责实际生成 `backend/data/cache/*.webp`。
- 队列当前特性：
  - 同页新 generation 会取代旧页面任务
  - 已有缓存立即返回
  - 状态接口通过 `cursor` 增量返回新完成项
  - 任务完成后会把缓存缩略图写回 `ImageAsset.thumbs`

### 5.8 查看器与系统设置

- `viewer_service.py` 主要服务于 Windows：
  - 枚举可用图片查看器
  - 解析系统默认查看器
  - 生成查看器图标
  - 以应用内偏好查看器打开图片
- `app_settings_service.py` 当前持久化到 `backend/data/app_settings.json` 的设置包括：
  - 浏览缓存缩略图短边尺寸
  - 月份封面尺寸
  - 页面浏览模式与滚动窗口范围
  - 文件名自动打标设置

## 6. 数据模型摘要

| 模型 | 当前角色 |
| --- | --- |
| `ImageAsset` | 图片主表，保存哈希、宽高、`media_path`、`tags`、`category_id`、时间与缩略图信息 |
| `Album` | 相册树节点，保存路径、标题、封面和统计 |
| `AlbumImage` | 相册与图片关系表 |
| `Tag` | Tag 元数据、颜色、描述、`usage_count`、`last_used_at` |
| `Category` | 图片主分类 |
| `Collection` | 收藏夹 |
| `CollectionImage` | 收藏夹与图片关系表 |
| `TrashEntry` | 回收站条目与恢复所需 payload |

## 7. 开发与运行

### 7.1 安装依赖

```powershell
python -m venv ..\.venv
..\.venv\Scripts\python -m pip install --upgrade pip
..\.venv\Scripts\python -m pip install -r requirements.txt
```

或者直接在仓库根目录执行：

```powershell
.\.venv\Scripts\python -m pip install -r backend\requirements.txt
```

### 7.2 启动开发服务

```powershell
..\.venv\Scripts\python -m uvicorn app.main:app --reload
```

也可以从仓库根目录使用 `build/start_project.bat` 同时启动前后端。

## 8. 当前约定与注意事项

- 前端默认直连 `http://127.0.0.1:8000`，后端端口变化时需要同步更新前端代码。
- `backend/data/app.db` 是当前默认数据库文件，仓库运行期间会持续变化。
- 文件名自动打标配置 API 已存在，但前端设置页尚未接入对应 UI。
- 草稿 Tag 属于正常数据库记录，只是通过 `created_by` 被隐藏；调试数据库时要注意区分。
