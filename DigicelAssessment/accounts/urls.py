from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.role_home_redirect, name="home"),
    path("accounts/login/", views.RoleAwareLoginView.as_view(), name="login"),
    path("accounts/logout/", views.RoleLogoutView.as_view(), name="logout"),
    path("customer/", views.customer_home, name="customer_home"),
    path("agent/", views.agent_home, name="agent_home"),
    path("admin-portal/", views.admin_home, name="admin_home"),
]
