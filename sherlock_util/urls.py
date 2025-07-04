from django.urls import path
from . import views

urlpatterns = [
    path('username-sherlock', views.get_username_info_sherlock, name='username_sherlock'),
]