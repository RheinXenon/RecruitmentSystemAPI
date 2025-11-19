from django.urls import path
from . import views

urlpatterns = [
    path('screening/', views.ResumeScreeningAPIView.as_view(), name='resume-screening'),
    path('tasks/<uuid:task_id>/status/', views.ScreeningTaskStatusAPIView.as_view(), name='screening-task-status'),
    path('tasks-history/', views.ScreeningTaskHistoryAPIView.as_view(), name='screening-task-history'),
    path('reports/<uuid:report_id>/download/', views.ScreeningReportDownloadAPIView.as_view(), name='screening-report-download'),
    path('reports/<uuid:report_id>/detail/', views.ScreeningReportDetailAPIView.as_view(), name='screening-report-detail'),
    path('data/', views.ResumeDataAPIView.as_view(), name='resume-data'),
    path('groups/create/', views.CreateResumeGroupAPIView.as_view(), name='create-resume-group'),
    path('groups/add-resume/', views.AddResumeToGroupAPIView.as_view(), name='add-resume-to-group'),
    path('groups/remove-resume/', views.RemoveResumeFromGroupAPIView.as_view(), name='remove-resume-from-group'),
    path('groups/set-status/', views.SetResumeGroupStatusAPIView.as_view(), name='set-resume-group-status'),
    path('groups/<uuid:group_id>/', views.ResumeGroupDetailAPIView.as_view(), name='resume-group-detail'),
    path('groups/', views.ResumeGroupListAPIView.as_view(), name='resume-group-list'),
    path('link-resume-to-video/', views.LinkResumeToVideoAPIView.as_view(), name='link-resume-to-video'),
    path('unlink-resume-from-video/', views.UnlinkResumeFromVideoAPIView.as_view(), name='unlink-resume-from-video'),
]