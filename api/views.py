# from distutils.util import strtobool
from django.contrib.auth.password_validation import validate_password

from django.conf import settings
from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import Q
# from django.db import IntegrityError
# from django.db.models import Q, Sum, F
from django.urls import resolve
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as t
from django.views.decorators.cache import cache_page, never_cache
from django.views.decorators.vary import vary_on_headers
from rest_framework import viewsets, mixins
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, action
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from core.mixins import SuperSelectableMixin, ViewSetViewSerializersMixin, ViewSetViewDescriptionsMixin
from core.models import Category, Shop, ProductInfo, Product, ProductParameter
from core.partner_info_loader import load_partner_info
from core.permissions import IsShop
from core.response import ResponseOK, ResponseCreated, ResponseBadRequest, ResponseForbidden
from core.utils import to_positive_int
from rest_auth.models import User, ConfirmEmailToken, Contact, ADDRESS_ITEMS_LIMIT

from .serializers import RegisterUserSerializer, CategorySerializer, CategoryDetailSerializer, \
    ContactSerializer, PartnerUpdateSerializer, ContactBulkDeleteSerializer, \
    ShopSerializer, ProductInfoSerializer, UserLoginSerializer, ListUserSerializer, \
    CaptchaInfoSerializer, ConfirmUserSerializer, UpdateUserDetailsSerializer, \
    ProductSerializer, ProductParameterSerializer
# from backend.models import Order, OrderItem
# from backend.serializers import  \
#     OrderItemSerializer, OrderSerializer

from .schemas import SimpleActionSchema, SimpleCreatorSchema, PartnerUpdateSchema, UserLoginSchema, CaptchaInfoSchema
from .signals import new_user_registered, new_order

shared_user_properties = {

    'serializer_class': ListUserSerializer,
    'permission_classes': tuple(),
    'throttle_scope': 'user',
    'queryset': User.objects.all(),

    'ordering_fields': ('first_name', 'last_name', 'email', 'company', 'position', 'id', ),
    'search_fields': ('first_name', 'last_name', 'email', 'company', 'position', ),
    'ordering': ('last_name', 'id', ),

    'action_serializers': {
        'retrieve': UpdateUserDetailsSerializer,
        'login': UserLoginSerializer,
        'captcha': CaptchaInfoSerializer,
        'register': RegisterUserSerializer,
        'confirm': ConfirmUserSerializer,
        'details': UpdateUserDetailsSerializer,
        'update_info': PartnerUpdateSerializer,
    },

    'action_throttles': {
        'login': 'user.login',
        'captcha': 'user.captcha',
        'register': 'user.register',
        'confirm': 'user.register',
        'details': 'user.register',
        'update_info': 'partner.update',
    },

    'action_descriptions': {
        'list': t('Список пользователей'),
        'retrieve': t('Информация о пользователе')
    },

    'action_querysets': {},

    'action_permissions': {
        'list': (IsAuthenticated, ),
        'retrieve': (IsAuthenticated, ),
        'details': (IsAuthenticated, ),
        'update_info': (IsAuthenticated, IsShop, ),
    },
    
}


class BaseUserViewSet(SuperSelectableMixin,
                      viewsets.ReadOnlyModelViewSet):
    """
    Базовый класс для работы с пользователями:
    вход, регистрация, сброс пароля, просмотр контактов и т.п.
    """

    user_type = 'buyer'

    serializer_class = shared_user_properties.get('serializer_class', tuple())
    permission_classes = shared_user_properties.get('permission_classes', tuple())
    throttle_scope = shared_user_properties.get('throttle_scope', None)
    queryset = shared_user_properties.get('queryset', tuple())

    ordering_fields = shared_user_properties.get('ordering_fields', tuple())
    search_fields = shared_user_properties.get('search_fields', tuple())
    ordering = shared_user_properties.get('ordering', tuple())

    action_serializers = shared_user_properties.get('action_serializers', {})
    action_throttles = shared_user_properties.get('action_throttles', {})
    action_descriptions = shared_user_properties.get('action_descriptions', {})
    action_querysets = shared_user_properties.get('action_querysets', {})
    action_permissions = shared_user_properties.get('action_permissions', {})

    @action(detail=False, methods=('get',), name='Get reCaptcha public key',
            url_name='captcha', url_path='captcha',
            schema=CaptchaInfoSchema(),
            )
    @method_decorator(never_cache)
    def captcha(self, request, *args, **kwargs):
        """
        Запрос публичного ключа для reCaptcha 
        """
        return ResponseOK(public_key=settings.GR_CAPTCHA_SITE_KEY)


    @action(detail=False, methods=('post',), name='Get authorization token',
            url_name='login', url_path='login',
            schema=UserLoginSchema(),
            )
    @method_decorator(never_cache)
    def login(self, request, *args, **kwargs):
        """
        Запрос токена для авторизации 
        """
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data
        user = authenticate(request, username=data['email'], password=data['password'])
        if user is None:
            return Response({'Status': False, 'Errors': t('Не удалось авторизовать')})
        if user.is_active:
            token, _ = Token.objects.get_or_create(user=user)
        return ResponseOK(token=token.key)

    @action(detail=False, methods=('post',), name='Register account',
            url_name='register', url_path='register',
            schema=SimpleCreatorSchema(),
            )
    @method_decorator(never_cache)
    def register(self, request, *args, **kwargs):       
        """
        Регистрация покупателей
        """
        serializer = self.get_serializer_class()(data=request.data, context={user_type: user_type})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        new_user_registered.send(sender=self.__class__, user_id=user.id)
        return ResponseCreated()

    @action(detail=False, methods=('post',), name='Confirm account',
            url_name='confirm', url_path='confirm',
            schema=SimpleActionSchema(),
            )
    @method_decorator(never_cache)
    def confirm(self, request, *args, **kwargs):
        """
        Подтверждение регистрации покупателя
        """
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        token = ConfirmEmailToken.objects.filter(user__email=data['email'],
                                                 key=data['token']).first()
        if not token:
            return ResponseBadRequest('Неправильно указан токен или email')

        token.user.is_active = True
        token.user.save()
        token.delete()

        return ResponseOK()

    # получить данные
    @action(detail=False, methods=('get', 'put', ), name='Account details',
            url_name='details', url_path='details',
            schema=SimpleActionSchema(),
            )
    @method_decorator(never_cache)
    def details(self, request, *args, **kwargs):
        """
        Информация об акаунте пользователя
        """
        if request.method == 'GET':
            serializer = self.get_serializer_class()(request.user, context={'request': request})
            return Response(serializer.data)
        else:
            serializer = self.get_serializer_class()(request.user, data=request.data, partial=True, context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return ResponseOK()


class UserViewSet(BaseUserViewSet):
    """
    Класс для работы с покупателями
    """
    
    serializer_class = shared_user_properties.get('serializer_class', tuple())
    permission_classes = shared_user_properties.get('permission_classes', tuple())
    throttle_scope = shared_user_properties.get('throttle_scope', None)
    queryset = shared_user_properties.get('queryset', tuple())

    ordering_fields = shared_user_properties.get('ordering_fields', tuple())
    search_fields = shared_user_properties.get('search_fields', tuple())
    ordering = shared_user_properties.get('ordering', tuple())

    action_serializers = shared_user_properties.get('action_serializers', {})
    action_throttles = shared_user_properties.get('action_throttles', {})
    action_descriptions = shared_user_properties.get('action_descriptions', {})
    action_querysets = shared_user_properties.get('action_querysets', {})
    action_permissions = shared_user_properties.get('action_permissions', {})


class PartnerViewSet(BaseUserViewSet):
    """
    Класс для работы с поставщиком
    """

    user_type = 'shop'

    serializer_class = shared_user_properties.get('serializer_class', tuple())
    permission_classes = shared_user_properties.get('permission_classes', tuple())
    throttle_scope = shared_user_properties.get('throttle_scope', None)
    queryset = shared_user_properties.get('queryset', tuple())

    ordering_fields = shared_user_properties.get('ordering_fields', tuple())
    search_fields = shared_user_properties.get('search_fields', tuple())
    ordering = shared_user_properties.get('ordering', tuple())

    action_serializers = shared_user_properties.get('action_serializers', {})
    action_throttles = shared_user_properties.get('action_throttles', {})
    action_descriptions = shared_user_properties.get('action_descriptions', {})
    action_querysets = shared_user_properties.get('action_querysets', {})
    action_permissions = shared_user_properties.get('action_permissions', {})


    @action(detail=False, methods=('post',), name='Load partner information',
            url_name='update', url_path='update',
            schema=PartnerUpdateSchema(),
            )
    @method_decorator(never_cache)
    # @method_decorator(cache_page(60*60*2))
    def update_info(self, request, *args, **kwargs):
        """
        Обновление прайса от поставщика из указанного url или загруженного файла
        """

        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        return load_partner_info(data.get('url'), data.get('file'), request.user.id)


class ContactViewSet(ViewSetViewSerializersMixin, ViewSetViewDescriptionsMixin, viewsets.ModelViewSet):
    """
    Класс для работы с контактами покупателей
    """

    permission_classes = (IsAuthenticated, )
    serializer_class = ContactSerializer

    filterset_fields = ('city', )
    ordering_fields = ('person', 'id', )
    search_fields = ('person', 'phone', 'city', 'street', 'house', 'structure', 'building', 'apartment', )
    ordering = ('person', )

    action_descriptions = {
        'list': t('Список контактов текущего пользователя'),
        'retrieve': t('Контакт текущего пользователя'),
    }

    action_serializers = {
        'bulk_delete': ContactBulkDeleteSerializer,
    }


    def get_queryset(self):
        return self.request.user.contacts.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer_class()(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            Contact.objects.create(user=request.user, **data)
        except Exception as e:
            return ResponseBadRequest(e)

        return ResponseCreated()

    @action(detail=False, methods=('delete', ), name='Bulk delete contact information',
            url_name='bulkdelete', url_path='bulkdelete',
            schema=SimpleActionSchema(),
            )
    def bulk_delete(self, request, *args, **kwargs):
        """
        Групповое удаление (не работает в веб апи)
        """
        items_sting = request.data.get('items')
        if not items_sting:
            return ResponseBadRequest('Не указаны все необходимые аргументы')

        items_list = items_sting.split(',')
        query = Q()
        objects_to_delete = 0
        for contact_id in items_list:
            contact_id = to_positive_int(contact_id)
            if contact_id is None:
                return ResponseBadRequest('id контакта должен быть положительным числом')
            query = query | Q(user_id=request.user.id, id=contact_id)
            objects_to_delete += 1

        deleted_count = 0
        try:
            with transaction.atomic():
                deleted_count = Contact.objects.filter(query).delete()[0] if objects_to_delete else 0
                if deleted_count != objects_to_delete:
                    raise Exception()
        except Exception:
            return ResponseBadRequest('Не удалось найти и удалить все указанные объекты. Операция отменена.')

        return ResponseOK(Deleted=deleted_count)


class CategoryViewSet(ViewSetViewSerializersMixin, viewsets.ReadOnlyModelViewSet):
    """
    Просмотр категорий
    """

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    throttle_scope = 'categories'

    action_serializers = {
        'retrieve': CategoryDetailSerializer,
    }

    ordering_fields = ('name', 'id', )
    search_fields = ('name', )
    ordering = ('name', )


class ShopViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Просмотр магазинов
    """

    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer
    throttle_scope = 'shops'
    filterset_fields = ('state', )
    ordering_fields = ('name', 'id', )
    search_fields = ('name', )
    ordering = ('name', )


class ProductParametersViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Класс для поиска товаров
    """

    queryset = ProductParameter.objects.all()
    serializer_class = ProductParameterSerializer

    filterset_fields = ('parameter__name', 'value' )
    ordering_fields = ('parameter__name', 'id', 'value', )
    search_fields = ('parameter__name', 'value', )
    ordering = ('parameter__name', )


class ProductInfoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Класс для поиска товаров
    """

    serializer_class = ProductInfoSerializer

    filterset_fields = ('shop', )
    ordering_fields = ('product', 'shop', 'quantity', 'price', 'price_rrc', 'id', )
    search_fields = ('product__name', 'shop__name', )
    ordering = ('product', )
    

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


####################################################################################################

# from django.conf import settings
# from django.contrib.auth import authenticate
# from django.contrib.auth.password_validation import validate_password
# from django.core.files.uploadedfile import InMemoryUploadedFile as FileClass
# from django.db import transaction
# from django.db.models import Q
# from django.urls import resolve
# from django.utils.decorators import method_decorator
# from django.utils.translation import gettext_lazy as t
# from django.views.decorators.cache import cache_page, never_cache
# from django.views.decorators.vary import vary_on_headers
# from rest_framework import viewsets
# from rest_framework.authtoken.models import Token
# from rest_framework.decorators import api_view
# from rest_framework.generics import ListAPIView, RetrieveAPIView
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.response import Response
# from rest_framework.reverse import reverse
# from rest_framework.views import APIView

# from core.models import Category, Shop
# from core.partner_info_loader import load_partner_info
# from core.utils import ViewSetViewSerializersMixin
# from rest_auth.models import ConfirmEmailToken, Contact, ADDRESS_ITEMS_LIMIT
# from .serializers import UserSerializer, CategorySerializer, CategoryDetailSerializer, \
#     SeparateContactSerializer, \
#     ShopSerializer, ProductInfoSerializer
# from .signals import new_user_registered, new_order


# @cache_page(settings.CACHE_TIMES['ROOT_API'])
# @api_view(['GET'])
# def api_root(request, *args, format=None, **kwargs):
#     app_name = resolve(request.path).app_name 
#     return Response({
#         'partner/update': reverse(f'{app_name}:partner-update', request=request, format=format),
#         'user/login': reverse(f'{app_name}:user-login', request=request, format=format),
#         'user/register': reverse(f'{app_name}:user-register', request=request, format=format),
#         'user/register/confirm': reverse(f'{app_name}:user-register-confirm', request=request, format=format),
#         'user/password_reset': reverse(f'{app_name}:password-reset', request=request, format=format),
#         'user/password_reset/confirm': reverse(f'{app_name}:password-reset-confirm', request=request, format=format),
#         'user/details': reverse(f'{app_name}:user-details', request=request, format=format),
#         'categories': reverse(f'{app_name}:categories', request=request, format=format),
#         'user/contact': reverse(f'{app_name}:user-contact', request=request, format=format),
#         'shops': reverse(f'{app_name}:shops', request=request, format=format),
#         'products': reverse(f'{app_name}:products', request=request, format=format),
#         'docs': reverse(f'{app_name}:openapi-schema', request=request, format=format),
#         'swagger-ui': reverse(f'{app_name}:swagger-ui', request=request, format=format),
#         'redoc': reverse(f'{app_name}:redoc', request=request, format=format),
#     })


# class PartnerUpdate(APIView):
#     """
#     Класс для обновления прайса от поставщика
#     """

#     throttle_scope = 'partner_update'
#     permission_classes = [IsAuthenticated]

#     @method_decorator(never_cache)
#     def post(self, request, *args, **kwargs):

#         if request.user.type != 'shop':
#             return Response({'Status': False, 'Error': t('Только для магазинов')}, status=403)

#         url = request.data.get('url')
#         file_obj = request.data.get('file')

#         return load_partner_info(url, file_obj, request.user.id)


# class LoginAccount(APIView):
#     """
#     Класс для авторизации пользователей
#     """

#     @method_decorator(never_cache)
#     def post(self, request, *args, **kwargs):

#         if not {'email', 'password'}.issubset(request.data):
#             return Response({'Status': False, 'Errors': t('Не указаны все необходимые аргументы')})

#         user = authenticate(request, username=request.data['email'], password=request.data['password'])

#         if user is None:
#             return Response({'Status': False, 'Errors': t('Не удалось авторизовать')})

#         if user.is_active:
#             token, _ = Token.objects.get_or_create(user=user)

#         return Response({'Status': True, 'Token': token.key})       


# class RegisterAccount(APIView):
#     """
#     Для регистрации покупателей
#     """

#     @method_decorator(never_cache)
#     def post(self, request, *args, **kwargs):

#         # проверяем обязательные аргументы
#         if not {'first_name', 'last_name', 'email', 'password', 'company', 'position'}.issubset(request.data):
#             return Response({'Status': False, 'Errors': t('Не указаны все необходимые аргументы')})

#         # проверяем пароль на сложность

#         try:
#             validate_password(request.data['password'])
#         except Exception as password_error:
#             error_array = []
#             # noinspection PyTypeChecker
#             for item in password_error:
#                 error_array.append(item)
#             return Response({'Status': False, 'Errors': {'password': error_array}})

#         # проверяем данные для уникальности имени пользователя
#         # request.data._mutable = True # request.data = request.data.copy()
#         # request.data.update({})
#         user_serializer = UserSerializer(data=request.data)
#         if not user_serializer.is_valid():
#             return Response({'Status': False, 'Errors': user_serializer.errors})

#         # сохраняем пользователя
#         user = user_serializer.save()
#         user.set_password(request.data['password'])
#         user.save()
#         new_user_registered.send(sender=self.__class__, user_id=user.id)
#         return Response({'Status': True}, status=201)


# class ConfirmAccount(APIView):
#     """
#     Класс для подтверждения почтового адреса
#     """

#     @method_decorator(never_cache)
#     def post(self, request, *args, **kwargs):

#         # проверяем обязательные аргументы
#         if not {'email', 'token'}.issubset(request.data):
#             return Response({'Status': False, 'Errors': t('Не указаны все необходимые аргументы')})

#         token = ConfirmEmailToken.objects.filter(user__email=request.data['email'],
#                                                  key=request.data['token']).first()
#         if not token:
#             return Response({'Status': False, 'Errors': t('Неправильно указан токен или email')})

#         token.user.is_active = True
#         token.user.save()
#         token.delete()
#         return Response({'Status': True})
        

# class AccountDetails(APIView):
#     """
#     Класс для работы с данными пользователя
#     """

#     permission_classes = [IsAuthenticated]

#     # получить данные
#     @method_decorator(never_cache)
#     def get(self, request, *args, **kwargs):
#         serializer = UserSerializer(request.user)
#         return Response(serializer.data)

#     # Редактирование методом PUT
#     @method_decorator(never_cache)
#     def put(self, request, *args, **kwargs):

#         # проверяем обязательные аргументы
#         if 'password' in request.data:
#             # проверяем пароль на сложность
#             try:
#                 validate_password(request.data['password'])
#             except Exception as password_error:
#                 error_array = []
#                 # noinspection PyTypeChecker
#                 for item in password_error:
#                     error_array.append(item)
#                 return Response({'Status': False, 'Errors': {'password': error_array}})
#             else:
#                 request.user.set_password(request.data['password'])

#         if 'contacts' in request.data:
#             contacts = request.data['contacts']
#             if not isinstance(contacts, list) or len(contacts) > ADDRESS_ITEMS_LIMIT:
#                 return Response({'Status': False, 'Errors': t('Число контактов должно быть не более {}').format(ADDRESS_ITEMS_LIMIT)})

#         # проверяем остальные данные
#         user_serializer = UserSerializer(request.user, data=request.data, partial=True)
#         if user_serializer.is_valid():
#             user_serializer.save()
#             return Response({'Status': True})
#         else:
#             return Response({'Status': False, 'Errors': user_serializer.errors})


# class CategoryView(ListAPIView):
#     """
#     Класс для просмотра категорий
#     """

#     throttle_scope = 'categories'

#     queryset = Category.objects.all()
#     serializer_class = CategorySerializer


# class CategoryDetailView(RetrieveAPIView):
#     """
#     Класс для просмотра категорий
#     """

#     throttle_scope = 'categories'

#     queryset = Category.objects.all()
#     serializer_class = CategoryDetailSerializer


# class ContactView(APIView):
#     """
#     Класс для работы с контактами покупателей
#     """

#     permission_classes = [IsAuthenticated]

#     # получить мои контакты
#     @method_decorator(vary_on_headers('Authorization'))
#     def get(self, request, *args, **kwargs):
#         contact = Contact.objects.filter(user_id=request.user.id)
#         serializer = SeparateContactSerializer(contact, many=True)
#         return Response(serializer.data)

#     # добавить новый контакт
#     @method_decorator(never_cache)
#     def post(self, request, *args, **kwargs):

#         if not 'phone' in request.data and not all([x in request.data for x in ('city', 'street', 'house')]):
#             return Response({'Status': False, 'Errors': t('Не указаны все необходимые аргументы')})

#         if Contact.objects.filter(user_id=request.user.id).count() >= ADDRESS_ITEMS_LIMIT:
#             return Response({'Status': False,
#                              'Errors': t('Нельзя добавить новый контакт. Уже добавлено {} контактов').format(ADDRESS_ITEMS_LIMIT)})

#         data = request.data.copy()
#         data.update({'user': request.user.id})
#         serializer = SeparateContactSerializer(data=data)

#         if not serializer.is_valid():
#             Response({'Status': False, 'Errors': serializer.errors})

#         serializer.save()
#         return Response({'Status': True, 'data': serializer.data}, status=201)
        
#     # удалить контакт
#     @method_decorator(never_cache)
#     def delete(self, request, *args, **kwargs):

#         items_sting = request.data.get('items')
#         if not items_sting:
#             return Response({'Status': False, 'Errors': t('Не указаны все необходимые аргументы')})

#         items_list = items_sting.split(',')
#         query = Q()
#         objects_to_delete = 0
#         for contact_id in items_list:
#             contact_id = to_positive_int(contact_id)
#             if contact_id is None:
#                 return Response({'Status': False, 'Errors': t('id контакта должен быть положительным числом')})
#             query = query | Q(user_id=request.user.id, id=contact_id)
#             objects_to_delete += 1

#         deleted_count = 0
#         try:
#             with transaction.atomic():
#                 deleted_count = Contact.objects.filter(query).delete()[0] if objects_to_delete else 0
#                 if deleted_count != objects_to_delete:
#                     raise Exception()
#         except Exception:
#             return Response({'Status': False, 'Error': t('Не удалось найти и удалить все указанные объекты. Операция отменена.')})

#         return Response({'Status': True, 'Deleted': deleted_count})

#     # редактировать контакт (полностью)
#     @method_decorator(never_cache)
#     def put(self, request, *args, **kwargs):

#         if 'id' not in request.data or \
#             (not 'phone' in request.data and not all([x in request.data for x in ('city', 'street', 'house')])):
#                 return Response({'Status': False, 'Errors': t('Не указаны все необходимые аргументы')})

#         if to_positive_int(request.data['id']) is None:
#             return Response({'Status': False, 'Errors': t('id контакта должен быть положительным числом')})

#         contact = Contact.objects.filter(id=request.data['id'], user_id=request.user.id).first()
#         if not contact:
#             return Response({'Status': False, 'Errors': t('Не найден контакт с id {}').format(request.data['id'])})

#         data = request.data.copy()
#         data.update({'user': request.user.id})

#         serializer = SeparateContactSerializer(contact, data=data)
#         if not serializer.is_valid():
#             return Response({'Status': False, 'Errors': serializer.errors})

#         serializer.save()
#         return Response({'Status': True})

#     # редактировать контакт (частично)
#     @method_decorator(never_cache)
#     def patch(self, request, *args, **kwargs):

#         if 'id' not in request.data:
#             return Response({'Status': False, 'Errors': t('Не указаны все необходимые аргументы')})

#         if to_positive_int(request.data['id']) is None:
#             return Response({'Status': False, 'Errors': t('id контакта должен быть положительным числом')})

#         contact = Contact.objects.filter(id=request.data['id'], user_id=request.user.id).first()
#         if not contact:
#             return Response({'Status': False, 'Errors': t('Не найден контакт с id {}').format(request.data['id'])})

#         serializer = SeparateContactSerializer(contact, data=request.data, partial=True)
#         if not serializer.is_valid():
#             return Response({'Status': False, 'Errors': serializer.errors})

#         serializer.save()
#         return Response({'Status': True})

        
# class ShopView(ListAPIView):
#     """
#     Класс для просмотра списка магазинов
#     """

#     throttle_scope = 'shops'

#     queryset = Shop.objects.filter(state=True)
#     serializer_class = ShopSerializer


# class ShopDetailView(ListAPIView):
#     """
#     Класс для просмотра списка магазинов
#     """

#     throttle_scope = 'shops'

#     queryset = Shop.objects.filter(state=True)
#     serializer_class = ShopSerializer


# class ProductInfoView(ListAPIView):
#     """
#     Класс для поиска товаров
#     """

#     queryset = Shop.objects.filter(state=True)
#     serializer_class = ProductInfoSerializer

#     def get_queryset(self):

#         query = Q(shop__state=True)
#         shop_id = self.request.query_params.get('shop_id')
#         category_id = self.request.query_params.get('category_id')

#         if shop_id:
#             query = query & Q(shop_id=shop_id)

#         if category_id:
#             query = query & Q(product__category_id=category_id)

#         # фильтруем и отбрасываем дубликаты
#         return ProductInfo.objects.filter(
#             query).select_related(
#             'shop', 'product__category').prefetch_related(
#             'product_parameters__parameter').distinct()

