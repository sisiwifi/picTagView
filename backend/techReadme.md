# picTagView Backend 技术说明书

## 1. 项目位置
- `D:\Python_projects\picTagView_main\backend`

## 2. 后端架构概览
- 框架：FastAPI
- ORM：SQLModel（基于 SQLAlchemy）
- 数据库：SQLite（默认文件为 `backend/data/app.db`，路径由 `app/core/config.py` 配置）
- 静态文件：FastAPI `StaticFiles` 挂载 `TEMP_DIR`、`CACHE_DIR`、`MEDIA_DIR`、`TRASH_DIR` 与 `VIEWER_ICON_DIR`，分别用于月份封面缩略图、缓存缩略图、原图、回收站预览回退与看图程序图标访问
- 并行：`concurrent.futures` 的 `ProcessPoolExecutor` + `ThreadPoolExecutor`，用于哈希与缩略图生成

## 3. 主要模块说明

### 3.1 `app/main.py`
- 入口文件，创建应用 `create_app()`：
  - `init_db()`（初始化/建表/迁移）
  - CORS 配置为 `*`
  - 挂载 `/thumbnails` -> `TEMP_DIR`
  - 挂载 `/cache` -> `CACHE_DIR`
  - 挂载 `/media` -> `MEDIA_DIR`
  - 挂载 `/trash-media` -> `TRASH_DIR`
  - 挂载 `/viewer-icons` -> `VIEWER_ICON_DIR`
  - 注册路由 `app.include_router(api_router)`

### 3.2 `app/api/routes.py` + `app/api/routers/*`
  - 路由聚合入口
    - `app/api/routes.py`
      - 只负责 `include_router`
  - 按职责拆分的子路由模块
    - `app/api/routers/basic.py`
      - `GET /`
      - `POST /api/import`
        - 导入批次内会按当前 `tag_match_setting` 自动执行文件名 Tag 匹配，并以追加去重方式写回图片 `tags`
      - `GET /api/images/count`
      - `POST /api/admin/refresh`
    - `app/api/routers/categories.py`
      - `GET /api/categories`
      - `POST /api/categories`
      - `PATCH /api/categories/{category_id}`
      - `DELETE /api/categories/{category_id}`
      - `POST /api/categories/bulk`
    - `app/api/routers/dates.py`
      - `GET /api/dates`
      - `GET /api/dates/{date_group}/items`
    - `app/api/routers/albums.py`
      - `GET /api/albums/by-path/{album_path:path}`
      - `GET /api/albums/open-by-path/{album_path:path}`
      - `GET /api/albums/{album_id}`
    - `app/api/routers/images.py`
      - `GET /api/images/meta`
      - `GET /api/images/{image_id}/open`
      - `POST /api/images/tags/filename-match`
      - `POST /api/images/tags/apply`
    - `app/api/routers/tags.py`
      - `GET /api/tags`
      - `GET /api/tags/{tag_id}`
      - `POST /api/tags/draft`
      - `POST /api/tags`
      - `PATCH /api/tags/{tag_id}`
      - `DELETE /api/tags/{tag_id}`
      - `GET /api/tags/export/json`
      - `POST /api/tags/import/json`
    - `app/api/routers/trash.py`
      - `GET /api/trash/items`
      - `POST /api/trash/move`
      - `POST /api/trash/restore`
      - `POST /api/trash/hard-delete`
      - `DELETE /api/trash`
    - `app/api/routers/system.py`
      - `GET /api/system/cache-thumb-setting`
      - `POST /api/system/cache-thumb-setting`
      - `GET /api/system/month-cover-setting`
      - `POST /api/system/month-cover-setting`
      - `GET /api/system/page-config`
      - `POST /api/system/page-config`
      - `GET /api/system/tag-match-setting`
      - `POST /api/system/tag-match-setting`
      - `GET /api/system/viewer-info`
      - `GET /api/system/image-viewers`
      - `GET /api/system/viewer-preference`
      - `POST /api/system/viewer-preference`
    - `app/api/routers/cache.py`
      - `DELETE /api/cache`
      - `POST /api/thumbnails/cache`
      - `GET /api/thumbnails/cache/status/{task_id}`
      - 其中 `POST /api/thumbnails/cache` 已改为 generation 感知的共享缓存队列入口；`GET /api/thumbnails/cache/status/{task_id}` 支持 `cursor` 增量轮询
  - 共享查询与路径工具
    - `app/api/common.py`
      - 缩略图 URL 解析、存储路径解析、`media_path` 实例选择与路径谓词匹配
      - 2026-04 补充：`app/api/common.py` 新增请求级预览可用性索引与 `AssetPreviewResolver`。`GET /api/dates*` / `GET /api/albums*` 会在单次请求内各扫描一次 `backend/temp/` 与 `backend/data/cache/`，后续只用内存集合判断缩略图是否存在，避免列表装配阶段按条目重复 `exists()`

补充（2026-04）：
- `GET /api/dates/{date_group}/items` 与 `GET /api/albums/{album_id}` 的条目模型新增 `sort_ts`（Unix 秒级时间戳，可为空）。
- `GET /api/dates/{date_group}/items` 与 `GET /api/albums/{album_id}` 的图片条目现同时返回 `tags`（Tag ID 整数列表）；接口仍只返回 ID，不在主查询中联表展开 Tag 名称。
- `GET /api/dates/{date_group}/items` 与 `GET /api/albums/{album_id}` 的图片条目现同时返回 `width` / `height`；相册条目则返回封面图对应的 `width` / `height`。
- `GET /api/dates/{date_group}/items` 与 `GET /api/albums/{album_id}` 的相册条目现同时返回 `photo_count` / `created_at`，供选择详情浮层展示相册图片数量与创建时间。
- 日期视图与相册浏览接口现在只依据图片主分类过滤内容；相册本身不再持有主分类，只要其子树中仍有至少一张可见图片，该相册路径就保持可见。
- `sort_ts` 生成规则：
  - 图片条目：优先 `file_created_at`，回退 `imported_at`，再回退 `created_at`。
  - 相册条目：优先 `updated_at`，回退 `created_at`。
- 前端据此支持“Date/Alpha 排序字段切换 + 升降序切换”。
- 前端排序规则补充：相册项与图片项分组独立排序（各自按 Date/Alpha 与升降序），最终始终保持“相册在前，图片在后”。
- 前端交互补充：排序字段选择器由滑块改为 `select`（`Date`/`Alpha`），升降序箭头按钮独立放在选择框外侧。
- 主分类体系：
  - `Category` 表与 `app/services/category_service.py` 共同维护默认主分类、使用计数、批量启用 / 停用与删除回退。
  - `ImageAsset` 持有唯一生效的 `category_id`；`Album` 只保留目录结构，`Tag` 不再绑定主分类，`TrashEntry.category_id` 仅用于图片条目的删除快照与恢复。
  - 设置页提供独立“主分类配置”入口；主分类页使用与 BrowsePage 一致的面包屑 header，右上角将“管理”和“新建主分类”拆分为独立按钮。
  - 主分类卡片按屏幕方向切换比例：横屏使用横向卡片，竖屏使用竖向卡片；页面主体为独立滚动区。
  - 常态卡片仅显示编辑按钮；管理模式把圆形选择按钮放到卡片右上角，并在卡片右下角显示移除按钮。右下角按钮岛负责批量打开 / 关闭、全选与取消选择；窄屏下仍保持单行紧凑布局，折叠时向页面边缘收拢。
  - 页面反馈使用浏览器顶端浮动 message，不占据正文布局高度。
  - 选择详情浮层仅在图片选择态显示 `Category.display_name` 作为“主分类”字段。
- 前端结构补充：日期详情页与相册页的 header 已统一为面包屑样式，并组件化为 `frontend/src/components/BreadcrumbHeader.vue`，用于复用“返回按钮 + 面包屑 + 项目数 + 排序控件 + 右侧扩展操作区”。
- 前端交互补充：BrowsePage 已启用 header 上预留的“选择”按钮。进入选择模式后，列表强制切换为固定比例媒体卡片网格；卡片由 `frontend/src/components/MediaItemCard.vue` 组件承载，结构为“正方形图片区 + 固定 56px 信息区”。当前网格列数策略为：横屏固定 5 列，竖屏固定 3 列，用于控制同屏资源消耗。
- 渲染策略补充：BrowsePage 仅对列表模式与选择模式启用窗口化渲染，滚动时按可视区切片更新 DOM；“大缩略图”照片墙继续保留全量 `justifiedRows` 布局，但新增“精确容器宽度 + 布局指纹”级别的内存排布缓存，减少重复重算。
- 选择模式交互补充：
  - 第一项选中的类型会锁定当前批量选择类型（`image` 或 `album`），另一类型卡片置灰且不可选。
  - 支持单击单选、`Ctrl`/`Cmd` 追加切换、`Shift` 范围选择；若范围内出现异类项则跳过。
  - 支持鼠标长按后拖选，以及触屏长按滑选。
  - 卡片左上角的圆形选择符号已缩小并改为可点击控件；点击已选项的该符号会直接取消该项选择。
  - 右上角 grid/list/select 三个模式按钮可直接互切；在选择态下点击 grid 或 list 会退出当前选择态并进入对应浏览模式。
  - 页面右下角显示半透明操作岛，提供已选计数、“详情”“全选”“取消选择”；若当前视图同时存在相册与图片，点击“全选”会向上展开“相册 / 图片”两个快捷入口，再次点击空白处收起。操作岛左侧提供收拢按钮，点击后会向页面右侧边缘收起；窄屏下保持单行紧凑布局，不再拆成多行块状按钮面板。
  - 卡片右下角的 `...` 按钮与操作岛“详情”按钮都会打开主内容区内的二级详情浮层；浮层遮罩不覆盖左侧 Sidebar，可通过右上角文字关闭按钮或点击空白处关闭。
  - 详情浮层尺寸由主内容区当前可视宽度与可视高度共同约束，不再受整页内容高度或单张图片视觉尺寸反推；左侧图片区内部按原图比例自适应展示缩略图，多选时左侧改为隐藏滚动条且可滚动的比例缩略图列表。
  - 详情浮层单选时展示 cache/temp 缩略图与文件元数据，多选时同值字段直接显示，异值字段统一渲染为斜体 `various`；动作区底部保持“删除”占位按钮可见。若当前选中的是相册，则“尺寸”栏切换为“图片数量”并展示 `photo_count`，创建时间改读相册 `created_at`，主按钮文案改为“查看相册”。
  - 打开详情浮层时会锁定页面滚动，并拦截中键自动滚动对底层页面的影响；关闭后恢复原有滚动位置。
  - 若条目是在旧响应下加载、缺失 `file_size/imported_at/file_created_at`，前端会额外调用 `/api/images/meta?ids=...` 补齐当前选中图片的详情字段。
  - 详情浮层调用 `PATCH /api/images/metadata` 修改文件名 / 主分类 / 创建时间后，前端不再整页执行 `loadData()`；名称与主分类直接局部回写当前 `items`，创建时间修改则按新 `media_rel_path` 判断是否仍属于当前日期页或相册页，只做局部重排或移除。
- 列表模式交互补充：
  - 列表模式支持长按条目进入列表选择态，并沿用与卡片选择界面一致的 Ctrl/Shift、多选逻辑与统一圆形选择符号。
  - 列表选择态下，条目点击不再打开内容；选择符号支持直接取消单项选择。
  - 相册标识从列表右侧移至缩略图右侧，改为圆角矩形 `ALB` 标签后接相册名，右侧预留为空白区域。
- 信息区显示补充：选择模式信息区默认显示文件名；点击任一卡片的信息区后，当前页面所有卡片统一切换为 Tag 文本显示，再次点击切回文件名。
- 缩略图策略补充：BrowsePage 普通模式与选择模式统一优先显示 `data/cache/*.webp` 或 `temp/*.webp` 缩略图；当 `cache_thumb_url` 缺失时，前端先显示骨架占位，并通过 `/api/thumbnails/cache` 按需异步生成缓存后再更新显示。原图回退不再作为常规浏览路径。
- 后端性能补充：日期列表、月份内条目列表和相册详情在组装 `thumb_url` / `cache_thumb_url` 时，会复用同一个请求级目录索引；接口语义仍保持“仅在文件实际存在时返回 URL”，但磁盘存在性判断从逐条 `Path.exists()` 收敛为每请求两次目录扫描。
- 浏览锚点补充：BrowsePage 现区分“视觉锚点”和“缓存锚点”。视觉锚点用于 grid / list / 选择模式互切时恢复同一内容的位置，保证目标内容至少落在新布局的第一排内；缓存锚点则专门用于缓存缩略图生成请求。
- 照片墙布局补充：BrowsePage 的“大缩略图”模式会优先使用浏览接口返回的 `width` / `height` 初始化 `justifiedRows` 布局，避免依赖图片逐张加载后再回填宽高，从而降低首轮重排频率；`onImgLoad` 现在只在 `width` / `height` 缺失时做异常兜底回填，不再作为常规排布来源。
- 缓存队列补充：BrowsePage 与 CalendarOverview 发起的缓存缩略图请求已改为 `page_token + generation` 协议。前端会先按“缓存锚点、当前首排、前后 N 张”构造优先级列表，其中 `N` 由设置页 `scroll_window_size` 决定，可选 `40-200`、默认 `100`（即锚点前后各约 `50` 项），再交给后端共享 worker 池；同页新 generation 到来时，未启动的旧 job 会被丢弃，状态轮询通过 `cursor` 增量返回新增完成项。
- Tag 请求策略补充：前端仅在信息区切换到 Tag 模式时，才会从当前页面条目中去重收集 `tags` ID，并分批调用 `GET /api/tags?ids=...` 批量换取 `display_name/name`；普通浏览与默认文件名模式不触发该请求，以减少 DB 压力与事务占用。
- 返回与面包屑导航行为：
  - 前端路由已重构为层级结构（2026-04）：
    - 一级页面（并列）：主页 `/`、标签总览 `/tags`、图库管理 `/gallery`、日期视图 `/calendar`、系统设置 `/settings`、回收站 `/trash`
    - 二级页面（设置域）：
      - `/settings/categories` — 主分类配置页
    - 二级页面（日期域浏览）：
      - `/calendar/:group` — 月份图片列表（BrowsePage）
      - `/calendar/:group/:albumPath+` — 相册浏览，支持任意层级嵌套（BrowsePage）
    - 旧路由 `/album/:id` 已废弃，相册通过物理路径映射到 URL：`/calendar/2024-07/vacation/day1`
  - 面包屑结构：日期视图 › YYYY-MM › 相册1 › 相册2（当前），完全由 URL 路径段驱动，无需异步补标题。
  - BrowsePage 同时承载月份列表和相册浏览，通过 `$route.params` 判断模式：无 `albumPath` 为月份模式，有则为相册模式，调用 `GET /api/albums/by-path/{path}` 获取数据。
  - 组件复用策略：两个 browse 路由共享 `meta.reuseKey = 'browse'`，App.vue 使用 `:key="route.meta?.reuseKey || route.name"` 避免组件销毁重建，消除跨层级导航闪动。
  - 后续若要以 BrowsePage 为基底构建新的浏览页，统一通过 `browseContract` 注入页面差异，避免复制整套页面壳；更完整的契约字段、生命周期钩子与适配器规范见 [frontend/commonBrowsePage.md](../frontend/commonBrowsePage.md)。
  - Gallery 路由额外声明 `meta.keepAlive = true`；`App.vue` 需要保持 `<KeepAlive>` 容器本身常驻，只把普通路由放在独立分支渲染，这样 Gallery 导入队列与进度状态在切换页面时才会进入 deactivated 而不是被卸载。
  - 返回按钮语义统一为"目录上一级"：在相册内返回上一级相册或月份列表，月份列表返回日期总览。
  - CalendarOverview 为纯月份网格页面，不再内含详情子视图。
  - CalendarOverview 的月份网格按页面方向切换列数：横向（`orientation: landscape`）固定 6 列，纵向（`orientation: portrait`）固定 3 列，不再使用最小宽度断点控制。
  - 侧边栏 `/calendar` 高亮规则：路径以 `/calendar` 开头即激活。
  - sessionStorage `pendingAlbumTitle` 机制已移除，标题由 URL 路径段或 API 响应即时提供。
- **页面切换过渡动画**：
  - `App.vue` 中 `<router-view>` 使用 `<Transition name="page" mode="out-in">` 包裹路由组件，一级页面切换有淡入淡出动画（离开 110ms、进入 160ms）。
  - BrowsePage 内在 group/album 层级间导航时组件复用（不销毁），由 watch `$route.params` 触发数据刷新，面包屑即时更新，无闪动。
  - `BreadcrumbHeader.vue` 中面包屑 `<nav>` 通过 `TransitionGroup` 实现节点增减动画。
- 默认策略：
  - 日期视图详情（非相册视图）默认 `Date` 升序。
  - 相册视图默认 `Alpha` 升序。
- 回收站交互补充：
  - 设置页右上角新增更显眼的“回收站”入口，但路由直接复用 `BrowsePage`，通过 `browseContract = 'trash'` 注入回收站策略，不再维护独立的回收站页面。
  - `BreadcrumbHeader.vue` 通过 slot 注入回收站页头右侧操作按钮；选择态右下角操作岛由页面契约提供“详情 / 还原 / 删除 / 全选 / 取消选择”，并与日历浏览共用同一套窄屏单行紧凑布局与向页面边缘收拢的交互。
  - 详情浮层复用 `SelectionDetailOverlay.vue`，但主动作切换为“还原”，危险动作切换为“删除”，并禁用 Tag 编辑入口（无 `+` 按钮）。
  - 详情浮层的 Tag 区改为复用 `TagChipList` 显示，与 BrowsePage 保持同款显色样式；该页面仅展示，不提供编辑能力。
  - BrowsePage 的“删除到回收站”与回收站 contract 的“还原 / 删除 / 清空回收站”统一改为 `ConfirmationDialog.vue` 居中弹窗确认，不再使用浏览器原生 `confirm/alert`。
  - 回收站 contract 的列表刷新会捕获首屏视觉锚点，并在 contract 变化或静默对账后恢复到对应条目附近；选择态卡片按可视窗口虚拟渲染，避免大回收站一次性挂载全部卡片。
  - 批量删除/清空/还原确认后，页面会立即进入 busy 锁定态：确认按钮不可重复点击，主界面显示“处理中”遮罩，降低大批量操作下的重复误触风险。

### 3.3 `app/services/import_service.py`（门面）
- 对外稳定入口：
  - `import_files(files, last_modified_times, created_times, category_id=None)`
  - `refresh_library()`
  - `rebuild_hash_index()`
  - `recalculate_album_counts()`
- 该文件仅做兼容导出；实现已拆到 `app/services/imports/*`。

### 3.3a `app/services/category_service.py`
- 主分类服务：
  - `ensure_default_category(session)`：确保默认主分类存在，固定 `id=1`、`name=default`、`display_name=默认`
  - `get_active_category_ids(session)`：返回当前可见主分类集合，并强制包含默认主分类 `1`
  - `is_category_visible(category_id, active_category_ids)`：供浏览接口复用的可见性判断
  - `resolve_category_id(session, category_id, category_name)`：兼容旧数据或导入 JSON 中的分类名称
  - `sync_category_usage_counts(session)`：同步 `{image}` 使用计数
  - `reassign_category_references(session, source_category_id, target_category_id=1)`：删除主分类前，把关联图片与图片回收站条目统一回退到默认主分类
  - `backfill_category_ids_from_legacy()`：初始化时只从图片与图片回收站 legacy 字段回填 `category_id`

### 3.3b `app/services/imports/pipeline.py`
- 导入主流程（批处理与去重核心）
- `import_files(files, last_modified_times, created_times, category_id=None)`：
  - 解析上传路径（兼容 `webkitRelativePath`），`_parse_relative_path` 返回 `(subdir_chain, filename)`
  - 过滤非图片，由扩展名判断
  - 维护目录级 `date_group`，按子目录最早时间分组（格式 `YYYY-MM`）
  - 可选接收 `category_id`；当导入请求来自前端多行导入表单时，每行会带入一个主分类选择值
  - 前端多行导入表单会把根目录直下文件与嵌套子目录统一按 `50` 个文件切块后顺序提交，避免大子目录形成单次超大请求；导入开始时表单自动收起，主页面进度文案显示当前目录标签
  - 导入完成后，Gallery 页面不再额外弹出顶部“完成确认”结果框；成功结果收敛到状态行，失败目录仍保留在导入表单中供重试
  - 导入前加载哈希索引缓存 `.hash_index.json`，用于 O(1) 去重查找
  - 子目录链 → 自动创建 Album 树（`_ensure_album_chain`），所有嵌套层级继承顶层 `date_group`
  - 主分类决策规则：`category_id` 只写入图片；新建图片直接使用请求值，已存在图片仅在当前仍为默认主分类时提升，避免 hash 去重场景下误改既有非默认分类图片
  - 去重策略：相同哈希在相册内 → 保留并添加 album 关系；直传重复 → 跳过
  - 每个导入批次在单个数据库事务内完成该批图片的写入、相册关系更新，以及按文件名自动匹配 Tag
  - 文件名 Tag 自动匹配复用系统设置 `tag_match_setting` 与 `/api/images/tags/filename-match` 的同一套规则：按空格分词、不拆下划线、支持噪声词 / 最小长度 / 纯数字过滤，并自动忽略草稿 Tag
  - 导入期自动打标固定使用 `append_unique` 语义：只追加本次文件名命中的 Tag，不覆盖图片既有 Tag
  - 受影响 Tag 的 `usage_count` 在批次事务内按增量更新，`last_used_at` 只刷新本批次新增关联的 Tag，避免为导入逐批全表重算图片标签计数
  - 导入结束后保存哈希索引并释放内存
  - 批次读取文件内容（`IMPORT_BATCH_SIZE=50`）
  - 线程池并行 `process_from_bytes` 只为"每月封面所需图片"生成 temp 缩略图
  - 其他图片调用 `process_hash_only_from_bytes`（`_compute_hash_only` worker）：并行完成 SHA-256 + xxhash + **cv2.imdecode 尺寸读取**，不生成缩略图
  - DB 串行写入循环中仅使用已并行得到的宽高，不再在主线程调用 cv2（性能优化方案 A）
  - 导入请求中的 `category_id` 只作用于图片；子目录仍会创建树形 `Album`，但不会再把主分类写入相册链或从祖先相册继承主分类
  - 导入不中断行为：`GalleryPage.vue` 仍在本地维护导入队列、当前目录与累计进度，但 `/gallery` 路由现在通过 `meta.keepAlive = true` 保活；用户切到其它页面时组件进入 deactivated 状态而不是被销毁，返回 Gallery 后会继续显示同一轮导入。
  - `window.__ptvImporting` 在导入开始/结束时仍会置为 `true/false`，但它只作为导入期状态标记；真正保证“切换页面不打断导入”的实现是前端路由保活。
  - `App.vue` 的实现不能把 `<KeepAlive>` 放在“当前路由是否 keepAlive”的条件分支上；否则一旦跳到普通页面，`KeepAlive` 容器会被整体移除，Gallery 也会随之卸载，正在进行的导入循环会中断。
  - 前端多行队列采用“单行失败不阻塞后续行”的策略；失败行会在导入结束后保留在表单中，供用户修正后重试。
  - Gallery 导入期间新增“停止导入”按钮：前端会设置 stop flag，并对当前批次请求使用 `AbortController` 做最佳努力取消；一旦停止，后续批次不再发送，当前及未完成的目录行会保留在表单中供继续导入。由于停止发生在 HTTP 请求层，如果当前批次已被后端接收，个别文件仍可能已经入库，后续继续导入时会由既有 hash 去重规则跳过重复项。
  - 前端刷新策略变更（路由切换相关）：项目已移除“路由切换自动触发全库刷新”的行为，`frontend/src/router/index.js` 不再在每次路由变更时发起后台 `POST /api/admin/refresh`。当前前端刷新策略为：
    - 仅在 Gallery 页面由用户点击的“刷新”按钮触发完整的 `POST /api/admin/refresh?mode=full`（保留为手动触发的全库修复/补齐与新文件收编）。
    - 切换到首页（`/`）时仅请求 `GET /api/images/count`，用于刷新并显示库总数的统计信息。
    - 在 Gallery、DateView（日历）与 BrowsePage 的两个 contract（calendar / trash）中，前端会对缩略图加载错误（例如 `404`）做出响应：当页面检测到 `TEMP_DIR` 或 `CACHE_DIR` 中的目标预览缺失时，会立即（无延迟）调用 `POST /api/admin/refresh?mode=quick`；其中 calendar contract 传入 `image_ids`，trash contract 传入 `trash_entry_ids`。后端会补齐缺失预览并把新生成的缩略图路径、文件哈希等信息回写元数据，前端随后重新拉取对应数据以避免脏引用长期停留在页面中。
  - 文件时间规则：取创建时间与修改时间最小值，回刷到导入文件，并记录到元数据
  - 写入 `ImageAsset`（`quick_hash`、尺寸、mime、tags/thumbs 等扩展字段）

### 3.3c `app/services/imports/maintenance.py`
- 维护/修复工作流：
- `refresh_library()`：
  - 支持 `mode=quick|full`（默认 `quick`）
  - 三阶段执行：
    1) 路径对账与关系修复：清理失效 `media_path`、重建 `ImageAsset.album`、维护 `Album` 表并处理非相册唯一实例冲突
    2) 缩略图与元数据修复：补齐代表图所需 400×400 temp 缩略图及缺失元数据
    3) `full` 模式下收编新文件：扫描 `MEDIA_DIR` 中未入库图片，按导入规则做 hash 去重并写回索引
  - 清理 orphan cache（无对应媒体记录的 `*_cache.webp`）
  - 不再维护用户软删除状态；用户级删除/恢复改由 `TrashEntry + trash/` 承载，`refresh_library()` 仅负责 live `media/` 的对账与收编
- `reconcile_library_paths()`：
  - 对现有 `ImageAsset.media_path` 做 live 路径对账，删除完全失效的资产记录
  - 根据当前 live 路径重建 `Album` 树与 `album_image` 关系
- `ingest_media_entries(entries)`：
  - 提供可复用的本地文件重收编入口，供回收站“还原”流程按导入规则重新建库，而不必扫描整个媒体库
- `recalculate_album_counts()`：重算 `photo_count` / `subtree_photo_count` 与封面；同时清空并完整重建 `album_image` 关联表。

### 3.3d `app/services/imports/hash_index.py`
- 哈希索引缓存子模块：
  - `load_hash_index()` / `save_hash_index()`
  - `lookup_hash_index()` / `lookup_quick_hash()`
  - `add_to_hash_index()` / `rebuild_hash_index()`

### 3.3e `app/services/imports/helpers.py`
- 导入与维护公共工具：
  - 路径转换：`to_project_relative`、`resolve_stored_path`
  - 文件时间：`apply_file_times`、`set_windows_creation_time`
  - 缩略图条目：`required_thumb_entry`、`upsert_thumb`、`has_required_thumb`
  - 媒体基础能力：`quick_hash_from_bytes`、`mime_from_name`、`image_dimensions_from_*`
  - 目录冲突处理：`unique_dir_dest()`，供回收站还原相册时在目标月份目录下自动追加 `_1`、`_2` 等后缀避免重名覆盖

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
  - 提供页面浏览模式配置：
    - `get_page_config()`（默认 `scroll`）
    - `set_page_config(setting)`（当前支持 `scroll` / `paged`）
  - 该配置被 `cache_thumb_service` 在生成 `data/cache/*.webp` 时使用
  - `parallel_processor` 会使用月份封面尺寸配置生成 `temp/*.webp`

### 3.4d `app/services/cache_thumb_service.py`
- 浏览缓存缩略图服务：
  - `generate_cache_thumb_entry(key, file_path, cache_dir)`：单张图片缓存生成入口，供共享队列 worker 使用
  - `generate_cache_thumbs_progressively(...)`：兼容其它批量场景的渐进式生成接口
  - `get_cache_thumb_worker_count()`：按 CPU 核数动态计算 worker 数，默认保留 2 个核心给系统，并设置 8 个 worker 上限

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
  - `width` / `height` / `file_size` / `mime_type`: 媒体元信息；其中 `width` / `height` 会直接透传到 BrowsePage 相关接口，供照片墙预布局使用
  - `category_id` (int): 主分类 ID，默认回退到 1
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
  - `is_leaf` (bool): 是否为叶节点相册（无子相册）
  - `parent_id` (int | null): 父相册 ID（顶层相册为 null）
  - `cover` (JSON dict | null): 封面信息 `{photo_id, thumb_path, filename, updated_at}`，按文件名字母序选取最早文件
  - `photo_count` (int): 直属照片数
  - `subtree_photo_count` (int): 含所有子相册的总照片数
  - `sort_mode` (str): 排序模式 `alpha`（默认）/ `date` / `manual`
  - `settings` / `stats` (JSON dict): 扩展设置与统计
  - `date_group` (str | null): 所有嵌套层级继承顶层的 `date_group`
  - `created_at` / `updated_at`: 时间戳
  - 可见性、封面与计数由当前活跃主分类下的图片实时派生，而不是由相册字段直接决定

### 3.5c `app/models/category.py`
- 数据模型 `Category`：
  - `id` (int): 主键；系统默认主分类固定为 `1`
  - `public_id` (str): 对外标识，格式 `category_{id}`
  - `name` (str): 规范名，仅允许小写字母、数字和下划线
  - `display_name` (str): 前端展示名
  - `description` (str): 说明
  - `usage_count` (JSON dict): 使用计数 `{image}`
  - `is_active` (bool): 前端显示开关
  - `created_at` (datetime): 创建时间

### 3.5d `app/models/trash_entry.py`
- 数据模型 `TrashEntry`（独立回收站表）：
  - `id` (int): 主键
  - `entry_key` (str): 回收站条目唯一键，用于稳定识别条目与其落盘 payload
  - `entity_type` (str): 目标类型，当前为 `image` 或 `album`
  - `display_name` (str): 前端展示名称
  - `original_path` (str): 删除前 live 路径；图片对应具体 `media_path` 条目，相册对应 `Album.path`
  - `original_date_group` (str | null): 删除前所属月份
  - `trash_path` (str): 实际移动到 `TRASH_DIR` 后的 payload 路径
  - `preview_path` / `preview_thumb_path` / `preview_cache_path`: 预览与回退缩略图路径；当前策略下回收站优先复用 `preview_cache_path` 指向的共享 cache，`preview_thumb_path` 仅保留兼容字段
  - `file_hash` / `width` / `height` / `file_size` / `mime_type`: 预览与恢复辅助元数据
  - `category_id` (int | null): 仅图片条目保留删除前主分类 ID；相册条目始终为空
  - `imported_at` / `file_created_at` / `source_created_at`: 原文件时间信息
  - `photo_count` (int | null): 相册条目直属或子树图片数快照
  - `tags` / `metadata_json`: 附加 JSON 元数据
  - `created_at` (datetime): 记录创建时间

说明：用户删除时，文件或目录会先从 `MEDIA_DIR` 物理移动到 `TRASH_DIR`，再写入 `TrashEntry`。文件夹内为每个条目直接扁平存放为 `trash/<entry_key>__<原名>`，因为 `entry_key` 已足够提供唯一命名空间。普通浏览接口只反映 live `media/` 内容；回收站界面则直接读取 `TrashEntry`。恢复时按导入/刷新规则重新收编，清空回收站或硬删除时才真正移除 `TRASH_DIR` 中的 payload。

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
"category_id": 1,
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
  - `name` (str): 规范化名称，仅允许小写字母 / 数字 / 下划线，数据库唯一约束，最大 256 字节
  - `display_name` (str): 前端展示名称，默认与 name 相同
  - `type` (str): 标签种类，取值为 `normal` / `artist` / `copyright` / `character` / `series`，默认 `normal`
  - `description` (str | null): 描述，最大 1024 字节
  - `usage_count` (int): 缓存字段，表示当前有多少张图片0关联了该 Tag，由写入侧维护
  - `last_used_at` (str | null): Tag 最后被关联或访问的时间，格式 `YYYYMMDDHHMMSS`；Tag 菜单输入为空时会按该字段倒序读取最近使用 5 条
  - `metadata_` (JSON dict): 存储为数据库列 `metadata`，可扩展扩展字段，结构如下：
    - `schema_version` (int): Tag 元信息版本号，当前为 1
    - `color` (str): 展示颜色，统一使用 HEX8，如 `#FF9900FF`
    - `border_color` (str): 边框颜色，统一使用 HEX8，如 `#FF9900FF`
    - `background_color` (str): 背景颜色，统一使用 HEX8，如 `#FF990066`
    - `created_via` (str): 创建来源，合法值见下表
    - `ui_hint` (dict): 前端 UI 展示提示，如 `{"badge": "city", "promote": true}`
    - `notes` (str): 备注，默认留空
  - `created_at` (datetime): 记录创建时间（UTC）
  - `created_by` (str): 创建者，主控生成为 `admin`，导入为 `import`；系统预占草稿使用 `system:draft-reserve`
  - `updated_at` (datetime): 最后更新时间（UTC）

  **草稿 Tag 说明：**
  - 前端“新增标签”会先调用 `POST /api/tags/draft` 预占一个真实 `id/public_id`
  - 草稿 Tag 以 `created_by=system:draft-reserve` 标记，不会出现在 `/api/tags` 列表、导出 JSON、最近使用标签、文件名自动匹配与图片批量打标接口中
  - 用户取消新增弹窗时，前端会调用 `DELETE /api/tags/{id}` 清理草稿；提交时通过 `PATCH /api/tags/{id}` 将草稿转正

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

本项目所有持久化数据均存储在同一个 SQLite 文件（路径由 `app/core/config.py` 中的 `DB_PATH` 配置，默认 `backend/data/app.db`）。

| 表名 | 对应模型 | 主要作用 |
|---|---|---|
| `imageasset` | `ImageAsset` (`app/models/image_asset.py`) | 图片媒体资产主表；存储哈希、路径、尺寸、日期分组、缩略图条目、关联 Tag ID 数组等全量元数据 |
| `album` | `Album` (`app/models/album.py`) | 树形相册结构；存储相册名称、层级路径、封面、照片计数、日期分组 |
| `trashentry` | `TrashEntry` (`app/models/trash_entry.py`) | 回收站条目表；记录回收站内图片/相册的原路径、trash payload、预览信息与恢复所需元数据 |
| `album_image` | `AlbumImage` (`app/models/album_image.py`) | 相册-图片显式多对多关联表；通过索引 JOIN 替代全表扫描，加速相册与日期视图查询 |
| `tag` | `Tag` (`app/models/tag.py`) | 标签库；存储标准化名称、展示名称、使用次数、来源、元信息等，`ImageAsset.tags` 存储该表的 `id` 外键 |

附加文件：
- `MEDIA_DIR/.hash_index.json`：哈希索引缓存（非 SQLite），用于导入时 O(1) 去重，详见 §3.3d。

## 4. 核心业务流程
1. 用户前端上传图像文件列表
2. `/api/import` 解析 `last_modified_json` 与可选 `category_id`，并发处理图像哈希/缩略图；每个批次在同一事务内完成图片写入并按文件名自动追加匹配到的 Tag
3. 记录写入数据库并保存到 `MEDIA_DIR`（按 `date_group`/子目录组织）
4. 前端调用 `/api/dates` 和 `/api/dates/{date_group}/items` 构建图库视图
5. 管理端 `/api/admin/refresh` 保持一致性（支持 `quick/full`）
6. 用户从 BrowsePage 删除图片或相册时，请求 `/api/trash/move`，目标会从 `media/` 移入 `trash/` 并生成 `TrashEntry`
7. 回收站 contract 通过 `/api/trash/items` 先展示当前可显示的回收站条目；轻量对账改由 `/api/trash/reconcile` 提供，前端在首屏绘制后静默异步调用，对账结果若改变列表则再按当前锚点刷新页面
8. 回收站 contract 批量“还原”调用 `/api/trash/restore`，“删除”调用 `/api/trash/hard-delete`，“清空回收站”调用 `DELETE /api/trash`；其中图片恢复保留正常缩略图链路，相册恢复优先走轻量哈希收编再按需补预览，以降低等待时间

补充：
- 设置页可通过 `GET/POST /api/system/cache-thumb-setting` 管理缓存缩略图短边尺寸。
- 设置页可通过 `GET/POST /api/system/month-cover-setting` 管理月份封面尺寸。
- 设置页可通过 `GET/POST /api/system/page-config` 管理 BrowsePage 的 calendar / trash contract 共享的“滚动浏览 / 分页浏览”模式，以及滚动模式下的 `scroll_window_size`；分页时每页内容由前端按当前视口高度切分，后端负责持久化模式与窗口范围本身。
- 当尺寸保存成功后，前端会调用 `DELETE /api/cache` 清空 `data/cache/` 与 `temp/`，后续缓存缩略图按新尺寸重新生成。

## 5. 配置与外部依赖
- `app/core/config.py`（含 `MEDIA_DIR`, `TEMP_DIR`, `CACHE_DIR`, `TRASH_DIR`, `DB_PATH`）
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
- `IMPORT_BATCH_SIZE=50`：避免一次性内存占满，通过分批读取并处理减少压力
- 并行调用逻辑
  - `process_from_bytes`（线程池，适合来自前端上传的流式字节）
  - `process_from_paths`（进程池，适合本地磁盘批量扫描）
  - `process_hash_only_from_paths`（进程池，适合回收站相册恢复时只做哈希与尺寸收集，跳过同步缩略图写入）
- 回收站规则
  - 普通浏览接口只处理 live `media/` 与数据库中的 `ImageAsset` / `Album` 记录，不再依赖路径级软删除过滤
  - 删除动作会把 payload 物理移入 `TRASH_DIR` 并写入 `TrashEntry`；新写入条目直接扁平存放在 `trash/` 根下，而不是创建额外的深层 payload 目录
  - 删除动作会优先为新写入的 `TrashEntry` 复用或补齐共享 `CACHE_DIR/{file_hash}_cache.webp`，避免回收站再单独维护一套 temp 缩略图
  - 恢复动作会将 payload 移回 `MEDIA_DIR` 后复用导入链路重新建库；相册重名时通过 `unique_dir_dest()` 自动编号
  - `GET /api/trash/items` 只负责返回当前可显示条目；轻量回收站对账改由 `POST /api/trash/reconcile` 触发，供前端在首屏展示后静默执行
- 缩略图缓存策略
  - **导入缩略图**（月份封面）：仅对每月代表图生成 `TEMP_DIR/{file_hash}.webp`，400×400 方形裁剪
  - **缓存展示缩略图**（相册内浏览）：按需生成 `CACHE_DIR/{file_hash}_cache.webp`，最短边 600，保持原始比例
  - 回收站条目常规浏览优先复用 `cache_thumb_url`，其次兼容 `thumb_url`；若 cache/temp 预览缺失，前端先显示骨架，再通过带目标 `trash_entry_ids` 的 `POST /api/admin/refresh?mode=quick` 静默补齐。`/trash-media/...` 仅在详情层缩略图失败时作为少量兜底原图使用
  - 因为 `GET /api/trash/items` 已直接返回 `cache_thumb_url` 与宽高，BrowsePage 的 trash contract 不走 BrowsePage 日历契约的 generation/cursor 轮询协议；页面只在前端维护精确宽度排布缓存、视觉锚点恢复、可见窗口定向修复与缺失尺寸的 `img.onload` 兜底回填
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
  - `POST /api/import` 多文件上传（`files` + 可选 `last_modified_json` + 可选 `created_time_json` + 可选 `category_id`）；若 `tag_match_setting.enabled=true`，导入批次会按文件名自动追加匹配到的 Tag
  - `POST /api/admin/refresh?mode=quick|full` 修复库状态（默认 `quick`）
   - `GET /api/images/count` 计数
  - `GET /api/images/meta?ids=...` 批量读取图片详情字段与 `media_paths`
   - `GET /api/dates` 列出年月分组
  - `GET /api/dates/{date_group}/items` 列出直图/子相册（图片条目含 `media_index` 与 `media_rel_path`）
  - `GET /api/albums/by-path/{album_path:path}` / `GET /api/albums/open-by-path/{album_path:path}` 相册浏览与在资源管理器打开目录
  - `GET /api/images/{image_id}/open?path=...` 按指定 `media_path` 实例打开图片
    - `POST /api/images/tags/filename-match` 按文件名自动匹配并批量回写标签（自动忽略草稿 Tag）；导入流程会复用同一套匹配规则
    - `POST /api/images/tags/apply` 批量添加/覆盖/移除标签（`merge_mode=append_unique|replace|remove`，自动忽略草稿 Tag）
    - `GET /api/tags?sort_by=last_used_desc&limit=5` 获取最近使用标签
    - `POST /api/tags/draft` 预占真实 `id/public_id` 并创建隐藏草稿 Tag
    - `PATCH /api/tags/{id}` 支持更新 `name / display_name / type / description / metadata`
  - `GET /api/trash/items`、`POST /api/trash/move`、`POST /api/trash/restore`、`POST /api/trash/hard-delete`、`DELETE /api/trash` 回收站相关操作

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
- 回收站目录：`TRASH_DIR` = 例如项目根的 `trash`
- 数据库路径：`DB_PATH` = 例如 `backend/data/app.db`
- `date_group` 规则：`YYYY-MM`（如 `2024-07`），用于前端按年/月分组

---