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
        if 'Errors' not in response.data and 'ErrorDetail' in response.data:
            response.data['Errors'] = response.data['ErrorDetail']
            del response.data['ErrorDetail']
        if 'Errors' not in response.data and 'Error' in response.data:
            response.data['Errors'] = response.data['Error']
            del response.data['Error']
        if 'Errors' not in response.data and 'non_field_errors' in response.data:
            response.data['Errors'] = response.data['non_field_errors']
            del response.data['non_field_errors']

    return response

