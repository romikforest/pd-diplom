from decimal import Decimal
# from distutils.util import strtobool

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile as FileClass
from django.core.validators import URLValidator
from django.db import transaction
from django.db.models import Q
# from django.db import IntegrityError
# from django.db.models import Q, Sum, F
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as t
from django.views.decorators.cache import cache_page, never_cache
from django.views.decorators.vary import vary_on_headers
import os
from requests import get
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view
from rest_framework.exceptions import ParseError
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework_xml.parsers import XMLParser
from rest_framework.views import APIView
from ujson import loads as load_json
from yaml import load as load_yaml, Loader, YAMLError

from core.models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter
from rest_auth.models import ConfirmEmailToken, Contact, ADDRESS_ITEMS_LIMIT
from .serializers import UserSerializer, CategorySerializer, SeparateContactSerializer, \
    ShopSerializer, ProductInfoSerializer
# from backend.models import Order, OrderItem
# from backend.serializers import  \
#     OrderItemSerializer, OrderSerializer
from .signals import new_user_registered, new_order


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

def load_xml(stream):
    """
    Parses the incoming bytestream as XML and returns the resulting data.
    """

    return XMLParser().parse(ContentFile(stream))

@cache_page(settings.CAHCE_TIMES['ROOT_API'])
@api_view(['GET'])
def api_root(request, format=None):
    return Response({
        'partner/update': reverse('api_v1:partner-update', request=request, format=format),
        'user/login': reverse('api_v1:user-login', request=request, format=format),
        'user/register': reverse('api_v1:user-register', request=request, format=format),
        'user/register/confirm': reverse('api_v1:user-register-confirm', request=request, format=format),
        'user/password_reset': reverse('api_v1:password-reset', request=request, format=format),
        'user/password_reset/confirm': reverse('api_v1:password-reset-confirm', request=request, format=format),
        'user/details': reverse('api_v1:user-details', request=request, format=format),
        'categories': reverse('api_v1:categories', request=request, format=format),
        'user/contact': reverse('api_v1:user-contact', request=request, format=format),
        'shops': reverse('api_v1:shops', request=request, format=format),
        'products': reverse('api_v1:products', request=request, format=format),
        'docs': reverse('api_v1:openapi-schema', request=request, format=format),
})


class PartnerUpdate(APIView):
    """
    Класс для обновления прайса от поставщика
    """

    throttle_scope = 'partner_update'
    permission_classes = [IsAuthenticated]

    @method_decorator(never_cache)
    def post(self, request, *args, **kwargs):

        if request.user.type != 'shop':
            return Response({'Status': False, 'Error': t('Только для магазинов')}, status=403)

        url = request.data.get('url')
        file_obj = request.data.get('file')

        print(type(file_obj))
        if not url and not (file_obj and isinstance(file_obj, FileClass)):
            return Response({'Status': False, 'Errors': t('Не указаны все необходимые аргументы')})

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
            if mime in ('application/x-yaml', 'text/yaml'):
                data = load_yaml(stream, Loader=Loader)
            elif mime in ('application/json', 'text/json'):
                data = load_json(stream)
            elif mime in ('application/xml', 'text/xml'):
                data = load_xml(stream)
            elif extension == '.yaml':
                data = load_yaml(stream, Loader=Loader)
            elif extension == '.json':
                data = load_json(stream)
            elif extension == '.xml':
                data = load_xml(stream)
            else:
                return Response({'Status': False, 'Error': t('Не опознан формат файла {}').format(url)})
        except (ParseError, YAMLError, ValueError, TypeError) as e:
            return Response({'Status': False, 'Error': t('Некорректный формат файла: {}').format(str(e))})

        # Check format:
        if not type(data) == dict:
            return Response({'Status': False, 'Error': t('Некорректный формат файла: исходные данные должны представлять собой словарь')})

        if not data.get('shop'):
            return Response({'Status': False, 'Error': t('Некорректный формат файла: не задано/некорректное название магазина')})

        categories = data.get('categories', [])
        if type(categories) is not list:
            return Response({'Status': False, 'Error': t('Некорректный формат файла: категории должны быть заданы в списке')})
        for category in categories:
            if type(category) is not dict:
                return Response({'Status': False, 'Error': t('Некорректный формат файла: категории должны быть описаны как словарь')}) 
            if not category.get('name'):
                return Response({'Status': False, 'Error': t('Некорректный формат файла: не задано/некорректное название категории')})

        goods = data.get('goods', [])
        if type(goods) is not list:
            return Response({'Status': False, 'Error': t('Некорректный формат файла: товары должны быть заданы в списке')})
        names = set()
        for item in goods:
            if type(item) is not dict:
                return Response({'Status': False, 'Error': t('Некорректный формат файла: товары должны быть описаны как словарь')}) 
            name = item.get('name')
            category = item.get('category')
            price = to_decimal(item.get('price'))
            price_rrc = to_decimal(item.get('price_rrc'))
            quantity = to_positive_int(item.get('quantity'))
            if not name or not category or None in (price, price_rrc, quantity):
                return Response({'Status': False, 'Error': t('Некорректный формат файла: некорректно указана информация по продукту {}').format(name)})
            if name in names:
                return Response({'Status': False, 'Error': t('Некорректный формат файла: продукты с одинаковым именем')})
            names.add(name)
            parameters = item.get('parameters')
            if parameters is not None:
                if type(parameters) is not list:
                    return Response({'Status': False,
                                     'Error': t('Некорректный формат файла: параметры для продукта {} должны быть заданы как массив полей name и value').format(name)})
                parameter_names = set()
                for entry in parameters:
                    if type(entry) is not dict:
                        return Response({'Status': False,
                                         'Error': t('Некорректный формат файла: параметр для продукта должен быть описан как словарь (продукт {})').format(name)})
                    par_name = entry.get('name')
                    if not par_name or entry.get('value') is None:
                        return Response({'Status': False,
                            'Error': t('Некорректный формат файла: параметры для продукта {} должны иметь не пустые значения name и value').format(name)})
                    if par_name in parameter_names:
                        return Response({'Status': False, 'Error': t('Некорректный формат файла: параметры с одинаковым именем у продукта {}').format(name)})
                    parameter_names.add(par_name)
        
        # Actions:
        shop, _ = Shop.objects.get_or_create(name=data['shop'], defaults=dict(user_id=request.user.id))
        if shop.user_id != request.user.id:
            return Response({'Status': False, 'Error': t('Магазин не принадлежит пользователю')}, status=403)

        for category in data.get('categories', []):
            category_object, _ = Category.objects.get_or_create(name=category['name'])
            category_object.shops.add(shop.id)
            category_object.save()
        ProductInfo.objects.filter(shop_id=shop.id).delete()
        for item in data.get('goods', []):           
            category_object, _ = Category.objects.get_or_create(name=item['category'])
            product, _ = Product.objects.get_or_create(name=item['name'], category_id=category_object.id)

            product_info = ProductInfo.objects.create(product_id=product.id,
                                                      external_id=item.get('id'),
                                                      price=item['price'],
                                                      price_rrc=item['price_rrc'],
                                                      quantity=item['quantity'],
                                                      shop_id=shop.id)
            for entry in item.get('parameters', []):
                parameter_object, _ = Parameter.objects.get_or_create(name=entry.get('name'))
                ProductParameter.objects.create(product_info_id=product_info.id,
                                                parameter_id=parameter_object.id,
                                                value=entry.get('value'))

        return Response({'Status': True}, status=201)


class LoginAccount(APIView):
    """
    Класс для авторизации пользователей
    """

    @method_decorator(never_cache)
    def post(self, request, *args, **kwargs):

        if not {'email', 'password'}.issubset(request.data):
            return Response({'Status': False, 'Errors': t('Не указаны все необходимые аргументы')})

        user = authenticate(request, username=request.data['email'], password=request.data['password'])

        if user is None:
            return Response({'Status': False, 'Errors': t('Не удалось авторизовать')})

        if user.is_active:
            token, _ = Token.objects.get_or_create(user=user)

        return Response({'Status': True, 'Token': token.key})       


class RegisterAccount(APIView):
    """
    Для регистрации покупателей
    """

    @method_decorator(never_cache)
    def post(self, request, *args, **kwargs):

        # проверяем обязательные аргументы
        if not {'first_name', 'last_name', 'email', 'password', 'company', 'position'}.issubset(request.data):
            return Response({'Status': False, 'Errors': t('Не указаны все необходимые аргументы')})

        errors = {}

        # проверяем пароль на сложность

        try:
            validate_password(request.data['password'])
        except Exception as password_error:
            error_array = []
            # noinspection PyTypeChecker
            for item in password_error:
                error_array.append(item)
            return Response({'Status': False, 'Errors': {'password': error_array}})

        # проверяем данные для уникальности имени пользователя
        # request.data._mutable = True # request.data = request.data.copy()
        # request.data.update({})
        user_serializer = UserSerializer(data=request.data)
        if not user_serializer.is_valid():
            return Response({'Status': False, 'Errors': user_serializer.errors})

        # сохраняем пользователя
        user = user_serializer.save()
        user.set_password(request.data['password'])
        user.save()
        new_user_registered.send(sender=self.__class__, user_id=user.id)
        return Response({'Status': True}, status=201)


class ConfirmAccount(APIView):
    """
    Класс для подтверждения почтового адреса
    """

    @method_decorator(never_cache)
    def post(self, request, *args, **kwargs):

        # проверяем обязательные аргументы
        if not {'email', 'token'}.issubset(request.data):
            return Response({'Status': False, 'Errors': t('Не указаны все необходимые аргументы')})

        token = ConfirmEmailToken.objects.filter(user__email=request.data['email'],
                                                 key=request.data['token']).first()
        if not token:
            return Response({'Status': False, 'Errors': t('Неправильно указан токен или email')})

        token.user.is_active = True
        token.user.save()
        token.delete()
        return Response({'Status': True})
        

class AccountDetails(APIView):
    """
    Класс для работы с данными пользователя
    """

    permission_classes = [IsAuthenticated]

    # получить данные
    @method_decorator(never_cache)
    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    # Редактирование методом PUT
    @method_decorator(never_cache)
    def put(self, request, *args, **kwargs):

        # проверяем обязательные аргументы
        if 'password' in request.data:
            errors = {}
            # проверяем пароль на сложность
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                error_array = []
                # noinspection PyTypeChecker
                for item in password_error:
                    error_array.append(item)
                return Response({'Status': False, 'Errors': {'password': error_array}})
            else:
                request.user.set_password(request.data['password'])

        if 'contacts' in request.data:
            contacts = request.data['contacts']
            if not isinstance(contacts, list) or len(contacts) > ADDRESS_ITEMS_LIMIT:
                return Response({'Status': False, 'Errors': t('Число контактов должно быть не более {}').format(ADDRESS_ITEMS_LIMIT)})

        # проверяем остальные данные
        user_serializer = UserSerializer(request.user, data=request.data, partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            return Response({'Status': True})
        else:
            return Response({'Status': False, 'Errors': user_serializer.errors})


class CategoryView(ListAPIView):
    """
    Класс для просмотра категорий
    """

    throttle_scope = 'categories'

    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ContactView(APIView):
    """
    Класс для работы с контактами покупателей
    """

    permission_classes = [IsAuthenticated]

    # получить мои контакты
    @method_decorator(vary_on_headers('Authorization'))
    def get(self, request, *args, **kwargs):
        contact = Contact.objects.filter(user_id=request.user.id)
        serializer = SeparateContactSerializer(contact, many=True)
        return Response(serializer.data)

    # добавить новый контакт
    @method_decorator(never_cache)
    def post(self, request, *args, **kwargs):

        if not 'phone' in request.data and not all([x in request.data for x in ('city', 'street', 'house')]):
            return Response({'Status': False, 'Errors': t('Не указаны все необходимые аргументы')})

        if Contact.objects.filter(user_id=request.user.id).count() >= ADDRESS_ITEMS_LIMIT:
            return Response({'Status': False,
                             'Errors': t('Нельзя добавить новый контакт. Уже добавлено {} контактов').format(ADDRESS_ITEMS_LIMIT)})

        data = request.data.copy()
        data.update({'user': request.user.id})
        serializer = SeparateContactSerializer(data=data)

        if not serializer.is_valid():
            Response({'Status': False, 'Errors': serializer.errors})

        serializer.save()
        return Response({'Status': True, 'data': serializer.data}, status=201)
        
    # удалить контакт
    @method_decorator(never_cache)
    def delete(self, request, *args, **kwargs):

        items_sting = request.data.get('items')
        if not items_sting:
            return Response({'Status': False, 'Errors': t('Не указаны все необходимые аргументы')})

        items_list = items_sting.split(',')
        query = Q()
        objects_to_delete = 0
        for contact_id in items_list:
            contact_id = to_positive_int(contact_id)
            if contact_id is None:
                return Response({'Status': False, 'Errors': t('id контакта должен быть положительным числом')})
            query = query | Q(user_id=request.user.id, id=contact_id)
            objects_to_delete += 1

        deleted_count = 0
        try:
            with transaction.atomic():
                deleted_count = Contact.objects.filter(query).delete()[0] if objects_to_delete else 0
                if deleted_count != objects_to_delete:
                    raise Exception()
        except Exception:
            return Response({'Status': False, 'Error': t('Не удалось найти и удалить все указанные объекты. Операция отменена.')})

        return Response({'Status': True, 'Deleted': deleted_count})

    # редактировать контакт (полностью)
    @method_decorator(never_cache)
    def put(self, request, *args, **kwargs):

        if 'id' not in request.data or \
            (not 'phone' in request.data and not all([x in request.data for x in ('city', 'street', 'house')])):
                return Response({'Status': False, 'Errors': t('Не указаны все необходимые аргументы')})

        if to_positive_int(request.data['id']) is None:
            return Response({'Status': False, 'Errors': t('id контакта должен быть положительным числом')})

        contact = Contact.objects.filter(id=request.data['id'], user_id=request.user.id).first()
        if not contact:
            return Response({'Status': False, 'Errors': t('Не найден контакт с id {}').format(request.data['id'])})

        data = request.data.copy()
        data.update({'user': request.user.id})

        serializer = SeparateContactSerializer(contact, data=data)
        if not serializer.is_valid():
            return Response({'Status': False, 'Errors': serializer.errors})

        serializer.save()
        return Response({'Status': True})

    # редактировать контакт (частично)
    @method_decorator(never_cache)
    def patch(self, request, *args, **kwargs):

        if 'id' not in request.data:
            return Response({'Status': False, 'Errors': t('Не указаны все необходимые аргументы')})

        if to_positive_int(request.data['id']) is None:
            return Response({'Status': False, 'Errors': t('id контакта должен быть положительным числом')})

        contact = Contact.objects.filter(id=request.data['id'], user_id=request.user.id).first()
        if not contact:
            return Response({'Status': False, 'Errors': t('Не найден контакт с id {}').format(request.data['id'])})

        serializer = SeparateContactSerializer(contact, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({'Status': False, 'Errors': serializer.errors})

        serializer.save()
        return Response({'Status': True})

        
class ShopView(ListAPIView):
    """
    Класс для просмотра списка магазинов
    """

    throttle_scope = 'shops'

    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer


class ProductInfoView(ListAPIView):
    """
    Класс для поиска товаров
    """

    queryset = Shop.objects.filter(state=True)
    serializer_class = ProductInfoSerializer

    def get_queryset(self):

        query = Q(shop__state=True)
        shop_id = self.request.query_params.get('shop_id')
        category_id = self.request.query_params.get('category_id')

        if shop_id:
            query = query & Q(shop_id=shop_id)

        if category_id:
            query = query & Q(product__category_id=category_id)

        # фильтруем и отбрасываем дубликаты
        return ProductInfo.objects.filter(
            query).select_related(
            'shop', 'product__category').prefetch_related(
            'product_parameters__parameter').distinct()


