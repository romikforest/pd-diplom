import collections
from collections import OrderedDict
from copy import deepcopy
from decimal import Decimal
from django.conf.urls import url
from django.urls import reverse
from django.utils.translation import gettext_lazy as t
from rest_framework import status as http_status
from rest_framework import routers
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.schemas.openapi import AutoSchema
from rest_framework.status import is_success
from rest_framework.views import exception_handler


def is_dict(value):
    """
    Проверка, что объект value имеет поведение словаря
    """
    return isinstance(value, collections.Mapping)

def is_list(value):
    """
    Проверка, что объект value является списком
    """
    return type(value) == list
    # return isinstance(value, collections.Iterable)

# Конверторы. Возвращают None при ошибке:

def to_float(value):
    """
    Преобразование значения в число с плавающей точкой.
    При неудаче возвращается None
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def to_int(value):
    """
    Преобразование значения в целое со знаком.
    При неудаче возвращается None
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return None

def to_positive_int(value):
    """
    Преобразование значения в неотрицательное целое.
    При неудаче возвращается None
    """
    try:
        value = int(value)
        return value if value >= 0 else None
    except (ValueError, TypeError):
        return None

def to_decimal(value):
    """
    Преобразование значения в большое число с фиксированной дробной частью.
    При неудаче возвращается None
    """
    value = to_float(value)
    return None if value is None else Decimal.from_float(value)

def to_positive_decimal(value):
    """
    Преобразование значения в неотрицательное большое число с фиксированной дробной частью.
    При неудаче возвращается None
    """
    value = to_float(value)
    return None if value is None or value < 0 else Decimal.from_float(value)


# Заготовки типичных http ответов:

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
            response['Error'] = t(error if is_dict(error) else str(error)).format(**format if is_dict(format) else str(format))
        else:
            response['Error'] = t(error if is_dict(error) else str(error))
    if kwargs:
        response.update(kwargs)
    return Response(response, status=status)

def ResponseBadRequest(error=None, format=None, status=None, **kwargs):
    status = http_status.HTTP_400_BAD_REQUEST
    return UniversalResponse(error, format, status, **kwargs)

def ResponseForbidden(error=None, format=None, status=None, **kwargs):
    status = http_status.HTTP_403_FORBIDDEN
    return UniversalResponse(error, format, status, **kwargs)


def custom_exception_handler(exc, context):
    """
    Обработчик добавляет поля Status и Error в сообщения об ошибках при
    исключительных ситуациях. Должен быть зарегистрирован в settings

    """

    response = exception_handler(exc, context)

    if response is not None:
        if 'Status' not in response.data:
            response.data['Status'] = False
        if 'Error' not in response.data and 'detail' in response.data:
            response.data['Error'] = response.data['detail']
            del response.data['detail']

    return response


# Классы проверки прав доступа:

class IsShop(BasePermission):
    """
    Permissin class
    Проверка, что пользователь имеет тип shop
    """

    message = t('Только для магазинов')

    def has_permission(self, request, view):
        return request.user.type == 'shop' or request.user.is_superuser


# ViewSet роутеры:

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


# Примеси для сериалайзеров:

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


# Контроль openapi схемы

class ResponsesSchema(AutoSchema):
    """
    Заготовка openapi схемы
    Класс копирует в стандартной схеме поля запроса и ответа для разных
    поддерживаемых форматов: json, xml, http
    Также добавляет статус коды ответов и копирует примеры для них по
    данным в поле status_description
    В поле положительных ответов копируется поле Status и все поля,
    помеченные как только для чтения.
    В поле отрицательных ответов копируются все поля (для валидации)
    Класс является базовым для других классов схем
    """

    standard_success_properties = {
        'Status': {'type': 'boolean', 'readOnly': True, 'description': 'Http Status code'},
    }

    standard_error_properties = {
        'Status': {'type': 'boolean', 'readOnly': True, 'description': 'Http Status code'},
        'Error': {'type': 'string', 'readOnly': True, 'description': 'Error message(s)'},
    }

    dict_path = ('content', 'application/json', 'schema', 'properties', )

    standard_mime_types = ('application/json', 'application/yaml', 'application/xml')

    status_description = {}

    def get_properties_for_success(self, content):
        for item in self.dict_path:
            if not is_dict(content) or item not in content:
                return self.standard_success_properties
            content = content[item]
        properties = {}
        for key, value in content.items():
            if not is_dict(value) or not 'readOnly' in value:
                continue
            if key != 'Error' and value['readOnly'] == True:
                if key == 'Status':
                    value = deepcopy(value)
                    value['type'] = 'boolean'
                properties[key] = value

        return properties

    def get_properties_for_error(self, content):
        for item in self.dict_path:
            if not is_dict(content) or item not in content:
                return self.standard_error_properties
            content = content[item]
        properties = {}
        for key, value in content.items():
            if not is_dict(value):
                continue
            if 'readOnly' not in value or not value['readOnly']:
                value = deepcopy(value)
                value['type'] = 'string'
                if 'format' in value:
                    del value['format']
            properties[key] = value

        return properties

    def generate_response_options(self, content):
        options = {}
        test = content
        for item in self.dict_path:
            if not is_dict(test) or item not in test:
                return None
            test = test[item]
        base = deepcopy(content['content']['application/json'])
        base['schema']['xml'] = { 'name': 'root' }
        success_properties = self.get_properties_for_success(content)
        error_properties = self.get_properties_for_error(content)
        success_content = deepcopy(content)
        error_content = deepcopy(content)
        base['schema']['properties'] = success_properties
        for mime in self.standard_mime_types:
            success_content['content'][mime] = base
        base = deepcopy(base)
        base['schema']['properties'] = error_properties
        for mime in self.standard_mime_types:
            error_content['content'][mime] = base

        for code in self.status_description:
            int_code = to_positive_int(code)
            if not int_code:
                continue
            content = success_content if is_success(int_code) else error_content
            options[code] = content.copy()
            options[code]['description'] = self.status_description[code]
        return options

    def get_operation(self, path, method, *arg, **kwargs):
        operation = super().get_operation(path, method, *arg, **kwargs)
        if not len(operation['responses']):
            return operation
        content = operation['responses'][next(iter(operation['responses']))]          
        operation['responses'] = self.generate_response_options(content)
        test = operation['requestBody']
        for item in ('content', 'application/json', 'schema'):
            if not is_dict(test) or item not in test:
                return operation
            test = test[item]
        body = operation['requestBody']['content']['application/json']
        body['schema']['xml'] = { 'name': 'root' }
        for mime in self.standard_mime_types:
            operation['requestBody']['content'][mime] = body
        return operation


class SimpleCreatorSchema(ResponsesSchema):
    """
    Класс схемы для простого создателя (успех обозначает как http код 201)
    """

    status_description = {
        '201': 'Created',
        '400': 'Error in input data',
        '401': 'Auth required...',
        '403': 'Forbidden...',
    }


class SimpleActionSchema(ResponsesSchema):
    """
    Класс схемы для простого действия (успех обозначает как http код 200)
    """

    status_description = {
        '200': 'Done',
        '400': 'Error in input data',
        '401': 'Auth required...',
        '403': 'Forbidden...',
    }
 

class ResponsesNoInputSchema(ResponsesSchema):
    """
    Базовый класс схемы openapi не копирующей входные параметры для валидации
    """

    def get_properties_for_error(self, content):
        for item in self.dict_path:
            if not is_dict(content) or item not in content:
                return self.standard_error_properties
            content = content[item]
        properties = {}
        for key, value in content.items():
            if not is_dict(value) or not 'readOnly' in value:
                continue
            if value['readOnly'] == True:
                properties[key] = value

        return properties


class SimpleNoInputCreatorSchema(ResponsesNoInputSchema):
    """
    Класс схемы для простого создателя (успех обозначает как http код 201),
    не копирующего входные параметры для валидации
    """

    status_description = {
        '201': 'Created',
        '400': 'Error in input data',
        '401': 'Auth required...',
        '403': 'Forbidden...',
    }


class SimpleNoInputActionSchema(ResponsesNoInputSchema):
    """
    Класс схемы для простого действия (успех обозначает как http код 200),
    не копирующего входные параметры для валидации
    """

    status_description = {
        '200': 'Done',
        '400': 'Error in input data',
        '401': 'Auth required...',
        '403': 'Forbidden...',
    }
