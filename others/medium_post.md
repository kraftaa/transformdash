# Building a Lightweight dbt Alternative: Lessons from TransformDash

*A technical deep-dive into building a data transformation platform that works with existing databases*

---

Over the past few months, I've been building TransformDash - an open-source data transformation platform. After working with dbt, Airflow, Airbyte, Superset, and Tableau, and building/running custom Rust transformations in Kubernetes via CronJobs, I wanted a single tool that combines transformation, orchestration, and visualization. I'm sharing this because the technical challenges were interesting, and maybe the lessons will be useful to others building data tools.

## The Original Problem

The data engineering workflow I kept encountering looked like this: data lives in PostgreSQL (or sometimes MongoDB), and I need to write transformations. The standard answer is "use dbt," which is great, but dbt assumes you're loading data into a warehouse like Snowflake or BigQuery.

What if you just want to transform data where it already lives? What if you're prototyping and don't want to set up a whole warehouse? What if your dataset is 100GB, not 100TB, and a full warehouse is overkill?

I couldn't find a tool that gave me dbt's developer experience (SQL with Jinja, dependency management, incremental models) but worked with my existing database infrastructure.

So I built one.

## Architecture Decisions

### Why Not Just Use dbt?

I actually tried. dbt can technically work with PostgreSQL, but the model is "extract from source, transform in warehouse." The warehouse is a first-class concept. You can't just point dbt at your prod database and say "transform data here."

More importantly, dbt's execution model assumes you're in an environment where queries are cheap and parallelizable (a modern warehouse). Running dozens of CREATE TABLE statements against a transactional PostgreSQL database is different - you need to be more careful about locking and resource usage.

### Core Design Choices

**1. FastAPI Backend**

I went with FastAPI because:
- Native async support for parallel query execution
- Automatic OpenAPI documentation
- Fast development cycle with hot reload
- Type hints everywhere (helps catch bugs early)

The async part turned out to be important. When executing a DAG of transformations, you can run independent branches in parallel. With traditional synchronous Python, you'd need threading or multiprocessing, which gets messy.

**2. No Frontend Framework**

Controversial choice: I wrote the frontend in vanilla JavaScript. No React, no Vue, no build tooling.

Why? This is a developer tool, not a consumer app. The UI needs to be functional, not fancy. Adding a framework means:
- Build pipeline complexity
- Dependency management
- Learning curve for contributors
- Slower development for simple features

For a dashboard with forms and charts, vanilla JS with Chart.js is plenty. The entire frontend is about 2000 lines. A React version would probably be similar size but with 100MB of node_modules.

**3. Embedded Metadata**

One subtle decision: where to store metadata about model runs, incremental state, etc.

dbt uses files (YAML + JSON). Modern tools use dedicated metadata databases. I went with a PostgreSQL table in the same database as the transformations.

Tradeoffs:
- Simpler deployment (one database, not two)
- Easier to query metadata with SQL
- But couples the tool to PostgreSQL
- And pollutes the namespace with metadata tables

For my use case, it was the right call.

## Technical Challenges

### 1. Safe SQL Composition

The biggest security concern was SQL injection. When you're building queries programmatically with user-provided table names, column names, and SQL snippets, you need to be very careful.

Python's f-strings make it tempting to do this:

```python
# DON'T DO THIS
query = f"SELECT {column} FROM {table}"
```

But `column` or `table` could be "; DROP TABLE users; --"

The solution is psycopg2's SQL composition tools:

```python
from psycopg2 import sql

query = sql.SQL("SELECT {column} FROM {table}").format(
    column=sql.Identifier(column_name),
    table=sql.Identifier(table_name)
)
```

This properly escapes identifiers. Combined with parameterized queries for values, it's safe.

But there's a catch: you still need to validate identifiers match regex `^[a-zA-Z_][a-zA-Z0-9_]*$` because even `sql.Identifier()` can't protect against all attacks if you allow arbitrary strings.

I ended up writing validation functions that get called everywhere SQL is constructed. It's tedious but necessary.

### 2. Dependency Resolution

The core feature of dbt is "write SQL with `{{ ref() }}` macros and we'll figure out the execution order." This is a DAG resolution problem.

My implementation:

```python
def build_dag(self, models):
    graph = {}
    for model in models:
        deps = self.extract_dependencies(model.sql)
        graph[model.name] = deps

    return self.topological_sort(graph)
```

The interesting part is `extract_dependencies`. I parse Jinja templates looking for `{{ ref('model_name') }}` patterns using regex. It's not as robust as a proper Jinja parser, but it works for 95% of cases.

Topological sort is textbook Kahn's algorithm. The tricky bit is handling cycles gracefully - instead of crashing, I detect them and give a helpful error message with the cycle path.

### 3. Incremental Models

This is proving harder than I expected and isn't fully implemented yet. The dbt model is:

```sql
{{ config(materialized='incremental') }}

SELECT * FROM source_table
{% if is_incremental() %}
WHERE updated_at > (SELECT MAX(updated_at) FROM {{ this }})
{% endif %}
```

Currently, the system accepts this syntax and renders the template, but `is_incremental()` always returns `False`, so it does full refreshes (DROP/CREATE) every time.

To make true incremental work, I need to:
1. Track whether the target table exists and has data
2. If it does, inject `is_incremental() = True` into the Jinja context
3. Replace `{{ this }}` with the actual table name (this part works)
4. Execute the query as INSERT INTO ... SELECT, not DROP and CREATE TABLE (this is the missing piece)
5. Store metadata about runs (last_run_time, max_id, row_count) for state tracking

The state tracking and INSERT logic are on my roadmap. For now, you can write incremental models using dbt syntax, but they behave like regular tables.

Edge cases I need to handle:
- What if someone manually drops the incremental table?
- What if the source schema changes?
- What if two processes try to update the same incremental model?
- How to handle deduplication with unique_key?

### 4. Authentication & Authorization

I needed user management with role-based access control. The standard pattern:

- JWT tokens for stateless auth
- bcrypt for password hashing (with proper salting)
- HTTP-only cookies to prevent XSS token theft
- Permission checks on every API endpoint

One interesting decision: I used FastAPI's dependency injection for permissions:

```python
@app.post("/api/models/execute")
async def execute_model(
    model_name: str,
    user: dict = Depends(require_permission('models', 'execute'))
):
    # user is only set if permission check passes
    ...
```

This is cleaner than decorators or manual checks in each function. The dependency system handles it automatically.

### 5. Rate Limiting

To prevent brute-force attacks on login and DoS on expensive queries, I implemented rate limiting using a token bucket algorithm.

The simple version:

```python
class RateLimiter:
    def __init__(self):
        self.requests = {}  # {ip: {endpoint: (count, window_start)}}

    def is_limited(self, ip, endpoint, max_requests, window_seconds):
        if ip not in self.requests:
            self.requests[ip] = {}

        if endpoint not in self.requests[ip]:
            self.requests[ip][endpoint] = (1, time.time())
            return False

        count, window_start = self.requests[ip][endpoint]

        if time.time() - window_start > window_seconds:
            self.requests[ip][endpoint] = (1, time.time())
            return False

        if count >= max_requests:
            return True

        self.requests[ip][endpoint] = (count + 1, window_start)
        return False
```

This works for single-server deployments. For distributed systems, you'd need Redis.

## Performance Considerations

### Query Execution

For parallel execution, I use Python's asyncio with connection pooling:

```python
async def execute_models(models):
    async with create_pool() as pool:
        tasks = []
        for model in models:
            if model.dependencies_met():
                task = asyncio.create_task(execute_model(model, pool))
                tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)
```

This lets independent models run concurrently while respecting dependencies.

### Incremental Performance

Incremental models can be much faster than full refreshes, but only if you index properly. I automatically add indexes on columns used in incremental conditions:

```python
if model.is_incremental and model.incremental_column:
    cursor.execute(sql.SQL(
        "CREATE INDEX IF NOT EXISTS {idx} ON {table} ({column})"
    ).format(
        idx=sql.Identifier(f"idx_{table}_{column}"),
        table=sql.Identifier(table),
        column=sql.Identifier(column)
    ))
```

## Deployment

I provide three deployment options:

1. **Docker Compose** - For local development
2. **Kubernetes** - For production (with TLS, secrets, scaling)
3. **Pip install** - For integration into existing Python projects

The Docker setup was interesting because I needed to:
- Run the app as a non-root user (security)
- Initialize the database schema on first startup
- Handle environment variable substitution in config files
- Set up TLS certificates with cert-manager for Kubernetes

## What I'd Do Differently

**Testing**: I should have written more tests earlier. I have some integration tests now, but unit test coverage is spotty. Testing SQL generation is hard because you need a real database, but it's worth it.

**Type System**: FastAPI's Pydantic models are great, but I should have been more strict with types throughout. There are too many `dict` and `Any` types where specific models would be better.

**Configuration**: The mix of environment variables, YAML files, and Python config is confusing. Should have picked one system and stuck with it.

**Error Messages**: Still not good enough. When a model fails to execute, the error should tell you exactly what went wrong and how to fix it. Right now it often just says "SQL error."

## Lessons Learned

**1. Security is Hard**

Even with all the SQL composition tools and validation, I found security issues during code review. It takes constant vigilance. Every user input is a potential attack vector.

**2. Documentation is Harder Than Code**

I spent about 30% of total project time on documentation. Writing docs that help people actually get started is much harder than writing code that works.

**3. Deployment Complexity Adds Up**

Supporting multiple deployment methods (Docker, Kubernetes, pip) means maintaining multiple configuration systems. It's worth it for adoption, but it's a lot of work.

**4. Developer Experience Matters**

Small touches like helpful error messages, sensible defaults, and clear configuration make a huge difference. I tried to make it so you can go from git clone to running queries in under 10 minutes.

## Current State & Future

The project is functional and I'm using it for several projects. It's open-source on GitHub: https://github.com/kraftaa/transformdash

Things that work well:
- Model execution with dependency resolution
- Views and tables with automatic creation
- Dashboard creation and visualization
- User authentication with RBAC
- Docker and Kubernetes deployment

Things that need work:
- True incremental model support (currently does full refreshes)
- Testing framework for model validation
- Better error messages
- Performance optimization for large datasets
- Support for more databases (ClickHouse, MySQL)
- Scheduling and orchestration

I'm not trying to compete with dbt or replace it. This is for a specific niche: people who want dbt-style transformations but are working with existing databases and don't need a full warehouse setup.

I'm primarily building this for my own use cases, but I want it to be genuinely useful for others. If you try it and have feature requests, I'd be happy to prioritize things that help real users.

If you're building data tools, here's my advice:

1. Start with a clear use case and build for that
2. Don't try to be everything to everyone
3. Security can't be an afterthought
4. Documentation is product, not afterthought
5. Deploy early to find real-world issues

## Try It Out

If this sounds interesting, try it out:

```bash
git clone https://github.com/kraftaa/transformdash.git
cd transformdash

# Generate JWT secret and start
python -c 'import secrets; print(secrets.token_urlsafe(32))' > jwt_key.txt
export JWT_SECRET_KEY=$(cat jwt_key.txt)
docker-compose up -d
```

Visit http://localhost:8000 (default login: admin/admin). Docker Compose will start PostgreSQL and the app automatically. From there you can connect databases, write models, and create dashboards.

I'm interested in feedback, especially from people working with data transformation pipelines. What features would make this more useful? What pain points does it miss?

Issues and PRs welcome: https://github.com/kraftaa/transformdash/issues

---

*Maria builds open-source data tools. Find her work at [github.com/kraftaa](https://github.com/kraftaa)*
