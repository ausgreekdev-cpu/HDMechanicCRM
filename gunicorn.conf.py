import os
import multiprocessing

bind = os.environ.get("CRM_GUNICORN_BIND", "0.0.0.0:8000")
workers = int(os.environ.get("CRM_GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"
worker_connections = 1000
timeout = int(os.environ.get("CRM_GUNICORN_TIMEOUT", "120"))
keepalive = 5
graceful_timeout = 30

accesslog = os.environ.get("CRM_ACCESS_LOG", "-")
errorlog = os.environ.get("CRM_ERROR_LOG", "-")
loglevel = os.environ.get("CRM_LOG_LEVEL", "info").lower()

proc_name = "hdmechanic"

preload_app = True
max_requests = 1000
max_requests_jitter = 50

forwarded_allow_ips = os.environ.get("CRM_FORWARDED_ALLOW_IPS", "*")
proxy_protocol = False
proxy_allow_from = "*"

server_header = False
disable_redirect_access_logsyslog = True
