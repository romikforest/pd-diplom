from django.utils.translation import gettext_lazy as t
from rest_framework.exceptions import ValidationError

class NotBlankTogetherValidator():
    """
    Валидатор, что поля не пустые одновременно
    """

    message = t('Хотя бы одно из полей {field_names} должно быть заполнено.')

    def __init__(self, queryset=None, fields=None, message=None):
        self.fields = fields
        self.message = message or self.message

    def __call__(self, attrs):

        message = self.message.format(field_names=self.fields)

        all_items = {
            field_name: message
            for field_name in self.fields
        }
        blank_items = {
            field_name for field_name in self.fields
            if field_name not in attrs or attrs[field_name] == ''
        }
        if len(blank_items) == len(all_items):
            raise ValidationError(all_items, code='required')

    def __repr__(self):
        return '<{}(fields={})>'.format(
            self.__class__.__name__,
            smart_repr(self.fields)
        )


class EqualTogetherValidator():
    """
    Валидатор, что поля равны
    """

    message = t('Поля {field_names} не совпадают.')

    def __init__(self, queryset=None, fields=None, message=None):
        self.fields = fields
        self.message = message or self.message

    def __call__(self, attrs):

        message = self.message.format(field_names=self.fields)

        all_items = {
            field_name: message
            for field_name in self.fields
        }

        values = [
            attrs[field_name] for field_name in self.fields
            if field_name in attrs
        ]

        if len(values) != len(self.fields) or len(set(values)) != 1:
            raise ValidationError(all_items, code='unique')

    def __repr__(self):
        return '<{}(fields={})>'.format(
            self.__class__.__name__,
            smart_repr(self.fields)
        )