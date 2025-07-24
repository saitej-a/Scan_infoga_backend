from django.urls import path
from . import views

urlpatterns = [
    path('aadharVerify/', views.handleAadhaarVerify, name='aadhar-verify'),
    path('trucallerVerify', views.handleTrucallerVerify, name='pan-verify'),
]
