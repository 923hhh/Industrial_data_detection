# Front-end Workspace

当前目录已从占位符升级为正式前端工程骨架，目标是逐步替代根目录下的静态演示页。

## 技术栈

- `Next.js`
- `React`
- `TypeScript`

## 当前页面

- `/`：正式工作台首页
- `/knowledge`：知识检索中心
  - 当前已补齐 PDF 导入、文档列表和分段预览骨架
- `/tasks`：检修任务中心
- `/cases`：案例沉淀与审核中心
- `/history`：历史记录与导出入口
- `/agents`：Agent 协作过程面板

## 环境变量

新前端默认读取：

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

## 运行方式

```bash
npm install
npm run dev
```

生产部署最小命令：

```bash
npm install
npm run build
npm run start -- --hostname 0.0.0.0 --port 3000
```

## 说明

- 当前静态页面仍保留在仓库根目录，作为兼容和兜底演示入口。
- `NEXT_PUBLIC_API_BASE_URL` 变更后必须重新执行 `npm run build`，只重启 `npm run start` 不会生效。
- 新前端优先消费正式 API：
  - `/api/v1/workbench/overview`
  - `/api/v1/agents/assist`
  - `/api/v1/agents/runs/{id}`
  - `/api/v1/knowledge/imports`
  - `/api/v1/knowledge/imports/{id}`
  - `/api/v1/knowledge/documents`
  - `/api/v1/knowledge/documents/{id}/chunks`
  - `/api/v1/knowledge/search`
  - `/api/v1/tasks`
  - `/api/v1/cases`
