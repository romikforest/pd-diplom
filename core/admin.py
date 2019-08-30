from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from nested_inline.admin import NestedStackedInline, NestedTabularInline, NestedModelAdmin
 
from .models import Shop, Category, Product, ProductInfo, Order, OrderItem, Parameter, ProductParameter


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


# @admin.register(ProductInfo)
# class ProductInfoAdmin(admin.ModelAdmin):
#     inlines = (ProductParameterInline, )


@admin.register(Product)
class ProductAdmin(NestedModelAdmin):
    inlines = (ProductInfoInline, )


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    inlines = (OrderItemInline, )



