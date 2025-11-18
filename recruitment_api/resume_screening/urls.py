from django.urls import path
from . import views

urlpatterns = [
    path('screening/', views.ResumeScreeningAPIView.as_view(), name='resume-screening'),
    path('tasks/<uuid:task_id>/status/', views.ScreeningTaskStatusAPIView.as_view(), name='screening-task-status'),
    path('tasks-history/', views.ScreeningTaskHistoryAPIView.as_view(), name='screening-task-history'),
    path('reports/<uuid:report_id>/download/', views.ScreeningReportDownloadAPIView.as_view(), name='screening-report-download'),
    path('data/', views.ResumeDataAPIView.as_view(), name='resume-data'),
]