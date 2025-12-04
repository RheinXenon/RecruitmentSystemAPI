"""
面试辅助模块Admin配置
"""

from django.contrib import admin
from .models import InterviewAssistSession, InterviewQARecord


@admin.register(InterviewAssistSession)
class InterviewAssistSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_candidate_name', 'interviewer_name', 'status', 'current_round', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['resume_data__candidate_name', 'interviewer_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def get_candidate_name(self, obj):
        return obj.resume_data.candidate_name if obj.resume_data else '-'
    get_candidate_name.short_description = '候选人'


@admin.register(InterviewQARecord)
class InterviewQARecordAdmin(admin.ModelAdmin):
    list_display = ['id', 'get_session_candidate', 'round_number', 'question_source', 'get_score', 'created_at']
    list_filter = ['question_source', 'was_followed_up', 'created_at']
    search_fields = ['question', 'answer']
    readonly_fields = ['id', 'created_at']
    
    def get_session_candidate(self, obj):
        if obj.session and obj.session.resume_data:
            return obj.session.resume_data.candidate_name
        return '-'
    get_session_candidate.short_description = '候选人'
    
    def get_score(self, obj):
        if obj.evaluation:
            return f"{obj.evaluation.get('normalized_score', 0):.1f}"
        return '-'
    get_score.short_description = '评分'
