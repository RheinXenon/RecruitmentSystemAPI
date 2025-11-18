# resume_screening/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import FileResponse, JsonResponse
from .models import ResumeScreeningTask, ScreeningReport, ResumeData
from .serializers import ResumeScreeningSerializer
from .screening_manage import parse_position_resumes_json, run_resume_screening_from_payload, set_current_task
from .data_manager import save_resume_screening_data, get_or_create_screening_report
import uuid
import os
import json
from django.conf import settings
import threading


class ResumeScreeningAPIView(APIView):
    """
    简历初筛API - 集成Autogen增强分析
    """

    def post(self, request, format=None):
        # 优先解析前端传来的岗位与简历 JSON，解析成功后直接返回提交成功响应
        try:
            position_data, resumes_data = parse_position_resumes_json(request.data)
        except ValueError as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # 创建筛选任务，同时保存岗位信息
        task = ResumeScreeningTask.objects.create(
            status='pending',
            progress=0,
            total_steps=len(resumes_data),
            current_step=0,
            position_data=position_data  # 保存岗位信息
        )

        # 异步处理简历筛选任务
        threading.Thread(
            target=self._run_screening_task,
            args=(task, position_data, resumes_data)
        ).start()

        # 立即返回响应给前端
        return Response({
            "status": "submitted",
            "message": "简历筛选任务已提交，正在后台处理",
            "task_id": str(task.id)
        }, status=status.HTTP_202_ACCEPTED)

    def _run_screening_task(self, task, position_data, resumes_data):
        """在后台线程中运行简历筛选任务"""
        try:
            # 设置当前任务对象，以便在筛选过程中更新发言者信息
            set_current_task(task)
            
            # 更新任务状态为运行中
            task.status = 'running'
            task.save()
            
            results = run_resume_screening_from_payload(
                position=position_data,
                resumes=resumes_data,
                run_chat=True  # False没有开启对话
            )
            
            # 保存报告文件到数据库
            reports = []
            resume_screening_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resumes')
            
            for i, (candidate_name, result_content) in enumerate(results.items()):
                # 更新进度
                task.progress = int((i + 1) / len(results) * 100)
                task.current_step = i + 1
                task.save()
                
                # 查找生成的MD文件
                md_filename = f"{candidate_name}简历初筛结果.md"
                md_file_path = os.path.join(resume_screening_dir, md_filename)
                
                # 查找生成的JSON文件
                json_filename = f"{candidate_name}.json"
                json_file_path = os.path.join(resume_screening_dir, json_filename)
                
                # 获取简历内容
                resume_content = ""
                for resume in resumes_data:
                    if os.path.splitext(resume['name'])[0] == candidate_name:
                        resume_content = resume['content']
                        break
                
                # 读取报告文件内容
                md_report_content = ""
                json_report_content = ""
                
                if os.path.exists(md_file_path):
                    with open(md_file_path, 'r', encoding='utf-8') as f:
                        md_report_content = f.read()
                
                if os.path.exists(json_file_path):
                    with open(json_file_path, 'r', encoding='utf-8') as f:
                        json_report_content = f.read()
                
                # 获取或创建报告记录，并保存简历内容和JSON报告内容
                report = get_or_create_screening_report(task, candidate_name, md_file_path, json_report_content)
                if report:
                    # 保存简历内容到报告中
                    report.resume_content = resume_content
                    report.save()
                    reports.append(report)
                
                # 保存到统一数据管理表
                save_resume_screening_data(
                    task=task,
                    position_data=position_data,
                    candidate_name=candidate_name,
                    resume_content=resume_content,
                    md_report_content=md_report_content,
                    json_report_content=json_report_content
                )
                        
            # 更新任务状态为完成
            task.status = 'completed'
            task.progress = 100
            task.current_step = task.total_steps
            task.current_speaker = None  # 清除当前发言者信息
            task.save()
            
        except Exception as e:
            # 更新任务状态为失败
            task.status = 'failed'
            task.error_message = str(e)
            task.current_speaker = None  # 清除当前发言者信息
            task.save()


class ScreeningTaskStatusAPIView(APIView):
    """查询任务状态API（手动刷新方案）"""

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

            # 如果任务正在运行，包含当前发言者信息
            if task.status == 'running' and task.current_speaker:
                response_data['current_speaker'] = task.current_speaker

            # 如果任务完成，包含报告下载链接以及岗位信息和简历内容
            if task.status == 'completed':
                reports = ScreeningReport.objects.filter(task=task)
                if reports.exists():
                    response_data['reports'] = []
                    for report in reports:
                        report_data = {
                            "report_id": str(report.id),
                            "report_filename": report.original_filename,
                            "download_url": f"/api/screening/reports/{report.id}/download/",
                            "resume_content": report.resume_content if report.resume_content else ""
                        }
                        
                        # 如果任务中有岗位信息，添加到报告数据中
                        if task.position_data:
                            report_data["position_info"] = task.position_data
                        
                        response_data['reports'].append(report_data)
               
                # 添加简历数据（包括JSON内容）
                resume_data_list = ResumeData.objects.filter(task=task)
                if resume_data_list.exists():
                    response_data['resume_data'] = []
                    for resume_data in resume_data_list:
                        resume_data_info = {
                            "candidate_name": resume_data.candidate_name,
                            "position_title": resume_data.position_title,
                            "scores": resume_data.screening_score,
                            "summary": resume_data.screening_summary,
                            "json_content": resume_data.json_report_content,  # JSON报告内容
                            "resume_content": resume_data.resume_content,
                            "report_md_url": resume_data.report_md_file.url if resume_data.report_md_file else None,
                            "report_json_url": resume_data.report_json_file.url if resume_data.report_json_file else None,
                        }
                        response_data['resume_data'].append(resume_data_info)

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


class ResumeDataAPIView(APIView):
    """简历数据统一管理API"""
    
    def get(self, request, format=None):
        """
        获取简历数据列表
        支持查询参数: candidate_name, position_title
        """
        candidate_name = request.GET.get('candidate_name', None)
        position_title = request.GET.get('position_title', None)
        
        queryset = ResumeData.objects.all()
        
        if candidate_name:
            queryset = queryset.filter(candidate_name__icontains=candidate_name)
            
        if position_title:
            queryset = queryset.filter(position_title__icontains=position_title)
            
        # 简单分页
        page = int(request.GET.get('page', 1))
        page_size = min(int(request.GET.get('page_size', 10)), 50)
        start = (page - 1) * page_size
        end = start + page_size
        
        data_list = queryset[start:end]
        
        result = []
        for data in data_list:
            result.append({
                "id": str(data.id),
                "created_at": data.created_at.isoformat(),
                "position_title": data.position_title,
                "candidate_name": data.candidate_name,
                "screening_score": data.screening_score,
                "resume_file_hash": data.resume_file_hash,
                "report_md_url": data.report_md_file.url if data.report_md_file else None,
                "report_json_url": data.report_json_file.url if data.report_json_file else None,
            })
            
        return JsonResponse({
            "results": result,
            "total": queryset.count(),
            "page": page,
            "page_size": page_size
        })
    
    def post(self, request, format=None):
        """
        创建新的简历数据记录（用于手动添加）
        """
        try:
            position_title = request.data.get('position_title')
            position_details = request.data.get('position_details')
            candidate_name = request.data.get('candidate_name')
            resume_content = request.data.get('resume_content')
            
            if not all([position_title, candidate_name, resume_content]):
                return Response(
                    {"error": "缺少必要参数"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            resume_data = ResumeData.objects.create(
                position_title=position_title,
                position_details=position_details or {},
                candidate_name=candidate_name,
                resume_content=resume_content,
                resume_file_hash=hashlib.sha256(resume_content.encode('utf-8')).hexdigest()
            )
            
            return Response({
                "id": str(resume_data.id),
                "message": "简历数据创建成功"
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ScreeningTaskHistoryAPIView(APIView):
    """查询历史任务信息API"""

    def get(self, request, format=None):
        # 获取查询参数
        status = request.GET.get('status', None)
        page = int(request.GET.get('page', 1))
        page_size = min(int(request.GET.get('page_size', 10)), 50)
        
        # 构建查询
        tasks = ResumeScreeningTask.objects.all().order_by('-created_at')
        
        # 根据状态过滤
        if status:
            tasks = tasks.filter(status=status)
            
        # 分页
        start = (page - 1) * page_size
        end = start + page_size
        paginated_tasks = tasks[start:end]
        
        # 构建响应数据
        history_data = []
        for task in paginated_tasks:
            task_data = {
                "task_id": str(task.id),
                "status": task.status,
                "progress": task.progress,
                "current_step": task.current_step,
                "total_steps": task.total_steps,
                "created_at": task.created_at.isoformat()
            }
            
            # 如果任务正在运行，包含当前发言者信息
            if task.status == 'running' and task.current_speaker:
                task_data['current_speaker'] = task.current_speaker

            # 如果任务完成，包含报告下载链接以及岗位信息和简历内容
            if task.status == 'completed':
                reports = ScreeningReport.objects.filter(task=task)
                if reports.exists():
                    task_data['reports'] = []
                    for report in reports:
                        report_data = {
                            "report_id": str(report.id),
                            "report_filename": report.original_filename,
                            "download_url": f"/api/screening/reports/{report.id}/download/",
                            "resume_content": report.resume_content if report.resume_content else ""
                        }
                        
                        # 如果任务中有岗位信息，添加到报告数据中
                        if task.position_data:
                            report_data["position_info"] = task.position_data
                        
                        task_data['reports'].append(report_data)
                
                # 添加简历数据（包括JSON内容）
                resume_data_list = ResumeData.objects.filter(task=task)
                if resume_data_list.exists():
                    task_data['resume_data'] = []
                    for resume_data in resume_data_list:
                        resume_data_info = {
                            "candidate_name": resume_data.candidate_name,
                            "position_title": resume_data.position_title,
                            "scores": resume_data.screening_score,
                            "summary": resume_data.screening_summary,
                            "json_content": resume_data.json_report_content,  # JSON报告内容
                            "resume_content": resume_data.resume_content,
                            "report_md_url": resume_data.report_md_file.url if resume_data.report_md_file else None,
                            "report_json_url": resume_data.report_json_file.url if resume_data.report_json_file else None,
                        }
                        task_data['resume_data'].append(resume_data_info)
            
            history_data.append(task_data)
        
        return JsonResponse({
            "tasks": history_data,
            "total": tasks.count(),
            "page": page,
            "page_size": page_size
        })
