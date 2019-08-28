from decimal import Decimal
# from distutils.util import strtobool

# from django.contrib.auth import authenticate
# from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
# from django.db import IntegrityError
# from django.db.models import Q, Sum, F
#from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _t
import os
from requests import get
# from rest_framework.authtoken.models import Token
# from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from ujson import loads as load_json
from yaml import load as load_yaml, Loader, YAMLError

from core.models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter
# from backend.models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, \
#     Contact, ConfirmEmailToken
# from backend.serializers import UserSerializer, CategorySerializer, ShopSerializer, ProductInfoSerializer, \
#     OrderItemSerializer, OrderSerializer, ContactSerializer
# from backend.signals import new_user_registered, new_order

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


class PartnerUpdate(APIView):
    """
    Класс для обновления прайса от поставщика
    """

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({'Status': False, 'Error': _t('Log in required')}, status=403)

        if request.user.type != 'shop':
            return Response({'Status': False, 'Error': _t('Только для магазинов')}, status=403)

        url = request.data.get('url')
        file_obj = request.data.get('file')
        if url or file_obj:

            if file_obj:
                stream = file_obj.read()
                _, extension = os.path.splitext(file_obj.name)
                mime = ''
            else:
                validate_url = URLValidator()
                try:
                    validate_url(url)
                except ValidationError as e:
                    return Response({'Status': False, 'Error': str(e)})

                response = get(url)
                _, extension = os.path.splitext(url)
                stream = response.content
                mime = response.headers.get('content-type')

            try:
                if mime == 'application/x-yaml' or mime == 'text/yaml':
                    data = load_yaml(stream, Loader=Loader)
                elif mime == 'application/json' or mime == 'text/json':
                    data = load_json(stream)
                elif extension == '.yaml':
                    data = load_yaml(stream, Loader=Loader)
                elif extension == '.json':
                    data = load_json(stream)
                else:
                    return Response({'Status': False, 'Error': _t('Не опознан формат файла {}').format(url)})
            except (YAMLError, ValueError, TypeError) as e:
                return Response({'Status': False, 'Error': _t('Некорректный формат файла: {}').format(str(e))})

            # Check format:
            name = data.get('shop')
            if not name:
                return Response({'Status': False, 'Error': _t('Некорректный формат файла: некорректное название магазина')})

            for category in data.get('categories', []):
                name = category.get('name')
                if not name:
                    return Response({'Status': False, 'Error': _t('Некорректный формат файла: некорректное название категории')})

            names = set()
            for item in data.get('goods', []):
                name = item.get('name')
                category = item.get('category')
                price = to_decimal(item.get('price'))
                price_rrc = to_decimal(item.get('price_rrc'))
                quantity = to_positive_int(item.get('quantity'))
                if not name or not category or None in (price, price_rrc, quantity):
                    return Response({'Status': False, 'Error': _t('Некорректный формат файла: некорректно указана информация по продукту {}').format(name)})
                if name in names:
                    return Response({'Status': False, 'Error': _t('Некорректный формат файла: продукты с одинаковым именем')})
                names.add(name)

            if item.get('parameters') is not None and type(item.get('parameters')) is not dict:
                return Response({'Status': False, 'Error': _t('Некорректный формат файла: параметры для продукты должны быть заданы как словарь')})

            # Actions:
            shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=request.user.id)
            if shop.user_id != request.user.id:
                return Response({'Status': False, 'Error': _t('Магазин не принадлежит пользователю')}, status=403)

            for category in data.get('categories', []):
                category_object, _ = Category.objects.get_or_create(name=category['name'])
                category_object.shops.add(shop.id)
                category_object.save()
            ProductInfo.objects.filter(shop_id=shop.id).delete()
            for item in data.get('goods', []):
                name = item.get('name')
                category = item.get('category')
                price = item.get('price')
                price_rrc = item.get('price_rrc')
                quantity = to_positive_int(item.get('quantity'))
                
                category_object, _ = Category.objects.get_or_create(name=category)
                product, _ = Product.objects.get_or_create(name=name, category_id=category_object.id)

                product_info = ProductInfo.objects.create(product_id=product.id,
                                                          external_id=item.get('id'),
                                                          price=price,
                                                          price_rrc=price_rrc,
                                                          quantity=quantity,
                                                          shop_id=shop.id)
                for name, value in item.get('parameters', []).items():
                    parameter_object, _ = Parameter.objects.get_or_create(name=name)
                    ProductParameter.objects.create(product_info_id=product_info.id,
                                                    parameter_id=parameter_object.id,
                                                    value=value)

            return Response({'Status': True}, status=201)

        return Response({'Status': False, 'Errors': _t('Не указаны все необходимые аргументы')})


