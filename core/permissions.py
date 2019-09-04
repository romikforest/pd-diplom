from django.utils.translation import gettext_lazy as t
from rest_framework.permissions import BasePermission


# Классы проверки прав доступа:

class IsShop(BasePermission):
    """
    Permissin class
    Проверка, что пользователь имеет тип shop
    """

    message = t('Только для магазинов')

    def has_permission(self, request, view):
        return request.user.type == 'shop' or request.user.is_superuser
