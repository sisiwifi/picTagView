# picTagView

本地图片管理系统，基于 **FastAPI + SQLModel + SQLite + Vue 3 + Tailwind CSS**。
核心功能：选择文件夹一键导入图片、自动按日期归类整理、生成缩略图、去重、支持日期维度浏览与**相册管理**。

---

## ✅ 功能概览

| 功能 | 说明 |
|------|------|
| **文件夹导入** | 选择任意文件夹（含子目录），按 groupByDate 规则整理到 `media/` |
| **日期归类** | 直接文件按自身修改时间归类；子目录作为整体单元，以目录内最早文件时间归类 |
| **缩略图生成** | 自动生成 300×200 (3:2) 缩略图，保存到 `backend/thumbnails/` |
| **SHA-256 去重** | 哈希匹配完全重复图片，自动跳过；缩略图存在但 media 丢失时自动补全 |
| **日期与日历浏览** | 日历总览与按年月/相册路径浏览分离，支持嵌套层级与统一面包屑 |
| **相册管理** | 子目录导入自动创建树形相册结构，支持嵌套层级、按相册路径浏览 |
| **选择模式** | 日期详情页/相册页可切换到选择模式，使用固定比例媒体卡片；图片区优先显示 `backend/data/cache` 缩略图，横屏 5 列、竖屏 3 列，支持 Ctrl/Shift、多选拖选、卡片详情浮层、右下角操作岛与混合类型按需全选，并对可视区外卡片做窗口化渲染；详情浮层打开时会锁定页面滚动，混合类型时点击“全选”会展开“相册 / 图片”入口 |
| **列表选择** | 列表模式支持长按进入选择，沿用与选择界面一致的选择逻辑与圆形选择符号；相册项标识改为缩略图右侧的圆角矩形标签，并对列表项做窗口化渲染 |
| **信息区切换** | 选择模式下信息区默认显示文件名；点击信息区可整页切换为 Tag 文本显示，按需批量查询标签 |
| **哈希索引缓存** | `.hash_index.json` 加速导入去重，避免逐条 DB 查询 |
| **媒体库刷新** | 清除失效 DB 记录及孤立缩略图；补全 `media/` 中未入库的文件；重建哈希索引 |

---

## 🧱 技术栈

### 后端
| 库 | 用途 |
|----|------|
| **FastAPI** | REST API 框架 |
| **SQLModel** | 数据模型 + SQLAlchemy ORM |
| **SQLite** | 本地文件数据库（`backend/data/app.db`） |
| **opencv-python** | 缩略图生成（裁剪 + 缩放，`thumbnail_service.py`） |
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
│   │   │   └── config.py          # 全局路径配置（MEDIA_DIR, THUMB_DIR 等）
│   │   ├── db/
│   │   │   └── session.py         # 数据库连接 / init_db()
│   │   ├── models/
│   │   │   ├── image_asset.py     # ImageAsset SQLModel 模型
│   │   │   └── album.py           # Album SQLModel 模型（树形相册结构）
│   │   ├── services/
│   │   │   ├── hash_service.py        # SHA-256 哈希计算（单文件工具）
│   │   │   ├── thumbnail_service.py   # 缩略图生成（OpenCV，3:2 裁剪）
│   │   │   ├── parallel_processor.py  # 并行处理模块（多线程/多进程）
│   │   │   └── import_service.py      # 导入 + 刷新核心逻辑
│   │   └── main.py                # FastAPI 应用入口 / 静态文件路由
│   ├── data/
│   │   └── app.db                 # SQLite 数据库文件
│   ├── thumbnails/                # 缩略图输出目录（自动创建）
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── assets/
│   │   │   └── tailwind.css       # Tailwind 入口（@tailwind base/components/utilities）
│   │   ├── components/
│   │   │   ├── Sidebar.vue        # 侧边栏导航（可折叠）
│   │   │   ├── MediaItemCard.vue   # 选择模式媒体卡片组件
│   │   │   ├── ThumbCard.vue      # 通用缩略图卡片组件
│   │   │   └── LoadingSpinner.vue # 加载中旋转动画组件
│   │   ├── pages/
│   │   │   ├── HomePage.vue       # 主页（文件总数统计）
│   │   │   ├── GalleryPage.vue    # 图库管理（导入 + 刷新）
│   │   │   ├── CalendarOverview.vue # 日历总览页（按年月分组）
│   │   │   └── BrowsePage.vue     # 浏览页（年月内容 / 物理路径相册）
│   │   ├── router/
│   │   │   └── index.js           # 路由配置
│   │   ├── App.vue
│   │   └── main.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── package.json
├── media/                         # 导入后图片的存储目录（自动创建）
│   └── YYYY-M/                    # 按年-月（不补零）组织的子目录
│       ├── image.jpg              # 直接文件
│       └── subdir/                # 整体移入的子目录
├── comp/
│   └── groupByDate/
│       └── groupByDate.py         # 参考脚本：本地文件夹批量整理（独立使用）
├── build/
│   └── start_project.bat          # Windows 一键启动脚本
└── docker-compose.yml
```

---

## 🔧 核心逻辑详解

### 1. 导入逻辑（groupByDate）

导入时完整实现了与 `comp/groupByDate/groupByDate.py` 相同的规则：

| 文件位置 | 日期来源 | 目标路径 |
|----------|----------|----------|
| 直接在选中文件夹根目录下 | 文件自身 `lastModified` | `media/YYYY-M/文件名.ext` |
| 在一级子目录中（含嵌套） | 该子目录内所有文件 `lastModified` 的**最小值** | `media/YYYY-M/子目录名/原相对路径` |

日期格式为非补零形式：`2025-3`（而非 `2025-03`）。

### 2. 去重逻辑

| 情况 | 条件 | 处理方式 |
|------|------|----------|
| A 相册内重复 | 哈希匹配 + 有子目录 | 保存新副本，添加 album/media_path 关系 |
| B 直传重复（media 丢失） | 哈希匹配 + 无子目录 + media ✗ | 仅写入 media，修复 DB |
| C 直传完全重复 | 哈希匹配 + 无子目录 + media ✓ + thumb ✓ | 直接跳过 |
| D 全新文件 | DB 无该哈希记录 | 生成缩略图 + 写入 media + 新建 DB 记录 |

### 3. 媒体库刷新（`POST /api/admin/refresh`）

**Step 1 — Prune（清理）**：遍历所有 DB 记录，若 `media_path` 对应文件不存在 → 删除缩略图文件 + 删除 DB 记录。

**Step 2 — Repair（修复）**：跳过已完整（media + 缩略图均存在）的文件；对余下文件并行计算 SHA-256 + 生成缩略图，再顺序写入 DB。

---

### 4. 并行处理架构（`parallel_processor.py`）

CPU 密集型工作（SHA-256 哈希 + OpenCV 缩略图生成）被抽取为独立模块，支持两种并行策略：

| 场景 | 函数 | 并发方式 | 原因 |
|------|------|----------|------|
| **导入-封面图**（`import_files`） | `process_from_bytes` | `ThreadPoolExecutor` | 字节已在内存；完整流水线：SHA-256 + cv2 裁剪缩放 + WebP 写盘 |
| **导入-普通图**（`import_files`） | `process_hash_only_from_bytes` | `ThreadPoolExecutor` | SHA-256 + xxhash + **cv2.imdecode 宽高**，不生成缩略图；cv2 在 worker 中并行执行，不阻塞 DB 写入循环 |
| **刷新**（`refresh_library`） | `process_from_paths` | `ProcessPoolExecutor` | Worker 自行从磁盘读文件，无大字节 IPC 传输；多进程绕过 GIL 获得真正 CPU 并行 |

**内存优化策略**

- `import_files` 按批次（`IMPORT_BATCH_SIZE = 20`）读取文件内容，每批处理完毕后立即释放，峰值内存最多保留 20 张图片字节。
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
    category:        Optional[str]          # 分类
    tags:            Optional[list[str]]    # 标签（JSON）
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
    is_leaf:               bool             # 是否为叶节点
    parent_id:             Optional[int]    # 父相册 ID
    cover:                 Optional[dict]   # 封面信息（JSON）
    photo_count:           int              # 直属照片数
    subtree_photo_count:   int              # 含子相册的总照片数
    date_group:            Optional[str]    # 继承顶层 date_group
    sort_mode:             str              # alpha / date / manual
```

  软删除记录现在统一存放在独立表 `path_soft_delete` 中：`entity_type` 标记目标类型（`image` / `album`），`owner_id` 关联 `ImageAsset.id` 或 `Album.id`，`target_path` 保存被删除的规范化路径。查询层通过该表过滤可见项，因此 `ImageAsset` 与 `Album` 本身不再保存 `deleted_at` 字段。

---

## 🌐 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET`  | `/`                              | 健康检查，返回 `{"status": "ok"}` |
| `POST` | `/api/import`                    | 导入图片文件夹（multipart/form-data） |
| `GET`  | `/api/images/count`              | 返回已导入图片总数 |
| `POST` | `/api/admin/refresh`             | 媒体库刷新（清理 + 修复 + 重建哈希索引） |
| `GET`  | `/api/dates`                     | 返回所有年/月分组及首张缩略图 |
| `GET`  | `/api/dates/{date_group}/items`  | 返回指定日期组的一级内容（直图 + 顶层相册） |
| `GET`  | `/api/albums/by-path/{album_path:path}` | 通过物理路径获取相册详情 |
| `GET`  | `/api/albums/{album_id}`         | 获取相册详情（子相册 + 直属图片） |
| `POST` | `/api/thumbnails/cache`          | 异步生成缓存缩略图 |
| `GET`  | `/api/thumbnails/cache/status/{task_id}` | 查询缓存生成进度 |
| `DELETE` | `/api/cache`                   | 清除所有缓存 |
| `GET`  | `/api/system/viewer-preference`  | 获取图片查看器偏好 |
| `POST` | `/api/system/viewer-preference`  | 设置图片查看器偏好 |
| `GET`  | `/api/system/image-viewers`      | 列出系统中可用的图片查看器 |
| `GET`  | `/thumbnails/{filename}`         | 静态文件：缩略图 |
| `GET`  | `/cache/{filename}`              | 静态文件：缓存缩略图 |

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
    { "type": "image", "name": "photo.jpg", "thumb_url": "/thumbnails/abc.webp", "id": 1, "width": 4032, "height": 3024, "file_size": 2451040, "imported_at": "2026-04-18T13:20:14", "file_created_at": "2025-03-02T09:42:18", "tags": [23, 45] },
    { "type": "album", "name": "旅行", "thumb_url": "/thumbnails/def.webp", "count": 42, "public_id": "album_1", "width": 4032, "height": 3024, "tags": [] }
  ]
}
```

说明：`tags` 为图片条目关联的 Tag ID 列表。BrowsePage 普通模式与选择模式都会优先使用 `cache_thumb_url` 或 `thumb_url` 显示缩略图；若缓存尚未生成，前端先显示骨架占位，再按统一的 `/api/thumbnails/cache` 轮询链路补齐。前端仅在用户把选择模式信息区切换到 Tag 显示时，才会去重后批量调用 `/api/tags?ids=...` 拉取展示名称，避免普通浏览时产生额外查询。

补充：图片条目现在还会额外返回 `file_size` / `imported_at` / `file_created_at`。BrowsePage 的选择模式详情浮层直接消费这组字段，单选时会在固定尺寸的左侧图区内按原图比例显示缩略图；多选时左侧改为可滚动的比例缩略图列表，右下保留“删除”占位按钮，同值字段原样展示、异值字段统一显示 *various*。弹层宽高会同时受主内容区当前可视宽高约束，竖屏下不会再超出界面。

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
- **网格模式**：按年份分组，每个月份显示为缩略图卡片（首张图 + 月份标签 + 图片数）。
- **详情模式**：点击月份卡片后展开，显示该月所有一级内容：
  - 直接图片文件
  - 顶层相册（右上角白底徽章，显示名称和图片数）
  - 点击相册跳转到独立相册页面 `/album/:id`
- **动画**：
  - 前进（打开详情）：网格淡出 → 详情面板从点击位置缩放飞出
  - 后退（返回网格）：详情面板缩回点击位置 → 网格淡入

### 相册视图 `/album/:id`
- 显示指定相册内容：子相册 + 直属图片
- 支持嵌套导航：点击子相册进入更深层级
- 返回导航：有父相册时返回父相册，否则浏览器后退
- 缓存缩略图按需生成（与日期视图相同的滚动触发机制）

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
docker compose up --build
```

后端容器运行在 `http://127.0.0.1:8000`，`media/` 和 `data/` 目录通过 volume 挂载保持持久化。
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

- `media/` 和 `backend/thumbnails/` 目录由后端自动创建，**不要手动移动其中的文件**，否则需要使用"刷新"功能重建索引。
- 使用 `🔄 刷新` 按钮可随时修复不一致状态（文件移动后、手动删除后等）。
- 数据库文件 `backend/data/app.db` 可直接备份；删除后重启会自动创建空数据库。
- `comp/groupByDate/groupByDate.py` 是一个独立命令行工具，可对已有本地文件夹执行整理，与 Web 导入功能独立工作。
