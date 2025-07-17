from django.urls import path
from . import views

urlpatterns = [
    path('user-wallet-history', views.wallet_history_list, name='wallet-history'),
    path('get-user-info', views.get_user_info, name='get-user-info'),
    path('get-login-history', views.get_login_history, name='get-login-history'),
    path('get-user-bookmark-list', views.get_bookmarks_by_user, name='get-bookmarks'),
    path('get-user-wallet-balance', views.get_user_wallet_balance, name='get-wallet-balance'),

]