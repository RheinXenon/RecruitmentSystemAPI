"""
面试辅助模块URL配置
"""

from django.urls import path
from . import views

urlpatterns = [
    # 会话管理
    path('sessions/', views.SessionView.as_view(), name='create_session'),
    path('sessions/<uuid:session_id>/', views.SessionView.as_view(), name='session_detail'),
    
    # 问题生成
    path('sessions/<uuid:session_id>/generate-questions/', 
         views.GenerateQuestionsView.as_view(), name='generate_questions'),
    
    # 记录问答并评估
    path('sessions/<uuid:session_id>/record-qa/', 
         views.RecordQAView.as_view(), name='record_qa'),
    
    # 生成追问建议
    path('sessions/<uuid:session_id>/generate-followup/', 
         views.GenerateFollowupView.as_view(), name='generate_followup'),
    
    # 问答历史
    path('sessions/<uuid:session_id>/history/', 
         views.QAHistoryView.as_view(), name='qa_history'),
    
    # 生成最终报告
    path('sessions/<uuid:session_id>/generate-report/', 
         views.GenerateReportView.as_view(), name='generate_report'),
]
