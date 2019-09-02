from django.utils.translation import gettext_lazy as t
from rest_framework import serializers
from rest_auth.models import User, Contact
from core.models import Category, Shop, ProductInfo, Product, ProductParameter, OrderItem, Order


class DefaultSerializer(serializers.Serializer):
    Error = serializers.SerializerMethodField(read_only=True, help_text=t('Error message(s)'), label=t('Error'))
    Status = serializers.SerializerMethodField(read_only=True, help_text=t('Http Status code'), label=t('Status code'))

class DefaultModelSerializer(serializers.ModelSerializer):
    Error = serializers.SerializerMethodField(read_only=True, help_text=t('Error message(s)'), label=t('Error'))
    Status = serializers.SerializerMethodField(read_only=True, help_text=t('Http Status code'), label=t('Status code'))


class PartnerUpdateSerializer(DefaultSerializer):
    url = serializers.URLField(required=False, help_text=t('Путь к загружаемому файлу'), label=t('URL path'))
    file = serializers.FileField(required=False, help_text=t('Файл, передаваемый через http'), label=t('File field'))

    class Meta:
        write_only_fields = ('url', 'file', )


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ('id', 'person', 'phone', 'city', 'street', 'house', 'structure', 'building', 'apartment')
        read_only_fields = ('id', )


class SeparateContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ('id', 'person', 'phone', 'city', 'street', 'house', 'structure', 'building', 'apartment', 'user')
        read_only_fields = ('id', )
        extra_kwargs = {
            'user': {'write_only': True},
            'person': {'default': ''},
            'phone': {'default': ''},
            'city': {'default': ''},
            'street': {'default': ''},
            'house': {'default': ''},
            'structure': {'default': ''},
            'building': {'default': ''},
            'apartment': {'default': ''},
        }


class UserLoginSerializer(DefaultSerializer):
    email = serializers.EmailField(required=True, allow_blank=False, label=t('Email'), help_text=t('Iput email'))
    password = serializers.CharField(required=True, allow_blank=False, style={'input_type': 'password'}, label=t('Password'), help_text=t('Iput password'))
    password2 = serializers.CharField(required=True, allow_blank=False, style={'input_type': 'password'}, label=t('Repeat Password'), help_text=t('Iput password again'))
    token = serializers.SerializerMethodField(read_only=True)



class UserSerializer(serializers.ModelSerializer):
    contacts = ContactSerializer(many=True, required=False)

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 'company', 'position', 'contacts')
        read_only_fields = ('id',)

    def create(self, validated_data):
        contact_data = validated_data.pop('contacts') if 'contacts' in validated_data else []
            
        user = User.objects.create(**validated_data)

        for contact in contact_data:
            try:
                contact = Contact.objects.create(user_id=user.id, **contact)
                user.contacts.add(contact.id)
            except Exception:
                break

        user.save()

        return user

    def update(self, instance, validated_data):
        contact_data = validated_data.pop('contacts') if 'contacts' in validated_data else []
        instance = super(UserSerializer, self).update(instance, validated_data)

        Contact.objects.filter(user_id=instance.id).delete()
        for contact in contact_data:
            try:
                contact, _ = Contact.objects.get_or_create(user_id=instance.id, **contact)
                instance.contacts.add(contact.id)
            except Exception:
                break

        instance.save()
        return instance


class CategorySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Category
        fields = ('url', 'id', 'name',)
        read_only_fields = ('id',)
        

class CategoryDetailSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Category
        fields = ('url', 'id', 'name', 'shops')
        read_only_fields = ('id',)


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('id', 'name', 'state',)
        read_only_fields = ('id',)


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()

    class Meta:
        model = Product
        fields = ('name', 'category',)


class ProductParameterSerializer(serializers.ModelSerializer):
    parameter = serializers.StringRelatedField()

    class Meta:
        model = ProductParameter
        fields = ('parameter', 'value',)


class ProductInfoSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_parameters = ProductParameterSerializer(read_only=True, many=True)

    class Meta:
        model = ProductInfo
        fields = ('id', 'product', 'shop', 'quantity', 'price', 'price_rrc', 'product_parameters',)
        read_only_fields = ('id',)


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ('id', 'product_info', 'quantity', 'order',)
        read_only_fields = ('id',)
        extra_kwargs = {
            'order': {'write_only': True}
        }


class OrderItemCreateSerializer(OrderItemSerializer):
    product_info = ProductInfoSerializer(read_only=True)


class OrderSerializer(serializers.ModelSerializer):
    ordered_items = OrderItemCreateSerializer(read_only=True, many=True)

    total_sum = serializers.IntegerField()
    contact = ContactSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'ordered_items', 'state', 'dt', 'total_sum', 'contact',)
        read_only_fields = ('id',)


