from django.urls import path
from . import views
from .views import ResumeScreeningAPIView

urlpatterns = [
    path('screening/', ResumeScreeningAPIView.as_view(), name='resume-screening'),
]