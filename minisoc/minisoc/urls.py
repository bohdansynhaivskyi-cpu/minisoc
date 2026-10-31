from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path

from soc import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.dashboard, name="dashboard"),
    path("login/", auth_views.LoginView.as_view(template_name="soc/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),  # nur per POST
    path("mfa/setup/", views.mfa_setup, name="mfa_setup"),
    path("mfa/verify/", views.mfa_verify, name="mfa_verify"),
    path("alerts/<int:pk>/ack/", views.ack_alert, name="ack_alert"),
]
