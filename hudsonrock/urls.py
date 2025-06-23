from django.urls import path
from . import views

urlpatterns = [
    path('save', views.save_hudson_data, name='save-hudson-data'),
    path('get/', views.get_hudson_data, name='get-hudson-data'),
    path('search-by-email', views.search_by_email, name='search-by-email'),
    path('search-by-ip', views.search_by_ip, name='search-by-ip'),
]