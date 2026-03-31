# 软件杯服务器部署 Runbook

本文档面向“已经有一台 Linux 服务器，需要反复更新代码并稳定把前后端跑起来”的场景。

目标不是解释架构，而是提供一套**每次上线都能重复执行**的命令顺序，降低“前端没数据、后端 500、迁移漏跑、环境变量没生效”这类问题的概率。

## 1. 适用范围

- 操作系统：Ubuntu 22.04 或兼容 Linux
- 后端：FastAPI + Uvicorn
- 前端：Next.js 正式工作台
- 数据库：SQLite 单机演示或 PostgreSQL
- 部署方式：源码目录部署

## 2. 统一约定

下面命令默认采用以下目录和端口约定：

```bash
PROJECT_DIR=/root/dachuang_project
BACKEND_VENV=$PROJECT_DIR/venv
BACKEND_PORT=8000
FRONTEND_PORT=3000
```

如果你的实际目录不同，请先替换为自己的路径，再执行后续命令。

## 3. 首次部署

### 3.1 安装系统依赖

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git nodejs npm
```

### 3.2 获取代码

```bash
git clone <your-repo-url> $PROJECT_DIR
cd $PROJECT_DIR
```

### 3.3 创建后端虚拟环境并安装依赖

```bash
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
```

### 3.4 安装前端依赖

```bash
cd $PROJECT_DIR/front-end
npm install
cd $PROJECT_DIR
```

### 3.5 配置环境变量

后端：

```bash
cp .env.example .env
```

至少确认：

```env
DATABASE_URL=sqlite+aiosqlite:///./sensor_data.db
DEBUG=false
DEEPSEEK_API_KEY=your_key
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
```

前端：

```bash
cat > front-end/.env.local <<'EOF'
NEXT_PUBLIC_API_BASE_URL=http://<server-ip>:8000
EOF
```

说明：

- 这里的 `<server-ip>` 必须替换成浏览器实际能访问到的后端地址。
- 如果你后续改了 `NEXT_PUBLIC_API_BASE_URL`，必须重新执行 `npm run build`，只重启前端进程不够。

### 3.6 初始化数据库

```bash
cd $PROJECT_DIR
./venv/bin/python scripts/init_db.py --init-only
```

说明：

- 这一步会执行 `alembic upgrade head`。
- 以后每次更新代码，只要后端模型或 Alembic 有变更，都要重新执行一次。

### 3.7 构建前端

```bash
cd $PROJECT_DIR/front-end
npm run build
cd $PROJECT_DIR
```

## 4. 启动方式

### 4.1 最小启动方式

后端：

```bash
cd $PROJECT_DIR
./venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT
```

前端：

```bash
cd $PROJECT_DIR/front-end
npm run start -- --hostname 0.0.0.0 --port $FRONTEND_PORT
```

这种方式适合首次联调，不适合长期托管。

### 4.2 推荐方式：systemd 托管后端

后端 service 示例见：

- [fault-detection.service.example](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/deploy/systemd/fault-detection.service.example)

如果你已经配置了 systemd，后端启动与重启统一使用：

```bash
sudo systemctl restart fault-detection
sudo systemctl status fault-detection --no-pager
```

前端如果没有 systemd，可以先用单独终端、`screen` 或 `tmux` 托管。

## 5. 标准更新流程

每次服务器代码更新后，严格按下面顺序执行。

### 5.1 进入项目目录并同步代码

```bash
cd $PROJECT_DIR
```

如果用 Git：

```bash
git pull --rebase origin main
```

如果服务器网络不稳定，可以采用本地打包上传方式。

### 5.2 更新后端依赖

```bash
cd $PROJECT_DIR
./venv/bin/pip install -r requirements.txt
```

### 5.3 执行数据库迁移

```bash
cd $PROJECT_DIR
./venv/bin/python scripts/init_db.py --init-only
```

这是必须步骤。不要跳过。

### 5.4 重新构建前端

```bash
cd $PROJECT_DIR/front-end
npm install
npm run build
cd $PROJECT_DIR
```

出现以下任一情况时，前端必须重新 build：

- 前端页面代码有改动
- `front-end/.env.local` 有改动
- 任何 `NEXT_PUBLIC_*` 环境变量有改动

### 5.5 重启服务

如果后端用 systemd：

```bash
sudo systemctl restart fault-detection
sudo systemctl status fault-detection --no-pager
```

如果前端是手动启动，请停止旧进程后重新执行：

```bash
cd $PROJECT_DIR/front-end
npm run start -- --hostname 0.0.0.0 --port $FRONTEND_PORT
```

## 6. 每次上线后的强制验证

### 6.1 后端验证

```bash
curl http://127.0.0.1:$BACKEND_PORT/health
curl http://127.0.0.1:$BACKEND_PORT/api/v1/workbench/overview
```

要求：

- `/health` 返回正常
- `/api/v1/workbench/overview` 不能返回 500

### 6.2 前端验证

```bash
curl -I http://127.0.0.1:$FRONTEND_PORT
```

然后在浏览器中访问：

- `http://<server-ip>:3000/`
- `http://<server-ip>:3000/agents`
- `http://<server-ip>:3000/tasks`
- `http://<server-ip>:3000/cases`

### 6.3 主链路冒烟

每次上线后至少走一遍：

1. 打开 `/agents`
2. 触发一次 Agent 协作
3. 创建正式任务
4. 进入 `/tasks/[id]`
5. 打开 `/tasks/[id]/export`
6. 沉淀案例
7. 进入 `/cases/[id]`
8. 回看知识来源

## 7. 常见故障排查

### 7.1 前端页面打开了，但没有数据

先不要怀疑前端页面，先在服务器执行：

```bash
curl http://127.0.0.1:$BACKEND_PORT/api/v1/workbench/overview
```

如果这里都失败，问题在后端或数据库，不在前端。

再检查：

- `front-end/.env.local` 中的 `NEXT_PUBLIC_API_BASE_URL` 是否正确
- 改完前端环境变量后是否重新执行了 `npm run build`
- 浏览器是否通过 `https://` 打开页面，但前端请求仍然是 `http://`

### 7.2 `/api/v1/workbench/overview` 返回 500

这是当前最常见的部署故障。

优先检查：

```bash
cd $PROJECT_DIR
./venv/bin/python scripts/init_db.py --init-only
```

通常是**新代码已部署，但 Alembic 迁移没跑**，导致数据库缺少新列。

### 7.3 `ModuleNotFoundError`

如果看到类似：

- `No module named 'pandas'`
- `No module named 'aiosqlite'`
- `No module named 'asyncpg'`

基本说明你用错了 Python 环境。优先改用：

```bash
./venv/bin/python ...
./venv/bin/pip ...
```

不要混用系统 `python3` 和项目虚拟环境。

### 7.4 前端环境变量改了但没生效

Next.js 的 `NEXT_PUBLIC_*` 是**构建时注入**，不是运行时动态读取。

所以必须执行：

```bash
cd $PROJECT_DIR/front-end
npm run build
```

然后再重启前端进程。

### 7.5 浏览器报 Mixed Content 或跨域失败

如果前端是 `https://` 打开的，而 `NEXT_PUBLIC_API_BASE_URL` 还是 `http://...:8000`，浏览器会直接拦截。

更稳的做法是：

- 使用 Nginx 做同源反代
- 让前端访问 `/api/...`
- 不让浏览器直接访问 `:8000`

## 8. 回滚建议

上线前建议至少备份以下内容：

```bash
mkdir -p $PROJECT_DIR/backups
cp $PROJECT_DIR/.env $PROJECT_DIR/backups/.env.$(date +%F-%H%M%S)
cp $PROJECT_DIR/front-end/.env.local $PROJECT_DIR/backups/.env.local.$(date +%F-%H%M%S)
```

如果使用 SQLite，再备份数据库：

```bash
cp $PROJECT_DIR/sensor_data.db $PROJECT_DIR/backups/sensor_data.db.$(date +%F-%H%M%S)
```

## 9. 最终执行清单

每次服务器部署或更新，只按下面顺序执行：

```bash
cd $PROJECT_DIR
./venv/bin/pip install -r requirements.txt
./venv/bin/python scripts/init_db.py --init-only
cd front-end && npm install && npm run build && cd ..
sudo systemctl restart fault-detection
curl http://127.0.0.1:$BACKEND_PORT/health
curl http://127.0.0.1:$BACKEND_PORT/api/v1/workbench/overview
```

然后再做浏览器主链路冒烟。
