from django.urls import path
from django.views.generic import TemplateView
from django_rest_passwordreset.views import reset_password_request_token, reset_password_confirm
# from rest_framework.documentation import include_docs_urls
from rest_framework.schemas import get_schema_view
from rest_framework.urlpatterns import format_suffix_patterns

from .views import PartnerUpdate, LoginAccount, RegisterAccount, ConfirmAccount, AccountDetails, \
    CategoryView, ContactView, ShopView, ProductInfoView, \
    api_root

# from backend.views import \
#     BasketView, \
#     OrderView, PartnerState, PartnerOrders

app_name = 'api_v1'

openapi_view = get_schema_view(title='Shop Integrator API', description='API for the shop Integrator ...', urlconf='api.urls')
# openapi_view = get_schema_view(title='Shop Integrator API', description='API for the shop Integrator ...')

urlpatterns = [
    path('', api_root, name='api-root'),
    path('partner/update', PartnerUpdate.as_view(), name='partner-update'),
    path('user/login', LoginAccount.as_view(), name='user-login'),
    path('user/register', RegisterAccount.as_view(), name='user-register'),
    path('user/register/confirm', ConfirmAccount.as_view(), name='user-register-confirm'),
    path('user/password_reset', reset_password_request_token, name='password-reset'),
    path('user/password_reset/confirm', reset_password_confirm, name='password-reset-confirm'),
    path('user/details', AccountDetails.as_view(), name='user-details'),
    path('categories', CategoryView.as_view(), name='categories'),
    path('user/contact', ContactView.as_view(), name='user-contact'),
    path('shops', ShopView.as_view(), name='shops'),
    path('products', ProductInfoView.as_view(), name='products'),

    path('docs', openapi_view, name='openapi-schema'),
    # path('core-docs', include_docs_urls(title='Shop Integrator API')),
    path('swagger-ui/', TemplateView.as_view(
        template_name='api/swagger-ui.html',
        extra_context={'schema_url': 'api_v1:openapi-schema'}
    ), name='swagger-ui'),
    path('redoc/', TemplateView.as_view(
        template_name='api/redoc.html',
        extra_context={'schema_url':'api_v1:openapi-schema'}
    ), name='redoc'),
    

    # path('partner/state', PartnerState.as_view(), name='partner-state'),
    # path('partner/orders', PartnerOrders.as_view(), name='partner-orders'),
    # path('basket', BasketView.as_view(), name='basket'),
    # path('order', OrderView.as_view(), name='order'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
