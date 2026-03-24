# Findings: HAI Dataset & Architecture Research

## HAI Dataset Structure (end-test1.csv)
- **Rows**: 1-second interval time series
- **Columns**: ~170 sensor tags
- **Tag naming convention**:
  - `DM-*`: Device measurement tags (DM-PP01-R, DM-FT01Z, etc.)
  - `NNNN.N-OUT`: Output signals from controller NNNN
  - `NNNN.N-OUT1/2`: Multi-channel outputs
- **Value types**:
  - Binary: 0/1 (valve states,开关 states)
  - Continuous: Floats (temperatures, pressures, flows)

## Storage Strategy Analysis

### Option A: Pure Wide Table
Each sensor tag as a dedicated column.
- ✅ Query performance: Excellent for single-sensor queries
- ✅ Data integrity: ORM field type checking
- ❌ Schema rigidity: Adding/removing sensors requires ALTER TABLE
- ❌ Migration complexity: 170+ columns hard to manage

### Option B: Pure JSON Packing
All sensor values in a single JSON/JSONB column.
- ✅ Schema flexibility: Add/remove sensors freely
- ❌ Query performance: Indexing individual JSON fields is complex
- ❌ Data integrity: No type checking on JSON contents

### Option C: Hybrid (Chosen)
- Core indexed fields: `id`, `timestamp`, primary sensor columns
- Extended data: `extra_sensors` JSONB for auxiliary tags
- ✅ Balances query performance and flexibility
- ✅ Allows PostgreSQL optimization while remaining SQLite-compatible

## Technology Decisions
- **SQLAlchemy 2.0**: Native async support, 2.0 style API
- **aiosqlite**: SQLite async driver for development
- **asyncpg**: PostgreSQL async driver for production
- **Pydantic V2**: Modern validation with native async support
