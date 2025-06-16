# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('set-cookies', views.set_cookie, name='set-cookies'),
    path('payworld-data', views.payworld_data, name='payworld-data'),
]