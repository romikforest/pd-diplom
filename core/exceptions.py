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
        if 'Errors' not in response.data and 'detail' in response.data:
            response.data['Errors'] = response.data['detail']
            del response.data['detail']

    return response

