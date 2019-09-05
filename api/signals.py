from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver, Signal
from django_rest_passwordreset.signals import reset_password_token_created
from django.utils.translation import gettext_lazy as t

from rest_auth.models import ConfirmEmailToken, User

from core.tasks import send_multi_alternative

new_user_registered = Signal(
    providing_args=['user_id'],
)

new_order = Signal(
    providing_args=['user_id'],
)


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, **kwargs):
    """
    Отправляем письмо с токеном для сброса пароля
    When a token is created, an e-mail needs to be sent to the user
    :param sender: View Class that sent the signal
    :param instance: View Instance that sent the signal
    :param reset_password_token: Token Model Object
    :param kwargs:
    :return:
    """
    # send an e-mail to the user

    send_multi_alternative.delay(
        # title:
        t('Сброс пароля для {}').format(reset_password_token.user),
        # message:
        t('Токен для сброса пароля {}').format(reset_password_token.key),
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [reset_password_token.user.email]
    )


@receiver(new_user_registered)
def new_user_registered_signal(user_id, **kwargs):
    """
    отправляем письмо с подтрердждением почты
    """
    # send an e-mail to the user
    token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user_id)

    send_multi_alternative.delay(
        # title:
        t('Подтверждение регистрации в магазинчике для {}').format(token.user.email),
        # message:
        t('Токен для подтверждения регистрации {}').format(token.key),
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [token.user.email]
    )


@receiver(new_order)
def new_order_signal(user_id, **kwargs):
    """
    отправяем письмо при изменении статуса заказа
    """
    # send an e-mail to the user
    user = User.objects.get(id=user_id)

    send_multi_alternative.delay(
        # title:
        t('Обновление статуса заказа'),
        # message:
        t('Заказ сформирован'),
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [user.email]
    )



# from django.conf import settings
# from django.core.mail import EmailMultiAlternatives
# from django.dispatch import receiver, Signal
# from django_rest_passwordreset.signals import reset_password_token_created
# from django.utils.translation import gettext_lazy as t

# from rest_auth.models import ConfirmEmailToken, User

# new_user_registered = Signal(
#     providing_args=['user_id'],
# )

# new_order = Signal(
#     providing_args=['user_id'],
# )


# @receiver(reset_password_token_created)
# def password_reset_token_created(sender, instance, reset_password_token, **kwargs):
#     """
#     Отправляем письмо с токеном для сброса пароля
#     When a token is created, an e-mail needs to be sent to the user
#     :param sender: View Class that sent the signal
#     :param instance: View Instance that sent the signal
#     :param reset_password_token: Token Model Object
#     :param kwargs:
#     :return:
#     """
#     # send an e-mail to the user

#     msg = EmailMultiAlternatives(
#         # title:
#         t('Сброс пароля для {}').format(reset_password_token.user),
#         # message:
#         t('Токен для сброса пароля {}').format(reset_password_token.key),
#         # from:
#         settings.EMAIL_HOST_USER,
#         # to:
#         [reset_password_token.user.email]
#     )
#     msg.send()


# @receiver(new_user_registered)
# def new_user_registered_signal(user_id, **kwargs):
#     """
#     отправляем письмо с подтрердждением почты
#     """
#     # send an e-mail to the user
#     token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user_id)

#     msg = EmailMultiAlternatives(
#         # title:
#         t('Подтверждение регистрации в магазинчике для {}').format(token.user.email),
#         # message:
#         t('Токен для подтверждения регистрации {}').format(token.key),
#         # from:
#         settings.EMAIL_HOST_USER,
#         # to:
#         [token.user.email]
#     )
#     msg.send()


# @receiver(new_order)
# def new_order_signal(user_id, **kwargs):
#     """
#     отправяем письмо при изменении статуса заказа
#     """
#     # send an e-mail to the user
#     user = User.objects.get(id=user_id)

#     msg = EmailMultiAlternatives(
#         # title:
#         t('Обновление статуса заказа'),
#         # message:
#         t('Заказ сформирован'),
#         # from:
#         settings.EMAIL_HOST_USER,
#         # to:
#         [user.email]
#     )
#     msg.send()
