# Project Context: Industrial Fault Detection Backend

## 1. Role & Objective
你现在是一位资深的 Python 后端架构师。我们正在开发一个用于工业故障检测的 FastAPI 后端系统，该系统未来需要支持 LangChain 多智能体接入，并具备从当前开发环境平滑迁移至生产环境的能力。

## 2. Technology Stack & Constraints
- **Framework**: Python 3.10+, FastAPI
- **ORM**: SQLAlchemy 2.0 (必须使用 2.0 风格的 API)
- **Validation**: Pydantic V2 (利用其原生异步支持)
- **Database**: 开发期使用 SQLite (`aiosqlite`)，生产期迁移至 PostgreSQL (`asyncpg`)。代码必须保证这两者的兼容性。

## 3. Key Architectural Decisions
- **Async Engine**: 必须使用 SQLAlchemy 2.0 的 AsyncEngine 以完美支持 FastAPI 的异步特性。
- **Hybrid Storage Strategy**: 针对 HAI 数据集（约 170 个传感器标签），采用混合存储策略。核心索引字段（如 `id`, `timestamp`, 关键传感器）作为独立列，其余扩展传感器数据打包存入 `extra_sensors` JSONB 字段。这兼顾了查询性能与 Schema 的灵活性。
- **Repository Pattern**: 服务层（Services）必须隔离数据库逻辑，为未来的 Agent 集成保持模块化纯洁度。

## 4. Current State & Progress
我们把开发分为 6 个 Phase。
- **已完成**: Phase 1 至 Phase 5 已全面竣工。底层 AsyncEngine、混合存储模型 (`models`)、Pydantic 验证体系 (`schemas`) 以及应用生命周期与 `/health` 路由全部测试通过，并成功启动。
- **当前进行中**: Phase 6 (Service Layer & Data Ingestion 核心服务与数据导入)。

## 5. Immediate Task Instructions (Next Steps)
请严格遵守我们的“Repository Pattern (仓储模式)”架构，确保路由层和数据访问层分离。协助我完成以下工作：

1. **编写核心业务逻辑 (`app/services/sensor_service.py`)**：
   - 编写异步函数 `create_sensor_data`，支持单条和批量写入。
   - 编写异步函数 `get_sensor_data_by_time_range`，支持按 `timestamp` 范围进行高效查询（未来将供 LangChain Tool 调用）。
   - 代码需注入 `AsyncSession`，并做好异常捕获与回滚。

2. **编写数据初始化脚本 (`scripts/init_db.py`)**：
   - 编写一个独立的 Python 脚本，使用 `pandas` 或内置 `csv` 模块读取 HAI 数据集文件（如 `end-test1.csv`）。
   - 将这约 170 列的宽表数据动态映射为我们设计的混合模型（匹配 60 个核心 `dm_` 等字段，其余塞入 `extra_sensors` JSON 字段）。
   - 使用 SQLAlchemy 2.0 的批量插入（如 `insert().values()` 或 `add_all()`）将数据高效灌入 SQLite 开发数据库。

**架构约束提醒**：在写 `init_db.py` 批量导入脚本时，必须考虑内存占用，建议采用分块读取（chunking）策略，避免一次性加载几十万行数据导致 OOM。
**禁止行为**：当前阶段请勿编写任何关于 LangChain Agent 或 API Router 的业务逻辑代码，保持绝对专注。

全程使用中文回答和思考，回答结束加上完成
所有注释也用中文