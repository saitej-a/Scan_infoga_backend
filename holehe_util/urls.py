from django.urls import path
from . import views

urlpatterns = [
    path('email_used_only', views.get_email_info_holehe, name='email_used_only'),
]