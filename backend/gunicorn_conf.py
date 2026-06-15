"""
Gunicorn config tuned for serving hundreds of concurrent users.

Each worker is an async Uvicorn worker (can juggle many simultaneous
connections); we run several workers to use all CPU cores.

Start with:  gunicorn -c gunicorn_conf.py main:app
"""
import multiprocessing
import os

# Bind address.
bind = os.environ.get("BIND", "0.0.0.0:8000")

# Workers: (2 x cores) + 1 is a good default. Each handles many async clients.
workers = int(os.environ.get("WEB_CONCURRENCY", (multiprocessing.cpu_count() * 2) + 1))
worker_class = "uvicorn.workers.UvicornWorker"

# Each worker also keeps a threadpool for the blocking graph work we offload.
threads = int(os.environ.get("THREADS", "8"))

# Connection / timeout tuning.
timeout = 60
graceful_timeout = 30
keepalive = 5
# Recycle workers periodically to avoid memory leaks. Set MAX_REQUESTS=0 to
# disable (e.g. during benchmarks so keep-alive connections aren't dropped).
max_requests = int(os.environ.get("MAX_REQUESTS", "10000"))
max_requests_jitter = int(os.environ.get("MAX_REQUESTS_JITTER", "1000"))

accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
