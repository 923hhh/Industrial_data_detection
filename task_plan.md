# Task Plan: Industrial Fault Detection FastAPI Backend

## Project Overview
Design a scalable FastAPI backend for industrial fault detection, supporting future LangChain agents and PostgreSQL.

## HAI Dataset Analysis
- **Structure**: Wide table with ~170 sensor columns per timestamp
- **Timestamp**: datetime, 1-second resolution
- **Sensor types**: Binary (0/1), integers, floats
- **No explicit anomaly label column** in sample

## Storage Strategy Decision
**Chosen: Hybrid Approach (Wide Table + JSONB)**
- Core indexed fields as explicit columns (timestamp, key sensors)
- Extended sensor data as JSONB for flexibility
- Rationale: Query performance + schema flexibility balance

## Phases

### Phase 1: Project Structure
- [x] Create directory structure
- [x] Define core modules: routers, models, schemas, services, agents, core

### Phase 2: Database Layer
- [x] Create `app/core/config.py` - Configuration management
- [x] Create `app/core/database.py` - Async SQLAlchemy 2.0 engine
- [x] Implement SQLite/PostgreSQL compatibility
- [x] Create `app/models/__init__.py` and `app/models/sensor_data.py`

### Phase 3: Pydantic Schemas
- [x] Create `app/schemas/sensor_data.py` - Request/Response models

### Phase 4: API Routes
- [x] Create `app/routers/health.py` - Health check endpoint

### Phase 5: Application Entry
- [x] Create `app/main.py` - FastAPI application factory

### Phase 6: Testing
- [x] Verify application starts
- [x] Verify /health endpoint works

## Directory Structure
```
app/
├── __init__.py
├── main.py
├── agents/           # Future LangChain agent modules
│   └── __init__.py
├── core/             # Configuration & database
│   ├── __init__.py
│   ├── config.py
│   └── database.py
├── models/           # SQLAlchemy ORM models
│   ├── __init__.py
│   └── sensor_data.py
├── routers/          # API route handlers
│   ├── __init__.py
│   └── health.py
├── schemas/          # Pydantic V2 models
│   ├── __init__.py
│   └── sensor_data.py
└── services/         # Business logic layer
    ├── __init__.py
    └── sensor_service.py
tests/
├── __init__.py
└── test_health.py
scripts/
├── __init__.py
└── init_db.py
requirements.txt
```

## Key Design Decisions
1. **Async engine**: SQLAlchemy 2.0 AsyncEngine for FastAPI async support
2. **Hybrid storage**: Explicit columns + JSONB for sensor flexibility
3. **Repository pattern**: Services isolate DB logic for future agent integration

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| N/A | - | - |
