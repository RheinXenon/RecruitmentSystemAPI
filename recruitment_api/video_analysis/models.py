from django.db import models
import uuid
from django.utils import timezone

class VideoAnalysis(models.Model):
    """视频分析模型"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now)
    
    # 视频信息
    video_name = models.CharField(max_length=255, verbose_name="视频名称")
    video_file = models.FileField(upload_to='video_analysis/videos/%Y/%m/%d/', verbose_name="视频文件")
    file_size = models.BigIntegerField(verbose_name="文件大小(字节)", null=True, blank=True)
    
    # 候选人信息
    candidate_name = models.CharField(max_length=100, verbose_name="候选人姓名")
    position_applied = models.CharField(max_length=255, verbose_name="应聘岗位")
    
    # 分析状态
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('processing', '分析中'),
        ('completed', '已完成'),
        ('failed', '失败')
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="分析状态")
    
    # 分析结果（6个维度评分，取值0-1之间）
    fraud_score = models.FloatField(null=True, blank=True, verbose_name="欺诈评分")
    neuroticism_score = models.FloatField(null=True, blank=True, verbose_name="神经质评分")
    extraversion_score = models.FloatField(null=True, blank=True, verbose_name="外倾性评分")
    openness_score = models.FloatField(null=True, blank=True, verbose_name="开放性评分")
    agreeableness_score = models.FloatField(null=True, blank=True, verbose_name="宜人性评分")
    conscientiousness_score = models.FloatField(null=True, blank=True, verbose_name="尽责性评分")
    
    # 综合信息
    summary = models.TextField(null=True, blank=True, verbose_name="分析摘要")
    confidence_score = models.FloatField(null=True, blank=True, verbose_name="置信度评分")
    
    # 错误信息
    error_message = models.TextField(null=True, blank=True, verbose_name="错误信息")
    
    class Meta:
        db_table = 'video_analysis'
        ordering = ['-created_at']
        verbose_name = "视频分析"
        verbose_name_plural = "视频分析"
        indexes = [
            models.Index(fields=['candidate_name']),
            models.Index(fields=['position_applied']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.candidate_name} - {self.video_name}"
    
    @property
    def analysis_result(self):
        """将评分结果组合成字典格式返回"""
        return {
            "fraud_score": self.fraud_score,
            "neuroticism_score": self.neuroticism_score,
            "extraversion_score": self.extraversion_score,
            "openness_score": self.openness_score,
            "agreeableness_score": self.agreeableness_score,
            "conscientiousness_score": self.conscientiousness_score
        }