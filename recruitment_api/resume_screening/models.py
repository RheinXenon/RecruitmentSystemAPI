from django.db import models
from django.utils import timezone
import uuid
import hashlib


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
    current_step = models.IntegerField(default=0)  # 当前步骤
    total_steps = models.IntegerField(default=1)  # 总步骤数
    error_message = models.TextField(blank=True, null=True)
    current_speaker = models.CharField(max_length=100, blank=True, null=True)  # 当前发言者
    # 添加岗位信息字段
    position_data = models.JSONField(null=True, blank=True, verbose_name="岗位信息")

    class Meta:
        db_table = 'resume_screening_tasks'
        ordering = ['-created_at']


class ScreeningReport(models.Model):
    """初筛报告模型"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(ResumeScreeningTask, on_delete=models.CASCADE, related_name='reports')
    created_at = models.DateTimeField(default=timezone.now)
    md_file = models.FileField(upload_to='screening_reports/%Y/%m/%d/')
    original_filename = models.CharField(max_length=255)
    # 添加简历内容字段
    resume_content = models.TextField(null=True, blank=True, verbose_name="简历内容")
    # 添加JSON报告内容字段
    json_report_content = models.TextField(null=True, blank=True, verbose_name="JSON报告内容")

    class Meta:
        db_table = 'screening_reports'
        ordering = ['-created_at']


class ResumeGroup(models.Model):
    """简历组模型 - 用于组织具有相同岗位信息的简历"""
    # 状态选项
    STATUS_CHOICES = [
        ('pending', '待分析'),
        ('interview_analysis', '面试分析中'),
        ('comprehensive_screening', '综合筛选中'),
        ('completed', '已完成'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now)
    
    # 岗位信息（与组内所有简历相同）
    position_title = models.CharField(max_length=255, verbose_name="岗位名称")
    position_details = models.JSONField(verbose_name="岗位详细信息")
    
    # 岗位信息的哈希值，用于验证岗位信息一致性
    position_hash = models.CharField(max_length=64, unique=True, verbose_name="岗位信息哈希值")
    
    # 组标识信息
    group_name = models.CharField(max_length=255, verbose_name="简历组名称")
    description = models.TextField(blank=True, null=True, verbose_name="组描述")
    
    # 统计信息
    resume_count = models.IntegerField(default=0, verbose_name="简历数量")
    
    # 状态信息
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending', verbose_name="状态")
    
    class Meta:
        db_table = 'resume_groups'
        ordering = ['-created_at']
        verbose_name = "简历组"
        verbose_name_plural = "简历组"
        indexes = [
            models.Index(fields=['position_title']),
            models.Index(fields=['position_hash']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status']),
        ]


class ResumeData(models.Model):
    """简历数据统一管理模型"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now)
    
    # 岗位信息
    position_title = models.CharField(max_length=255, verbose_name="岗位名称")
    position_details = models.JSONField(verbose_name="岗位详细信息")
    
    # 候选人信息
    candidate_name = models.CharField(max_length=100, verbose_name="候选人姓名")
    resume_content = models.TextField(verbose_name="简历内容")
    
    # 筛选结果
    screening_score = models.JSONField(null=True, blank=True, verbose_name="筛选评分")
    screening_summary = models.TextField(null=True, blank=True, verbose_name="筛选总结")
    
    # 文件存储
    resume_file_hash = models.CharField(max_length=64, unique=True, verbose_name="简历文件哈希值")
    report_md_file = models.FileField(upload_to='screening_reports/%Y/%m/%d/', null=True, blank=True, verbose_name="报告MD文件")
    report_json_file = models.FileField(upload_to='screening_reports/%Y/%m/%d/', null=True, blank=True, verbose_name="报告JSON文件")
    # 添加JSON报告内容字段
    json_report_content = models.TextField(null=True, blank=True, verbose_name="JSON报告内容")
    
    # 关联任务
    task = models.ForeignKey(ResumeScreeningTask, on_delete=models.SET_NULL, null=True, blank=True, related_name='resume_data')
    report = models.ForeignKey(ScreeningReport, on_delete=models.SET_NULL, null=True, blank=True, related_name='resume_data')
    
    # 关联简历组
    group = models.ForeignKey(ResumeGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name='resumes')
    
    # 关联视频分析记录（一对一关系，每个简历数据只能对应一个视频记录）
    video_analysis = models.OneToOneField('video_analysis.VideoAnalysis', on_delete=models.SET_NULL, null=True, blank=True, related_name='linked_resume_data')
    
    class Meta:
        db_table = 'resume_data'
        ordering = ['-created_at']
        verbose_name = "简历数据"
        verbose_name_plural = "简历数据"
        indexes = [
            models.Index(fields=['candidate_name']),
            models.Index(fields=['position_title']),
            models.Index(fields=['resume_file_hash']),
            models.Index(fields=['created_at']),
        ]