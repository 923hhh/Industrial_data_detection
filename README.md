# 工业故障检测系统

基于 FastAPI、LangGraph 和工业传感器数据的故障诊断后端项目，支持同步诊断、SSE 流式诊断和简单的浏览器调试页联调。

当前定位是比赛/MVP 级交付：重点保证主链路可演示、可部署、可复现、可验证，而不是追求商用生产级复杂能力。

## 当前能力

- `POST /api/v1/diagnose`：返回完整诊断报告
- `GET /api/v1/diagnose/stream`：通过 SSE 返回节点进度和最终报告
- `GET /health`：检查服务和数据库连通性
- `index.html`：静态调试页，支持自定义后端地址、基础输入校验和错误提示
- Alembic 管理数据库 schema，不再依赖隐式建表
- 当前测试结果：`19 passed, 4 skipped`

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

建议使用项目内 `venv` 或你自己的独立虚拟环境，避免系统 Python 缺失 `aiosqlite`。

### 2. 配置环境变量

仓库提供了 [`.env.example`](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/.env.example) 作为模板。

至少需要确认：

```env
DATABASE_URL=sqlite+aiosqlite:///./sensor_data.db
DEEPSEEK_API_KEY=sk-xxxxx
DEEPSEEK_API_BASE=https://api.deepseek.com
OPENAI_API_KEY=sk-xxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxx
DEBUG=false
```

本地真实密钥只保存在 `.env`，不要提交到仓库。

### 3. 初始化数据库

```bash
python scripts/init_db.py --init-only
```

该命令会执行 `alembic upgrade head`，确保数据库结构与迁移脚本一致。

如需导入样例数据：

```bash
python scripts/init_db.py --csv-path datasets/haiend-23.05/end-test1.csv
```

### 4. 启动后端

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后可访问：

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/health`

### 5. 打开前端调试页

直接用浏览器打开 [index.html](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/index.html)。

建议先确认页面中的“后端地址”与实际启动地址一致，再发起诊断。

## 演示流程

推荐按以下顺序演示：

1. 启动后端服务
2. 访问 `/health`
3. 打开 `index.html`
4. 填写时间范围和模型
5. 发起一次流式诊断，观察 `connected -> node_start -> node_finish -> report -> done`
6. 如需展示接口文档，再打开 `/docs`

更细的手工联调清单见 [docs/DEMO_CHECKLIST.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/docs/DEMO_CHECKLIST.md)。

## 部署

比赛/MVP 阶段建议先保证“新机器按文档就能跑起来”。

- 后端容器镜像：见 [Dockerfile](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/Dockerfile)
- 数据库容器：见 [docker-compose.yml](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/docker-compose.yml)
- 最小部署说明：见 [docs/DEPLOYMENT.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/docs/DEPLOYMENT.md)
- Linux systemd 样例：见 [deploy/systemd/fault-detection.service.example](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/deploy/systemd/fault-detection.service.example)

## 自动化验证

仓库新增了 GitHub Actions workflow：

- [`.github/workflows/ci.yml`](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/.github/workflows/ci.yml)

默认在 `push` 和 `pull_request` 时执行：

```bash
pytest -q
```

## 项目结构

```text
app/                    FastAPI 应用、路由、服务、智能体
alembic/                Alembic 迁移环境与版本脚本
scripts/                初始化数据库和导入数据脚本
tests/                  异步接口、流式链路和回归测试
index.html              静态调试页
docs/                   MVP 级部署和演示文档
deploy/systemd/         Linux 部署示例
```

## 当前还没做的事

以下内容在比赛/MVP 阶段通常应继续推进：

- 真实浏览器联调验收
- 云服务器部署验证
- CI 实际接入 GitHub 仓库并跑通
- 更系统的日志、监控和告警
- 如有需要，再补 Nginx、HTTPS、鉴权、权限控制
