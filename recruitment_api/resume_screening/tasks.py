from celery import shared_task
from django.core.files.base import ContentFile
from .models import ResumeScreeningTask, ScreeningReport
import os
import uuid
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer  # 用于WebSocket通信


@shared_task(bind=True)  # bind=True 允许访问任务实例（如更新状态）
def run_autogen_screening(self, task_id, resume_data, position_data):
    """
    执行autogen脚本进行简历初筛的Celery任务

    Args:
        self: 任务实例
        task_id: 任务记录ID
        resume_data: 简历数据
        position_data: 岗位数据
    """
    try:
        # 获取任务对象
        task = ResumeScreeningTask.objects.get(id=task_id)
        task.status = 'running'
        task.celery_task_id = self.request.id
        task.save()

        # 获取WebSocket通道层（用于实时推送进度）
        channel_layer = get_channel_layer()
        room_group_name = f'screening_task_{task_id}'

        # 进度更新函数
        def update_progress(progress, message, current_step=None, total_steps=None):
            # 更新任务状态
            task.progress = progress
            if current_step and total_steps:
                task.current_step = current_step
                task.total_steps = total_steps
            task.save()

            # 通过WebSocket推送进度更新
            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {
                    'type': 'screening_progress',
                    'progress': progress,
                    'message': message,
                    'current_step': current_step or task.current_step,
                    'total_steps': total_steps or task.total_steps
                }
            )

        # 开始执行 - 更新进度
        update_progress(10, '开始处理简历分析', 1, 5)

        # TODO: 在这里集成你的autogen脚本调用
        # 以下是示例代码，你需要根据实际autogen脚本进行调整

        # 模拟调用autogen脚本的不同阶段
        update_progress(30, 'AI分析简历内容中...', 2, 5)

        # 调用你的autogen函数1
        # autogen_result_1 = your_autogen_analysis_function1(resume_data, position_data)

        update_progress(50, '进行技能匹配分析...', 3, 5)

        # 调用你的autogen函数2
        # autogen_result_2 = your_autogen_analysis_function2(resume_data, position_data)

        update_progress(70, '生成详细评估报告...', 4, 5)

        # 调用你的autogen函数3 - 生成Markdown内容
        # autogen_result_3 = your_autogen_report_function(resume_data, position_data)

        # 示例Markdown内容（替换为你的autogen实际输出）
        md_content = f"""# 简历初筛报告 - {resume_data.get('name', '未知')}

## 岗位匹配度: 85%
**应聘岗位**: {position_data.get('position', '未知岗位')}

### 技能匹配分析
- ✅ **必备技能匹配度**: 90%
- 📊 **可选技能匹配度**: 75%

### 详细评估
这里是autogen生成的详细分析内容...

*报告生成时间: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        update_progress(90, '保存报告文件中...', 5, 5)

        # 保存Markdown文件
        filename = f"screening_report_{task_id}_{uuid.uuid4().hex[:8]}.md"
        report = ScreeningReport.objects.create(
            task=task,
            original_filename=filename
        )

        # 将Markdown内容保存为文件
        report.md_file.save(filename, ContentFile(md_content.encode('utf-8')))

        # 标记任务完成
        task.status = 'completed'
        task.progress = 100
        task.save()

        update_progress(100, '分析完成！')

        return {
            'status': 'success',
            'report_id': report.id,
            'download_url': f"/api/screening/reports/{report.id}/download/"
        }

    except Exception as e:
        # 错误处理
        if 'task' in locals():
            task.status = 'failed'
            task.error_message = str(e)
            task.save()

        # 推送错误信息
        if 'channel_layer' in locals() and 'room_group_name' in locals():
            async_to_sync(channel_layer.group_send)(
                room_group_name,
                {
                    'type': 'screening_error',
                    'error_message': str(e)
                }
            )

        raise self.retry(exc=e, countdown=60, max_retries=3)  # 失败重试