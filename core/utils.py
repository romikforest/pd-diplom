import collections
from collections import OrderedDict
from decimal import Decimal
from django.conf.urls import url
from django.urls import reverse
from django.utils.translation import gettext_lazy as t
from rest_framework.permissions import BasePermission
from rest_framework import routers
from rest_framework.response import Response
from rest_framework import status as http_status


def is_dict(value):
    return isinstance(value, collections.Mapping)

def is_list(value):
    return type(value) == list
    # return isinstance(value, collections.Iterable)


# Заготовки типичных ответов:

def ResponseOK(**kwargs):
    response = {'Status': True}
    if kwargs:
        response.update(kwargs)
    return Response(response, status=http_status.HTTP_200_OK)

def ResponseCreated(**kwargs):
    response = {'Status': True}
    if kwargs:
        response.update(kwargs)
    return Response(response, status=http_status.HTTP_201_CREATED)

def UniversalResponse(error=None, format=None, status=418, **kwargs):
    response = {'Status': False}
    if error:
        if format:
            response['Error'] = t(str(error)).format(**format if is_dict(format) else str(format))
        else:
            response['Error'] = t(str(error))
    if kwargs:
        response.update(kwargs)
    return Response(response, status=status)

def ResponseBadRequest(error=None, format=None, status=None, **kwargs):
    status = http_status.HTTP_400_BAD_REQUEST
    return UniversalResponse(error, format, status, **kwargs)

def ResponseForbidden(error=None, format=None, status=None, **kwargs):
    status = http_status.HTTP_403_FORBIDDEN
    return UniversalResponse(error, format, status, **kwargs)


class IsShop(BasePermission):
    """
    Permissin class
    Проверка, что пользователь имеет тип shop
    """

    message = t('Только для магазинов')

    def has_permission(self, request, view):
        return request.user.type == 'shop' or request.user.is_superuser



class CustomDefaultRouter(routers.DefaultRouter):
    """
    Роутер генерирует пути для конечного слеша и без него
    Он также старается добавить простые пути в api root view, не только list
    С помощью свойств root_view_pre_items и root_view_post_items
    можно добавить дополнительные поля в api root view
    соответсвенно до и после зарегистрированных роутов
    (ключ - отображаемый ключ, значение - имя в urlpatterns) 
    """
    root_view_pre_items = OrderedDict()
    root_view_post_items = OrderedDict()

    def get_urls(self):
        urls = super(CustomDefaultRouter, self).get_urls()
        for i in range(len(urls)):
            regex = str(urls[i].pattern)
            if regex[-2:] == '/$':
                regex = regex[:-2] + '/?$'
            urls[i] = url(regex=regex, view=urls[i].callback, name=urls[i].name)
        return urls

    def get_api_root_view(self, api_urls=None):
        """
        Return a basic root view.
        """
        api_root_dict = OrderedDict()
        api_root_dict.update(self.root_view_pre_items)

        viewsets = {}
        prefixes = {}
        for prefix, viewset, basename in self.registry:
            viewsets[viewset] = basename
            prefixes[viewset] = prefix

        for viewset in viewsets:
            routes = self.get_routes(viewset)
            basename = viewsets[viewset]
            prefix = prefixes[viewset]
            for route in routes:
                if not '{lookup}' in route.url:
                    name = route.name.format(basename=basename)
                    url = route.url.format(prefix=prefix, trailing_slash='').replace('^', '').replace('$', '')
                    if len(route.mapping) == 1:
                        method = next(iter(route.mapping)).upper()
                        if method != 'GET':
                            url += f' ({method})'
                    api_root_dict[url] = name

        api_root_dict.update(self.root_view_post_items)

        return self.APIRootView.as_view(api_root_dict=api_root_dict)


class CustomSimpleRouter(routers.SimpleRouter):
    """
    Роутер генерирует пути для конечного слеша и без него
    """

    def get_urls(self):
        urls = super(CustomDefaultRouter, self).get_urls()
        for i in range(len(urls)):
            regex = str(urls[i].pattern)
            if regex[-2:] == '/$':
                regex = regex[:-2] + '/?$'
            urls[i] = url(regex=regex, view=urls[i].callback, name=urls[i].name)
        return urls


class SelectableSerializersMixin(object):
    """
    Миксин выбора сериалайзера отдельно для каждого действия
    Используется с ViewSets.
    Для задания сериалайзеров используйте свойство action_serializers
    Оно должно представлять собой словарь <название действия> - <сериалайзер>
    Если сериалайзер не найден в action_serializers возвращается сериалайзер,
    указанный в свойстве serializer_class
    """

    def get_serializer_class(self):
        if hasattr(self, 'action_serializers'):
            if self.action in self.action_serializers:
                return self.action_serializers[self.action]
        return super(SelectableSerializersMixin, self).get_serializer_class()


# Конверторы. Возвращают None при ошибке:

def to_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def to_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def to_positive_int(value):
    try:
        value = int(value)
        return value if value >= 0 else None
    except (ValueError, TypeError):
        return None

def to_decimal(value):
    value = to_float(value)
    return None if value is None else Decimal.from_float(value)

def to_positive_decimal(value):
    value = to_float(value)
    return None if value is None or value < 0 else Decimal.from_float(value)

 