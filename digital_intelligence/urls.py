from django.urls import path
from . import views

urlpatterns = [
    path('get-alt-mobile-number', views.get_alternate_mobile_numbers, name='get-alt-mobile-number'),
    path('get-alt-email', views.get_email, name='get-alt-email'),
    path('get-lpg-info', views.get_lpg_info, name='get-lpg-info'),
]