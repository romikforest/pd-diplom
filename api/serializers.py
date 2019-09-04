from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
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

    def validate(self, data):
        phone = data.get('phone')
        city = data.get('city')
        street = data.get('street')
        house = data.get('house')
        if not phone and not all((city, street, house, )):
            raise serializers.ValidationError(dict(Errors=t('Не указаны все необходимые аргументы. Нужно указать хотябы телефон или город/улицу/дом')))
        return super(ContactSerializer, self).validate(data)

    
class ContactBulkDeleteSerializer(DefaultSerializer):
    items = serializers.ListField(child=serializers.IntegerField(min_value=0), write_only=True)
        


# class SeparateContactSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Contact
#         fields = ('id', 'person', 'phone', 'city', 'street', 'house', 'structure', 'building', 'apartment', 'user')
#         read_only_fields = ('id', )
#         extra_kwargs = {
#             'user': {'write_only': True},
#             'person': {'default': ''},
#             'phone': {'default': ''},
#             'city': {'default': ''},
#             'street': {'default': ''},
#             'house': {'default': ''},
#             'structure': {'default': ''},
#             'building': {'default': ''},
#             'apartment': {'default': ''},
#         }


class UserLoginSerializer(DefaultSerializer):
    email = serializers.EmailField(required=True, allow_blank=False, label=t('Email'), help_text=t('Iput email'))
    password = serializers.CharField(required=True, allow_blank=False, style={'input_type': 'password'}, label=t('Password'), help_text=t('Iput password'))
    token = serializers.CharField(read_only=True, label=t('Auth token'), help_text=t('Auth token'))
    recaptcha = ReCaptchaField(write_only=True)


class CaptchaInfoSerializer(DefaultSerializer):
    public_key = serializers.CharField(read_only=True, label=t('reCaptcha public key'), help_text=t('reCaptcha public key'))



class ListUserSerializer(DefaultModelSerializer):

    class Meta:
        model = User
        fields = ('url', 'id', 'first_name', 'last_name', 'email', 'company', 'position', )
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
        fields = ('url', 'id', 'first_name', 'last_name', 'email', 'company', 'position', 'password', 'password2', 'recaptcha', 'contacts')
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
        user_type = self.context.get('user_type', 'buyer')
            
        user = User.objects.create(**validated_data, type=user_type)
        user.set_password(password)

        for contact in contact_data:
            try:
                contact = Contact.objects.create(user_id=user.id, **contact)
                user.contacts.add(contact.id)
            except Exception:
                break

        user.save()

        return user

    def validate(self, data):
        contacts=data.get('contacts')
        if contacts and (not isinstance(contacts, list) or len(contacts) > ADDRESS_ITEMS_LIMIT):
            raise serializers.ValidationError(dict(contacts=t('Число контактов должно быть не более {}').format(ADDRESS_ITEMS_LIMIT)))
        return super(RegisterUserSerializer, self).validate(data)

class UpdateUserDetailsSerializer(DefaultModelSerializer):

    contacts = ContactSerializer(many=True, required=False)
    password = serializers.CharField(write_only=True, required=True, allow_blank=False, style={'input_type': 'password'},
                                     label=t('Password'), help_text=t('Iput password'),
                                     validators=(validate_password, ))

    class Meta:
        model = User
        fields = ('url', 'id', 'first_name', 'last_name', 'email', 'company', 'position', 'password', 'contacts')
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
                    instance.contacts.add(contact.id)
                except Exception:
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
        fields = ('url', 'id', 'name',)
        read_only_fields = ('url', 'id',)


class CategoryDetailSerializer(DefaultModelSerializer):
    class Meta:
        model = Category
        fields = ('url', 'id', 'name', 'shops')
        read_only_fields = ('url', 'id',)


class ShopSerializer(DefaultModelSerializer):
    class Meta:
        model = Shop
        fields = ('url', 'id', 'name', 'state',)
        read_only_fields = ('url', 'id',)


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'category')


class ProductParameterSerializer(DefaultModelSerializer):
    parameter = serializers.StringRelatedField()

    class Meta:
        model = ProductParameter
        fields = ('url', 'id', 'parameter', 'value',)


class ProductInfoSerializer(DefaultModelSerializer):

    ShopSerializer = ModelPresenter(Shop, ('url', 'name', ))
    ProductParameterSerializer = ModelPresenter(ProductParameter, ('parameter', 'value', ), {'parameter': serializers.StringRelatedField()})
    CategorySerializer = ModelPresenter(Category, ('url', 'id', 'name', ))
    ProductSerializer = ModelPresenter(Product, ('name', 'category', ), {'category': CategorySerializer()})

    product = ProductSerializer(read_only=True)
    product_parameters = ProductParameterSerializer(read_only=True, many=True)
    shop = ShopSerializer(read_only=True)

    class Meta:
        model = ProductInfo
        fields = ('url', 'id', 'product', 'shop', 'quantity', 'price', 'price_rrc', 'product_parameters',)
        read_only_fields = ('url', 'id',)


class OrderItemSerializer(DefaultModelSerializer):
    class Meta:
        model = OrderItem
        fields = ('url', 'id', 'product_info', 'quantity', 'order',)
        read_only_fields = ('url', 'id',)
        extra_kwargs = {
            'order': {'write_only': True}
        }


class OrderItemCreateSerializer(OrderItemSerializer):
    product_info = ProductInfoSerializer(read_only=True)


class OrderSerializer(DefaultModelSerializer):
    ordered_items = OrderItemCreateSerializer(read_only=True, many=True)

    total_sum = serializers.IntegerField()
    contact = ContactSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ('url', 'id', 'ordered_items', 'state', 'dt', 'total_sum', 'contact',)
        read_only_fields = ('url', 'id', )


