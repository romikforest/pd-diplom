from django.conf import settings
from django.urls import path, re_path
# from django.utils.translation import gettext_lazy as t
from django.views.decorators.cache import cache_page, never_cache
from django.views.decorators.vary import vary_on_headers
from django.views.generic import TemplateView
from django_rest_passwordreset.views import reset_password_request_token, reset_password_confirm
# from rest_framework.documentation import include_docs_urls
from rest_framework.schemas import get_schema_view
from rest_framework.urlpatterns import format_suffix_patterns

from core.routers import CustomDefaultRouter, CustomSimpleRouter #, CustomNestedSimpleRouter
from .views import UserViewSet, PartnerViewSet, OrderViewSet, \
    ShopViewSet, ProductInfoViewSet, BasketViewSet, \
    CategoryViewSet, ContactViewSet, ProductParametersViewSet

app_name = 'api'

openapi_view = get_schema_view(title='Shop Integrator API', description='API for the shop Integrator ...')

router = CustomDefaultRouter()
router.APIRootView.__doc__ = 'Добро пожаловать в магазинчик'

# router.register('users/contacts', ContactViewSet, base_name='contact')
router.register('users', UserViewSet, 'user')
router.register('partners', PartnerViewSet, 'partner')
router.register('contacts', ContactViewSet, base_name='contact') # Общий функционал для user/partner
router.register('categories', CategoryViewSet)
router.register('shops', ShopViewSet)
router.register('products', ProductInfoViewSet, 'productinfo')
router.register('productparameters', ProductParametersViewSet, 'productparameter')
router.register('orders', OrderViewSet, 'order')
router.register('basket', BasketViewSet, 'basket')


router.root_view_pre_items['api root'] = 'api-root'
router.root_view_pre_items['docs (OpenAPI schema)'] = 'openapi-schema'
router.root_view_pre_items['swagger-ui'] = 'swagger-ui'
router.root_view_pre_items['redoc'] = 'redoc'

# login, register - только чтобы обеспечить красивый порядок
# (т.к. заносятся в OrderedList)
# их заново переопределит UserViewSet,
# который в роутере регистрируется первым
router.root_view_pre_items['users/login (POST)'] = 'user-login'
router.root_view_pre_items['users/register'] = 'user-register'
router.root_view_pre_items['users/register/confirm'] = 'user-register-confirm'
router.root_view_pre_items['users/password_reset'] = 'password-reset'
router.root_view_pre_items['users/password_reset/confirm'] = 'password-reset-confirm'


urlpatterns = [
    re_path('^users/password_reset/?$', reset_password_request_token, name='password-reset'),
    re_path('^users/password_reset/confirm/?$', reset_password_confirm, name='password-reset-confirm'),
    re_path('^docs/?$', cache_page(settings.CACHE_TIMES['OPENAPI'])(openapi_view), name='openapi-schema'),
    re_path('^swagger-ui/?$', cache_page(settings.CACHE_TIMES['SWAGGER'])(TemplateView.as_view(
        template_name='api/swagger-ui.html',
        extra_context={'schema_url': f'{app_name}:openapi-schema'}
    )), name='swagger-ui'),
    re_path('^redoc/?$', cache_page(settings.CACHE_TIMES['REDOC'])(TemplateView.as_view(
        template_name='api/redoc.html',
        extra_context={'schema_url': f'{app_name}:openapi-schema'}
    )), name='redoc'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
urlpatterns += router.urls


##########################################################################################################

# from django.conf import settings
# from django.urls import path
# from django.utils.translation import gettext_lazy as t
# from django.views.decorators.cache import cache_page, never_cache
# from django.views.decorators.vary import vary_on_headers
# from django.views.generic import TemplateView
# from django_rest_passwordreset.views import reset_password_request_token, reset_password_confirm
# # from rest_framework.documentation import include_docs_urls
# from rest_framework.schemas import get_schema_view
# from rest_framework.urlpatterns import format_suffix_patterns

# from .views import PartnerUpdate, LoginAccount, RegisterAccount, ConfirmAccount, AccountDetails, \
#     CategoryView, CategoryDetailView, ContactView, ShopView, ShopDetailView, ProductInfoView, \
#     api_root

# app_name = 'api'

# openapi_view = get_schema_view(title=t('Shop Integrator API'), description=t('API for the shop Integrator ...'))

# urlpatterns = [
#     path('', api_root, name='api-root'),
#     path('partner/update/', PartnerUpdate.as_view(), name='partner-update'),
#     path('user/login/', LoginAccount.as_view(), name='user-login'),
#     path('user/register/', RegisterAccount.as_view(), name='user-register'),
#     path('user/register/confirm/', ConfirmAccount.as_view(), name='user-register-confirm'),
#     path('user/password_reset/', reset_password_request_token, name='password-reset'),
#     path('user/password_reset/confirm/', reset_password_confirm, name='password-reset-confirm'),
#     path('user/details/', AccountDetails.as_view(), name='user-details'),
#     path('categories/', cache_page(settings.CACHE_TIMES['CATEGORIES'])(CategoryView.as_view()), name='category'),
#     path('categories/<int:pk>/', cache_page(settings.CACHE_TIMES['CATEGORIES'])(CategoryDetailView.as_view()), name='category-detail'),
#     path('user/contact/', ContactView.as_view(), name='user-contact'),
#     path('shops/', cache_page(settings.CACHE_TIMES['SHOPS'])(ShopView.as_view()), name='shop'),
#     path('shops/<int:pk>/', cache_page(settings.CACHE_TIMES['SHOPS'])(ShopDetailView.as_view()), name='shop-detail'),
#     path('products/', ProductInfoView.as_view(), name='products'), # default caching

#     path('docs/', cache_page(settings.CACHE_TIMES['OPENAPI'])(openapi_view), name='openapi-schema'),
#     # path('core-docs', include_docs_urls(title='Shop Integrator API')),
#     path('swagger-ui/', cache_page(settings.CACHE_TIMES['SWAGGER'])(TemplateView.as_view(
#         template_name='api/swagger-ui.html',
#         extra_context={'schema_url': f'{app_name}:openapi-schema'}
#     )), name='swagger-ui'),
#     path('redoc/', cache_page(settings.CACHE_TIMES['REDOC'])(TemplateView.as_view(
#         template_name='api/redoc.html',
#         extra_context={'schema_url': f'{app_name}:openapi-schema'}
#     )), name='redoc'),
# ]

# urlpatterns = format_suffix_patterns(urlpatterns)
