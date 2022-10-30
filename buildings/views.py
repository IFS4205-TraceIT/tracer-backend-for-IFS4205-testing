from .models import Buildings,Buildingaccess, Users
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from datetime import date, timedelta, datetime
from django.utils import timezone
from .serializers import BuildingSerializer, BuildingAccessSerializer

import qrcode
import io
import base64   
import logging
logger = logging.getLogger('loki')

# Create your views here.

class ListBuilding (ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = BuildingSerializer
    queryset = Buildings.objects.all()

class ListBuildingAccess (ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = BuildingAccessSerializer
    lookup_url_kwarg = ["buildingid","date"]

    def get_queryset(self):
        id = self.kwargs.get(self.lookup_url_kwarg[0])
        querydate = self.kwargs.get(self.lookup_url_kwarg[1], None)
        if querydate is None:
            querydate = datetime.combine(date.today(), datetime.min.time(), timezone.now().tzinfo)
        else:
            try:
                querydate =  datetime.strptime(querydate,"%Y-%m-%d").astimezone(timezone.now().tzinfo)
            except ValueError:
                raise ValidationError(detail="Invalid Date format, yyyy-mm-dd")
        try:
            building = Buildings.objects.get(id = id)
        except:
            raise ValidationError(detail="Invalid Building!")

        result = Buildingaccess.objects.filter(building = building, access_timestamp__range=(querydate,querydate+timedelta(hours=23,minutes=59)))
        logger.info('Building access request.', extra={'action': 'list_building_access', 'request': self.request, 'building_id': id, 'user_id': self.request.user.id})
        return result

class ListBuildingUserAccess (ListAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = BuildingAccessSerializer
    lookup_url_kwarg = ["userid","date"]

    def get_queryset(self):
        logger.info('List user building access request.', extra={'action': 'list_building_user_access', 'request': self.request, 'user_id': self.request.user.id})
        id = self.kwargs.get(self.lookup_url_kwarg[0], None)
        if id is None:
            return None
        querydate = self.kwargs.get(self.lookup_url_kwarg[1], None)

        try:
            user = Users.objects.get(nric = id)
        except:
            return None

        result = Buildingaccess.objects.filter(user = user)

        if querydate is None:
            return result
        else:
            try:
                querydate =  datetime.strptime(querydate,"%Y-%m-%d").astimezone(timezone.now().tzinfo)
                result = result.filter(access_timestamp__range=(querydate,querydate+timedelta(hours=23,minutes=59)))
            except ValueError:
                return None
        
        return result

class GenerateQRCodeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        try:
            building = Buildings.objects.get(name=kwargs['name'])
        except Buildings.DoesNotExist:
            raise ValidationError(detail="Building does not exist")
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(building.id)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        tmp = io.BytesIO()
        img_save = img.save(tmp)
        png_qr = tmp.getvalue()
        b64_img = base64.b64encode(png_qr)
        logger.info('Generated Building QR code.', extra={'action': 'generate_building_qr_code', 'request': request, 'building_id': building.id})
        return Response(data={"qrcode": b64_img}, status=status.HTTP_200_OK)
