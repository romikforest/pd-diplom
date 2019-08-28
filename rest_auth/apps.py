from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class RestAuthConfig(AppConfig):
    name = 'rest_auth'
    verbose_name = _('Пользователи и группы')
    verbose_name_plural = _('Пользователи')
