import logging

from django.core.mail import send_mail as core_send_mail
from django.core.mail import EmailMultiAlternatives
from orders.celery import app


@app.task
def send_mail(subject, message, from_email, recipient_list, fail_silently=False,
              auth_user=None, auth_password=None, connection=None, html_message=None):
    try:
        core_send_mail(subject=subject, message=message, from_email=from_email,  recipient_list=recipient_list,
                       fail_silently=fail_silently, auth_user=auth_user, auth_password=auth_password, connection=connection, html_message=html_message)
    except Exception as e:
        logging.warning(f'Error sending email: {str(e)}. subject={subject}, recipient_list={recipient_list}')

@app.task
def send_multi_alternative(subject='', body='', from_email=None, to=None, bcc=None,
                 connection=None, attachments=None, headers=None, alternatives=None,
                 cc=None, reply_to=None):
    msg = EmailMultiAlternatives(subject=subject, body=body, from_email=from_email, to=to, bcc=bcc,
                 connection=connection, attachments=attachments, headers=headers, alternatives=alternatives,
                 cc=cc, reply_to=reply_to)
    msg.send()

