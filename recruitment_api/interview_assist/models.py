"""
面试辅助模块数据模型
人在回路的面试官AI助手
"""

from django.db import models
import uuid
from django.utils import timezone


class InterviewAssistSession(models.Model):
    """面试辅助会话"""
    
    STATUS_CHOICES = [
        ('active', '进行中'),
        ('paused', '暂停'),
        ('completed', '已完成'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    # 关联信息
    resume_data = models.ForeignKey(
        'resume_screening.ResumeData', 
        on_delete=models.CASCADE,
        related_name='interview_sessions',
        verbose_name="简历数据"
    )
    interviewer_name = models.CharField(max_length=100, verbose_name="面试官姓名")
    
    # 岗位配置
    job_config = models.JSONField(default=dict, verbose_name="岗位配置")
    company_config = models.JSONField(default=dict, verbose_name="公司配置")
    
    # 会话状态
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="会话状态")
    current_round = models.IntegerField(default=0, verbose_name="当前轮次")
    
    # 缓存的问题池
    question_pool = models.JSONField(default=list, verbose_name="候选问题池")
    
    # 简历亮点/兴趣点（从简历中提取的值得追问的点）
    resume_highlights = models.JSONField(default=list, verbose_name="简历亮点")
    
    # 最终报告
    final_report = models.JSONField(null=True, blank=True, verbose_name="最终报告")
    report_file = models.FileField(
        upload_to='interview_assist_reports/%Y/%m/%d/', 
        blank=True, null=True, 
        verbose_name="报告文件"
    )
    
    class Meta:
        db_table = 'interview_assist_sessions'
        verbose_name = "面试辅助会话"
        verbose_name_plural = "面试辅助会话"
        ordering = ['-created_at']
    
    def __str__(self):
        candidate_name = self.resume_data.candidate_name if self.resume_data else "未知"
        return f"面试会话 - {candidate_name} ({self.status})"


class InterviewQARecord(models.Model):
    """面试问答记录"""
    
    QUESTION_SOURCE_CHOICES = [
        ('ai_suggested', 'AI建议'),
        ('ai_followup', 'AI追问建议'),
        ('ai_resume_based', 'AI基于简历'),
        ('hr_custom', 'HR自定义'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        InterviewAssistSession, 
        on_delete=models.CASCADE, 
        related_name='qa_records',
        verbose_name="所属会话"
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    
    # 轮次
    round_number = models.IntegerField(verbose_name="轮次")
    
    # 问题信息
    question = models.TextField(verbose_name="提问内容")
    question_source = models.CharField(
        max_length=20, 
        choices=QUESTION_SOURCE_CHOICES,
        default='ai_suggested',
        verbose_name="问题来源"
    )
    question_category = models.CharField(max_length=50, blank=True, verbose_name="问题类别")
    expected_skills = models.JSONField(default=list, verbose_name="考察技能")
    question_difficulty = models.IntegerField(default=5, verbose_name="问题难度(1-10)")
    
    # 关联的简历兴趣点
    related_interest_point = models.JSONField(null=True, blank=True, verbose_name="关联兴趣点")
    
    # 回答信息
    answer = models.TextField(blank=True, verbose_name="候选人回答")
    answer_recorded_at = models.DateTimeField(null=True, blank=True, verbose_name="回答记录时间")
    answer_duration_seconds = models.IntegerField(null=True, blank=True, verbose_name="回答时长(秒)")
    
    # AI评估结果
    evaluation = models.JSONField(null=True, blank=True, verbose_name="评估结果")
    
    # 追问建议
    followup_suggestions = models.JSONField(default=list, verbose_name="追问建议")
    was_followed_up = models.BooleanField(default=False, verbose_name="是否已追问")
    
    class Meta:
        db_table = 'interview_qa_records'
        verbose_name = "面试问答记录"
        verbose_name_plural = "面试问答记录"
        ordering = ['session', 'round_number']
    
    def __str__(self):
        return f"第{self.round_number}轮 - {self.question[:30]}..."
