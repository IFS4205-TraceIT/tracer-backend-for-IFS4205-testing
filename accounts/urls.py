from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    LoginAPIView,
    LogoutAPIView,
    RegistrationAPIView,
    UserRetrieveUpdateAPIView,
    RegisterTOTPView,
    ValidateTOTPView
)

app_name = 'accounts'

urlpatterns = [
    path('register', RegistrationAPIView.as_view(), name='register_user'),
    path('login', LoginAPIView.as_view(), name='login_user'),
    path('logout', LogoutAPIView.as_view(), name="logout_user"),
    path('user', UserRetrieveUpdateAPIView.as_view(), name='user'),
    path('totp', ValidateTOTPView.as_view(), name='validate_totp'),
    path('totp/register', RegisterTOTPView.as_view(), name='register_totp'),
    # path('token', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh', TokenRefreshView.as_view(), name='token_refresh'),
]