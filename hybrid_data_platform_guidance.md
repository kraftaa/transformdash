# Hybrid Data Transformation & Dashboard Platform  
## Project Guidelines

### 1. Core Architecture  
- Modular layers:  
  - Extraction/Load (multi-source, including non-SQL)  
  - Transformation (dbt-like DAG, supports SQL/Python/Spark)  
  - Visualization (integrated interactive dashboards)

### 2. Metadata & Configuration  
- YAML/JSON configs  
- Declare data sources and targets per task  
- Allow model language selection: SQL, Python, Pandas/Spark  
- Track lineage, run history, and cache state

### 3. Engine & Execution  
- Asynchronous DAG scheduler (Celery, Prefect)  
- Worker threads for parallel, cross-db execution  
- Support for in-memory staging with DuckDB or Arrow

### 4. UI & Visualization  
- Web UI for lineage graphs and data preview  
- Direct dashboard builder connected to staged data  
- Metadata tagging, quality scoring, and filtering

### 5. Extensibility  
- Connector plugins for new sources/destinations  
- Transformation modules: SQL and Python  
- Dashboard APIs: embed charts, export results

### 6. Suggested Stack  
| Layer           | Technologies                    |
|-----------------|--------------------------------|
| Connectors      | Airbyte, Singer                |
| Engine          | Python/Rust, FastAPI, Arrow    |
| Transformation  | SQL parser, Pandas, PySpark    |
| Metadata        | PostgreSQL, DuckDB             |
| Orchestration   | Prefect, Dagster               |
| UI/Dashboard    | React, Superset, Dash          |

### 7. Roadmap Enhancements  
- Change Data Capture (CDC) support  
- Data observability and profiling tools  
- Visual workflow editor for no/low-code users
