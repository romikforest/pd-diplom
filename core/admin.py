from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from nested_inline.admin import NestedStackedInline, NestedTabularInline, NestedModelAdmin
 
from .models import Shop, Category, Product, ProductInfo, Order, OrderItem, Contact, \
    Parameter, ProductParameter, \
    ADDRESS_ITEMS_LIMIT


admin.site.site_header = 'Администрирование магазина'


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    pass


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    pass


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    pass

class ProductParameterInline(NestedTabularInline):
    model = ProductParameter
    extra = 0

class ProductInfoInline(NestedStackedInline):
    model = ProductInfo
    extra = 0
    inlines = (ProductParameterInline, )


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    inlines = (ProductParameterInline, )


@admin.register(Product)
class ProductAdmin(NestedModelAdmin):
    inlines = (ProductInfoInline, )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = (OrderItemInline, )


class ContactInline(admin.StackedInline):
    model = Contact
    extra = 0
    max_num = ADDRESS_ITEMS_LIMIT


class ContactProxy(get_user_model()):

    class Meta:
        proxy = True
        verbose_name = _('Контакты пользователя')
        verbose_name_plural = _('Контакты пользователей')


@admin.register(ContactProxy)
class ContactAdmin(admin.ModelAdmin):
    fieldsets = (
         (None, {'fields': tuple()}),
     )
    inlines = (ContactInline, )


