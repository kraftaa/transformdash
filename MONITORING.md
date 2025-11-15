# TransformDash Monitoring Guide

Complete guide for monitoring your TransformDash instance, managing jobs, and tracking system health.

## Table of Contents

1. [Web UI System Monitor](#web-ui-system-monitor)
2. [API Endpoints](#api-endpoints)
3. [CLI Commands](#cli-commands)
4. [Monitoring Best Practices](#monitoring-best-practices)

---

## Web UI System Monitor

Access the System Monitor at: **http://localhost:8000** → Navigate to **System Monitor**

### Features

#### 1. Live Status Cards
- **Server Status**: Health status and uptime
- **Memory Usage**: RAM consumption in MB
- **CPU Usage**: Current CPU utilization percentage
- **Active Jobs**: Number of scheduled tasks

#### 2. Scheduled Jobs Table
View all active scheduled jobs with:
- Job ID and name
- Cron schedule
- Next run time (with countdown)
- Pause/Resume controls

#### 3. Process Information
- Process ID
- Thread count
- Database connection status
- Scheduler status

### Actions

**Refresh Status**: Click the "Refresh" button to update all metrics

**Pause Job**: Click the pause button (⏸) next to a job to temporarily suspend it

**Resume Job**: Click the play button (▶️) to resume a paused job

---

## API Endpoints

All API endpoints return JSON responses.

### GET /api/status

Get comprehensive server status.

**Request:**
```bash
curl http://localhost:8000/api/status
```

**Response:**
```json
{
  "status": "healthy",
  "service": "transformdash",
  "timestamp": "2025-11-14T19:36:27.671912",
  "process": {
    "pid": 21000,
    "uptime_seconds": 121.15,
    "memory_mb": 123.22,
    "cpu_percent": 0.1,
    "threads": 3
  },
  "scheduler": {
    "active": true,
    "jobs_count": 1,
    "jobs": [
      {
        "id": "schedule_3",
        "name": "Models: stg_commissions, stg_employees, stg_warehouses",
        "next_run_time": "2025-11-15T09:00:00+00:00",
        "trigger": "cron[month='*', day='*', day_of_week='*', hour='9', minute='0']"
      }
    ]
  },
  "database": {
    "transformdash": "connected",
    "app": "connected"
  }
}
```

### GET /api/jobs

List all scheduled jobs.

**Request:**
```bash
curl http://localhost:8000/api/jobs
```

**Response:**
```json
{
  "jobs": [
    {
      "id": "schedule_3",
      "name": "Models: stg_commissions, stg_employees, stg_warehouses",
      "next_run_time": "2025-11-15T09:00:00+00:00",
      "trigger": "cron[month='*', day='*', day_of_week='*', hour='9', minute='0']"
    }
  ],
  "jobs_count": 1
}
```

### GET /api/jobs/{job_id}

Get detailed information about a specific job.

**Request:**
```bash
curl http://localhost:8000/api/jobs/schedule_3
```

**Response:**
```json
{
  "id": "schedule_3",
  "name": "Models: stg_commissions, stg_employees, stg_warehouses",
  "next_run_time": "2025-11-15T09:00:00+00:00",
  "trigger": "cron[month='*', day='*', day_of_week='*', hour='9', minute='0']",
  "args": [3, ["stg_commissions", "stg_employees", "stg_warehouses"]],
  "kwargs": {}
}
```

### POST /api/jobs/{job_id}/pause

Pause a scheduled job.

**Request:**
```bash
curl -X POST http://localhost:8000/api/jobs/schedule_3/pause
```

**Response:**
```json
{
  "status": "paused",
  "job_id": "schedule_3"
}
```

### POST /api/jobs/{job_id}/resume

Resume a paused job.

**Request:**
```bash
curl -X POST http://localhost:8000/api/jobs/schedule_3/resume
```

**Response:**
```json
{
  "status": "resumed",
  "job_id": "schedule_3"
}
```

### GET /api/health

Simple health check endpoint.

**Request:**
```bash
curl http://localhost:8000/api/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "transformdash"
}
```

---

## CLI Commands

The TransformDash CLI provides a command-line interface for monitoring and managing your instance.

### Installation

The CLI is already available at `transformdash-cli.py` in the project root.

**Dependencies** (automatically installed with `pip install -r requirements.txt`):
- `requests`
- `tabulate`
- `psutil`

### Available Commands

#### status - Show Server Status

Display comprehensive server health and metrics.

```bash
python transformdash-cli.py status
```

**Output:**
```
✅ TransformDash Server Status
============================================================
Status: HEALTHY
Timestamp: 2025-11-14T19:36:27.671912

📊 Process Information:
  PID: 21000
  Uptime: 1m
  Memory: 123.0 MB
  CPU: 0.1%
  Threads: 3

⏰ Scheduler:
  Status: ✅ Active
  Active Jobs: 1

💾 Database: ✅ Connected
```

#### jobs - List All Jobs

Display all scheduled jobs in a formatted table.

```bash
python transformdash-cli.py jobs
```

**Output:**
```
⏰ Scheduled Jobs (1 active)
================================================================================
+------------+---------------------------------------------+------------+-----------------------------------------------------------------+
| Job ID     | Name                                        | Next Run   | Trigger                                                         |
+============+=============================================+============+=================================================================+
| schedule_3 | Models: stg_commissions, stg_employees, ... | in 8h 19m  | cron[month='*', day='*', day_of_week='*', hour='9', minute='0'] |
+------------+---------------------------------------------+------------+-----------------------------------------------------------------+
```

#### job - Show Job Details

Get detailed information about a specific job.

```bash
python transformdash-cli.py job schedule_3
```

**Output:**
```
📋 Job Details: schedule_3
============================================================
Name: Models: stg_commissions, stg_employees, stg_warehouses
Next Run: in 8h 19m
Trigger: cron[month='*', day='*', day_of_week='*', hour='9', minute='0']
Arguments: [3, ['stg_commissions', 'stg_employees', 'stg_warehouses']]
```

#### pause - Pause a Job

Temporarily suspend a scheduled job.

```bash
python transformdash-cli.py pause schedule_3
```

**Output:**
```
✅ Job schedule_3 paused successfully
```

#### resume - Resume a Job

Resume a paused job.

```bash
python transformdash-cli.py resume schedule_3
```

**Output:**
```
✅ Job schedule_3 resumed successfully
```

#### watch - Live Monitor

Watch server status with auto-refresh (like `top` or `htop`).

```bash
# Default: refresh every 5 seconds
python transformdash-cli.py watch

# Custom refresh interval (in seconds)
python transformdash-cli.py watch --interval 10

# Press Ctrl+C to stop
```

**Features:**
- Auto-refreshing status display
- Live job countdown
- Real-time metrics
- Clears screen on each refresh

### CLI Help

```bash
python transformdash-cli.py --help
```

---

## Monitoring Best Practices

### 1. Regular Health Checks

**Automated Monitoring:**
```bash
# Create a cron job to check health every 5 minutes
*/5 * * * * python /path/to/transformdash-cli.py status >> /var/log/transformdash-health.log
```

**Alerting:**
```bash
# Simple alert script
#!/bin/bash
STATUS=$(curl -s http://localhost:8000/api/health | jq -r '.status')
if [ "$STATUS" != "healthy" ]; then
    echo "ALERT: TransformDash is unhealthy!" | mail -s "TransformDash Alert" admin@example.com
fi
```

### 2. Resource Monitoring

**Memory Thresholds:**
- Normal: < 500 MB
- Warning: 500-1000 MB
- Critical: > 1000 MB

**CPU Thresholds:**
- Normal: < 50%
- Warning: 50-80%
- Critical: > 80%

**Monitor with:**
```bash
# Watch memory and CPU every 10 seconds
python transformdash-cli.py watch --interval 10
```

### 3. Job Management

**Before Production:**
- Test all schedules in development
- Verify cron expressions
- Check timezone settings
- Monitor first few executions

**During Operation:**
- Review job execution history
- Check for failed runs
- Monitor execution duration
- Adjust schedules as needed

**Maintenance Windows:**
```bash
# Pause all jobs before maintenance
python transformdash-cli.py jobs | grep schedule_ | awk '{print $1}' | xargs -I {} python transformdash-cli.py pause {}

# Resume after maintenance
python transformdash-cli.py jobs | grep schedule_ | awk '{print $1}' | xargs -I {} python transformdash-cli.py resume {}
```

### 4. Log Monitoring

**Server Logs:**
```bash
tail -f /tmp/transformdash.log
```

**Grep for Errors:**
```bash
grep -i error /tmp/transformdash.log
grep -i failed /tmp/transformdash.log
```

**Scheduler Events:**
```bash
grep "scheduler" /tmp/transformdash.log | tail -20
```

### 5. Database Connection Monitoring

Check database status regularly:
```bash
curl -s http://localhost:8000/api/status | jq '.database'
```

If database shows issues:
1. Check connection credentials in `.env`
2. Verify PostgreSQL is running
3. Test connection manually: `psql -h localhost -U postgres -d transformdash`
4. Restart TransformDash if needed

### 6. Dashboard Alerts

**Setup Alerts in Web UI:**
1. Navigate to System Monitor
2. Note critical metrics
3. Set up email/Slack notifications (future feature)

**Current Workaround - External Monitoring:**
```bash
# Use external tools like Prometheus + Grafana
# Export metrics from /api/status endpoint
```

### 7. Performance Optimization

**If Memory Usage is High:**
- Check for memory leaks
- Review query complexity
- Consider increasing resources
- Implement caching

**If CPU Usage is High:**
- Review expensive queries
- Optimize transformations
- Reduce concurrent jobs
- Add indexes to database

**If Jobs are Slow:**
- Check job execution logs
- Profile SQL queries
- Optimize data transformations
- Consider incremental updates

---

## Troubleshooting

### Server Not Responding

```bash
# Check if server is running
curl http://localhost:8000/api/health

# Check server process
ps aux | grep python | grep app_refactored

# Check logs
tail -50 /tmp/transformdash.log

# Restart server
lsof -ti:8000 | xargs kill -9
python ui/app_refactored.py
```

### Jobs Not Running

```bash
# Check scheduler status
python transformdash-cli.py status

# List all jobs
python transformdash-cli.py jobs

# Check specific job
python transformdash-cli.py job schedule_3

# Check logs for scheduler errors
grep -i "scheduler\|schedule_" /tmp/transformdash.log
```

### CLI Not Working

```bash
# Verify server is running
curl http://localhost:8000/api/health

# Check Python environment
source venv/bin/activate
which python

# Install dependencies
pip install requests tabulate psutil

# Test with verbose error
python -v transformdash-cli.py status
```

---

## Integration Examples

### Prometheus Metrics Export

```python
# Add to app_refactored.py
from prometheus_client import Counter, Gauge, generate_latest

metrics_requests = Counter('transformdash_requests_total', 'Total requests')
metrics_memory = Gauge('transformdash_memory_bytes', 'Memory usage')
metrics_jobs = Gauge('transformdash_active_jobs', 'Active jobs')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "TransformDash Monitoring",
    "panels": [
      {
        "title": "Memory Usage",
        "targets": [{"expr": "transformdash_memory_bytes"}]
      },
      {
        "title": "Active Jobs",
        "targets": [{"expr": "transformdash_active_jobs"}]
      }
    ]
  }
}
```

### Slack Notifications

```bash
# Alert on job failure
#!/bin/bash
WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

JOBS=$(python transformdash-cli.py jobs | grep -c schedule_)
if [ "$JOBS" -eq 0 ]; then
    curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"⚠️ No active jobs in TransformDash!"}' \
        $WEBHOOK_URL
fi
```

---

## Summary

TransformDash provides three ways to monitor your instance:

1. **Web UI** - Visual dashboard at http://localhost:8000
2. **API** - RESTful endpoints for automation
3. **CLI** - Command-line tools for quick checks

Choose the method that best fits your workflow!

For more information:
- Main docs: [README.md](README.md)
- Deployment: [DEPLOYMENT.md](DEPLOYMENT.md)
- API docs: http://localhost:8000/docs
