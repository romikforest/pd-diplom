from django.conf import settings
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import Group
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_rest_passwordreset.tokens import get_token_generator

from phonenumber_field.modelfields import PhoneNumberField

ADDRESS_ITEMS_LIMIT = 5

USER_TYPE_CHOICES = (
    ('shop', _('Магазин')),
    ('buyer', _('Покупатель')),

)


class Group(Group):
    class Meta:
        proxy = True
        verbose_name = _('Группа')
        verbose_name_plural = _('Группы')


class UserManager(BaseUserManager):
    """
    Миксин для управления пользователями
    """
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given username, email, and password.
        """
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Стандартная модель пользователей
    """
    REQUIRED_FIELDS = []
    objects = UserManager()
    USERNAME_FIELD = 'email'
    email = models.EmailField(_('email address'), unique=True)
    company = models.CharField(verbose_name=_('Компания'), max_length=40, blank=True)
    position = models.CharField(verbose_name=_('Должность'), max_length=40, blank=True)
    username_validator = UnicodeUsernameValidator()
    username = models.CharField(
        _('username'),
        max_length=150,
        help_text=_('Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        validators=[username_validator],
        error_messages={
            'unique': _('A user with that username already exists.'),
        },
    )
    is_active = models.BooleanField(
        _('active'),
        default=False,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    type = models.CharField(verbose_name=_('Тип пользователя'), choices=USER_TYPE_CHOICES, max_length=10, default='buyer')

    def __str__(self):
        return f'{self.first_name} {self.last_name} {self.email}'

    class Meta:
        verbose_name = _('Пользователь')
        verbose_name_plural = _('Пользователи')
        ordering = ('email',)


class ConfirmEmailToken(models.Model):
    
    class Meta:
        verbose_name = _('Токен подтверждения Email')
        verbose_name_plural = _('Токены подтверждения Email')

    @staticmethod
    def generate_key():
        """ generates a pseudo random code using os.urandom and binascii.hexlify """
        return get_token_generator().generate_token()

    user = models.ForeignKey(
        User,
        related_name='confirm_email_tokens',
        on_delete=models.CASCADE,
        verbose_name=_('Пользователь, связанный с данным токеном сброса пароля')
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Время создания токена')
    )

    # Key field, though it is not the primary key of the model
    key = models.CharField(
        _('Key'),
        max_length=64,
        db_index=True,
        unique=True
    )

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(ConfirmEmailToken, self).save(*args, **kwargs)

    def __str__(self):
        return _('Токен сброса пароля для пользователя {}').format(self.user)


class Contact(models.Model):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Пользователь'), related_name='contacts',
                             on_delete=models.CASCADE)

    person = models.CharField(max_length=50, verbose_name=_('Контактное лицо'), blank=True, help_text=_('Контактное лицо'))

    phone = PhoneNumberField(null=True, blank=True, verbose_name=_('Телефон'), help_text=_('Телефон'))

    city = models.CharField(max_length=50, verbose_name=_('Город'), blank=True)
    street = models.CharField(max_length=100, verbose_name=_('Улица'), blank=True)
    house = models.CharField(max_length=15, verbose_name=_('Дом'), blank=True)
    structure = models.CharField(max_length=15, verbose_name=_('Корпус'), blank=True)
    building = models.CharField(max_length=15, verbose_name=_('Строение'), blank=True)
    apartment = models.CharField(max_length=15, verbose_name=_('Квартира'), blank=True)

    def save(self, *args, **kwargs):
        if self.user.contacts.count() < ADDRESS_ITEMS_LIMIT or self.user.contacts.filter(id=self.id).exists():
            super(Contact, self).save(*args, **kwargs)
        else:
            raise Exception(f'There are already {ADDRESS_ITEMS_LIMIT} contacts. No more are allowed.')

    class Meta:
        verbose_name = _('Контакт')
        verbose_name_plural = _('Отдельные контакты')

    def __str__(self):
        return f'{self.user}: {self.person} / {self.phone} / {self.city} {self.street} {self.house} {self.structure} {self.building} {self.apartment}'

