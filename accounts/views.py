from typing import Any, Optional

from django.conf import settings
from rest_framework import status
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView

from accounts.hooks import post_login_hook, post_registration_hook

from .renderers import UserJSONRenderer
from .serializers import (
    LoginSerializer,
    LogoutSerializer,
    RegistrationSerializer,
    UserSerializer,
    RegisterTOTPSerializer,
    ValidateTOTPSerializer
)
from .vault import create_vault_client
from .vault.totp import TOTP

import logging
logger = logging.getLogger('loki')

class RegistrationAPIView(APIView):
    permission_classes = (AllowAny,)
    renderer_classes = (UserJSONRenderer,)
    serializer_class = RegistrationSerializer

    def post(self, request: Request) -> Response:
        """Return user response after a successful registration."""
        user_request = request.data
        serializer = self.serializer_class(data=user_request)
        logger.info('User registration request.', extra={'action': 'register', 'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return post_registration_hook(request, serializer)


class LoginAPIView(APIView):
    permission_classes = (AllowAny,)
    renderer_classes = (UserJSONRenderer,)
    serializer_class = LoginSerializer

    def post(self, request: Request) -> Response:
        """Return user after login."""
        user = request.data
        logger.info('User login request.', extra={'action': 'login', 'request': request})
        serializer = self.serializer_class(data=user)
        if not serializer.is_valid():
            logger.warn('User login failed.', extra={'action': 'login', 'request': request})
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return post_login_hook(request, serializer)


class UserRetrieveUpdateAPIView(RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    renderer_classes = (UserJSONRenderer,)
    serializer_class = UserSerializer

    def retrieve(self, request: Request, *args: dict[str, Any], **kwargs: dict[str, Any]) -> Response:
        """Return user on GET request."""
        serializer = self.serializer_class(request.user, context={'request': request})

        return Response(serializer.data, status=status.HTTP_200_OK)

    def update(self, request: Request, *args: dict[str, Any], **kwargs: dict[str, Any]) -> Response:
        """Return updated user."""
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)
        # logger.info('User update request.', extra={'action': 'update', 'request': request, 'user_id': request.user.id})
        # serializer_data = request.data

        # serializer = self.serializer_class(
        #     request.user, data=serializer_data, partial=True, context={'request': request}
        # )
        # serializer.is_valid(raise_exception=True)
        # serializer.save()
        # logger.info('User updated.', extra={'action': 'user_update', 'request': request, 'user_id': request.user.id})
        # return Response(serializer.data, status=status.HTTP_200_OK)


class LogoutAPIView(APIView):
    serializer_class = LogoutSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = (IsAuthenticated,)

    def post(self, request: Request) -> Response:
        """Validate token and save."""
        logger.info('User logout request.', extra={'action': 'logout', 'request': request, 'user_id': request.user.id})
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(status=status.HTTP_204_NO_CONTENT)


class RegisterTOTPView(APIView):
    serializer_class = RegisterTOTPSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = (IsAuthenticated,)
    
    def post(self, request: Request) -> Response:
        """Validate token and save."""
        logger.info('User TOTP registration request.', extra={'action': 'register_totp', 'request': request, 'user_id': request.user.id})
        serializer = self.serializer_class(request.user, data={'has_otp': True}, context={'request': request})
        serializer.is_valid(raise_exception=True)

        vault = create_vault_client()
        totp = TOTP(vault)

        img = totp.create_key(generate=True, name=request.user.id, issuer='TraceIT', account_name=request.user.username)

        serializer.save()
        logger.info('User registered TOTP.', extra={'action': 'register_totp', 'request': request, 'user_id': request.user.id})
        return Response(img['data'], status=status.HTTP_200_OK)


class ValidateTOTPView(TokenObtainPairView):
    serializer_class = ValidateTOTPSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = (IsAuthenticated,)
    
    def post(self, request: Request) -> Response:
        logger.info('User validating TOTP.', extra={'action': 'validate_totp', 'request': request, 'user_id': request.user.id})
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        logger.info('User validated TOTP.', extra={'action': 'validate_totp', 'request': request, 'user_id': request.user.id})
        return Response(serializer.data, status=status.HTTP_200_OK)
