from django.urls import path
from .views import InterviewEvaluationView, download_report

urlpatterns = [
    path('interview-evaluation/', InterviewEvaluationView.as_view(), name='interview_evaluation'),
    path('interview-evaluation/<uuid:task_id>/', InterviewEvaluationView.as_view(), name='interview_evaluation_status'),
    path('interview-evaluation/<uuid:task_id>/delete/', InterviewEvaluationView.as_view(), name='interview_evaluation_delete'),
    path('download-report/<path:file_path>', download_report, name='download_report'),
]