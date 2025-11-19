from django.urls import path
from . import views

urlpatterns = [
    path('video-analysis/', views.VideoAnalysisAPIView.as_view(), name='video-analysis'),
    path('video-analysis/<uuid:video_id>/status/', views.VideoAnalysisStatusAPIView.as_view(), name='video-analysis-status'),
    path('video-analysis/<uuid:video_id>/update/', views.VideoAnalysisUpdateAPIView.as_view(), name='video-analysis-update'),
    path('video-analysis/list/', views.VideoAnalysisListAPIView.as_view(), name='video-analysis-list'),
]