from django.urls import path
from .views import wallet_history_list

urlpatterns = [
    path('/user-wallet-history', wallet_history_list, name='wallet-history'),
]