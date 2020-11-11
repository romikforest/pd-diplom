from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import path
from django.utils.translation import gettext_lazy as _

from nested_inline.admin import NestedStackedInline, NestedTabularInline, NestedModelAdmin
 
from .models import Shop, Category, Product, ProductInfo, Order, OrderItem, Parameter, ProductParameter
from .tasks import do_import


admin.site.site_header = 'Администрирование магазина'


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    change_list_template = 'admin/do_import.html'

    def get_urls(self):
        return [ path('do_import/', self.do_import) ] + super().get_urls()

    def do_import(self, request):
        do_import.delay()
        self.message_user(request, 'Обновление прайс листов началось')
        return HttpResponseRedirect('../')


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



