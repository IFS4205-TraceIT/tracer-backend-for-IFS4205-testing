from django.shortcuts import render
from django.utils import timezone
from .models import Infectionhistory, Users, Notifications
from .serializers import (
    ListInfectedSerializer, 
    CloseContactsSerializer,
    UpdateUploadSerializer
)
from rest_framework.generics import ListAPIView, UpdateAPIView, CreateAPIView
from rest_framework.response import Response
from datetime import timedelta, datetime
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated

import logging
logger = logging.getLogger('loki')


class ListInfectionAPIView(ListAPIView):
    
    permission_classes = (IsAuthenticated,)
    serializer_class = ListInfectedSerializer
    model = serializer_class.Meta.model
    lookup_url_kwarg = "date"

    def get_queryset(self):
        logger.info('List infection request.', extra={'action': 'list_infection', 'request': self.request, 'user_id': self.request.user.id})
        querydate = self.kwargs.get(self.lookup_url_kwarg, None)
        if querydate is None:
            querydate = timezone.now()
        else:
            try:
                querydate =  datetime.strptime(querydate,"%Y-%m-%d").astimezone(timezone.now().tzinfo)
            except ValueError:
                raise ValidationError(detail="Invalid Date format, yyyy-mm-dd")

        querydate = querydate + timedelta(days=1)
        queryset = self.model.objects.all()
        invalid = []
        for user in queryset:
            infectedhistory = user.infectionhistory_set.filter(
                recorded_timestamp__range=(
                    querydate-timedelta(days=15),
                    querydate
                    ))
            if infectedhistory.count()  == 0:
                invalid.append(user.id)
        
        queryset = self.model.objects.exclude(id__in=invalid)
        for user in queryset:
            user.infections = user.infectionhistory_set.filter(
                recorded_timestamp__range=(
                    querydate-timedelta(days=15),
                    querydate
                    )).latest("recorded_timestamp")

        return queryset

class ListCloseContactAPIView(ListAPIView):

    permission_classes = (IsAuthenticated,)
    serializer_class = CloseContactsSerializer
    model = serializer_class.Meta.model
    lookup_url_kwarg = "infectedId"

    def get_queryset(self):
        logger.info('List close contact request.', extra={'action': 'list_close_contact', 'request': self.request, 'user_id': self.request.user.id})
        try:
            uid = self.kwargs.get(self.lookup_url_kwarg)
            infectionId = self.kwargs.get("infectionId")
            closeContact = self.model.objects.filter(infected_user=uid,infectionhistory=infectionId)
        except:
            raise ValidationError(detail="Invalid User!")
        return closeContact

class UpdateUploadStatusAPIView(UpdateAPIView): 

    permission_classes = (IsAuthenticated,)
    queryset = Notifications.objects.all()
    serializer_class = UpdateUploadSerializer

    def get_object(self, pk, infectionId):
        try:
            cur_infection = Users.objects.get(id=pk).infectionhistory_set.get(id=infectionId)
        except:
            raise ValidationError(detail="Invalid User!")

        try:
            return self.get_queryset().get(infection = cur_infection), cur_infection
        except Notifications.DoesNotExist:
            return None, cur_infection

    def update(self, request, pk, infectionId):
        logger.info('Update upload status request.', extra={'action': 'update_upload_status', 'request': self.request, 'user_id': self.request.user.id})
        contact_tracer_id = request.user.id
        cur_notification, infection_id =  self.get_object(pk, infectionId)
        if cur_notification is None:
            serial = self.serializer_class(data={
                'infection': infection_id.id,
                'tracer':contact_tracer_id,     
                'uploaded_status': False,
                'due_date': timezone.now().date()+timedelta(days=7),
                'start_date': timezone.now().date()
            })
            serial.is_valid(raise_exception=True)
            serial.save()
        else:
            serial = self.serializer_class(cur_notification, data = {'uploaded_status': False}, partial=True)
            serial.is_valid(raise_exception=True)
            serial.save()

        return Response(status=status.HTTP_200_OK)

class AddInfectionHistoryAPIView(CreateAPIView):

    permission_classes = (IsAuthenticated,)

    def create(self, request):
        logger.info('Add infection history request.', extra={'action': 'add_infection_history', 'request': self.request, 'user_id': self.request.user.id})
        if 'nrics' not in request.data or type(request.data['nrics']) != list:
            raise ValidationError(detail="Invalid Request!")
        nrics = set(request.data['nrics'])
        query_set = Users.objects.filter(nric__in=nrics)
        if query_set.count() == 0:
            return Response(status=status.HTTP_201_CREATED)
        Infectionhistory.objects.bulk_create([Infectionhistory(recorded_timestamp=timezone.now(), user=user) for user in query_set])
        return Response(status=status.HTTP_201_CREATED)
