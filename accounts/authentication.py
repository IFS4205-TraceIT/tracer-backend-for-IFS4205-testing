from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.hooks import check_user

import logging

logger = logging.getLogger('loki')

class TwoFactorAuthentication(JWTAuthentication):
    def authenticate(self, request):
        values = super().authenticate(request)
        if values is None:
            logger.info('Token is invalid.', extra={'action': 'check_token', 'request': request, 'user': None})
            return None
        
        if values[0] is None or values[1] is None:
            logger.info('Token is invalid.', extra={'action': 'check_token', 'request': request, 'user': None})
            return None

        user, validated_token = values
        if ('verified_otp' not in validated_token) or (not validated_token['verified_otp']):
            logger.warn('User has not verified OTP.', extra={'action': 'check_token', 'request': request, 'user_id': user.id})
            return None

        if not check_user(user):
            logger.warn('User does not have permission to access this portal.', extra={'action': 'check_token', 'request': request, 'user_id': user.id})
            return None

        return user, validated_token