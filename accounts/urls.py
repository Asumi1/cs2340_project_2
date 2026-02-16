from django.urls import path
from .views import signup_view, login_view, logout_view, edit_profile

urlpatterns = [
    path("signup/", signup_view, name="signup"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("profile/edit/", edit_profile, name="edit_profile"),
]
