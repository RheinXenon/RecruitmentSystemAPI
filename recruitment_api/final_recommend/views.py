from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.http import HttpResponse, Http404, FileResponse
from django.conf import settings
import json
import logging
import threading
from django.core.files.base import ContentFile
import uuid
import os
from urllib.parse import unquote

from .models import InterviewEvaluationTask
from .after_interview import run_interview_evaluation, generate_candidate_info

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class InterviewEvaluationView(View):
    """
    面试后评估视图
    通过传入简历组ID启动整个面试后分析流程
    """
    
    def post(self, request):
        # print(request.body)
        try:
            # 解析请求数据
            data = json.loads(request.body)
            group_id = data.get('group_id')
            
            if not group_id:
                print("缺少参数group_id")
                return JsonResponse({
                    'status': 'error',
                    'message': '缺少必要的参数: group_id'
                }, status=400)
            
            # 创建任务记录
            task = InterviewEvaluationTask.objects.create(
                group_id=group_id,
                status='pending'
            )
            
            # 启动异步任务处理
            thread = threading.Thread(target=self._process_evaluation, args=(task.id, group_id))
            thread.start()
            
            # 立即返回任务ID
            return JsonResponse({
                'status': 'success',
                'message': '面试后评估任务已启动',
                'data': {
                    'task_id': str(task.id),
                    'status': task.status
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': '请求数据格式错误，应为有效的JSON格式'
            }, status=400)
        except Exception as e:
            logger.error(f"创建面试后评估任务时出错: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'创建面试后评估任务时出错: {str(e)}'
            }, status=500)
    
    def get(self, request, task_id=None):
        """获取任务状态"""
        if task_id:
            return self._get_task_status(task_id)
        else:
            # 如果没有task_id，检查是否有group_id参数
            group_id = request.GET.get('group_id')
            if group_id:
                return self._get_latest_task_by_group(group_id)
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': '缺少任务ID或简历组ID参数'
                }, status=400)
    
    def _get_task_status(self, task_id):
        """通过任务ID获取任务状态"""
        try:
            task = InterviewEvaluationTask.objects.get(id=task_id)
            response_data = {
                'task_id': str(task.id),
                'group_id': task.group_id,
                'status': task.status,
                'progress': task.progress,  # 现在返回对话轮数
                'current_speaker': task.current_speaker,
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat()
            }
            
            if task.status == 'completed' and task.result_file:
                response_data['result_file'] = task.result_file.url
                response_data['result_summary'] = task.result_summary
            elif task.status == 'failed':
                response_data['error_message'] = task.error_message
                
            return JsonResponse({
                'status': 'success',
                'data': response_data
            })
        except InterviewEvaluationTask.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': '未找到指定的任务'
            }, status=404)
        except Exception as e:
            logger.error(f"获取任务状态时出错: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'获取任务状态时出错: {str(e)}'
            }, status=500)
    
    def _get_latest_task_by_group(self, group_id):
        """根据group_id获取最近的任务状态"""
        try:
            # 获取该group_id的最新任务（按创建时间倒序排列）
            task = InterviewEvaluationTask.objects.filter(group_id=group_id).order_by('-created_at').first()
            
            # 如果没有找到任务，返回null数据
            if not task:
                return JsonResponse({
                    'status': 'success',
                    'data': None
                })
            
            # 构建响应数据
            response_data = {
                'task_id': str(task.id),
                'group_id': task.group_id,
                'status': task.status,
                'progress': task.progress,
                'current_speaker': task.current_speaker,
                'created_at': task.created_at.isoformat(),
                'updated_at': task.updated_at.isoformat()
            }
            
            # 根据任务状态添加额外字段
            if task.status == 'completed' and task.result_file:
                response_data['result_file'] = task.result_file.url
                response_data['result_summary'] = task.result_summary
            elif task.status == 'failed':
                response_data['error_message'] = task.error_message
                
            return JsonResponse({
                'status': 'success',
                'data': response_data
            })
            
        except Exception as e:
            logger.error(f"根据group_id获取任务状态时出错: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'根据group_id获取任务状态时出错: {str(e)}'
            }, status=500)


def download_report(request, file_path):
    """
    下载评估报告文件
    文件路径格式: /interview_evaluation_reports/2025/11/20/文件名.md
    """
    try:
        # 解码URL编码的文件路径
        decoded_file_path = unquote(file_path)
        
        # 构建完整文件路径
        full_file_path = os.path.join(settings.BASE_DIR, decoded_file_path.lstrip('/'))
        
        # 检查文件是否存在
        if not os.path.exists(full_file_path):
            return JsonResponse({
                'status': 'error',
                'message': '文件不存在'
            }, status=404)
        
        # 获取文件名
        filename = os.path.basename(full_file_path)
        
        # 返回文件响应
        response = FileResponse(
            open(full_file_path, 'rb'),
            as_attachment=True,
            filename=filename
        )
        return response
        
    except Exception as e:
        logger.error(f"下载文件时出错: {e}")
        return JsonResponse({
            'status': 'error',
            'message': f'下载文件时出错: {str(e)}'
        }, status=500)


    def _process_evaluation(self, task_id, group_id):
        """异步处理评估任务"""
        def update_speaker(speaker_name, message_count):
            """更新当前发言者和对话轮数"""
            try:
                task = InterviewEvaluationTask.objects.get(id=task_id)
                task.current_speaker = speaker_name
                task.progress = message_count  # 更新为对话轮数
                task.save()
            except Exception as e:
                logger.error(f"更新任务发言者时出错: {e}")
        
        try:
            # 更新任务状态为处理中
            task = InterviewEvaluationTask.objects.get(id=task_id)
            task.status = 'processing'
            task.current_speaker = '系统初始化'
            task.progress = 0  # 初始对话轮数为0
            task.save()
            
            # 运行面试后评估流程，传入进度回调函数
            messages, speakers = run_interview_evaluation(group_id, update_speaker)
            
            if not messages:
                raise Exception('评估流程未能生成有效结果')
            
            # 保存评估结果到数据库
            if messages:
                last_message = messages[-1]
                role = last_message.get('name', '未知角色')
                content = last_message.get('content', '')
                
                # 生成报告文件名
                filename = f"面试后综合评估报告_{group_id}_{task_id}.md"
                
                # 创建报告内容
                from datetime import datetime
                report_content = "# 企业招聘面试后综合评估报告\n\n"
                report_content += f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                report_content += f"**简历组ID**: {group_id}\n\n"
                report_content += f"**最终发言 - {role}**\n\n{content}\n\n"
                
                # 保存到数据库
                task.result_file.save(
                    filename,
                    ContentFile(report_content.encode('utf-8'))
                )
                
                # 保存摘要信息
                task.result_summary = content[:500]  # 保存前500个字符作为摘要
                
            task.status = 'completed'
            task.progress = len(messages)  # 最终对话轮数
            task.current_speaker = '完成'
            task.save()
            
        except Exception as e:
            logger.error(f"处理评估任务时出错: {e}")
            # 更新任务状态为失败
            try:
                task = InterviewEvaluationTask.objects.get(id=task_id)
                task.status = 'failed'
                task.error_message = str(e)
                task.current_speaker = '错误'
                task.save()
            except Exception as save_error:
                logger.error(f"保存任务失败状态时出错: {save_error}")