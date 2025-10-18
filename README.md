# ✨ TransformDash

**Hybrid Data Transformation & Dashboard Platform**

A modern, dbt-inspired data transformation platform that combines the power of SQL transformations, Python extensibility, DAG-based orchestration, and interactive data lineage visualization.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 🌟 Features

### Core Capabilities
- **📊 Multi-Layer Architecture**: Bronze → Silver → Gold medallion pattern (like dbt)
- **🔗 SQL Transformations**: dbt-style SQL models with Jinja templating
- **🐍 Python Extensibility**: Custom transformations for ML and complex logic
- **🌊 DAG Orchestration**: Automatic dependency resolution and parallel execution
- **🎨 Interactive Web UI**: Real-time lineage graphs and dashboards
- **🔄 Incremental Processing**: Efficient updates with incremental materializations
- **💾 Multi-Database Support**: PostgreSQL, MongoDB, Redis connectors

### dbt-Compatible Features
- `{{ source() }}` and `{{ ref() }}` macros
- `{{ config() }}` for model configuration
- `{% if is_incremental() %}` conditional logic
- YAML-based source definitions
- View, table, and incremental materializations

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      TransformDash                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Raw Sources (PostgreSQL, MongoDB, Redis)                  │
│         ↓                                                   │
│  Bronze Layer (stg_* models - Views)                       │
│    • Direct extraction from raw tables                      │
│    • Column aliasing and standardization                    │
│         ↓                                                   │
│  Silver Layer (int_* models - Incremental)                 │
│    • Multi-table joins                                      │
│    • Business logic and calculations                        │
│    • Aggregations and window functions                      │
│         ↓                                                   │
│  Gold Layer (fct_*/dim_* models - Tables)                  │
│    • Analytics-ready fact and dimension tables              │
│    • Final business metrics                                 │
│         ↓                                                   │
│  Web Dashboard & API                                        │
│    • Interactive lineage visualization                      │
│    • Model catalog and documentation                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL (or your preferred database)
- Git

### Installation

**Option 1: Install via pip (Recommended)**
```bash
pip install transformdash

# Run the web UI
transformdash

# Or import as a library
python -c "from transformations import TransformationModel"
```

**Option 2: Docker (Production)**
```bash
# Using Docker Compose (includes PostgreSQL)
docker-compose up -d

# Access at http://localhost:8000
```

**Option 3: From Source (Development)**
```bash
# Clone the repository
git clone https://github.com/kraftaa/transformdash.git
cd transformdash

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in editable mode
pip install -e .
```

### Configuration

1. **Set up database credentials**:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

2. **Configure your data sources**:
```bash
cp models/sources.example.yml models/sources.yml
# Edit models/sources.yml to point to your tables
```

### Run Your First Transformation

```bash
# Test database connection
python postgres.py

# Run transformation pipeline
python demo_real_dbt_style.py

# Start web UI
python ui/app.py
# Visit http://localhost:8000
```

---

## 📁 Project Structure

```
transformdash/
├── connectors/              # Database connectors
│   ├── redis.py            # Redis connector
│   └── (mongodb, etc.)
├── models/                  # dbt-style transformation models
│   ├── sources.yml         # Data source definitions
│   ├── bronze/             # Staging layer (stg_*)
│   │   ├── stg_customers.sql
│   │   └── stg_orders.sql
│   ├── silver/             # Intermediate layer (int_*)
│   │   └── int_customer_orders.sql
│   └── gold/               # Analytics layer (fct_*, dim_*)
│       └── fct_orders.sql
├── transformations/         # Core transformation engine
│   ├── model.py            # Transformation model class
│   ├── dag.py              # DAG builder and validator
│   └── dbt_loader.py       # dbt-style model loader
├── orchestration/           # Execution engine
│   └── engine.py           # DAG orchestrator
├── ui/                      # Web interface
│   └── app.py              # FastAPI application
├── tests/                   # Test suite
├── config.py               # Environment configuration
├── postgres.py             # PostgreSQL connector
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

---

## 📝 Creating Models

### Bronze Layer (Staging)

**File**: `models/bronze/stg_customers.sql`

```sql
{{ config(materialized='view') }}

-- Bronze layer: Direct extraction with minimal transformation

with transformed_data as (
    select
        id as customer_id,
        email,
        name as customer_name,
        created_at
    from {{ source('raw', 'customers') }}
)

select * from transformed_data
```

### Silver Layer (Intermediate)

**File**: `models/silver/int_customer_orders.sql`

```sql
{{ config(
    materialized='incremental',
    unique_key='order_id'
) }}

-- Silver layer: Join customers with orders

with transformed_data as (
    select
        o.order_id,
        o.customer_id,
        c.customer_name,
        c.email as customer_email,
        o.order_date,
        o.total_amount
    from {{ ref('stg_orders') }} o
    join {{ ref('stg_customers') }} c
        on o.customer_id = c.customer_id

    {% if is_incremental() %}
        -- Only process new orders
        where o.order_date > (select max(order_date) from {{ this }})
    {% endif %}
)

select * from transformed_data
```

### Gold Layer (Analytics)

**File**: `models/gold/fct_orders.sql`

```sql
{{ config(materialized='table') }}

-- Gold layer: Final fact table

with transformed_data as (
    select
        order_id,
        customer_id,
        customer_name,
        order_date,
        total_amount,
        extract(year from order_date) as order_year,
        extract(month from order_date) as order_month
    from {{ ref('int_customer_orders') }}
)

select * from transformed_data
```

---

## 🎨 Web UI Features

### Dashboard
- **Model Catalog**: Browse all transformation models
- **Layer Statistics**: Bronze/Silver/Gold model counts
- **Real-time Updates**: Refresh models dynamically

### Lineage Graph
- **Interactive Visualization**: D3.js-powered lineage graphs
- **Dependency Tracking**: See how models depend on each other
- **Color-Coded Layers**: Bronze (🟫), Silver (⚪), Gold (🟡)

### API Endpoints
- `GET /`: Interactive dashboard
- `GET /api/models`: List all models with dependencies
- `GET /api/lineage`: Get DAG structure
- `GET /api/health`: Health check

---

## 🔧 Configuration

### Environment Variables (`.env`)

```bash
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=your_database
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password

# MongoDB (optional)
MONGO_URI=mongodb://localhost:27017
MONGO_DB=your_mongo_db

# Redis (optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### Sources Configuration (`models/sources.yml`)

```yaml
version: 2

sources:
  - name: raw
    description: "Your raw data source"
    database: your_database
    schema: public
    tables:
      - name: customers
        columns:
          - name: id
            tests:
              - not_null
              - unique
          - name: email
```

---

## 🧪 Testing

```bash
# Run unit tests
pytest tests/

# Test database connection
python postgres.py

# Test model loader
python transformations/dbt_loader.py

# Run example pipeline
python demo_real_dbt_style.py
```

---

## 🛠️ Development

### Adding a New Database Connector

1. Create connector class in `connectors/`:
```python
class MyDatabaseConnector:
    def __init__(self, connection_string):
        self.conn = ...

    def query_to_dataframe(self, query):
        return pd.read_sql(query, self.conn)
```

2. Add to `config.py`:
```python
MY_DB_URI = os.getenv('MY_DB_URI')
```

3. Use in transformations:
```python
from connectors.mydatabase import MyDatabaseConnector

def my_transformation(context):
    with MyDatabaseConnector() as db:
        return db.query_to_dataframe("SELECT * FROM table")
```

### Adding Custom Macros

Extend `DBTModelLoader` in `transformations/dbt_loader.py`:

```python
def my_custom_macro(self, arg1, arg2):
    return f"processed_{arg1}_{arg2}"

# Register in render_sql method
env.globals['my_macro'] = self.my_custom_macro
```

---

## 📊 Use Cases

### Data Warehousing
- Extract data from multiple sources
- Transform with SQL for performance
- Load into analytics-ready tables

### Business Intelligence
- Create conformed dimensions
- Build fact tables for metrics
- Serve dashboards and reports

### Data Engineering
- Orchestrate complex pipelines
- Track data lineage
- Incremental processing for efficiency

### Analytics Engineering
- dbt-style transformations
- Version-controlled SQL
- Collaborative data modeling

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- Inspired by [dbt (data build tool)](https://www.getdbt.com/)
- Built with [FastAPI](https://fastapi.tiangolo.com/), [Pandas](https://pandas.pydata.org/), and [D3.js](https://d3js.org/)
- Follows the [Medallion Architecture](https://www.databricks.com/glossary/medallion-architecture) pattern

---

## 📞 Support

- **Documentation**: [GitHub Wiki](https://github.com/kraftaa/transformdash/wiki)
- **Issues**: [GitHub Issues](https://github.com/kraftaa/transformdash/issues)
- **Discussions**: [GitHub Discussions](https://github.com/kraftaa/transformdash/discussions)

---

## 🗺️ Roadmap

- [ ] Add Spark connector for big data
- [ ] Implement data quality testing framework
- [ ] Add CI/CD pipeline templates
- [ ] Create VSCode extension
- [ ] Support for dbt packages
- [ ] Real-time data streaming
- [ ] Cloud deployment guides (AWS, GCP, Azure)
- [ ] Airflow/Prefect integration
- [ ] Metric computation layer
- [ ] Row-level security

---

<div align="center">

**Built with ❤️ for the data community**

[⭐ Star us on GitHub](https://github.com/kraftaa/transformdash)

</div>
