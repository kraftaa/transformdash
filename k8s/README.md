# TransformDash Kubernetes Deployment

This directory contains Kubernetes manifests for deploying TransformDash to a Kubernetes cluster.

## Prerequisites

- Kubernetes cluster (v1.24+)
- kubectl configured to access your cluster
- Docker image built and pushed to a registry (or use local images with minikube/kind)

## Quick Start

### 1. Build and Push Docker Image

```bash
# Build the image
docker build -t your-registry/transformdash:latest .

# Push to registry (skip for local development)
docker push your-registry/transformdash:latest
```

### 2. Update Configuration

Edit the following files with your values:

- `secret.yaml` - Update database passwords
- `transformdash-deployment.yaml` - Update image name to match your registry
- `ingress.yaml` - Update domain name

### 3. Deploy to Kubernetes

```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create secrets (IMPORTANT: Update passwords first!)
kubectl apply -f k8s/secret.yaml

# Create config maps
kubectl apply -f k8s/configmap.yaml

# Create persistent volume claims
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/transformdash-pvc.yaml

# Deploy PostgreSQL
kubectl apply -f k8s/postgres-deployment.yaml

# Wait for postgres to be ready
kubectl wait --for=condition=ready pod -l component=database -n transformdash --timeout=120s

# Deploy TransformDash application
kubectl apply -f k8s/transformdash-deployment.yaml

# Optional: Deploy ingress (requires ingress controller)
kubectl apply -f k8s/ingress.yaml
```

### 4. Verify Deployment

```bash
# Check pod status
kubectl get pods -n transformdash

# Check services
kubectl get svc -n transformdash

# View logs
kubectl logs -f deployment/transformdash -n transformdash

# Get application URL
kubectl get ingress -n transformdash
# Or for LoadBalancer service:
kubectl get svc transformdash-service -n transformdash
```

## Access the Application

### Using LoadBalancer (Cloud Providers)

```bash
# Get external IP
kubectl get svc transformdash-service -n transformdash

# Access at http://<EXTERNAL-IP>:8000
```

### Using Ingress

Configure your domain's DNS to point to your ingress controller's IP, then access at:
```
https://transformdash.example.com
```

### Using Port Forward (Local Development)

```bash
kubectl port-forward svc/transformdash-service 8000:8000 -n transformdash

# Access at http://localhost:8000
```

## Scaling

```bash
# Scale application pods
kubectl scale deployment/transformdash --replicas=5 -n transformdash

# Auto-scaling (requires metrics-server)
kubectl autoscale deployment/transformdash \
  --min=2 --max=10 \
  --cpu-percent=70 \
  -n transformdash
```

## Maintenance

### Update Application

```bash
# Update image
kubectl set image deployment/transformdash \
  transformdash=your-registry/transformdash:v2.0 \
  -n transformdash

# Or edit deployment
kubectl edit deployment/transformdash -n transformdash

# Rollback if needed
kubectl rollout undo deployment/transformdash -n transformdash
```

### Database Backup

```bash
# Exec into postgres pod
kubectl exec -it deployment/postgres -n transformdash -- bash

# Create backup
pg_dump -U postgres transformdash > /tmp/backup.sql

# Copy backup out
kubectl cp transformdash/postgres-pod:/tmp/backup.sql ./backup.sql
```

### View Logs

```bash
# Application logs
kubectl logs -f deployment/transformdash -n transformdash

# Database logs
kubectl logs -f deployment/postgres -n transformdash

# Previous pod logs
kubectl logs deployment/transformdash -n transformdash --previous
```

## Troubleshooting

### Pods not starting

```bash
# Describe pod to see events
kubectl describe pod <pod-name> -n transformdash

# Check events
kubectl get events -n transformdash --sort-by='.lastTimestamp'
```

### Database connection issues

```bash
# Test postgres connectivity
kubectl run -it --rm debug \
  --image=postgres:15-alpine \
  --restart=Never \
  -n transformdash -- \
  psql -h postgres-service -U postgres -d transformdash
```

### Storage issues

```bash
# Check PVCs
kubectl get pvc -n transformdash

# Check PVs
kubectl get pv

# Describe PVC
kubectl describe pvc postgres-pvc -n transformdash
```

## Cleanup

```bash
# Delete all resources
kubectl delete namespace transformdash

# Or delete individually
kubectl delete -f k8s/
```

## Production Considerations

1. **Secrets Management**: Use external secret managers (e.g., HashiCorp Vault, AWS Secrets Manager)
2. **Database**: Consider managed database services (RDS, CloudSQL, etc.) instead of running in cluster
3. **Monitoring**: Add Prometheus/Grafana for monitoring
4. **Logging**: Configure centralized logging (ELK, Loki, etc.)
5. **Backup**: Implement automated backup solutions
6. **Security**:
   - Network policies
   - Pod security policies/standards
   - RBAC
   - TLS everywhere
7. **High Availability**:
   - Run multiple replicas
   - Use pod disruption budgets
   - Configure resource limits properly

## Local Development with Minikube/Kind

```bash
# Start minikube
minikube start

# Load image into minikube (instead of pushing to registry)
minikube image load transformdash:latest

# Use NodePort service type
kubectl apply -f k8s/

# Access application
minikube service transformdash-service -n transformdash
```

## Environment-Specific Deployments

For different environments (dev, staging, prod), use kustomize or helm:

```bash
# Using kustomize overlays
kubectl apply -k k8s/overlays/production/

# Using namespace-based separation
kubectl apply -f k8s/ -n transformdash-prod
kubectl apply -f k8s/ -n transformdash-staging
```
