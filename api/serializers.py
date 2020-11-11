from collections import OrderedDict
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError, ObjectDoesNotExist, PermissionDenied, FieldError
from django.db.utils import Error as DBError, ConnectionDoesNotExist
from django.utils.translation import gettext_lazy as t
from recaptcha.fields import ReCaptchaField
from rest_framework import serializers

from core.models import Category, Shop, ProductInfo, Product, ProductParameter, OrderItem, Order
from core.serializers import DefaultSerializer, DefaultModelSerializer, ModelPresenter
from core.utils import is_dict
from core.validators import NotBlankTogetherValidator, EqualTogetherValidator
from rest_auth.models import User, Contact, ADDRESS_ITEMS_LIMIT


class PartnerUpdateSerializer(DefaultSerializer):
    url = serializers.URLField(required=False, help_text=t('Путь к загружаемому файлу'), label=t('URL path'))
    file = serializers.FileField(required=False, help_text=t('Файл, передаваемый через http'), label=t('File field'))

    class Meta:
        write_only_fields = ('url', 'file', )
        validators = (
            NotBlankTogetherValidator(fields=('url', 'file', )),
        )


class ContactSerializer(DefaultModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'
        read_only_fields = ('id', 'url', 'user', )

        extra_kwargs = {
            'person': {'default': ''},
            'phone': {'default': ''},
            'city': {'default': ''},
            'street': {'default': ''},
            'house': {'default': ''},
            'structure': {'default': ''},
            'building': {'default': ''},
            'apartment': {'default': ''},
        }

    def validate(self, data):
        phone = data.get('phone')
        city = data.get('city')
        street = data.get('street')
        house = data.get('house')
        if not phone and not all((city, street, house, )):
            raise serializers.ValidationError(dict(Errors=t('Не указаны все необходимые аргументы. Нужно указать хотябы телефон или город/улицу/дом')))
        return super(ContactSerializer, self).validate(data)

    
class ContactBulkDeleteSerializer(DefaultSerializer):
    # items = serializers.ListField(child=serializers.IntegerField(min_value=0), write_only=True)
    items = serializers.CharField()


class UserLoginSerializer(DefaultSerializer):
    email = serializers.EmailField(required=True, allow_blank=False, label=t('Email'), help_text=t('Iput email'))
    password = serializers.CharField(required=True, allow_blank=False, style={'input_type': 'password'}, label=t('Password'), help_text=t('Iput password'))
    token = serializers.CharField(read_only=True, label=t('Auth token'), help_text=t('Auth token'))
    recaptcha = ReCaptchaField(write_only=True)


class CaptchaInfoSerializer(DefaultSerializer):
    public_key = serializers.CharField(read_only=True, label=t('reCaptcha public key'), help_text=t('reCaptcha public key'))



class ListUserSerializer(DefaultModelSerializer):

    def get_fields(self, *args, **kwargs):
        fields = super(ListUserSerializer, self).get_fields(*args, **kwargs)
        if self.context['view'].basename == 'partner':
           fields['url'] = serializers.HyperlinkedIdentityField(view_name='api:partner-detail')
        return fields

    class Meta:
        model = User
        fields = ('url', 'id', 'first_name', 'last_name', 'email', 'company', 'position', 'Errors', 'Status', )
        read_only_fields = ('url', 'id', 'first_name', 'last_name', 'email', 'company', 'position', )


class RegisterUserSerializer(DefaultModelSerializer):

    contacts = ContactSerializer(many=True, required=False)
    password = serializers.CharField(write_only=True, required=True, allow_blank=False, style={'input_type': 'password'},
                                     label=t('Password'), help_text=t('Iput password'),
                                     validators=(validate_password, ))
    password2 = serializers.CharField(write_only=True, required=True, allow_blank=False, style={'input_type': 'password'},
                                      label=t('Repeat Password'), help_text=t('Iput password again'),
                                      validators=(validate_password, ))
    recaptcha = ReCaptchaField(write_only=True)

    class Meta:
        model = User
        fields = ('url', 'id', 'first_name', 'last_name', 'email', 'company', 'position', 'password', 'password2', 'recaptcha', 'contacts', 'Errors', 'Status',)
        read_only_fields = ('url', 'id',)
        extra_kwargs = {
            'first_name': {'required': True, 'allow_blank': False},
            'last_name': {'required': True, 'allow_blank': False},
            'company': {'required': True, 'allow_blank': False},
            'position': {'required': True, 'allow_blank': False},
        }
        validators = (
            EqualTogetherValidator(fields=('password', 'password2', )),
        )

    def create(self, validated_data):
        contact_data = validated_data.pop('contacts', [])
        password = validated_data.pop('password')
        validated_data.pop('password2')
        validated_data.pop('recaptcha')
            
        user = User.objects.create(**validated_data, type=self.context['user_type'])
        user.set_password(password)

        for contact in contact_data:
            try:
                contact = Contact.objects.create(user_id=user.id, **contact)
                user.contacts.add(contact)
            except (DBError, ValidationError, ObjectDoesNotExist, PermissionDenied, FieldError, ConnectionDoesNotExist):
                break

        user.save()

        return user

    def validate(self, data):
        contacts=data.get('contacts')
        if contacts and (not isinstance(contacts, list) or len(contacts) > ADDRESS_ITEMS_LIMIT):
            raise serializers.ValidationError(dict(contacts=t('Число контактов должно быть не более {}').format(ADDRESS_ITEMS_LIMIT)))
        return super(RegisterUserSerializer, self).validate(data)


class RetrieveUserDetailsSerializer(DefaultModelSerializer):

    ContactSerializer = ModelPresenter(Contact, ('url', 'person', 'phone', 'city', 'street', 'house', 'structure', 'building', 'apartment'))

    contacts = ContactSerializer(many=True, required=False)

    def get_fields(self, *args, **kwargs):
        fields = super(RetrieveUserDetailsSerializer, self).get_fields(*args, **kwargs)
        if self.context['view'].basename == 'partner':
           fields['url'] = serializers.HyperlinkedIdentityField(view_name='api:partner-detail')
        return fields

    class Meta:
        model = User
        fields = ('url', 'id', 'first_name', 'last_name', 'email', 'company', 'position', 'contacts', 'Errors', 'Status', )
        read_only_fields = ('url', 'id', 'first_name', 'last_name', 'email', 'company', 'position', 'contacts', )


class UpdateUserDetailsSerializer(DefaultModelSerializer):

    contacts = ContactSerializer(many=True, required=False)
    password = serializers.CharField(write_only=True, required=True, allow_blank=False, style={'input_type': 'password'},
                                     label=t('Password'), help_text=t('Iput password'),
                                     validators=(validate_password, ))
                        

    class Meta:
        model = User
        fields = ('url', 'id', 'first_name', 'last_name', 'email', 'company', 'position', 'password', 'contacts', 'Errors', 'Status', )
        read_only_fields = ('url', 'id',)

    def update(self, instance, validated_data):
        contact_data = validated_data.pop('contacts', None)
        password = validated_data.pop('password', None)

        instance = super(UpdateUserDetailsSerializer, self).update(instance, validated_data)
        if password:
            instance.set_password(password)

        if contact_data:
            Contact.objects.filter(user_id=instance.id).delete()
            for contact in contact_data:
                try:
                    contact, _ = Contact.objects.get_or_create(user_id=instance.id, **contact)
                    instance.contacts.add(contact)
                except (DBError, ValidationError, ObjectDoesNotExist, PermissionDenied, FieldError, ConnectionDoesNotExist):
                    break

        instance.save()
        return instance

    def validate(self, data):
        contacts=data.get('contacts')
        if contacts and (not isinstance(contacts, list) or len(contacts) > ADDRESS_ITEMS_LIMIT):
            raise serializers.ValidationError(dict(contacts=t('Число контактов должно быть не более {}').format(ADDRESS_ITEMS_LIMIT)))
        return super(UpdateUserDetailsSerializer, self).validate(data)


class ConfirmUserSerializer(DefaultSerializer):
    email = serializers.EmailField(required=True, allow_blank=False, label=t('Email'), help_text=t('Iput email'))
    token = serializers.CharField(required=True, allow_blank=False, label=t('Auth token'), help_text=t('Auth token'))


class CategorySerializer(DefaultModelSerializer):
    class Meta:
        model = Category
        fields = ('url', 'id', 'name', 'Errors', 'Status', )
        read_only_fields = ('url', 'id', )


class CategoryDetailSerializer(DefaultModelSerializer):
    class Meta:
        model = Category
        fields = ('url', 'id', 'name', 'shops', 'Errors', 'Status', )
        read_only_fields = ('url', 'id', )


class ShopSerializer(DefaultModelSerializer):
    class Meta:
        model = Shop
        fields = ('url', 'id', 'name', 'state', 'Errors', 'Status', )
        read_only_fields = ('url', 'id', 'name', )


class ProductParameterSerializer(DefaultModelSerializer):
    parameter = serializers.StringRelatedField(label=t('Параметр товара'), help_text=t('Параметр товара'))

    class Meta:
        model = ProductParameter
        fields = ('url', 'id', 'parameter', 'value', 'Errors', 'Status', )


class ProductInfoSerializer(DefaultModelSerializer):

    ShopSerializer = ModelPresenter(Shop, ('url', 'name', ))
    ProductParameterSerializer = ModelPresenter(ProductParameter, ('parameter', 'value', ), {'parameter': serializers.StringRelatedField()})
    CategorySerializer = ModelPresenter(Category, ('url', 'id', 'name', ))
    ProductSerializer = ModelPresenter(Product, ('name', 'category', ), {'category': CategorySerializer()})

    product = ProductSerializer(read_only=True, label=t('Товар'), help_text=t('ДАнные по товару'))
    product_parameters = ProductParameterSerializer(read_only=True, many=True, label=t('Параметры'), help_text=t('Параметры товара'))
    shop = ShopSerializer(read_only=True, label=t('Магазин'), help_text=t('Данные по магазину'))

    class Meta:
        model = ProductInfo
        fields = ('url', 'id', 'product', 'shop', 'quantity', 'price', 'price_rrc', 'product_parameters', 'Errors', 'Status', )
        read_only_fields = ('url', 'id', )


class AddOrderItemSerializer(DefaultModelSerializer):
    items = serializers.JSONField(required=False)
    product_info = serializers.PrimaryKeyRelatedField(
        queryset=ProductInfo.objects.select_related('shop', 'product').prefetch_related('shop__user').all())
    class Meta:
        model = OrderItem
        fields = ('product_info', 'quantity', 'items', 'Errors', 'Status', )


class ShowBasketSerializer(DefaultModelSerializer):
    ShopSerializer = ModelPresenter(Shop, ('id', 'url', 'name', ))
    ProductInfoSerializer = ModelPresenter(ProductInfo, ('id', 'url', 'product', 'shop', 'price', 'price_rrc' ), {'product': serializers.StringRelatedField(), 'shop': ShopSerializer()})
    OrderedItemsSerializer = ModelPresenter(OrderItem, ('id', 'product_info', 'quantity' ), {'product_info': ProductInfoSerializer()})

    ordered_items = OrderedItemsSerializer(read_only=True, many=True, label=t('Заказанные товары'), help_text=t('Заказанные товары'))

    total_sum = serializers.DecimalField(read_only=True, max_digits=20, decimal_places=2, min_value=0, label=t('Total'), help_text=t('Общая сумма'))

    class Meta:
        model = Order
        fields = ('ordered_items', 'total_sum', 'Errors', 'Status', )


class OrderSerializer(DefaultModelSerializer):
    OrderedItemsSerializer = ModelPresenter(OrderItem, ('product_info', ), {'product_info': ProductInfoSerializer()})
    ordered_items = OrderedItemsSerializer(read_only=True, many=True, label=t('Заказанные товары'), help_text=t('Заказанные товары'))

    total_sum = serializers.DecimalField(read_only=True, max_digits=20, decimal_places=2, min_value=0, label=t('Total'), help_text=t('Общая сумма'))
    contact = ContactSerializer(read_only=True, label=t('Контакт'), help_text=t('Контактные данные, указанные заказчиком'))

    class Meta:
        model = Order
        fields = ('url', 'id', 'ordered_items', 'state', 'dt', 'total_sum', 'contact', 'Errors', 'Status', )
        read_only_fields = ('url', 'id', 'state')


class OrderItemsStringSerializer(DefaultModelSerializer):
    # items = serializers.ListField(child=serializers.IntegerField(min_value=0))
    items = serializers.CharField()
    class Meta:
        model = OrderItem
        fields = ('items', 'Errors', 'Status',  )


class BasketSetQuantitySerializer(DefaultModelSerializer):
    class KeyField(serializers.PrimaryKeyRelatedField):
        def get_queryset(self):
            if Order.objects.filter(user_id=self.context['request'].user.id, state='basket').exists():
                return Order.objects.get(user_id=self.context['request'].user.id, state='basket').ordered_items.prefetch_related(
                    'product_info__shop__user', 'order__user', 'product_info__product').all()
            return OrderItem.objects.none()


    id = KeyField(required=False, read_only=False, allow_null=False)
    items = serializers.CharField()
    quantity = serializers.IntegerField(min_value=0)

    class Meta:
        model = OrderItem
        fields = ('items', 'id', 'quantity', 'Errors', 'Status',  )


class CreateOrderSerializer(DefaultModelSerializer):

    class KeyField(serializers.PrimaryKeyRelatedField):
        def get_queryset(self):
            return self.context['request'].user.contacts.all()

    contact = KeyField(required=True, read_only=False, allow_null=False)

    class Meta:
        model = Order
        fields = ('contact', 'Errors', 'Status', )
        write_only_fields = ('contact', )
        extra_kwargs = {'contact': {'required': True, 'allow_null': False}}


