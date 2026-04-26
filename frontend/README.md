# picTagView Frontend 技术说明书

## 1. 项目位置
- `D:\Python_projects\picTagView_main\frontend`

## 2. 技术栈
- Vue 3（Vue CLI 项目）
- Vue Router（页面导航）
- Axios / Fetch（HTTP 请求，与后端API交互）
- Tailwind CSS（样式工具类）
- ES6+ JavaScript
- Node.js + npm（构建与脚本运行）

## 3. 目录结构
- `public/`：静态资源与 `index.html`
- `src/`：主要源码
  - `App.vue`：根组件
  - `main.js`：应用入口，挂载路由与全局样式
  - `router/index.js`：路由配置
  - `assets/tailwind.css`：Tailwind 入口
   - `assets/tag-chips.css`：Tag 圆角标签通用样式
  - `components/`：通用组件
    - `LoadingSpinner.vue`
      - `PagePaginationBar.vue`
    - `Sidebar.vue`
    - `ThumbCard.vue`
      - `TagChipList.vue`（按 Tag 元数据显色）
         - `TagMenuDialog.vue`（可复用的 Tag 菜单弹层）
   - `utils/`
      - `pageConfig.js`（页面浏览模式缓存、拉取与广播）
  - `pages/`：路由页面
    - `HomePage.vue`
    - `GalleryPage.vue`
      - `CalendarOverview.vue`
      - `BrowsePage.vue`
    - `EmptyPage.vue`

## 4. 主要功能说明
### 4.1 上传与导入
- `GalleryPage` 提供多行文件夹导入 UI，可为每一行单独选择主分类
- 调用 `POST /api/import`
- 传递 `files` 与 `lastModifiedJson`
- 按 groupByDate 规则顺序组批上传，单批最多 50 个文件
- `/gallery` 路由启用 `meta.keepAlive`，切换到其他页面时不会销毁导入队列；返回后继续显示当前进度

### 4.2 日历总览
- `CalendarOverview` 获取 `GET /api/dates`
- 按 `year -> month` 做嵌套显示
- 点击月组进入 `/calendar/{date_group}` 浏览页

### 4.3 展示图库内容
- `BrowsePage` 调用 `GET /api/dates/{date_group}/items` 或 `GET /api/albums/by-path/{album_path:path}`
- 直图显示 `ThumbCard`，子目录显示相册封面并支持物理路径继续下钻
- 同时消费 `GET /api/system/page-config` 的浏览方式设置；当模式为 `paged` 时，瀑布流、列表和选择网格都会按当前视口高度分页，列表页支持每页 `10 / 20 / 50 / 100`
- 选择模式详情浮层中的 Tag 使用 `TagChipList` 渲染，显色来自后端返回的 Tag 元数据字段，统一为 HEX8：
   - `color`
   - `border_color`
   - `background_color`

### 4.4 回收站浏览与页面配置
- `TrashPage` 调用 `GET /api/trash/items`
- 与 `BrowsePage` 共用 `PagePaginationBar` 和 `pageConfig.js`
- 当设置页切到“分页浏览”时，回收站瀑布流与选择网格也会分页，并在窗口缩放后按当前首个可见项重新定位页码

### 4.5 文件名分析回写 Tag
- 前端保留文件名分析回写能力，可调用 `POST /api/images/tags/filename-match`
- 支持批量图片分析并回写 tags，前端会即时刷新当前选择项的标签显示
- 多选显示规则：优先显示公共标签；没有公共标签但存在差异时显示 `various`

### 4.6 Tag 菜单手动回写
- 选择模式详情浮层的 Tag 区末尾提供 `+` 按钮，点击后弹出 Tag 标签菜单
- 菜单顶部“现有标签”在多选时显示所选图片的公共标签，右侧 `x` 按钮可移除该标签
- 菜单输入框为空时，固定高度建议容器显示最近使用的 5 个标签（`last_used_at` 最新）
- 菜单输入框有内容时按 `name` 与 `display_name` 搜索，建议项显示 `display_name`
- 每条建议右侧提供 `+` 与笔形按钮：`+` 先写入当前弹层草稿，笔形按钮可打开标签元数据编辑弹窗
- “添加新标签”会先调用 `POST /api/tags/draft` 预占真实 `public_id`，再进入标签表单弹窗；取消时删除草稿，保存时通过 `PATCH /api/tags/{id}` 转正
- 标签表单弹窗支持 `name` 正则校验、`type` 下拉选择、Tag 预览、7 个预设配色，以及 HEX8 + HSV + 透明度取色器
- 菜单底部保留“添加新标签（预留）”入口，原“编辑标签”位置改为“自动标签”按钮
- “自动标签”在菜单内调用 `POST /api/images/tags/filename-match` 做预分析并合并到草稿，不会立即回写
- 菜单右下角提供“取消 / 确定”：
   - 取消或右上角关闭：丢弃草稿，不改动任何图片标签
   - 确定：对所有变更图片调用 `POST /api/images/tags/apply`（`merge_mode=replace`）一次性提交

### 4.5 管理与重建
- 交互按钮触发 `POST /api/admin/refresh`
- 后端返回 `{pruned, repaired, errors}`

## 5. 前端路由说明 (`router/index.js`)
- `/` -> `HomePage`
- `/gallery` -> `GalleryPage`（`meta.keepAlive = true`，保留导入页面实例）
- `/calendar` -> `CalendarOverview`
- `/calendar/:group` -> `BrowsePage`
- `/calendar/:group/:albumPath+` -> `BrowsePage`

* `App.vue` 会对声明 `meta.keepAlive` 的路由使用 `KeepAlive` 包裹；当前仅 `GalleryPage` 依赖该机制来保留导入状态

* 具体文件中有嵌套路由、组件复用与参数处理

## 6. 构建与运行
### 6.1 安装依赖
```
cd frontend
npm install
```

### 6.2 开发模式
```
npm run serve
```
默认访问：http://localhost:8080

### 6.3 生产打包
```
npm run build
```
打包输出：`dist/`

### 6.4 Lint
```
npm run lint
```

## 7. 关键配置
- `vue.config.js`：如需代理后端 API (CORS)，可配置 `devServer.proxy` 指向 `http://localhost:8000`
- `tailwind.config.js`：Tailwind 主题/路径

## 8. 常见问题与排查
1. 页面白屏或组件样式异常
   - 检查 `npm install` 是否成功，依赖缺失（如 `vue`, `vue-router`, `tailwindcss`）
   - 检查浏览器控制台 JS 错误
2. API 请求失败（跨域/404）
   - 确认后端 `uvicorn` 运行并端口正确
   - 检查 `vue.config.js` 代理是否配置 `\"/api\"` 到 `http://localhost:8000`
3. 上传消耗时间过长、卡顿
   - 可能是本地资源读取或后端处理较多，建议分批次上传
   - 检查后端 `import_files` 进度与日志
4. 缩略图不显示
   - 确认后端 `POST /api/import` 成功返回
   - 缩略图 URL 形如 `/thumbnails/{hash}.jpg`
   - 确保 `backend/temp` 有该文件
5. 404 在 /calendar/{date_group} 或更深层相册路径
   - 确认日期组和相册路径在后端存在
   - 检查浏览页是否能正确解析 `album_path`

## 9. 补充说明
- 前端对后端 API 的依赖关系：
   - `/api/dates` 用于年月树
   - `/api/dates/{date_group}/items` 用于日历内容
   - `/api/albums/by-path/{album_path:path}` 用于物理路径相册详情
   - `/api/images/count` 可用于统计呈现
   - `/api/images/tags/filename-match` 用于文件名分析并回写图片标签
   - `/api/images/tags/apply` 用于标签菜单手动批量添加/移除标签
   - `/api/tags?sort_by=last_used_desc&limit=5` 用于输入为空时加载最近使用标签
   - `/api/system/page-config` 用于读取/保存滚动浏览与分页浏览模式
   - `/api/system/tag-match-setting` 用于读取/保存文件名匹配过滤配置
- `ThumbCard` 负责显示缩略图，统一尺寸对齐
- `Sidebar` 负责导航历史分组与用户操作按钮

---
