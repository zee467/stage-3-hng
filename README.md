# Blue/Green Deployment with Monitoring & Slack Alerts (Stage 3)

Automated monitoring and alerting system for Blue/Green deployment with Nginx failover.

---

## Features
- Automatic Failover — Seamless traffic switching on failures  
- Real-time Monitoring — Log-based health tracking  
- Slack Alerts — Instant notifications for failovers and errors  
- Error Rate Tracking — Sliding window analysis of 5xx responses  
- Alert Deduplication — Cooldown periods prevent spam  
- Maintenance Mode — Suppress alerts during planned changes  

---

## Prerequisites
- Docker & Docker Compose  
- Slack workspace with an incoming webhook configured  
- Container images deployed to a registry  

---

## Quick Start

### 1. Clone and Configure
```bash
git clone <your-repo>
cd blue-green-deployment
cp .env.example .env
```

### 2. Set Up Slack Webhook
- Go to Slack Incoming Webhooks
- Create a new webhook
- Copy the webhook URL
- Update .env:
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### 3. Start Services
```bash
docker compose up -d
```

### 4. Verify Deployment
```bash
docker compose ps
curl -i http://localhost:8080/version
```


Expected headers:

X-App-Pool: blue
X-Release-Id: blue-v1.0.0
