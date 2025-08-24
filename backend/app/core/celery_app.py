"""Celery application configuration for background task processing."""

import os
import logging
from celery import Celery
from celery.signals import setup_logging

# Create Celery instance
celery_app = Celery(
    "review_gap_analyzer",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
    include=[
        "app.tasks.analysis_tasks",
        "app.tasks.maintenance_tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "app.tasks.analysis_tasks.process_app_analysis": {"queue": "analysis"},
        "app.tasks.analysis_tasks.process_website_analysis": {"queue": "analysis"},
        "app.tasks.maintenance_tasks.*": {"queue": "maintenance"},
    },
    
    # Task execution settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task retry settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        'master_name': 'mymaster',
        'visibility_timeout': 3600,
    },
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    
    # Task time limits
    task_soft_time_limit=1800,  # 30 minutes
    task_time_limit=2400,  # 40 minutes
    
    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Monitoring and logging
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Beat schedule for periodic tasks
    beat_schedule={
        'cleanup-old-results': {
            'task': 'app.tasks.maintenance_tasks.cleanup_old_results',
            'schedule': 3600.0,  # Run every hour
        },
        'cleanup-failed-analyses': {
            'task': 'app.tasks.maintenance_tasks.cleanup_failed_analyses',
            'schedule': 86400.0,  # Run daily
        },
    },
    
    # Security settings
    task_always_eager=os.getenv("CELERY_ALWAYS_EAGER", "false").lower() == "true",
    task_eager_propagates=True,
    
    # Connection settings
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    
    # Task compression
    task_compression='gzip',
    result_compression='gzip',
)


@setup_logging.connect
def config_loggers(*args, **kwargs):
    """Configure logging for Celery workers."""
    from logging.config import dictConfig
    
    dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
            },
        },
        'handlers': {
            'console': {
                'level': 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'default',
            },
        },
        'root': {
            'level': 'INFO',
            'handlers': ['console'],
        },
        'loggers': {
            'celery': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False,
            },
            'app.tasks': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False,
            },
        }
    })


# Health check task
@celery_app.task(name='health_check')
def health_check():
    """Simple health check task for monitoring."""
    import time
    return {'status': 'healthy', 'timestamp': time.time()}