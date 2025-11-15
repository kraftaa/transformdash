# TransformDash Quick Start Guide

Get up and running with TransformDash in 5 minutes!

## 🚀 Fastest Way to Start

### Option 1: Docker Compose (No Setup Required)

```bash
# 1. Clone and start
git clone https://github.com/kraftaa/transformdash.git
cd transformdash
docker-compose up -d

# 2. Access the application
open http://localhost:8000

# That's it! 🎉
```

**What you get:**
- ✅ TransformDash application running on port 8000
- ✅ PostgreSQL database with sample data
- ✅ All dependencies installed
- ✅ Ready to create dashboards and models

---

## 📦 Local Installation (For Development)

### Prerequisites
```bash
# Check your Python version (need 3.9+)
python --version

# Check PostgreSQL is installed
psql --version
```

### Installation Steps

```bash
# 1. Clone repository
git clone https://github.com/kraftaa/transformdash.git
cd transformdash

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install TransformDash with ML support
pip install -e ".[ml]"

# 4. Set up environment
cp .env.example .env
# Edit .env with your database credentials

# 5. Create databases
createdb transformdash
createdb production

# 6. Run the application
python ui/app_refactored.py
```

Access at: http://localhost:8000

---

## 🎯 First Steps After Installation

### 1. Explore the UI

Navigate through:
- **Overview** - See your data pipeline at a glance
- **Models** - View and run SQL transformations
- **Chart Builder** - Create visualizations
- **Dashboards** - Build interactive dashboards
- **Data Sources** - Configure database connections

### 2. Run Your First Model

```bash
# In the UI:
1. Go to "Models" tab
2. Click "▶️ Run Models"
3. Watch the transformation pipeline execute
```

### 3. Create Your First Chart

```bash
# In the UI:
1. Go to "Chart Builder"
2. Select a data source/model
3. Choose chart type (bar, line, pie, etc.)
4. Configure axes and aggregations
5. Click "Create Chart"
```

### 4. Build Your First Dashboard

```bash
# In the UI:
1. Go to "Dashboards"
2. Click "+ New Dashboard"
3. Drag and drop charts
4. Add filters and tabs
5. Save and share!
```

---

## 🤖 Train Your First ML Model

```bash
# Run the example model training script
python ml/examples/train_example_model.py

# View registered models
python ml/registry/model_registry.py

# Models can now be used in SQL transformations!
```

---

## 🔧 Configuration Guide

### Minimal `.env` Configuration

```env
# TransformDash Database (for metadata)
TRANSFORMDASH_HOST=localhost
TRANSFORMDASH_PORT=5432
TRANSFORMDASH_DB=transformdash
TRANSFORMDASH_USER=postgres
TRANSFORMDASH_PASSWORD=your_password

# Application Database (for your data)
APP_HOST=localhost
APP_PORT=5432
APP_DB=production
APP_USER=postgres
APP_PASSWORD=your_password
```

---

## 📚 Common Tasks

### Add a New SQL Model

```sql
-- Create: models/silver/my_new_model.sql
{{ config(
    materialization='table'
) }}

SELECT
    customer_id,
    COUNT(*) as order_count,
    SUM(amount) as total_spent
FROM {{ ref('stg_orders') }}
GROUP BY customer_id
```

### Query via API

```bash
# Get data from a model
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{
    "table": "my_model",
    "limit": 100
  }'
```

### Schedule Model Runs

```python
# Add to scheduler (UI coming soon)
from scheduler import scheduler

scheduler.add_model_schedule(
    model_name='my_model',
    cron='0 9 * * *'  # Every day at 9 AM
)
```

---

## 🐳 Docker Commands Quick Reference

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f transformdash

# Stop services
docker-compose down

# Restart a service
docker-compose restart transformdash

# Rebuild after code changes
docker-compose up -d --build

# Start with pgAdmin for database management
docker-compose --profile tools up -d
# Access pgAdmin at http://localhost:5050
```

---

## ☸️ Kubernetes Quick Deploy

```bash
# Deploy to Kubernetes
kubectl apply -f k8s/

# Check status
kubectl get pods -n transformdash

# Access application
kubectl port-forward svc/transformdash-service 8000:8000 -n transformdash

# View logs
kubectl logs -f deployment/transformdash -n transformdash
```

---

## 📖 API Documentation

Access interactive API docs at:
```
http://localhost:8000/docs
```

Key endpoints:
- `GET /` - Dashboard home
- `POST /api/models/execute` - Run transformations
- `POST /api/query` - Query data
- `GET /api/charts` - List charts
- `GET /api/dashboards` - List dashboards
- `GET /api/ml/models` - List ML models
- `POST /api/ml/predict` - Make predictions

---

## 🆘 Troubleshooting

### Application won't start

```bash
# Check if port 8000 is already in use
lsof -ti:8000

# Kill existing process
lsof -ti:8000 | xargs kill -9

# Check database connection
psql -h localhost -U postgres -d transformdash
```

### Database connection errors

```bash
# Verify PostgreSQL is running
pg_isready

# Check credentials in .env file
cat .env

# Test connection manually
psql -h $TRANSFORMDASH_HOST -U $TRANSFORMDASH_USER -d $TRANSFORMDASH_DB
```

### Docker issues

```bash
# View container logs
docker-compose logs transformdash

# Check container status
docker-compose ps

# Restart everything
docker-compose down && docker-compose up -d

# Remove volumes and restart (WARNING: deletes data)
docker-compose down -v && docker-compose up -d
```

### Python/pip issues

```bash
# Verify Python version
python --version  # Should be 3.9+

# Reinstall in virtual environment
deactivate
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -e ".[ml]"
```

---

## 📚 Next Steps

Once you're up and running:

1. **Read the Full Documentation**
   - [README.md](README.md) - Complete feature overview
   - [DEPLOYMENT.md](DEPLOYMENT.md) - Detailed deployment guide
   - [PUBLISHING.md](PUBLISHING.md) - Publishing to PyPI

2. **Explore Examples**
   - Check `models/` for SQL transformation examples
   - Run `ml/examples/train_example_model.py` for ML examples

3. **Connect Your Data**
   - Configure connections in the UI
   - Add your own SQL models
   - Create custom dashboards

4. **Join the Community**
   - Star the repo: https://github.com/kraftaa/transformdash
   - Report issues: https://github.com/kraftaa/transformdash/issues
   - Contribute: See CONTRIBUTING.md

---

## 🎓 Learning Resources

### Understanding the Architecture

```
Your Data Sources (PostgreSQL, APIs, Files)
           ↓
Bronze Layer (Raw data staging - stg_* models)
           ↓
Silver Layer (Business logic - int_* models)
           ↓
Gold Layer (Final analytics - fct_*, dim_* models)
           ↓
Dashboards & ML Models
```

### Key Concepts

**Models**: SQL files that transform your data (like dbt)
**Charts**: Visualizations of your data
**Dashboards**: Collections of charts with filters
**ML Models**: Trained models for predictions
**Scheduler**: Automated job execution

---

## 💡 Tips & Best Practices

1. **Start Small**: Begin with a simple model, then expand
2. **Use Docker**: Easiest way to get started without configuration
3. **Version Control**: Commit your models and dashboards
4. **Test Locally**: Use development environment before deploying
5. **Monitor Performance**: Check query execution times
6. **Regular Backups**: Export dashboards and models regularly

---

## 🔗 Useful Links

- **Main Docs**: [README.md](README.md)
- **Deployment Guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Publishing Guide**: [PUBLISHING.md](PUBLISHING.md)
- **ML Documentation**: [ml/README.md](ml/README.md)
- **GitHub**: https://github.com/kraftaa/transformdash
- **Issues**: https://github.com/kraftaa/transformdash/issues

---

## ✅ Quick Checklist

After following this guide, you should have:
- [ ] TransformDash running on http://localhost:8000
- [ ] Database connection configured
- [ ] First model executed successfully
- [ ] First chart created
- [ ] First dashboard built
- [ ] API documentation accessible

**Need help?** Open an issue on GitHub!

---

**Welcome to TransformDash! 🚀**
