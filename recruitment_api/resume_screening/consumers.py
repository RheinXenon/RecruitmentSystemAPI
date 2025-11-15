# consumers.py (WebSocket消费者)
from channels.generic.websocket import AsyncWebsocketConsumer
import json


class ScreeningProgressConsumer(AsyncWebsocketConsumer):
    """简历初筛进度WebSocket消费者"""

    async def connect(self):
        self.task_id = str(self.scope['url_route']['kwargs']['task_id'])
        self.room_group_name = f'screening_task_{self.task_id}'

        # 加入任务组
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

        # 发送当前状态
        from .models import ResumeScreeningTask
        try:
            task = await database_sync_to_async(ResumeScreeningTask.objects.get)(id=self.task_id)
            await self.send(text_data=json.dumps({
                'type': 'current_status',
                'progress': task.progress,
                'message': f'当前进度: {task.progress}%',
                'current_step': task.current_step,
                'total_steps': task.total_steps,
                'status': task.status
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'error': f'获取任务状态失败: {str(e)}'
            }))

    async def disconnect(self, close_code):
        # 离开任务组
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # 接收来自Celery任务的消息
    async def screening_progress(self, event):
        """处理进度更新"""
        await self.send(text_data=json.dumps({
            'type': 'progress_update',
            'progress': event['progress'],
            'message': event['message'],
            'current_step': event['current_step'],
            'total_steps': event['total_steps']
        }))

    async def screening_complete(self, event):
        """处理任务完成"""
        await self.send(text_data=json.dumps({
            'type': 'task_complete',
            'report_url': event['report_url'],
            'message': '分析完成！'
        }))

    async def screening_error(self, event):
        """处理任务错误"""
        await self.send(text_data=json.dumps({
            'type': 'task_error',
            'error_message': event['error_message']
        }))