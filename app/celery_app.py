from celery import Celery
from .core.config import settings

# Create Celery instance
celery_app = Celery(
    "songcraft",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,  # 1 hour
    task_routes={
        "app.tasks.generate_song": {"queue": "song_generation"},
        "app.tasks.generate_video": {"queue": "video_generation"},
        "app.tasks.send_email": {"queue": "emails"},
    },
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
) 
