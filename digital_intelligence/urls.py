from django.urls import path
from . import views

urlpatterns = [
    path('get-alt-mobile-number', views.get_alternate_mobile_numbers, name='get-alt-mobile-number'),
    path('get-alt-email', views.get_email, name='get-alt-email'),
    path('get-lpg-info', views.get_lpg_info, name='get-lpg-info'),
    path('get-personal-info', views.get_personal_information_profile_advance, name='get-personal-info'),
    path('get-document-data', views.get_document_data_profile_advance, name='get-document-data'),
    path('get-address', views.get_address_profile_advance, name='get-address'),
]