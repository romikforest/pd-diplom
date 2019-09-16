from django.conf import settings
from django.core.mail import send_mail as core_send_mail
from django.core.mail import EmailMultiAlternatives
from django.utils.translation import gettext_lazy as t
import logging
from rest_framework.status import is_success

from orders.celery import app

from .models import Shop
from .partner_info_loader import load_partner_info


@app.task
def send_mail(subject, message, from_email, recipient_list, fail_silently=False,
              auth_user=None, auth_password=None, connection=None, html_message=None):
    try:
        core_send_mail(subject=subject, message=message, from_email=from_email,  recipient_list=recipient_list,
                       fail_silently=fail_silently, auth_user=auth_user, auth_password=auth_password, connection=connection, html_message=html_message)
    except Exception as e:
        logging.warning(f'Error sending email: {str(e)}. subject={subject}, recipient_list={recipient_list}')
        raise e

@app.task
def send_multi_alternative(subject='', body='', from_email=None, to=None, bcc=None,
                 connection=None, attachments=None, headers=None, alternatives=None,
                 cc=None, reply_to=None):
    msg = EmailMultiAlternatives(subject=subject, body=body, from_email=from_email, to=to, bcc=bcc,
                 connection=connection, attachments=attachments, headers=headers, alternatives=alternatives,
                 cc=cc, reply_to=reply_to)
    msg.send()


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
        except Exception:
            report_error(shop.user)
            raise
        else:
            if response and is_success(response.status_code):
                report_success(shop.user)
            else:
                report_error(shop.user)
