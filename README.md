# picTagView

本地图片管理系统，基于 **FastAPI + SQLModel + SQLite + Vue 3 + Tailwind CSS**。
核心功能：选择文件夹一键导入图片、自动按日期归类整理、生成缩略图、去重、支持日期维度浏览与**相册管理**，并提供独立回收站用于删除、还原和彻底清理。

---

## ✅ 功能概览

| 功能 | 说明 |
|------|------|
| **文件夹导入** | 选择任意文件夹（含子目录），按 groupByDate 规则整理到 `media/` |
| **日期归类** | 直接文件按自身修改时间归类；子目录作为整体单元，以目录内最早文件时间归类 |
| **缩略图生成** | 自动生成月份封面缩略图到 `backend/temp/`，并按需生成浏览缓存缩略图到 `backend/data/cache/` |
| **SHA-256 去重** | 哈希匹配完全重复图片，自动跳过；刷新与恢复流程沿用相同去重规则 |
| **日期与日历浏览** | 日历总览与按年月/相册路径浏览分离，支持嵌套层级与统一面包屑；月份总览按页面方向自适应，横向 6 列、纵向 3 列 |
| **相册管理** | 子目录导入自动创建树形相册结构，支持嵌套层级、按相册路径浏览 |
| **选择模式** | 日期详情页/相册页可切换到选择模式，使用固定比例媒体卡片；图片区优先显示 `backend/data/cache` 缩略图，横屏 5 列、竖屏 3 列，支持 Ctrl/Shift、多选拖选、卡片详情浮层、右下角操作岛与混合类型按需全选，并对可视区外卡片做窗口化渲染；详情浮层打开时会锁定页面滚动，混合类型时点击“全选”会展开“相册 / 图片”入口 |
| **列表选择** | 列表模式支持长按进入选择，沿用与选择界面一致的选择逻辑与圆形选择符号；相册项标识改为缩略图右侧的圆角矩形标签，并对列表项做窗口化渲染 |
| **信息区切换** | 选择模式下信息区默认显示文件名；点击信息区可整页切换为 Tag 文本显示，按需批量查询标签 |
| **主分类体系** | `Category` 表统一管理图片 / 相册 / Tag / 回收站条目的 `category_id`；主分类配置页按屏幕方向切换横向 / 竖向卡片比例，常态仅显示编辑按钮，管理模式才显示圆形选择按钮与移除按钮，右下角按钮岛负责批量打开 / 关闭，删除统一回退到默认主分类 |
| **回收站** | 设置页右上角提供更醒目的入口进入独立回收站页面；支持把图片或整棵相册目录移入 `trash/`、批量还原、彻底删除、“清空回收站”；进入页面时以后端批量轻量对账补齐预览，删除/还原确认统一改为页面中部弹窗 |
| **哈希索引缓存** | `.hash_index.json` 加速导入去重，避免逐条 DB 查询 |
| **媒体库刷新** | 清除失效 DB 记录及孤立缩略图；补全 `media/` 中未入库的文件；重建哈希索引；不再承担用户回收站状态维护 |

---

## 🧱 技术栈

### 后端
| 库 | 用途 |
|----|------|
| **FastAPI** | REST API 框架 |
| **SQLModel** | 数据模型 + SQLAlchemy ORM |
| **SQLite** | 本地文件数据库（`backend/data/app.db`） |
| **opencv-python** | 缩略图生成与尺寸读取（`parallel_processor.py` / `cache_thumb_service.py`） |
| **numpy** | 图像字节解码缓冲区 |
| **uvicorn** | ASGI 服务器 |

### 前端
| 库 | 用途 |
|----|------|
| **Vue 3** | 响应式 UI 框架 |
| **Vue Router** | 页面路由 |
| **Tailwind CSS v3** | 原子化 CSS（通过 `@apply` 在 `<style scoped lang="postcss">` 中使用） |
| **PostCSS** | 处理 Tailwind `@apply` 指令 |

---

## 📂 目录结构

```
picTagView/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes.py          # 所有 API 端点
│   │   │   └── schemas.py         # Pydantic 请求/响应模型
│   │   ├── core/
│   │   │   └── config.py          # 全局路径配置（MEDIA_DIR, TEMP_DIR, CACHE_DIR, TRASH_DIR 等）
│   │   ├── db/
│   │   │   └── session.py         # 数据库连接 / init_db()
│   │   ├── models/
│   │   │   ├── category.py        # Category SQLModel 模型（受控主分类）
│   │   │   ├── image_asset.py     # ImageAsset SQLModel 模型
│   │   │   ├── album.py           # Album SQLModel 模型（树形相册结构）
│   │   │   └── trash_entry.py     # TrashEntry SQLModel 模型（回收站条目）
│   │   ├── services/
│   │   │   ├── category_service.py    # 主分类默认项 / 回退 / 计数同步
│   │   │   ├── hash_service.py        # SHA-256 哈希计算（单文件工具）
│   │   │   ├── parallel_processor.py  # 并行处理模块（多线程/多进程）
│   │   │   ├── import_service.py      # 导入 + 刷新门面
│   │   │   ├── cache_thumb_service.py # 浏览缓存缩略图生成
│   │   │   └── trash_service.py       # 回收站移动 / 还原 / 彻底删除
│   │   └── main.py                # FastAPI 应用入口 / 静态文件路由
│   ├── data/
│   │   ├── app.db                 # SQLite 数据库文件
│   │   └── cache/                 # 浏览缓存缩略图目录
│   ├── temp/                      # 月份封面缩略图目录（自动创建）
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── assets/
│   │   │   └── tailwind.css       # Tailwind 入口（@tailwind base/components/utilities）
│   │   ├── components/
│   │   │   ├── Sidebar.vue        # 侧边栏导航（可折叠）
│   │   │   ├── MediaItemCard.vue  # 选择模式媒体卡片组件
│   │   │   ├── ThumbCard.vue      # 通用缩略图卡片组件
│   │   │   ├── LoadingSpinner.vue # 加载中旋转动画组件
│   │   │   ├── BreadcrumbHeader.vue # BrowsePage 头部面包屑
│   │   │   ├── CategoryFormDialog.vue # 主分类创建 / 编辑弹窗
│   │   │   ├── ConfirmationDialog.vue # 居中确认 / 提示弹窗
│   │   │   ├── SelectionDetailOverlay.vue # 详情浮层 / 操作按钮岛
│   │   │   └── TrashPageHeader.vue # 回收站专用头部
│   │   ├── pages/
│   │   │   ├── HomePage.vue       # 主页（文件总数统计）
│   │   │   ├── GalleryPage.vue    # 图库管理（导入 + 刷新）
│   │   │   ├── CalendarOverview.vue # 日历总览页（按年月分组）
│   │   │   ├── BrowsePage.vue     # 浏览页（年月内容 / 物理路径相册）
│   │   │   ├── CategorySettingsPage.vue # 主分类配置页
│   │   │   ├── SettingsPage.vue   # 设置页（含回收站入口）
│   │   │   └── TrashPage.vue      # 回收站页
│   │   ├── router/
│   │   │   └── index.js           # 路由配置
│   │   ├── App.vue
│   │   └── main.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── package.json
├── media/                         # 导入后图片的存储目录（自动创建）
│   └── YYYY-MM/                   # 按年-月组织的子目录
│       ├── image.jpg              # 直接文件
│       └── subdir/                # 整体移入的子目录
├── trash/                         # 回收站 payload 目录（自动创建）
├── comp/
│   └── groupByDate/
│       └── groupByDate.py         # 参考脚本：本地文件夹批量整理（独立使用）
├── build/
│   └── start_project.bat          # Windows 一键启动脚本
└── README.md
```

---

## 🔧 核心逻辑详解

### 1. 导入逻辑（groupByDate）

导入时完整实现了与 `comp/groupByDate/groupByDate.py` 相同的规则：

| 文件位置 | 日期来源 | 目标路径 |
|----------|----------|----------|
| 直接在选中文件夹根目录下 | 文件自身 `lastModified` | `media/YYYY-MM/文件名.ext` |
| 在一级子目录中（含嵌套） | 该子目录内所有文件 `lastModified` 的**最小值** | `media/YYYY-MM/子目录名/原相对路径` |

日期格式现统一为补零形式：`2025-03`。

### 2. 去重逻辑

| 情况 | 条件 | 处理方式 |
|------|------|----------|
| A 相册内重复 | 哈希匹配 + 有子目录 | 保存新副本，添加 album/media_path 关系 |
| B 直传重复（media 丢失） | 哈希匹配 + 无子目录 + media ✗ | 仅写入 media，修复 DB |
| C 直传完全重复 | 哈希匹配 + 无子目录 + media ✓ + thumb ✓ | 直接跳过 |
| D 全新文件 | DB 无该哈希记录 | 生成缩略图 + 写入 media + 新建 DB 记录 |

### 3. 媒体库刷新（`POST /api/admin/refresh?mode=quick|full`）

**Step 1 — Reconcile（对账）**：清理失效 `media_path`，重建 `ImageAsset.album`、`Album` 与 `album_image` 关系，只保留 live `media/` 中仍然存在的内容。

**Step 2 — Repair（修复）**：补齐月份封面缩略图、缺失元数据与 orphan cache 清理，不把原图当作常规浏览回退。

**Step 3 — Ingest（full 模式）**：扫描 `media/` 中尚未入库的文件，按现有导入规则收编并重建哈希索引。

刷新逻辑不再承担用户删除状态维护；用户级删除、还原和彻底删除统一交由回收站机制处理。

### 4. 回收站（`trash/` + `TrashEntry`）

- 从 BrowsePage 删除图片时，会按当前条目的 `media_rel_path` 把对应文件实例移入 `trash/`。
- 从 BrowsePage 删除相册时，会把整棵相册目录树移入 `trash/`，回收站内按单个条目展示。
- 回收站新写入的 payload 直接扁平存放为 `trash/<entry_key>__<原名>`；旧的深层 `entries/<entry_key>/payload/` 结构会在进入回收站时被自动迁移或清理。
- 进入回收站页面时，后端会对 `TrashEntry` 做一次批量轻量对账：若用户手动删掉了某些 payload，则自动移除失效条目；若仅删除了 temp 预览，则会成批补齐，不再逐条强制重建 cache 缩略图。
- 回收站页面支持瀑布流浏览、返回按钮、选择模式、详情浮层、批量“还原 / 删除 / 全选”以及“清空回收站”；删除到回收站、还原、彻底删除、清空均改为页面中部确认弹窗。
- 还原时会把 payload 移回 `media/` 并复用导入链路重新建库；相册重名时自动追加 `_1`、`_2` 等编号，且相册恢复会优先走轻量哈希收编以减少等待时间。

---

### 5. 并行处理架构（`parallel_processor.py`）

CPU 密集型工作（SHA-256 哈希 + OpenCV 缩略图生成）被抽取为独立模块，支持两种并行策略：

| 场景 | 函数 | 并发方式 | 原因 |
|------|------|----------|------|
| **导入-封面图**（`import_files`） | `process_from_bytes` | `ThreadPoolExecutor` | 字节已在内存；完整流水线：SHA-256 + cv2 裁剪缩放 + WebP 写盘 |
| **导入-普通图**（`import_files`） | `process_hash_only_from_bytes` | `ThreadPoolExecutor` | SHA-256 + xxhash + **cv2.imdecode 宽高**，不生成缩略图；cv2 在 worker 中并行执行，不阻塞 DB 写入循环 |
| **刷新**（`refresh_library`） | `process_from_paths` | `ProcessPoolExecutor` | Worker 自行从磁盘读文件，无大字节 IPC 传输；多进程绕过 GIL 获得真正 CPU 并行 |

**内存优化策略**

- `import_files` 按批次（`IMPORT_BATCH_SIZE = 50`）读取文件内容，每批处理完毕后立即释放，峰值内存最多保留一批图片字节。
- `refresh_library` 先构建已完整路径集合（`known_healthy`），跳过无需重处理的文件，仅对新增或缩略图丢失的文件触发并行处理。
- DB 写入始终在主线程/主进程中顺序执行，与 SQLite 单写者模型兼容。

**可调参数**（`parallel_processor.py` 顶部常量）

| 常量 | 默认值 | 说明 |
|------|--------|------|
| `DEFAULT_WORKERS` | `min(cpu_count, 8)` | 线程 / 进程数上限 |
| `IMPORT_BATCH_SIZE` | `50` | 每批并行处理的导入文件数 |
| `REFRESH_BATCH_SIZE` | `200` | 预留：刷新批次大小（当前整批提交给进程池） |

---

## 🗃️ 数据库模型

### ImageAsset

```python
class ImageAsset(SQLModel, table=True):
    id:              int                    # 主键（自增）
    original_path:   str                    # 导入时的原始路径/文件名
    full_filename:   Optional[str]          # 文件名
    file_hash:       str                    # SHA-256（唯一索引）
    quick_hash:      Optional[str]          # xxhash64 快速哈希
    thumbs:          Optional[list[dict]]   # 缩略图条目数组（JSON）
    media_path:      Optional[list[str]]    # media/ 下的原图路径数组（JSON）
    date_group:      Optional[str]          # 日期组，如 "2025-03"
    file_created_at: Optional[datetime]     # 文件原始创建时间
    imported_at:     datetime               # 导入时间
    width / height / file_size / mime_type  # 媒体元信息
    category_id:     int                    # 主分类 ID（默认回退到 1）
    tags:            Optional[list[int]]    # Tag ID 列表（JSON）
    album:           Optional[list[list[str]]]  # 所属相册路径（JSON），每个内层数组为 public_id 链
    collection:      Optional[list]         # 所属收藏集（JSON）
```

### Album

```python
class Album(SQLModel, table=True):
    id:                    int              # 主键（自增）
    public_id:             str              # 外部标识，格式 album_{id}（唯一索引）
    title:                 str              # 相册名称
    path:                  str              # 完整路径（{date_group}/{subdir1}/...）
    category_id:           int              # 主分类 ID（默认回退到 1）
    is_leaf:               bool             # 是否为叶节点
    parent_id:             Optional[int]    # 父相册 ID
    cover:                 Optional[dict]   # 封面信息（JSON）
    photo_count:           int              # 直属照片数
    subtree_photo_count:   int              # 含子相册的总照片数
    date_group:            Optional[str]    # 继承顶层 date_group
    sort_mode:             str              # alpha / date / manual
```

### Category

```python
class Category(SQLModel, table=True):
  id:           int                    # 主键（默认分类固定为 1）
  public_id:    str                    # 对外标识，格式 category_{id}
  name:         str                    # 规范名，仅允许小写字母/数字/下划线
  display_name: str                    # 前端展示名
  description:  str                    # 分类说明
  usage_count:  dict[str, int]         # {image, album, tag}
  is_active:    bool                   # 是否在前端可见
  created_at:   datetime               # 创建时间
```

- 系统保留默认主分类：`id=1`、`name=default`、`display_name=默认`。
- 删除其他主分类时，所有引用该分类的图片、相册、Tag 与回收站条目都会自动回退到默认主分类。

### TrashEntry

```python
class TrashEntry(SQLModel, table=True):
    id:                int                  # 主键（自增）
    entry_key:         str                  # 回收站条目唯一键
    entity_type:       str                  # image / album
    display_name:      str                  # 展示名称
    original_path:     str                  # 删除前 live 路径
    original_date_group: Optional[str]      # 删除前所属月份
    trash_path:        str                  # trash/ 中的 payload 路径
    preview_path:      Optional[str]        # 预览原图路径
    preview_thumb_path: Optional[str]       # temp 缩略图路径
    preview_cache_path: Optional[str]       # cache 缩略图路径
    file_hash:         Optional[str]        # 原图 hash
    category_id:       int                  # 主分类 ID（删除时保留，用于回收站详情）
    tags:              Optional[list[int]]  # Tag ID 列表（JSON）
    metadata_json:     Optional[dict]       # 其他恢复元数据
```

删除不再依赖旧的路径级软删除可见性表。现在的用户删除流程是把图片或整棵相册目录物理移动到 `trash/`，并在 `TrashEntry` 中记录恢复所需信息；普通浏览只看 live `media/`，回收站页面则直接读取 `TrashEntry`。

---

## 🌐 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET`  | `/`                              | 健康检查，返回 `{"status": "ok"}` |
| `POST` | `/api/import`                    | 导入图片文件夹（multipart/form-data） |
| `GET`  | `/api/images/count`              | 返回已导入图片总数 |
| `GET`  | `/api/images/meta`               | 批量读取图片详情与 `media_paths` |
| `GET`  | `/api/categories`                | 列出全部主分类与使用计数 |
| `POST` | `/api/categories`                | 创建主分类 |
| `PATCH`| `/api/categories/{category_id}`  | 更新主分类名称 / 显示名 / 说明 / 启用状态 |
| `DELETE` | `/api/categories/{category_id}` | 删除主分类，并把引用对象回退到默认主分类 |
| `POST` | `/api/categories/bulk`           | 批量启用 / 停用 / 删除主分类 |
| `GET`  | `/api/images/{image_id}/open`    | 按指定 `media_path` 实例在系统中打开图片 |
| `POST` | `/api/admin/refresh`             | 媒体库刷新（清理 + 修复 + 重建哈希索引） |
| `GET`  | `/api/dates`                     | 返回所有年/月分组及首张缩略图 |
| `GET`  | `/api/dates/{date_group}/items`  | 返回指定日期组的一级内容（直图 + 顶层相册） |
| `GET`  | `/api/albums/by-path/{album_path:path}` | 通过物理路径获取相册详情 |
| `GET`  | `/api/albums/open-by-path/{album_path:path}` | 在系统文件管理器中打开相册目录 |
| `GET`  | `/api/albums/{album_id}`         | 获取相册详情（子相册 + 直属图片） |
| `GET`  | `/api/trash/items`               | 列出回收站条目 |
| `POST` | `/api/trash/move`                | 将图片或相册移入回收站 |
| `POST` | `/api/trash/restore`             | 还原选中的回收站条目 |
| `POST` | `/api/trash/hard-delete`         | 彻底删除选中的回收站条目 |
| `DELETE` | `/api/trash`                   | 清空回收站 |
| `POST` | `/api/thumbnails/cache`          | 异步生成缓存缩略图 |
| `GET`  | `/api/thumbnails/cache/status/{task_id}` | 查询缓存生成进度 |
| `DELETE` | `/api/cache`                   | 清除所有缓存 |
| `GET`  | `/api/system/viewer-preference`  | 获取图片查看器偏好 |
| `POST` | `/api/system/viewer-preference`  | 设置图片查看器偏好 |
| `GET`  | `/api/system/image-viewers`      | 列出系统中可用的图片查看器 |
| `GET`  | `/thumbnails/{filename}`         | 静态文件：缩略图 |
| `GET`  | `/cache/{filename}`              | 静态文件：缓存缩略图 |
| `GET`  | `/trash-media/{path}`            | 静态文件：回收站 payload 预览回退 |

### `POST /api/import` 请求格式

```
Content-Type: multipart/form-data

files[]              — 图片文件（可多个）
                       filename 应为 file.webkitRelativePath（含目录结构）
last_modified_json   — JSON 数组，与 files[] 顺序一一对应的 lastModified 时间戳（毫秒）
created_time_json    — JSON 数组，与 files[] 顺序一一对应的创建时间戳（毫秒）
```

### `GET /api/dates/{date_group}/items` 响应格式

```json
{
  "date_group": "2025-03",
  "items": [
    { "type": "image", "name": "photo.jpg", "thumb_url": "/thumbnails/abc.webp", "id": 1, "width": 4032, "height": 3024, "file_size": 2451040, "imported_at": "2026-04-18T13:20:14", "file_created_at": "2025-03-02T09:42:18", "tags": [23, 45], "media_index": 0, "media_rel_path": "media/2025-03/photo.jpg" },
    { "type": "album", "name": "旅行", "thumb_url": "/thumbnails/def.webp", "count": 42, "photo_count": 10, "created_at": "2026-04-01T08:10:00", "public_id": "album_1", "width": 4032, "height": 3024, "tags": [] }
  ]
}
```

说明：`tags` 为图片条目关联的 Tag ID 列表。BrowsePage 普通模式与选择模式都会优先使用 `cache_thumb_url` 或 `thumb_url` 显示缩略图；若缓存尚未生成，前端先显示骨架占位，再按统一的 `/api/thumbnails/cache` 轮询链路补齐。前端仅在用户把选择模式信息区切换到 Tag 显示时，才会去重后批量调用 `/api/tags?ids=...` 拉取展示名称，避免普通浏览时产生额外查询。

补充：图片条目返回的 `media_index` 与 `media_rel_path` 用于稳定标识当前视图对应的具体文件实例。前端在调用 `/api/images/{image_id}/open` 时应优先传入 `path=media_rel_path`，避免一张图存在多个 `media_path` 时总是落到数组首项。

补充：图片条目现在还会额外返回 `file_size` / `imported_at` / `file_created_at`。BrowsePage 的选择模式详情浮层直接消费这组字段，单选时会在固定尺寸的左侧图区内按原图比例显示缩略图；多选时左侧改为可滚动的比例缩略图列表，右下保留“删除”占位按钮，同值字段原样展示、异值字段统一显示 *various*。弹层宽高会同时受主内容区当前可视宽高约束，竖屏下不会再超出界面。

补充：相册条目现在还会额外返回 `photo_count` / `created_at`。选择模式下若当前选中的是相册，详情浮层会把“尺寸”栏替换成“图片数量”，其值取 `photo_count`；“创建时间”展示相册自身的 `created_at`；主操作按钮会从“查看原图”切换为“查看相册”，通过后端接口直接在资源管理器中打开对应目录。

补充：若当前页面条目是在旧响应下加载、缺失上述元数据，前端会在打开详情浮层时按需调用 `GET /api/images/meta?ids=...` 补齐时间与大小信息；弹层打开期间会锁定页面滚动，避免滚轮或中键自动滚动把底层页面带走。

补充：图片条目与相册条目现在都会额外返回 `width` / `height`。BrowsePage 的“大缩略图”照片墙会优先使用这组后端元数据初始化拼图布局，减少图片逐张加载时的整页重排，同时不改变现有滚动锚点与缓存缩略图预取逻辑。

补充：BrowsePage 当前只对列表模式与选择模式启用窗口化渲染；“大缩略图”照片墙仍保留全量行布局与原有滚动锚点逻辑，避免影响缓存缩略图的预取范围判断。

### `GET /api/albums/{album_id}` 响应格式

```json
{
  "album": {
    "public_id": "album_1",
    "title": "旅行",
    "date_group": "2025-03",
    "photo_count": 10,
    "subtree_photo_count": 42,
    "parent_public_id": null
  },
  "items": [
    { "type": "album", "name": "Day1", "thumb_url": "...", "count": 20, "public_id": "album_2", "width": 4032, "height": 3024 },
    { "type": "image", "name": "photo.jpg", "thumb_url": "...", "id": 5, "width": 4032, "height": 3024 }
  ]
}
```

---

## 🖥️ 页面说明

### 主页 `/`
显示当前已导入图片总数（从 `/api/images/count` 获取）。

### 图库管理 `/gallery`
- **选择图片文件夹并导入**：使用 `webkitdirectory` 属性一次性选择整个文件夹，前端按 groupByDate 规则分批上传（每个一级子目录为一批）并显示实时进度。
- **🔄 刷新**：调用 `POST /api/admin/refresh`，清理失效记录、修复缺失缩略图。

### 日期视图 `/calendar`
- **总览模式**：按年份分组，每个月份显示为缩略图卡片（首张图 + 月份标签 + 图片数）。
- **月份浏览**：点击月份后进入 `/calendar/:group`，显示该月所有一级内容：
  - 直接图片文件
  - 顶层相册
  - 点击相册继续进入 `/calendar/:group/:albumPath+`
- **动画**：
  - 前进（打开详情）：网格淡出 → 详情面板从点击位置缩放飞出
  - 后退（返回网格）：详情面板缩回点击位置 → 网格淡入

### 相册视图 `/calendar/:group/:albumPath+`
- 显示指定相册内容：子相册 + 直属图片
- 支持嵌套导航：点击子相册进入更深层级
- 返回导航：回到上一级相册或月份视图
- 缓存缩略图按需生成（与日期视图相同的滚动触发机制）

### 设置页 `/settings`
- 管理缓存缩略图尺寸、月份封面尺寸与看图器偏好
- 右上角提供更显眼的回收站入口卡片，直接跳转到独立回收站页面

### 回收站 `/trash`
- 使用与 BrowsePage 一致的瀑布流/选择模式视觉体系，但独立成页，避免污染普通浏览状态
- header 左侧提供“返回”按钮
- header 右侧项目数前提供“清空回收站”按钮
- 选择态支持“详情 / 还原 / 删除 / 全选 / 取消选择”；当同时存在相册与图片时，全选按钮会展开“相册 / 图片”二级入口
- 详情浮层主动作是“还原”，危险动作是“删除”

---

## 🚀 启动方式

### 方式一：Windows 一键启动（推荐）

```bat
build\start_project.bat
```

会同时打开两个终端窗口：
- **后端**：`http://127.0.0.1:8000`（uvicorn，热重载）
- **前端**：`http://localhost:8080`（Vue CLI dev server）

**前提**：仓库根目录已存在 `.venv`，并已安装 Node.js 16+。

---

### 方式二：手动启动

```bash
# 后端
cd backend
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

```bash
# 前端（另开终端）
cd frontend
npm install
npm run serve
```

---

### 方式三：Docker（仅后端）

```bash
cd backend
docker build -t pictagview-backend .
docker run --rm -p 8000:8000 pictagview-backend
```

仓库当前提供的是 `backend/Dockerfile`，未附带 `docker-compose.yml`。
后端容器运行在 `http://127.0.0.1:8000`；若需要持久化 `media/` 与 `data/`，请按本机环境自行补充 volume 挂载参数。
前端仍需在宿主机运行（`npm run serve`）。

---

## 📦 依赖安装

### 后端 `backend/requirements.txt`
```
fastapi
uvicorn[standard]
sqlmodel
opencv-python
numpy
python-multipart
```

### 前端 `frontend/package.json`（主要）
```
vue ^3.x
vue-router ^4.x
tailwindcss ^3.x
postcss
autoprefixer
@vue/cli-service
```

---

## 🛠️ 开发说明

### 前端样式规范
所有 Vue 组件统一使用：
```html
<style scoped lang="postcss">
.my-class {
  @apply flex items-center gap-2 text-slate-600;
}
</style>
```
纯 CSS 语法仅在 `@apply` 无法表达的情况下使用（如 CSS 自定义属性、`@keyframes`、`clamp()` 等）。

### 共享组件
| 组件 | 用途 |
|------|------|
| `ThumbCard.vue` | 通用图片卡片（图片 / 遮罩 / 内容 slot，支持 `rounded` 和 `overlayOpacity` prop） |
| `LoadingSpinner.vue` | 旋转加载动画，支持 slot 自定义文字 |

### 添加新页面
1. 在 `frontend/src/pages/` 创建 `XxxPage.vue`
2. 在 `frontend/src/router/index.js` 添加路由
3. 在 `frontend/src/components/Sidebar.vue` 的 `navItems` 添加导航项

### 扩展后端接口
在 `backend/app/api/routes.py` 中添加新端点；
数据模型变更在 `backend/app/models/image_asset.py` 修改后删除 `backend/data/app.db` 重新启动即可重建。

---

## ⚠️ 注意事项

- `media/`、`trash/`、`backend/temp/` 和 `backend/data/cache/` 目录由后端自动创建，**不要手动移动其中的文件**；若用户手动删掉了 `trash/` 内部分 payload 或删掉了 temp/cache 预览，进入回收站时系统会自动做一次轻量对账与补齐。
- 使用 `🔄 刷新` 按钮可随时修复不一致状态（文件移动后、手动删除后等）。
- 数据库文件 `backend/data/app.db` 可直接备份；删除后重启会自动创建空数据库。
- 回收站中的文件仍然占用磁盘空间；只有在回收站页面执行“删除”或“清空回收站”后才会真正物理删除。
- `comp/groupByDate/groupByDate.py` 是一个独立命令行工具，可对已有本地文件夹执行整理，与 Web 导入功能独立工作。
