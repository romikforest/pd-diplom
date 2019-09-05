from django.conf import settings
from django.utils.translation import gettext_lazy as t
from rest_framework.status import is_success

from orders.celery import app

from core.models import Shop
from core.partner_info_loader import load_partner_info
from core.tasks import send_multi_alternative

@app.task
def do_import():

    def report_error(user):
        send_multi_alternative.delay(
            # title:
            t('Не удалось обновить прайс'),
            # message:
            t('Произошла ошибка при обновлении прайса'),
            # from:
            settings.EMAIL_HOST_USER,
            # to:
            [user.email]
        )

    def report_success(user):
        send_multi_alternative.delay(
            # title:
            t('Обновление прайс листов завершено'),
            # message:
            t('Все возможные прайс листы обновлены'),
            # from:
            settings.EMAIL_HOST_USER,
            # to:
            [user.email]
        )


    for shop in Shop.objects.all().prefetch_related('user'):
        response = None
        try:
            response = load_partner_info(shop.url, None, shop.user_id)
        except Exception as e:
            report_error(shop.user)
        else:
            if response and is_success(response.status_code):
                report_success(shop.user)
            else:
                report_error(shop.user)
