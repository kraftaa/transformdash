# Getting Started with TransformDash

This guide will help you get TransformDash running in under 10 minutes.

---

## Prerequisites

Before you begin, make sure you have:

- **Python 3.9+** installed (`python --version`)
- **PostgreSQL 15+** installed and running
- **Git** installed
- **Docker & Docker Compose** (optional, for easiest setup)

### Check Your Prerequisites

```bash
# Check Python version
python3 --version  # Should be 3.9 or higher

# Check PostgreSQL
psql --version     # Should be 15 or higher

# Check Docker (optional)
docker --version
docker-compose --version
```

---

## Quick Start (Docker - Recommended)

This is the fastest way to get started. Everything is automated.

### Step 1: Clone the Repository

```bash
git clone https://github.com/kraftaa/transformdash.git
cd transformdash
```

### Step 2: Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Generate a secure JWT secret key
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'

# Edit .env and paste the generated key
nano .env
# or
vim .env
# or open in your favorite editor
```

In your `.env` file, set:
```env
JWT_SECRET_KEY=<paste-your-generated-key-here>

# Optionally change database passwords (recommended for production)
POSTGRES_PASSWORD=your_secure_password
TRANSFORMDASH_PASSWORD=your_secure_password
APP_PASSWORD=your_secure_password
```

### Step 3: Start the Application

```bash
# Start all services in the background
docker-compose up -d

# Watch the logs (optional)
docker-compose logs -f transformdash
```

### Step 4: Access TransformDash

Open your browser and go to:
```
http://localhost:8000
```

**Default Login:**
- Username: `admin`
- Password: `admin`

**You're done!** Skip to the [First Steps](#first-steps) section.

---

## Local Installation (Without Docker)

If you prefer to run TransformDash directly on your machine:

### Step 1: Clone the Repository

```bash
git clone https://github.com/kraftaa/transformdash.git
cd transformdash
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows
```

### Step 3: Install Dependencies

```bash
# Install TransformDash with ML support
pip install -e ".[ml]"

# Verify installation
pip list | grep -i transformdash
```

### Step 4: Configure Environment

```bash
# Copy example config
cp .env.example .env

# Generate JWT secret key
python -c 'import secrets; print(secrets.token_urlsafe(32))'

# Edit .env and add the key
nano .env
```

In your `.env`, set:
```env
JWT_SECRET_KEY=<your-generated-key>
TRANSFORMDASH_HOST=localhost
TRANSFORMDASH_USER=postgres
TRANSFORMDASH_PASSWORD=your_postgres_password
```

### Step 5: Create Databases

```bash
# Create the TransformDash metadata database
createdb transformdash

# Create a database for your data (optional)
createdb production
```

### Step 6: Initialize Database Schema

```bash
# Run migrations
psql -d transformdash -f migrations/001_init.sql
psql -d transformdash -f migrations/002_auth.sql
# ... (run all migration files in order)

# Or use the init script (if available)
bash scripts/init_database.sh
```

### Step 7: Start the Application

```bash
# Run the app
python ui/app.py

# Or use the CLI command (if installed with pip)
transformdash
```

### Step 8: Access TransformDash

Open your browser:
```
http://localhost:8000
```

**Default Login:**
- Username: `admin`
- Password: `admin`

---

## First Steps

Now that TransformDash is running, here's what to do:

### 1. Change Your Password

```bash
# Log in as admin, then go to:
Settings > Users > Edit admin user > Change Password
```

### 2. Connect Your Data

TransformDash needs to connect to your data sources.

**Edit `connections.yml`:**
```yaml
connections:
  - id: my_analytics_db
    name: "My Analytics Database"
    host: localhost
    port: 5432
    database: my_database
    user: my_user
    password: my_password
    description: "My production analytics database"
```

**Or use environment variables in `.env`:**
```env
APP_HOST=my-analytics-server.com
APP_DB=analytics
APP_USER=readonly_user
APP_PASSWORD=secure_password
```

### 3. Define Your Data Sources

**Edit `models/sources.yml`:**
```yaml
version: 2
sources:
  - name: raw
    database: production  # Your database name
    schema: public        # Your schema name
    tables:
      - name: users
        description: "User accounts"
      - name: orders
        description: "Order transactions"
      - name: products
        description: "Product catalog"
```

### 4. Create Your First Transformation

**Create `models/bronze/stg_users.sql`:**
```sql
{{ config(
    materialized='view'
) }}

SELECT
    user_id,
    username,
    email,
    created_at,
    updated_at
FROM {{ source('raw', 'users') }}
WHERE deleted_at IS NULL
```

### 5. Run Your First Model

```bash
# In the UI, go to:
Models > Execute > Select "stg_users" > Run

# Or via CLI:
transformdash run --model stg_users
```

### 6. Create a Dashboard

```bash
# In the UI:
Dashboards > New Dashboard > Add Charts
```

---

## Troubleshooting

### Application Won't Start

**Error: "JWT_SECRET_KEY must be set"**
```bash
# Generate a new key
python -c 'import secrets; print(secrets.token_urlsafe(32))'

# Add to .env file
echo "JWT_SECRET_KEY=<your-key>" >> .env
```

**Error: "Connection refused" or "Database does not exist"**
```bash
# Check PostgreSQL is running
pg_isready

# Create database if missing
createdb transformdash

# Run migrations
psql -d transformdash -f migrations/001_init.sql
```

**Error: "Port 8000 already in use"**
```bash
# Find process using port 8000
lsof -i :8000

# Kill it
kill <PID>

# Or change port in ui/app.py
```

### Database Connection Issues

**Can't connect to PostgreSQL:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql  # Linux
brew services list                # macOS

# Check connection
psql -h localhost -U postgres -d transformdash

# Check .env settings match your PostgreSQL config
```

### Docker Issues

**Containers won't start:**
```bash
# Check Docker is running
docker ps

# View logs
docker-compose logs transformdash

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## Next Steps

- Read the [Full Documentation](README.md)
- Learn about [SQL Model Features](README.md#model-features)
- Explore [Dashboard Examples](DASHBOARDS_CREATED.md)
- Set up for [Production Deployment](DEPLOYMENT.md)

---

## Getting Help

- **Documentation**: [GitHub Wiki](https://github.com/kraftaa/transformdash/wiki)
- **Issues**: [Report a Bug](https://github.com/kraftaa/transformdash/issues)
- **Discussions**: [Ask Questions](https://github.com/kraftaa/transformdash/discussions)

---

## Common Configurations

### Using a Remote PostgreSQL Server

**In `.env`:**
```env
TRANSFORMDASH_HOST=my-postgres-server.com
TRANSFORMDASH_PORT=5432
TRANSFORMDASH_USER=transformdash_user
TRANSFORMDASH_PASSWORD=secure_password
```

### Using Multiple Data Sources

**In `connections.yml`:**
```yaml
connections:
  - id: sales_db
    host: sales-server.com
    database: sales
    user: readonly

  - id: marketing_db
    host: marketing-server.com
    database: marketing
    user: readonly
```

### Running on a Different Port

**In `ui/app.py`:**
```python
# Change this line at the bottom:
uvicorn.run(app, host="0.0.0.0", port=9000)  # Changed from 8000
```

---

## Security Checklist

Before deploying to production:

- [ ] Change default admin password
- [ ] Set strong JWT_SECRET_KEY
- [ ] Use strong database passwords
- [ ] Enable HTTPS/TLS
- [ ] Review user permissions
- [ ] Enable firewall rules
- [ ] Set up backup strategy
- [ ] Configure log rotation

See [DEPLOYMENT.md](DEPLOYMENT.md) for full production setup guide.
