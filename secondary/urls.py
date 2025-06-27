from django.urls import path
from . import views

urlpatterns = [
    path('set-cookies', views.set_cookie, name='set-cookies'),
    path('set-credentials-paynearby', views.set_paynearby_credentials, name='set-credentials-paynearby'),
    path('payworld-data', views.payworld_data, name='payworld-data'),
    path('payworld-all-data', views.get_full_payworld_data, name='payworld-all-data'),
    # path('payworld-delete', views.delete_payworld_data, name='payworld-delete'),
    path('ifsc-data', views.razorpay_ifsc_data, name='ifsc-data'),
    path('ifsc-all-data', views.get_full_razorpay_ifsc_data, name='ifsc-all-data'),
    # path('ifsc-delete', views.delete_razorpay_ifsc_data, name='ifsc-delete'),
    path('paynearby-data', views.paynearby_data, name='paynearby-data'),
    path('paynearby-all-data', views.get_full_paynearby_data, name='paynearby-all-data'),
]