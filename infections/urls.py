from django.urls import path

from .views import (
    ListInfectionAPIView,
    AddInfectionHistoryAPIView,
    ListCloseContactAPIView,
    UpdateUploadStatusAPIView
)

app_name = 'infections'

urlpatterns = [
    path('infections', ListInfectionAPIView.as_view()),
    path('infections/add', AddInfectionHistoryAPIView.as_view()),
    path('infections/<date>', ListInfectionAPIView.as_view()),
    path('closecontacts/<infectedId>/<infectionId>',ListCloseContactAPIView.as_view()),
    path('notify/<pk>/<infectionId>', UpdateUploadStatusAPIView.as_view())
]