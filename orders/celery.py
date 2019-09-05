import os
from celery import Celery
from django.conf import settings
 
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'orders.settings')
 
app = Celery('orders')
app.config_from_object('django.conf:settings')
 
# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'do_price_import': {
        'task': 'api.tasks.do_import',
        'schedule': crontab(minute=0, hour=0)
    },
}
