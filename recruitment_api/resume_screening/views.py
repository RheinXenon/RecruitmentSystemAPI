# resume_screening/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import FileResponse, JsonResponse
from .models import ResumeScreeningTask, ScreeningReport
from .serializers import ResumeScreeningSerializer
from .tasks import run_autogen_screening
import uuid


class ResumeScreeningAPIView(APIView):
    """
    简历初筛API - 集成Autogen增强分析
    """

    def post(self, request, format=None):
        # 1. 数据验证（使用你之前的序列化器）
        print(request.data)
        serializer = ResumeScreeningSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"status": "error", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        validated_data = serializer.validated_data
        position_data = validated_data['position']
        resumes_data = validated_data['resumes']

        try:
            screening_results = []

            # 对每份简历创建分析任务
            for i, resume in enumerate(resumes_data):
                # 创建任务记录
                task = ResumeScreeningTask.objects.create(
                    resume_data=resume,
                    position_data=position_data
                )

                # 异步调用autogen分析任务
                celery_result = run_autogen_screening.delay(
                    str(task.id),  # 转换为字符串确保序列化
                    resume,
                    position_data
                )

                # 保存Celery任务ID
                task.celery_task_id = celery_result.id
                task.save()

                screening_results.append({
                    "resume_name": resume.get('name', f'简历_{i + 1}'),
                    "task_id": str(task.id),
                    "status": "pending",
                    "progress": 0,
                    "websocket_channel": f"screening_task_{task.id}",
                    "monitor_url": f"/api/screening/tasks/{task.id}/monitor/",
                    "report_url": None  # 完成后更新
                })

            # 返回即时响应（HTTP 202 Accepted）
            return Response(
                {
                    "status": "processing",
                    "message": "简历分析任务已开始，请通过WebSocket监控进度",
                    "screening_id": str(uuid.uuid4()),  # 本次筛查会话ID
                    "results": screening_results,
                    "monitor_instructions": {
                        "websocket_url": "ws://your-domain.com/ws/screening/progress/",
                        "polling_url": "/api/screening/tasks/{task_id}/status/"
                    }
                },
                status=status.HTTP_202_ACCEPTED
            )

        except Exception as e:
            return Response(
                {
                    "status": "error",
                    "message": f"任务创建失败: {str(e)}"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ScreeningTaskStatusAPIView(APIView):
    """查询任务状态API（轮询备用方案）"""

    def get(self, request, task_id, format=None):
        try:
            task = ResumeScreeningTask.objects.get(id=task_id)
            response_data = {
                "task_id": str(task.id),
                "status": task.status,
                "progress": task.progress,
                "current_step": task.current_step,
                "total_steps": task.total_steps,
                "created_at": task.created_at.isoformat()
            }

            # 如果任务完成，包含报告下载链接
            if task.status == 'completed' and hasattr(task, 'report'):
                response_data['report_download_url'] = \
                    f"/api/screening/reports/{task.report.id}/download/"
                response_data['report_filename'] = task.report.original_filename

            return JsonResponse(response_data)

        except ResumeScreeningTask.DoesNotExist:
            return Response(
                {"error": "任务不存在"},
                status=status.HTTP_404_NOT_FOUND
            )


class ScreeningReportDownloadAPIView(APIView):
    """报告文件下载API"""

    def get(self, request, report_id, format=None):
        try:
            report = ScreeningReport.objects.get(id=report_id)

            # 返回文件下载响应
            response = FileResponse(
                report.md_file.open('rb'),
                content_type='text/markdown'
            )
            response['Content-Disposition'] = \
                f'attachment; filename="{report.original_filename}"'

            return response

        except ScreeningReport.DoesNotExist:
            return Response(
                {"error": "报告不存在"},
                status=status.HTTP_404_NOT_FOUND
            )