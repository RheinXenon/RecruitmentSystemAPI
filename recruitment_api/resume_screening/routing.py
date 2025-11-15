# (Channels路由配置)
from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/screening/progress/<uuid:task_id>/', consumers.ScreeningProgressConsumer.as_asgi()),
]
