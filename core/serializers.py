from django.utils.translation import gettext_lazy as t
from rest_framework import serializers


class DefaultSerializer(serializers.Serializer):
    """
    Базовый класс сериалайзера с полями для документирования ошибок и статуса
    """
    Errors = serializers.CharField(read_only=True, help_text=t('Error message(s)'), label=t('Error'))
    Status = serializers.BooleanField(read_only=True, help_text=t('Http Status code'), label=t('Status code'))


class DefaultModelSerializer(serializers.HyperlinkedModelSerializer):
    """
    Базовый класс сериалайзера ORM модели с полями для документирования ошибок и статуса
    """
    Errors = serializers.CharField(read_only=True, help_text=t('Error message(s)'), label=t('Error'))
    Status = serializers.BooleanField(read_only=True, help_text=t('Http Status code'), label=t('Status code'))


def ModelPresenter(model, fields, outer_properties=None):
    """
    Метакласс для генерации классов вида:
    class NewClass(DefaultModelSerializer):
        outer_properties...

        class Meta:
            model = model
            fields = fields 
    """

    class Serializer(DefaultModelSerializer):
        pass
    Meta = type('Meta', (), {'fields': fields, 'model': model})
    outer_properties = outer_properties or {}
    outer_properties.update({'Meta': Meta})
    return type(model.__class__.__name__+'Presenter', (Serializer, ), outer_properties)