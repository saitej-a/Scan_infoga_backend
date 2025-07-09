from django.urls import path
from . import views

urlpatterns = [
    # path('get-password', views.get_passwords, name='get-passwords'),
    path('get-password', views.GetPassword.as_view(), name='get-passwords'),
    path('get-jobseeker', views.GetJobSeekerData.as_view(), name='get-jobseeker-data'),
    path('get-corporate', views.GetCorporateData.as_view(), name='get-corporate-data'),
    path('get-zomato', views.GetZomatoData.as_view(), name='get-zomato-data'),
]