#!/usr/bin/env python3
import os
import re
import time
import subprocess
import requests
from collections import deque

# Config
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
ERROR_RATE_THRESHOLD = float(os.getenv('ERROR_RATE_THRESHOLD', 2))
WINDOW_SIZE = int(os.getenv('WINDOW_SIZE', 200))
ALERT_COOLDOWN_SEC = int(os.getenv('ALERT_COOLDOWN_SEC', 300))
MAINTENANCE_MODE = os.getenv('MAINTENANCE_MODE', 'false').lower() == 'true'
LOG_FILE = '/var/log/nginx/access_local.log'

# State
last_pool = None
request_window = deque(maxlen=WINDOW_SIZE)
last_alert_time = {'failover': 0, 'error_rate': 0}

LOG_PATTERN = re.compile(r'pool="([^"]*)".*upstream_status="([^"]*)"')


def send_slack(message, alert_type):
    if not SLACK_WEBHOOK_URL:
        print(f"[ALERT] {message}")
        return
    
    if MAINTENANCE_MODE and alert_type == 'failover':
        return
    
    now = time.time()
    if now - last_alert_time.get(alert_type, 0) < ALERT_COOLDOWN_SEC:
        return
    
    try:
        requests.post(SLACK_WEBHOOK_URL, json={'text': message}, timeout=5)
        last_alert_time[alert_type] = now
        print(f"[SLACK] {alert_type}: {message}")
    except Exception as e:
        print(f"[ERROR] {e}")


def check_failover(pool):
    global last_pool
    if not pool:
        return
    
    if last_pool is None:
        last_pool = pool
        print(f"[INIT] Pool: {pool}")
        return
    
    if pool != last_pool:
        msg = (f"🔄 *Failover Detected*\n"
               f"Pool switched: `{last_pool}` → `{pool}`\n\n"
               f"*Details:*\n"
               f"• Previous Pool: {last_pool.upper()}\n"
               f"• Current Pool: {pool.upper()}\n"
               f"• Total Requests Monitored: {len(request_window)}\n\n"
               f"*Action Required:*\n"
               f"• Check health of `{last_pool}` container\n"
               f"• Review application logs\n"
               f"• Verify `{pool}` is handling traffic correctly")
        send_slack(msg, 'failover')
        last_pool = pool


def check_error_rate():
    if len(request_window) < 50:
        return
    
    errors = sum(1 for s in request_window if s >= 500)
    rate = (errors / len(request_window)) * 100
    
    if rate > ERROR_RATE_THRESHOLD:
        msg = (f"⚠️ *High Error Rate Detected*\n"
               f"Error Rate: `{rate:.2f}%` (threshold: {ERROR_RATE_THRESHOLD}%)\n"
               f"Errors: {errors}/{len(request_window)} requests\n\n"
               f"*Action Required:*\n"
               f"• Inspect upstream application logs\n"
               f"• Check system resources (CPU, memory)\n"
               f"• Consider manual pool toggle if errors persist")
        send_slack(msg, 'error_rate')


print("[START] Watcher starting...")
print(f"[CONFIG] Threshold: {ERROR_RATE_THRESHOLD}%, Window: {WINDOW_SIZE}, Cooldown: {ALERT_COOLDOWN_SEC}s")

# Wait for log file
while not os.path.exists(LOG_FILE):
    print(f"[WAIT] Waiting for {LOG_FILE}...")
    time.sleep(2)

print(f"[READY] Tailing {LOG_FILE}")

# Use tail -f to follow the log (works with symlinks)
process = subprocess.Popen(['tail', '-f', '-n', '0', LOG_FILE], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

try:
    for line in iter(process.stdout.readline, b''):
        line = line.decode('utf-8').strip()
        if not line:
            continue
        
        match = LOG_PATTERN.search(line)
        if not match:
            continue
        
        pool = match.group(1)
        status_str = match.group(2).split(',')[-1].strip()
        
        try:
            status = int(status_str) if status_str != '-' else 0
        except ValueError:
            status = 0
        
        request_window.append(status)
        check_failover(pool)
        check_error_rate()
except KeyboardInterrupt:
    process.kill()
    print("\n[STOP] Watcher stopped")
