from django.urls import path
from . import views

urlpatterns = [
    path('', views.recruitment_criteria_api, name='recruitment_criteria_api'),
]