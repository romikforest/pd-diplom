from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from rest_auth.models import Contact


STATE_CHOICES = (
    ('basket', _('Статус корзины')),
    ('new', _('Новый')),
    ('confirmed', _('Подтвержден')),
    ('assembled', _('Собран')),
    ('sent', _('Отправлен')),
    ('delivered', _('Доставлен')),
    ('canceled', _('Отменен')),
)

CONTACT_TYPE_CHOICES = (
    ('phone', _('Телефон')),
    ('address', _('Адреса')),
)


class Shop(models.Model):
    name = models.CharField(max_length=50, verbose_name=_('Название'), unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Пользователь'),
                             related_name='shops',
                             blank=True, null=True,
                             on_delete=models.CASCADE)
    state = models.BooleanField(verbose_name=_('Получать заказы'), default=True)

    load_url = models.URLField(verbose_name=_('Ссылка'), null=True, blank=True)
    # filename = models.FileField(upload_to='shops/', null=True, blank=True)

    class Meta:
        verbose_name = _('Магазин')
        verbose_name_plural = _('Магазины')
        ordering = ('-name',)

    def __str__(self):
        return f'{self.name} ({self.user})'


class Category(models.Model):
    name = models.CharField(max_length=40, verbose_name=_('Название'), unique=True)
    shops = models.ManyToManyField(Shop, verbose_name=_('Магазины'), related_name='categories', blank=True)

    class Meta:
        verbose_name = _('Категория')
        verbose_name_plural = _('Категории')
        ordering = ('-name',)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=80, verbose_name=_('Название'), unique=True)
    category = models.ForeignKey(Category, verbose_name=_('Категория'), related_name='products', blank=True,
                                 on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('Продукт')
        verbose_name_plural = _('Продукты')
        ordering = ('-name',)

    def __str__(self):
        return self.name


class ProductInfo(models.Model):

    external_id = models.PositiveIntegerField(verbose_name=_('Внешний ИД'), blank=True, null=True)
    product = models.ForeignKey(Product, verbose_name=_('Продукт'), related_name='product_infos', blank=True,
                                on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, verbose_name=_('Магазин'), related_name='product_infos', blank=True,
                             on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(verbose_name=_('Количество'))
    price = models.DecimalField(max_digits=20, decimal_places=2, verbose_name=_('Цена'), validators=[MinValueValidator(0)])
    price_rrc = models.DecimalField(max_digits=20, decimal_places=2, verbose_name=_('Рекомендуемая розничная цена'), validators=[MinValueValidator(0)])

    class Meta:
        verbose_name = _('Информация о продукте')
        verbose_name_plural = _('Информация о продуктах')
        constraints = [
            models.UniqueConstraint(fields=['product', 'shop'], name='unique_product_info'),
        ]

    def __str__(self):
        return f'{self.shop}: {self.product}'

    def save(self, *args, **kwargs):
        category = self.product.category.name
        if not self.shop.categories.filter(name=category).exists():
            print(f'Add category {category}')
            self.shop.categories.add(Category.objects.get_or_create(name=category)[0].id)
        super(ProductInfo, self).save(*args, **kwargs)


class Parameter(models.Model):
    name = models.CharField(max_length=40, verbose_name=_('Название'), unique=True)

    class Meta:
        verbose_name = _('Название параметра')
        verbose_name_plural = _('Названия параметров продуктов')
        ordering = ('-name',)

    def __str__(self):
        return self.name


class ProductParameter(models.Model):
    product_info = models.ForeignKey(ProductInfo, verbose_name=_('Информация о продукте'),
                                     related_name='product_parameters', blank=True,
                                     on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, verbose_name=_('Параметр'), related_name='product_parameters', blank=True,
                                  on_delete=models.CASCADE)
    value = models.CharField(verbose_name=_('Значение'), max_length=100)

    class Meta:
        verbose_name = _('Параметр')
        verbose_name_plural = _('Параметры')
        constraints = [
            models.UniqueConstraint(fields=['product_info', 'parameter'], name='unique_product_parameter'),
        ]

    def __str__(self):
        return f'{self.parameter} [ {self.product_info} ]'


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Пользователь'),
                             related_name='orders', blank=True,
                             on_delete=models.CASCADE)
    dt = models.DateTimeField(auto_now_add=True)

    state = models.CharField(verbose_name=_('Статус'), choices=STATE_CHOICES, max_length=25)

    contact = models.ForeignKey(Contact, verbose_name='Контакт',
                                related_name='orders',
                                blank=True, null=True,
                                on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('Заказ')
        verbose_name_plural = _('Заказы')
        ordering = ('-dt',)
        constraints = [
            models.UniqueConstraint(fields=['user', 'dt'], name='unique_order'),
        ]

    def __str__(self):
        return f'{self.user} [ {self.dt} ]'

    # @property
    # def sum(self):
    #     return self.ordered_items.aggregate(total=Sum('quantity'))['total']


class OrderItem(models.Model):
    order = models.ForeignKey(Order, verbose_name=_('Заказ'), related_name='ordered_items', blank=True,
                              on_delete=models.CASCADE)

    product_info = models.ForeignKey(ProductInfo, verbose_name=_('Информация о продукте'), related_name='ordered_items',
                                     blank=True,
                                     on_delete=models.CASCADE)

    quantity = models.PositiveIntegerField(verbose_name=_('Количество'))

    class Meta:
        verbose_name = _('Позиция заказа')
        verbose_name_plural = _('Позиции заказов')
        constraints = [
            models.UniqueConstraint(fields=['order', 'product_info'], name='unique_order_item'),
        ]

    def __str__(self):
        return f'{self.order} / {self.product_info} / {self.quantity}'
