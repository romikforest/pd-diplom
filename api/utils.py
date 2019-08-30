from rest_framework.views import exception_handler

def custom_exception_handler(exc, context):

    response = exception_handler(exc, context)

    if response is not None:
        if 'Status' not in response.data:
            response.data['Status'] = False
        if 'Error' not in response.data and 'detail' in response.data:
            response.data['Error'] = response.data['detail']
            del response.data['detail']

    return response
