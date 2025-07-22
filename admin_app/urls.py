from django.urls import path

from payments.views import get_completed_txns, get_failed_txns
from . import views

urlpatterns = [
    path('user-wallet-history', views.wallet_history_list, name='wallet-history'),
    path('get-user-info', views.get_user_info, name='get-user-info'),
    path('get-login-history', views.get_login_history, name='get-login-history'),
    path('get-user-bookmark-list', views.get_bookmarks_by_user, name='get-bookmarks'),
    path('get-user-wallet-balance', views.get_user_wallet_balance, name='get-wallet-balance'),
    path('wallet-update', views.wallet_update, name='wallet-update'),
    path('get-user-activity', views.get_user_activity, name='get-user-activity'),
    path('user-note', views.user_note, name='user-note'),
    path('pending-txns', views.get_pending_txns, name='pending-txns'),
    path('successful-txns', views.get_completed_txns, name='completed-txns'),
    path('failed-txns', views.get_failed_txns, name='failed-txns')

]