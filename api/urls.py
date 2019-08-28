from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

from .views import PartnerUpdate


urlpatterns = [
    path('partner/update', PartnerUpdate.as_view(), name='partner-update'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
