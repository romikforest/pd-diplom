from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
 
from .models import Shop, Category, Product, ProductInfo, Order, OrderItem, Contact, \
    ProductParameterName, ProductParameter, CommonParameterName, CommonParameter, \
    ADDRESS_ITEMS_LIMIT


admin.site.site_header = 'Администрирование магазина'


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    pass


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    pass


@admin.register(CommonParameterName)
class CommonParameterNameAdmin(admin.ModelAdmin):
    pass


@admin.register(ProductParameterName)
class ProductParameterNameAdmin(admin.ModelAdmin):
    pass


# @admin.register(ProductParameter)
# class ProductParameterAdmin(admin.ModelAdmin):
#     pass

class CommonParameterInline(admin.TabularInline):
    model = CommonParameter
    extra = 0

class ProductParameterInline(admin.TabularInline):
    model = ProductParameter
    extra = 0

class ProductInfoInline(admin.StackedInline): #
    model = ProductInfo
    extra = 0
    inlines = (ProductParameterInline, )


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    inlines = (ProductParameterInline, )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = (CommonParameterInline, ProductInfoInline)


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


