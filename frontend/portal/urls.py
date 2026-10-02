from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="portal_login"),
    path("logout/", views.logout_view, name="portal_logout"),
    path("", views.dashboard_view, name="dashboard"),
    path("transactions/", views.transactions_view, name="transactions"),
    path("transfer/", views.transfer_view, name="transfer"),
    path("fraud-shield/", views.fraud_shield_view, name="fraud_shield"),
    path("accounts/", views.accounts_view, name="accounts"),
]