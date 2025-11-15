from rest_framework import serializers
from django.core.validators import MinValueValidator, MaxValueValidator


class PositionDataSerializer(serializers.Serializer):
    """岗位数据序列化器"""
    position = serializers.CharField(max_length=200, required=True)
    required_skills = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=True
    )
    optional_skills = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list
    )
    min_experience = serializers.IntegerField(
        required=True,
        validators=[MinValueValidator(0), MaxValueValidator(50)]
    )
    education = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=True
    )
    certifications = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list
    )
    salary_range = serializers.ListField(
        child=serializers.IntegerField(min_value=0),
        required=True
    )

    def validate_salary_range(self, value):
        """验证薪资范围格式"""
        if len(value) != 2:
            raise serializers.ValidationError("薪资范围必须包含两个值")
        if value[0] >= value[1]:
            raise serializers.ValidationError("最低薪资必须小于最高薪资")
        return value


class ResumeMetadataSerializer(serializers.Serializer):
    """简历元数据序列化器"""
    size = serializers.IntegerField(min_value=0, required=True)
    type = serializers.CharField(max_length=100, required=True)


class ResumeDataSerializer(serializers.Serializer):
    """单个简历数据序列化器"""
    name = serializers.CharField(max_length=255, required=True)
    content = serializers.CharField(required=True)
    metadata = ResumeMetadataSerializer(required=True)


class ResumeScreeningSerializer(serializers.Serializer):
    """简历初筛主序列化器"""
    position = PositionDataSerializer(required=True)
    resumes = serializers.ListField(
        child=ResumeDataSerializer(),
        required=True
    )

    def validate_resumes(self, value):
        """验证简历列表"""
        if not value:
            raise serializers.ValidationError("简历列表不能为空")
        if len(value) > 50:  # 限制最大数量
            raise serializers.ValidationError("单次处理简历数量不能超过50份")
        return value