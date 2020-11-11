from copy import deepcopy
from django.conf import settings
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.schemas.openapi import AutoSchema
from rest_framework.status import is_success

from .permissions import IsShop
from .utils import is_dict, to_positive_int

# Контроль openapi схемы

class ResponsesSchema(AutoSchema):
    """
    Заготовка openapi схемы
    Класс копирует в стандартной схеме поля запроса и ответа для разных
    поддерживаемых форматов: json, xml, http
    Также добавляет статус коды ответов и копирует примеры для них по
    данным в поле status_descriptions
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
        'Errors': {'type': 'string', 'readOnly': True, 'description': 'Error message(s)'},
    }

    dict_path = ('content', 'application/json', 'schema', 'properties', )

    standard_parser_mime_types = ('application/json', 'application/yaml', 'application/xml', )
    standard_render_mime_types = ('application/json', 'application/yaml', 'application/xml', )

    status_descriptions = {}

    def get_parsers_mimes(self, view):
        parsers = view.request.parsers if view.request else view.parser_classes 
        renders = view.renderer_classes
        mimes = set(self.standard_parser_mime_types)
        for parser in parsers:
            mimes.add(parser.media_type)
        self.standard_parser_mime_types = mimes
        mimes = set(self.standard_render_mime_types)
        for render in renders:
            mimes.add(render.media_type)
        self.standard_render_mime_types = mimes

    def get_properties_for_success(self, content):
        for item in self.dict_path:
            if not is_dict(content) or item not in content:
                return self.standard_success_properties
            content = content[item]
        properties = {}
        for key, value in content.items():
            if not is_dict(value):
                continue
            if not 'type' in value or value['type'] == 'array':
                properties[key] = value
            if not 'readOnly' in value:
                continue
            if key == 'Status':
                if hasattr(self.view, 'action') and (self.view.action == 'list' or self.view.action == 'retrieve'):
                    properties.pop('Status', None)
                    continue
                properties[key] = value
                continue
            if key != 'Errors' and value['readOnly'] == True:
                properties[key] = value

        if hasattr(self.view, 'action') and self.view.action == 'list':
            properties = {
                'count': {'type': 'integer', 'readOnly': True, 'description': 'Number of pages'},
                'next': {'type': 'string', 'readOnly': True, 'description': 'Next page'},
                'previous': {'type': 'string', 'readOnly': True, 'description': 'Previous page'},
                'results': {'type': 'array', 'items': {'required': [], 'properties': properties}},
            }

        return properties

    def get_status_only_error_properties(self, content):
        for item in self.dict_path:
            if not is_dict(content) or item not in content:
                return self.standard_error_properties
            content = content[item]
        properties = {}
        for key, value in content.items():
            if not is_dict(value):
                continue
            if key in ['Status', 'Errors']:
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

    def get_status_descriptions(self, has_body=False, *args, **kwargs):
        results = self.status_descriptions.copy()
        if hasattr(self.view, 'action') and self.view.action == 'create' and '201' not in results:
            results['201'] = 'Created'
        elif '200' not in results:
            results['200'] = 'OK'
        if any(isinstance(x, IsAuthenticated) for x in self.view.get_permissions()) and '401' not in results:
            results['401'] = 'Auth required...'
        if any(isinstance(x, IsShop) for x in self.view.get_permissions()) and '403' not in results:
            results['403'] = 'Forbidden...'
        if has_body and '400' not in results:
            results['400'] = 'Error in input data'
        return results


    def generate_response_options(self, content, has_body=False, *args, **kwargs):
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
        status_only_error_properties = self.get_status_only_error_properties(content)
        success_content = deepcopy(content)
        error_content = deepcopy(content)
        status_only_error_content = deepcopy(content)
        base['schema']['properties'] = success_properties
        for mime in self.standard_render_mime_types:
            success_content['content'][mime] = base
        base = deepcopy(base)
        base['schema']['properties'] = status_only_error_properties
        for mime in self.standard_render_mime_types:
            status_only_error_content['content'][mime] = base
        base = deepcopy(base)
        base['schema']['properties'] = error_properties
        for mime in self.standard_render_mime_types:
            error_content['content'][mime] = base

        for code, description in self.get_status_descriptions(has_body).items():
            int_code = to_positive_int(code)
            if not int_code:
                continue
            if is_success(int_code):
                content = success_content
            elif int_code == 400:
                content = error_content
            else:
                content = status_only_error_content
            options[code] = content.copy()
            options[code]['description'] = str(description)
        return options

    def get_operation(self, path, method, *arg, **kwargs):
        self.get_parsers_mimes(self.view)
        operation = super().get_operation(path, method, *arg, **kwargs)
        if not 'parameters' in operation:
            operation['parameters'] = []
        operation['parameters'].append({'name': 'fromat', 'in': 'query', 'required': False, 'description': 'Output format', 'schema': {'type': 'string'}})
        remark = ''
        for key, value in settings.PATH_REMARKS.items():
            if key in path:
                remark = value
        operation['description'] = str(self.view.get_view_description()) + remark
        responses = operation.get('responses', {})
        if len(responses):
            content = responses[next(iter(responses))]          
            operation['responses'] = self.generate_response_options(content, has_body=('requestBody' in operation))
        test = operation.get('requestBody', {})
        for item in ('content', 'application/json', 'schema'):
            if not is_dict(test) or item not in test:
                return operation
            test = test[item]
        body = operation['requestBody']['content']['application/json']
        body['schema']['xml'] = { 'name': 'root' }
        for mime in self.standard_parser_mime_types:
            operation['requestBody']['content'][mime] = body
        return operation


# class ResponsesNoInputSchema(ResponsesSchema):
#     """
#     Базовый класс схемы openapi не копирующей входные параметры для валидации
#     """

#     def get_properties_for_error(self, content):
#         for item in self.dict_path:
#             if not is_dict(content) or item not in content:
#                 return self.standard_error_properties
#             content = content[item]
#         properties = {}
#         for key, value in content.items():
#             if not is_dict(value) or not 'readOnly' in value:
#                 continue
#             if value['readOnly'] == True:
#                 properties[key] = value

#         return properties


