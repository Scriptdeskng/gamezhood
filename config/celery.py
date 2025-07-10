import os

from celery import Celery


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")


#  celery -A backend worker --loglevel=info -P gevent --concurrency 1 -E
app = Celery("config")

app.config_from_object("django.conf:settings", namespace="CELERY")

# Set a unique default queue to prevent overlap with other projects
app.conf.task_default_queue = 'gamezhood'

# Optional: Use Redis key prefix to avoid clashing with other apps
# Only needed if Redis is shared with homerecipe
app.conf.redis_backend_use_ssl = False  # if you're not using SSL
app.conf.result_backend_transport_options = {
    'retry_policy': {
        'timeout': 10.0
    }
}
app.conf.result_backend_namespace = 'gamezhood'

app.autodiscover_tasks()
