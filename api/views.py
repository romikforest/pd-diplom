# from distutils.util import strtobool

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db.models import Q
# from django.db import IntegrityError
# from django.db.models import Q, Sum, F
from django.urls import resolve
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as t
from django.views.decorators.cache import cache_page, never_cache
from django.views.decorators.vary import vary_on_headers
from rest_framework import viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, action
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from core.models import Category, Shop
from core.partner_info_loader import load_partner_info
from core.utils import SelectableSerializersMixin, ResponseBadRequest, ResponseForbidden, IsShop
from rest_auth.models import ConfirmEmailToken, Contact, ADDRESS_ITEMS_LIMIT
from .serializers import UserSerializer, CategorySerializer, CategoryDetailSerializer, \
    SeparateContactSerializer, PartnerUpdateSerializer, \
    ShopSerializer, ProductInfoSerializer
# from backend.models import Order, OrderItem
# from backend.serializers import  \
#     OrderItemSerializer, OrderSerializer

from .schemas import PartnerUpdateSchema
from .signals import new_user_registered, new_order




# class FooViewSet(viewsets.ModelViewSet):
#         queryset = Foo.objects.all()
#         serializer_class = FooSerializer

#         def get_throttles(self):
#             if self.action in ['delete', 'validate']:
#                 self.throttle_scope = 'foo.' + self.action
#             return super().get_throttles()

#         @list_route()
#         def validate(self, request):
#             return Response('Validation!')


class PartnerViewSet(viewsets.GenericViewSet):
    """
    Класс для работы с поставщиком
    """

    serializer_class = PartnerUpdateSerializer
    permission_classes = (IsAuthenticated, IsShop, )
    throttle_scope = 'partner_update'


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

        # if request.user.type != 'shop' and not request.user.is_superuser:
        #     return ResponseForbidden('Только для магазинов')

        url = request.data.get('url')
        file_obj = request.data.get('file')

        return load_partner_info(url, file_obj, request.user.id)


@cache_page(settings.CAHCE_TIMES['ROOT_API'])
@api_view(['GET'])
def api_root(request, *args, format=None, **kwargs):
    app_name = resolve(request.path).app_name 
    return Response({
        'partner/update': reverse(f'{app_name}:partner-update', request=request, format=format),
        'user/login': reverse(f'{app_name}:user-login', request=request, format=format),
        'user/register': reverse(f'{app_name}:user-register', request=request, format=format),
        'user/register/confirm': reverse(f'{app_name}:user-register-confirm', request=request, format=format),
        'user/password_reset': reverse(f'{app_name}:password-reset', request=request, format=format),
        'user/password_reset/confirm': reverse(f'{app_name}:password-reset-confirm', request=request, format=format),
        'user/details': reverse(f'{app_name}:user-details', request=request, format=format),
        'categories': reverse(f'{app_name}:categories', request=request, format=format),
        'user/contact': reverse(f'{app_name}:user-contact', request=request, format=format),
        'shops': reverse(f'{app_name}:shops', request=request, format=format),
        'products': reverse(f'{app_name}:products', request=request, format=format),
        'docs': reverse(f'{app_name}:openapi-schema', request=request, format=format),
        'swagger-ui': reverse(f'{app_name}:swagger-ui', request=request, format=format),
        'redoc': reverse(f'{app_name}:redoc', request=request, format=format),
    })


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


class CategoryViewSet(SelectableSerializersMixin, viewsets.ReadOnlyModelViewSet):
    """
    Просмотр категорий
    """

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    throttle_scope = 'categories'

    action_serializers = {
        'retrieve': CategoryDetailSerializer,
    }


class ShopViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Просмотр магазинов
    """

    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer
    throttle_scope = 'shops'


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
# from core.utils import SelectableSerializersMixin
# from rest_auth.models import ConfirmEmailToken, Contact, ADDRESS_ITEMS_LIMIT
# from .serializers import UserSerializer, CategorySerializer, CategoryDetailSerializer, \
#     SeparateContactSerializer, \
#     ShopSerializer, ProductInfoSerializer
# from .signals import new_user_registered, new_order


# @cache_page(settings.CAHCE_TIMES['ROOT_API'])
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

#         errors = {}

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
#             errors = {}
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

