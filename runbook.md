# Blue/Green Deployment Runbook

## Alert Types

### 🔄 Failover Detected

**What happened:** Traffic automatically switched from one pool to another due to upstream failures.

**Immediate Actions:**

1. Check failed pool health:
```bash
docker compose logs app_blue  # or app_green
curl http://localhost:8081/healthz  # Blue
curl http://localhost:8082/healthz  # Green
```

2. Verify active pool is serving traffic:
```bash
curl -i http://localhost:8080/version
```

3. Check for root cause in application logs

4. Monitor for stability - if flapping occurs, investigate immediately

---

### ⚠️ High Error Rate Detected

**What happened:** Upstream applications returning 5xx errors above threshold (default 2%).

**Immediate Actions:**

1. Check current error rate:
```bash
docker compose logs --tail=50 nginx
docker compose logs --tail=100 app_blue app_green
```

2. Identify which pool is failing:
```bash
curl -i http://localhost:8080/version
```

3. **If errors persist**, manually toggle pools:
```bash
# Enable maintenance mode
echo "MAINTENANCE_MODE=true" >> .env
docker compose restart alert_watcher

# Switch pools in .env
# Change ACTIVE_POOL=blue to ACTIVE_POOL=green (or vice versa)

# Reload Nginx
docker compose restart nginx

# Disable maintenance mode
sed -i 's/MAINTENANCE_MODE=true/MAINTENANCE_MODE=false/' .env
docker compose restart alert_watcher
```

4. Review logs to identify root cause

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ERROR_RATE_THRESHOLD` | 2 | Error rate % that triggers alerts |
| `WINDOW_SIZE` | 200 | Number of requests to analyze |
| `ALERT_COOLDOWN_SEC` | 300 | Seconds between same alert type |
| `MAINTENANCE_MODE` | false | Suppress failover alerts during planned changes |

### Adjust Thresholds

Edit `.env` and restart watcher:
```bash
ERROR_RATE_THRESHOLD=5
WINDOW_SIZE=500
ALERT_COOLDOWN_SEC=600
docker compose restart alert_watcher
```

---

## Testing Procedures

### Test Failover Alert
```bash
# Trigger chaos on Blue
curl -X POST http://localhost:8081/chaos/start?mode=error

# Generate traffic
for i in {1..20}; do curl http://localhost:8080/version; sleep 0.5; done

# Check Slack for alert
# Stop chaos
curl -X POST http://localhost:8081/chaos/stop
```

### Test Error Rate Alert
```bash
# Trigger chaos on both pools
curl -X POST http://localhost:8081/chaos/start?mode=error
curl -X POST http://localhost:8082/chaos/start?mode=error

# Generate traffic
for i in {1..250}; do curl http://localhost:8080/version; sleep 0.1; done

# Check Slack for alert
# Stop chaos
curl -X POST http://localhost:8081/chaos/stop
curl -X POST http://localhost:8082/chaos/stop
```

## Quick Commands
```bash
# View all logs
docker compose logs -f

# Check service health
curl http://localhost:8080/version
curl http://localhost:8081/healthz
curl http://localhost:8082/healthz

# Trigger chaos
curl -X POST http://localhost:8081/chaos/start?mode=error
curl -X POST http://localhost:8081/chaos/stop

# Manual pool toggle
# Edit ACTIVE_POOL in .env, then:
docker compose restart nginx
```
