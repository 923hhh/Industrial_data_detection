# 软件杯评审版部署说明

## 1. 部署目标

本文档面向比赛评审与答辩准备，目标是让评委或指导老师能够按统一流程部署并运行当前系统。

## 2. 推荐部署方案

- 操作系统：Linux Ubuntu 22.04
- Python：3.11 或兼容版本
- 数据库：PostgreSQL
- 应用服务：FastAPI + Uvicorn
- 进程托管：systemd

## 3. 代码准备

```bash
git clone <repo-url> dachuang_project
cd dachuang_project
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 4. 配置环境变量

```bash
cp .env.example .env
```

核心配置示例：

```env
DATABASE_URL=postgresql+asyncpg://fault_user:your_password@127.0.0.1:5432/fault_detection
DEBUG=false
DEEPSEEK_API_KEY=your_key
DEEPSEEK_API_BASE=https://api.deepseek.com
```

## 5. 初始化数据库

```bash
python scripts/init_db.py --init-only
```

## 6. 导入知识库

### 6.1 导入 PDF 手册

```bash
python scripts/import_knowledge_pdf.py "摩托车发动机维修手册.pdf" --equipment-type "摩托车发动机"
```

### 6.2 导入固定评测种子

```bash
python scripts/run_softbei_eval.py
```

## 7. 启动后端

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

或使用 systemd：

```bash
systemctl restart fault-detection
systemctl status fault-detection
```

## 8. 验证项

- `GET /health` 返回正常
- `/docs` 可访问
- 正式工作台可打开
- 固定检索词至少抽查 3 组命中
- 至少 1 条完整任务链路可走通

## 9. 演示建议

- 正式入口使用 `softbei_workbench.html`
- 不以 `diagnosis_console.html` 作为主页面
- 优先用固定案例，不现场自由发挥

## 10. 说明

本评审版部署说明服务于软件杯材料提交，与仓库中的 [DEPLOYMENT.md](/e:/南京航空航天大学/aaa大创/智能体案例/dachuang_project/docs/DEPLOYMENT.md) 共同存在：

- `DEPLOYMENT.md`：偏 MVP/开发部署
- `SOFTBEI_COMPETITION_DEPLOYMENT.md`：偏评审/答辩交付
