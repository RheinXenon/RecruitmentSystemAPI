import os
import django
from django.core.management.base import BaseCommand
from django.test import Client
from django.conf import settings
import json


class Command(BaseCommand):
    help = '测试视频分析功能'

    def handle(self, *args, **options):
        # 创建测试客户端
        client = Client()
        
        # 创建一个测试视频文件
        test_video_path = os.path.join(settings.BASE_DIR, 'test_video.mp4')
        with open(test_video_path, 'wb') as f:
            f.write(b'Test video content')
        
        try:
            # 测试上传视频
            with open(test_video_path, 'rb') as video_file:
                response = client.post('/api/video-analysis/', {
                    'video_file': video_file,
                    'candidate_name': '张三',
                    'position_applied': '高级Python开发工程师',
                    'video_name': '张三_面试视频.mp4'
                })
            
            self.stdout.write(
                self.style.SUCCESS(f'上传响应: {response.status_code}')
            )
            self.stdout.write(
                self.style.SUCCESS(f'响应内容: {json.dumps(response.json(), indent=2, ensure_ascii=False)}')
            )
            
            # 清理测试文件
            os.remove(test_video_path)
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'测试过程中发生错误: {str(e)}')
            )
            # 清理测试文件
            if os.path.exists(test_video_path):
                os.remove(test_video_path)