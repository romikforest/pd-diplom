from copy import deepcopy
from rest_framework.schemas.openapi import AutoSchema
from rest_framework.status import is_success

from .utils import is_dict, to_positive_int

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

    standard_parser_mime_types = ('application/json', 'application/yaml', 'application/xml')
    standard_render_mime_types = ('application/json', 'application/yaml', 'application/xml')

    status_description = {}

    def get_parsers_mimes(self, request):
        mimes = set(self.standard_parser_mime_types)
        for parser in request.parsers:
            mimes.add(parser.media_type)
        self.standard_parser_mime_types = mimes
        mimes = set(self.standard_render_mime_types)
        for parser in request.parsers:
            mimes.add(parser.media_type)
        self.standard_render_mime_types = mimes

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
        for mime in self.standard_render_mime_types:
            success_content['content'][mime] = base
        base = deepcopy(base)
        base['schema']['properties'] = error_properties
        for mime in self.standard_render_mime_types:
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
        self.get_parsers_mimes(self.view.request)
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
        for mime in self.standard_parser_mime_types:
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

