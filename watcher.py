#!/usr/bin/env python3
import os
import re
import time
import requests
from collections import deque

# Config
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
# The percentage of 5xx errors (default 2%) that triggers an alert
ERROR_RATE_THRESHOLD = float(os.getenv('ERROR_RATE_THRESHOLD', 2))
# Number of recent requests to track (sliding window)
WINDOW_SIZE = int(os.getenv('WINDOW_SIZE', 200))
# Minimum seconds between alerts of the same type (avoid spam)
ALERT_COOLDOWN_SEC = int(os.getenv('ALERT_COOLDOWN_SEC', 300))
# If true, disables failover alerts temporarily.
MAINTENANCE_MODE = os.getenv('MAINTENANCE_MODE', 'false').lower() == 'true'

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
    
    # Cooldown check
    now = time.time()
    if now - last_alert_time.get(alert_type, 0) < ALERT_COOLDOWN_SEC:
        return
    
    payload = {'text': message}
    try:
        requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
        last_alert_time[alert_type] = now
        print(f"[SLACK] Sent {alert_type} alert")
    except Exception as e:
        print(f"[ERROR] Slack failed: {e}")


def check_failover(pool):
    global last_pool
    if not pool or last_pool is None:
        last_pool = pool
        return
    
    if pool != last_pool:
        msg = f"Failover: {last_pool} → {pool}"
        send_slack(msg, 'failover')
        last_pool = pool


def check_error_rate():
    if len(request_window) < 50:
        return
    
    errors = sum(1 for status in request_window if status >= 500)
    error_rate = (errors / len(request_window)) * 100
    
    if error_rate > ERROR_RATE_THRESHOLD:
        msg = f"High Error Rate: {error_rate:.1f}% ({errors}/{len(request_window)})"
        send_slack(msg, 'error_rate')


def tail_logs():
    print("[WATCHER] Starting...")
    
    while not os.path.exists('/var/log/nginx/access.log'):
        time.sleep(1)
    
    with open('/var/log/nginx/access.log', 'r') as f:
        f.seek(0, 2)  # Go to end
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
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


if __name__ == '__main__':
    tail_logs()
