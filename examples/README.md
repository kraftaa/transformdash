# TransformDash Examples

Quick examples to get started with TransformDash.

## Quick Start

```bash
# Install
pip install transformdash

# Set up PostgreSQL
docker run -d --name transformdash-db \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=mypassword \
  -e POSTGRES_DB=transformdash \
  postgres:15

# Create .env file
cat > .env << 'EOF'
JWT_SECRET_KEY=your-secret-key-here

TRANSFORMDASH_HOST=localhost
TRANSFORMDASH_PORT=5432
TRANSFORMDASH_DB=transformdash
TRANSFORMDASH_USER=postgres
TRANSFORMDASH_PASSWORD=mypassword

APP_HOST=localhost
APP_PORT=5432
APP_DB=production
APP_USER=postgres
APP_PASSWORD=mypassword
EOF

# Start the app
python -m ui.app
```

Visit http://localhost:8000 (login: admin / admin)

## Examples

### 1. Simple Transformation (`simple_transformation/`)
Basic example showing:
- Bronze layer: staging from raw tables
- Silver layer: joining multiple tables
- Gold layer: analytics-ready fact tables

### 2. ML Models
See `ml/` directory in the main repo for ML model training and inference examples.

## Need Help?

- Main docs: [README.md](../README.md)
- Issues: [GitHub Issues](https://github.com/kraftaa/transformdash/issues)
