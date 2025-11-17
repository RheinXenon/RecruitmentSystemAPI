from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# 设置Django的默认配置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recruitment_api.settings')

# 创建Celery应用实例，这里的名字很重要
app = Celery('recruitment_api')

# 从Django的设置文件中加载Celery的配置
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动从所有已注册的Django应用中发现任务
app.autodiscover_tasks()