# picTagView Frontend 技术说明书

## 1. 项目位置
- `D:\project2025\Python_Projects\picTagView\frontend`

## 2. 技术栈
- Vue.js 2.x（Vue CLI 项目）
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
  - `components/`：通用组件
    - `LoadingSpinner.vue`
    - `Sidebar.vue`
    - `ThumbCard.vue`
  - `pages/`：路由页面
    - `HomePage.vue`
    - `GalleryPage.vue`
    - `DateViewPage.vue`
    - `EmptyPage.vue`

## 4. 主要功能说明
### 4.1 上传与导入
- 上线 `HomePage` 提供文件上传 UI
- 调用 `POST /api/import`
- 传递 `files` 与 `lastModifiedJson`
- 成功后刷新目录数据

### 4.2 按年月分组视图
- `DateViewPage` 获取 `GET /api/dates`
- 按 `year -> month` 做嵌套显示
- 点击月组进入 `GalleryPage`

### 4.3 展示图库内容
- `GalleryPage` 调用 `GET /api/dates/{date_group}/items`
- 直图显示 `ThumbCard`，子目录显示相册封面

### 4.4 管理与重建
- 交互按钮触发 `POST /api/admin/refresh`
- 后端返回 `{pruned, repaired, errors}`

## 5. 前端路由说明 (`router/index.js`)
- `/` -> `HomePage`
- `/gallery` -> `GalleryPage`（默认需选择日期组）
- `/dates` -> `DateViewPage`

\* 具体文件中有详细路由重定向与参数处理

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
5. 404 在 /gallery/{date_group}
   - 确认日期组存在后端数据
   - 在页面路由中选择查看具体 `date_group`

## 9. 补充说明
- 前端对后端 API 的依赖关系：
  - `/api/dates` 用于年月树
  - `/api/dates/{date_group}/items` 用于日历内容
  - `/api/images/count` 可用于统计呈现
- `ThumbCard` 负责显示缩略图，统一尺寸对齐
- `Sidebar` 负责导航历史分组与用户操作按钮

---
