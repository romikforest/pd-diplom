from django.utils.translation import gettext_lazy as t
from rest_framework import status as http_status
from rest_framework.response import Response

from core.utils import is_dict

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
            response['Errors'] = t(error if is_dict(error) else str(error)).format(**format if is_dict(format) else str(format))
        else:
            response['Errors'] = t(error if is_dict(error) else str(error))
    if kwargs:
        response.update(kwargs)
    return Response(response, status=status)

def ResponseBadRequest(error=None, format=None, status=None, **kwargs):
    status = http_status.HTTP_400_BAD_REQUEST
    return UniversalResponse(error, format, status, **kwargs)

def ResponseForbidden(error=None, format=None, status=None, **kwargs):
    status = http_status.HTTP_403_FORBIDDEN
    return UniversalResponse(error, format, status, **kwargs)

def ResponseConflict(error=None, format=None, status=None, **kwargs):
    status = http_status.HTTP_409_CONFLICT
    return UniversalResponse(error, format, status, **kwargs)

def ResponseNotFound(error=None, format=None, status=None, **kwargs):
    status = http_status.HTTP_404_NOT_FOUND
    return UniversalResponse(error, format, status, **kwargs)