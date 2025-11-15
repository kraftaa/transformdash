# TransformDash Deployment Guide

This guide covers all deployment options for TransformDash: local development, Docker, Docker Compose, and Kubernetes.

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Docker Deployment](#docker-deployment)
3. [Docker Compose Deployment](#docker-compose-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [pip Package Installation](#pip-package-installation)
6. [Configuration](#configuration)
7. [Production Considerations](#production-considerations)

---

## Local Development Setup

### Prerequisites

- Python 3.9+
- PostgreSQL 15+
- Git

### Step 1: Clone Repository

```bash
git clone https://github.com/kraftaa/transformdash.git
cd transformdash
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt

# Or install with extras
pip install -e ".[dev,ml,scraping]"
```

### Step 4: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your database credentials
nano .env
```

Example `.env`:
```env
# TransformDash Database
TRANSFORMDASH_HOST=localhost
TRANSFORMDASH_PORT=5432
TRANSFORMDASH_DB=transformdash
TRANSFORMDASH_USER=postgres
TRANSFORMDASH_PASSWORD=your_password

# App Production Database
APP_HOST=localhost
APP_PORT=5432
APP_DB=production
APP_USER=postgres
APP_PASSWORD=your_password
```

### Step 5: Initialize Database

```bash
# Create databases
createdb transformdash
createdb production

# Or using psql
psql -U postgres -c "CREATE DATABASE transformdash;"
psql -U postgres -c "CREATE DATABASE production;"
```

### Step 6: Run Application

```bash
python ui/app_refactored.py
```

Access the application at: http://localhost:8000

---

## Docker Deployment

### Prerequisites

- Docker 20.10+
- Docker Compose (optional)

### Build Docker Image

```bash
# Build the image
docker build -t transformdash:latest .

# Or with custom tag
docker build -t your-registry/transformdash:v1.0.0 .
```

### Run Container

#### Option 1: Using existing PostgreSQL

```bash
docker run -d \
  --name transformdash \
  -p 8000:8000 \
  -e TRANSFORMDASH_HOST=your-postgres-host \
  -e TRANSFORMDASH_PORT=5432 \
  -e TRANSFORMDASH_DB=transformdash \
  -e TRANSFORMDASH_USER=postgres \
  -e TRANSFORMDASH_PASSWORD=your_password \
  -e APP_HOST=your-postgres-host \
  -e APP_PORT=5432 \
  -e APP_DB=production \
  -e APP_USER=postgres \
  -e APP_PASSWORD=your_password \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/ml/models:/app/ml/models \
  -v $(pwd)/data:/app/data \
  transformdash:latest
```

#### Option 2: Using Docker network

```bash
# Create network
docker network create transformdash-net

# Run PostgreSQL
docker run -d \
  --name transformdash-postgres \
  --network transformdash-net \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=transformdash \
  -p 5432:5432 \
  -v postgres-data:/var/lib/postgresql/data \
  postgres:15-alpine

# Run TransformDash
docker run -d \
  --name transformdash-app \
  --network transformdash-net \
  -p 8000:8000 \
  -e TRANSFORMDASH_HOST=transformdash-postgres \
  -e TRANSFORMDASH_PORT=5432 \
  -e TRANSFORMDASH_DB=transformdash \
  -e TRANSFORMDASH_USER=postgres \
  -e TRANSFORMDASH_PASSWORD=postgres \
  transformdash:latest
```

---

## Docker Compose Deployment

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+

### Quick Start

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

### With pgAdmin

```bash
# Start with pgAdmin included
docker-compose --profile tools up -d

# Access pgAdmin at http://localhost:5050
# Default credentials: admin@transformdash.local / admin
```

### Configuration

Edit `docker-compose.yml` or create a `.env` file:

```env
# PostgreSQL Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=transformdash

# TransformDash Configuration
TRANSFORMDASH_DB=transformdash
TRANSFORMDASH_USER=postgres
TRANSFORMDASH_PASSWORD=your_secure_password

APP_DB=production
APP_USER=postgres
APP_PASSWORD=your_secure_password

# pgAdmin (optional)
PGADMIN_EMAIL=admin@transformdash.local
PGADMIN_PASSWORD=admin
PGADMIN_PORT=5050
```

### Production docker-compose

For production, use a separate `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  transformdash:
    image: your-registry/transformdash:v1.0.0
    restart: always
    environment:
      - TRANSFORMDASH_HOST=${DB_HOST}
      - TRANSFORMDASH_PASSWORD=${DB_PASSWORD}
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

---

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster 1.24+
- kubectl configured
- Docker registry access

### Quick Deploy

```bash
# Deploy everything
kubectl apply -f k8s/

# Check status
kubectl get pods -n transformdash -w
```

### Step-by-Step Deployment

#### 1. Build and Push Image

```bash
# Build
docker build -t your-registry/transformdash:v1.0.0 .

# Push
docker push your-registry/transformdash:v1.0.0

# For local development (minikube/kind)
minikube image load transformdash:v1.0.0
```

#### 2. Update Configuration

Edit `k8s/secret.yaml`:
```yaml
stringData:
  TRANSFORMDASH_PASSWORD: "your-production-password"
  POSTGRES_PASSWORD: "your-db-password"
```

Edit `k8s/transformdash-deployment.yaml`:
```yaml
containers:
- name: transformdash
  image: your-registry/transformdash:v1.0.0  # Update this
```

Edit `k8s/ingress.yaml`:
```yaml
spec:
  tls:
  - hosts:
    - transformdash.your-domain.com  # Update this
  rules:
  - host: transformdash.your-domain.com  # Update this
```

#### 3. Deploy

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Deploy secrets and config
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/configmap.yaml

# Deploy storage
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/transformdash-pvc.yaml

# Deploy database
kubectl apply -f k8s/postgres-deployment.yaml

# Wait for postgres to be ready
kubectl wait --for=condition=ready pod -l component=database -n transformdash --timeout=120s

# Deploy application
kubectl apply -f k8s/transformdash-deployment.yaml

# Deploy ingress
kubectl apply -f k8s/ingress.yaml
```

#### 4. Verify Deployment

```bash
# Check pods
kubectl get pods -n transformdash

# Check services
kubectl get svc -n transformdash

# View logs
kubectl logs -f deployment/transformdash -n transformdash

# Get application URL
kubectl get ingress -n transformdash
```

#### 5. Access Application

**Using LoadBalancer:**
```bash
kubectl get svc transformdash-service -n transformdash
# Access at http://<EXTERNAL-IP>:8000
```

**Using Ingress:**
```bash
# Configure DNS to point to ingress IP
kubectl get ingress -n transformdash

# Access at https://transformdash.your-domain.com
```

**Using Port Forward (Development):**
```bash
kubectl port-forward svc/transformdash-service 8000:8000 -n transformdash
# Access at http://localhost:8000
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment/transformdash --replicas=5 -n transformdash

# Auto-scaling
kubectl autoscale deployment/transformdash \
  --min=2 --max=10 \
  --cpu-percent=70 \
  -n transformdash
```

See [k8s/README.md](k8s/README.md) for more Kubernetes details.

---

## pip Package Installation

### Install from Source

```bash
# Clone repository
git clone https://github.com/kraftaa/transformdash.git
cd transformdash

# Install in development mode
pip install -e .

# Or install with extras
pip install -e ".[dev,ml,scraping]"
```

### Install from PyPI (when published)

```bash
# Basic installation
pip install transformdash

# With all extras
pip install transformdash[ml,scraping,orchestration]

# Development installation
pip install transformdash[dev]
```

### Build Distribution

```bash
# Install build tools
pip install build twine

# Build package
python -m build

# Check distribution
twine check dist/*

# Upload to PyPI (requires credentials)
twine upload dist/*
```

### Run After Installation

```bash
# Run the application
transformdash

# Or
python -m ui.app_refactored
```

---

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `TRANSFORMDASH_HOST` | TransformDash database host | localhost | Yes |
| `TRANSFORMDASH_PORT` | TransformDash database port | 5432 | Yes |
| `TRANSFORMDASH_DB` | TransformDash database name | transformdash | Yes |
| `TRANSFORMDASH_USER` | TransformDash database user | postgres | Yes |
| `TRANSFORMDASH_PASSWORD` | TransformDash database password | - | Yes |
| `APP_HOST` | Application data source host | localhost | Yes |
| `APP_PORT` | Application data source port | 5432 | Yes |
| `APP_DB` | Application data source database | production | Yes |
| `APP_USER` | Application data source user | postgres | Yes |
| `APP_PASSWORD` | Application data source password | - | Yes |
| `POSTGRES_HOST` | Generic Postgres host | localhost | No |
| `POSTGRES_PORT` | Generic Postgres port | 5432 | No |
| `POSTGRES_DB` | Generic Postgres database | postgres | No |
| `POSTGRES_USER` | Generic Postgres user | postgres | No |
| `POSTGRES_PASSWORD` | Generic Postgres password | - | No |

### Configuration Files

- `.env` - Local environment variables
- `models/schema.yml` - dbt-style model schemas
- `ml/models/registry.json` - ML model registry metadata

---

## Production Considerations

### Security

1. **Secrets Management**
   - Use external secret managers (Vault, AWS Secrets Manager, etc.)
   - Never commit `.env` files
   - Rotate credentials regularly

2. **Network Security**
   - Use TLS/SSL for all connections
   - Implement network policies in Kubernetes
   - Use firewalls and security groups

3. **Access Control**
   - Implement RBAC in Kubernetes
   - Use least privilege principle
   - Enable audit logging

### High Availability

1. **Database**
   - Use managed database services (RDS, CloudSQL, Azure Database)
   - Set up replication and failover
   - Regular backups

2. **Application**
   - Run multiple replicas (min 3 for production)
   - Use pod disruption budgets
   - Configure health checks

3. **Storage**
   - Use distributed storage for PVCs
   - Regular volume snapshots
   - Backup strategies

### Monitoring & Logging

1. **Metrics**
   - Deploy Prometheus + Grafana
   - Monitor resource usage
   - Set up alerts

2. **Logging**
   - Centralized logging (ELK, Loki, CloudWatch)
   - Log rotation and retention
   - Error tracking (Sentry)

3. **Tracing**
   - Distributed tracing (Jaeger, Zipkin)
   - Performance monitoring
   - Request tracking

### Performance

1. **Resource Limits**
   ```yaml
   resources:
     requests:
       memory: "512Mi"
       cpu: "500m"
     limits:
       memory: "2Gi"
       cpu: "2000m"
   ```

2. **Database Optimization**
   - Connection pooling
   - Query optimization
   - Index management

3. **Caching**
   - Redis for session data
   - Query result caching
   - Asset caching (CDN)

### Backup & Recovery

1. **Database Backups**
   ```bash
   # Manual backup
   kubectl exec deployment/postgres -n transformdash -- \
     pg_dump -U postgres transformdash > backup.sql

   # Automated backups (using CronJob)
   kubectl apply -f k8s/backup-cronjob.yaml
   ```

2. **Volume Snapshots**
   - Use storage class with snapshot support
   - Regular automated snapshots
   - Test restore procedures

3. **Disaster Recovery**
   - Document recovery procedures
   - Regular DR drills
   - Off-site backups

---

## Troubleshooting

### Common Issues

#### Application won't start

```bash
# Check logs
docker logs transformdash-app
# or
kubectl logs -f deployment/transformdash -n transformdash

# Common causes:
# - Database connection issues
# - Missing environment variables
# - Port conflicts
```

#### Database connection errors

```bash
# Test connection
psql -h localhost -U postgres -d transformdash

# Check if postgres is running
docker ps | grep postgres
# or
kubectl get pods -l component=database -n transformdash
```

#### Out of memory errors

```bash
# Increase memory limits
# In docker-compose.yml:
deploy:
  resources:
    limits:
      memory: 4G

# In Kubernetes:
resources:
  limits:
    memory: "4Gi"
```

### Getting Help

- GitHub Issues: https://github.com/kraftaa/transformdash/issues
- Documentation: https://github.com/kraftaa/transformdash/wiki
- Email: kraftaa@gmail.com

---

## Next Steps

After deployment:

1. **Configure Data Sources** - Add your PostgreSQL connections
2. **Create SQL Models** - Define your data transformations
3. **Build Dashboards** - Create visualizations
4. **Train ML Models** - Set up predictive models
5. **Schedule Jobs** - Automate model runs

See the main [README.md](README.md) for usage documentation.
