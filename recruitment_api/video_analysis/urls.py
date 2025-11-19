from django.urls import path
from . import views

urlpatterns = [
    path('', views.VideoAnalysisAPIView.as_view(), name='video-analysis'),
    path('<uuid:video_id>/status/', views.VideoAnalysisStatusAPIView.as_view(), name='video-analysis-status'),
    path('<uuid:video_id>/update/', views.VideoAnalysisUpdateAPIView.as_view(), name='video-analysis-update'),
    path('list/', views.VideoAnalysisListAPIView.as_view(), name='video-analysis-list'),
]