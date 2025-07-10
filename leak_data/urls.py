from django.urls import path
from . import views

urlpatterns = [
    # path('get-password', views.get_passwords, name='get-passwords'),
    path('get-password', views.get_password, name='get-password'),
    path('get-jobseeker', views.get_job_seeker_data, name='get-jobseeker-data'),
    path('get-corporate', views.get_corporate_data, name='get-corporate-data'),
    path('get-zomato', views.get_zomato_data, name='get-zomato-data'),
    path('get-cbse', views.get_cbse_data, name='get-cbse-data'),
]