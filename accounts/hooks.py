# Every backend has a special requirement after registraion and login.
# The hook is a way to add this requirement to the backend.

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from .models import AuthUser
from .serializers import UserSerializer
from infections.models import Contacttracers

import logging
logger = logging.getLogger('loki')

def post_registration_hook(request: Request, serializer: UserSerializer):
    """
    This function is called after a user registers.
    """
    ct = Contacttracers(id=serializer.data['id'])
    ct.save()
    logger.info('User registered.', extra={'action': 'register', 'request': request, 'user_id': serializer.data['id']})
    del serializer.data['id']
    return Response(serializer.data, status=status.HTTP_201_CREATED)

def post_login_hook(request: Request, serializer: UserSerializer):
    """
    This function is called after a user logs in.
    """
    try:
        Contacttracers.objects.get(id=serializer.data['id'])
    except Contacttracers.DoesNotExist:
        logger.warn('User does not have permission to access this portal.', extra={'action': 'login', 'request': request, 'user_id': serializer.data['id']})
        return Response(data={'error':['A user with this username and password was not found.']}, status=status.HTTP_400_BAD_REQUEST)
    logger.info('User logged in.', extra={'action': 'login', 'request': request, 'user_id': serializer.data['id']})
    del serializer.data['id']
    return Response(serializer.data, status=status.HTTP_200_OK)


def check_user(user: AuthUser):
    """
    This function is called after a user logs in.
    """
    try:
        Contacttracers.objects.get(id=user.id)
    except Contacttracers.DoesNotExist:
        return False
    return True