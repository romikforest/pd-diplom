from rest_framework.negotiation import DefaultContentNegotiation
from rest_framework.views import exception_handler


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


class AcceptAsContentTypeNegotiation(DefaultContentNegotiation):
    """
    Класс устанавливает формат ответа по умолчанию
    такой же, как формат запроса

    """

    def get_accept_list(self, request):

        def get_list(header=''):
            result = []
            for token in header.split(','):
                token = token.strip()
                if token and token != '*/*':
                    result.append(token)
            return result

        return get_list(request.META.get('HTTP_ACCEPT')) or (get_list(request.content_type) + ['*/*'])

