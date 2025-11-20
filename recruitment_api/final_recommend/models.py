from django.db import models
import uuid
from django.utils import timezone


class InterviewEvaluationTask(models.Model):
    """面试评估任务模型"""
    
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    # 任务相关信息
    group_id = models.CharField(max_length=255, verbose_name="简历组ID")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="任务状态")
    progress = models.IntegerField(default=0, verbose_name="处理进度")
    current_speaker = models.CharField(max_length=100, blank=True, null=True, verbose_name="当前发言者")
    
    # 错误信息
    error_message = models.TextField(blank=True, null=True, verbose_name="错误信息")
    
    # 结果信息
    result_file = models.FileField(upload_to='interview_evaluation_reports/%Y/%m/%d/', 
                                  blank=True, null=True, verbose_name="评估报告文件")
    result_summary = models.TextField(blank=True, null=True, verbose_name="评估结果摘要")
    
    class Meta:
        db_table = 'interview_evaluation_tasks'
        verbose_name = "面试评估任务"
        verbose_name_plural = "面试评估任务"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"面试评估任务 {self.group_id} ({self.status})"