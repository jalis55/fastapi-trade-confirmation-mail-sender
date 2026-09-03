from celery import Celery
import os


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "celery_service",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.api.v1.endpoints.reports"],  # Force-import the module that defines the tasks
)
celery_app.conf.update(
    worker_concurrency=os.cpu_count() or 1,   # 1 process per core, auto
    worker_pool="threads",
)

# Auto-discover tasks - IMPORTANT!
celery_app.autodiscover_tasks(['app.services'])