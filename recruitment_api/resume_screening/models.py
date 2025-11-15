from django.db import models
from django.utils import timezone
import uuid


class ResumeScreeningTask(models.Model):
    """简历初筛任务模型"""
    TASK_STATUS = [
        ('pending', '等待中'),
        ('running', '进行中'),
        ('completed', '已完成'),
        ('failed', '失败')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=TASK_STATUS, default='pending')
    progress = models.IntegerField(default=0)  # 进度百分比 0-100
    current_step = models.IntegerField(default=1)  # 当前步骤
    total_steps = models.IntegerField(default=1)  # 总步骤数
    celery_task_id = models.CharField(max_length=255, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    # 关联的简历和岗位数据（可序列化存储）
    resume_data = models.JSONField()
    position_data = models.JSONField()

    class Meta:
        db_table = 'resume_screening_tasks'
        ordering = ['-created_at']


class ScreeningReport(models.Model):
    """初筛报告模型"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.OneToOneField(ResumeScreeningTask, on_delete=models.CASCADE, related_name='report')
    created_at = models.DateTimeField(default=timezone.now)
    md_file = models.FileField(upload_to='screening_reports/%Y/%m/%d/')
    original_filename = models.CharField(max_length=255)

    class Meta:
        db_table = 'screening_reports'
        ordering = ['-created_at']