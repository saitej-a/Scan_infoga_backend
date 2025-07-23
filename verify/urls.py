from django.urls import path
from . import views

urlpatterns = [
    path('aadharVerify', views.handleAadhaarVerify, name='aadhar-verify'),
]
