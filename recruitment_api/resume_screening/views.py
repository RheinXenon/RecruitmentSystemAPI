# resume_screening/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import FileResponse, JsonResponse
from .models import ResumeScreeningTask, ScreeningReport, ResumeData, ResumeGroup
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
            import traceback
            # 更新任务状态为失败
            task.status = 'failed'
            task.error_message = f"{str(e)}\n{traceback.format_exc()}"
            task.current_speaker = None  # 清除当前发言者信息
            task.save()
            # 打印详细错误信息到控制台
            print(f"任务执行失败: {str(e)}")
            print(traceback.format_exc())


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
                            "id": str(resume_data.id),  # 添加ID字段
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


class CreateResumeGroupAPIView(APIView):
    """
    创建简历组API
    首次创建简历组时必须要有对应的一个或多个初筛记录，
    保证这几组记录对应同一个岗位（校验码值一样），否则返回错误
    """

    def post(self, request, format=None):
        """
        创建简历组
        请求参数：
        - group_name: 简历组名称
        - description: 描述（可选）
        - resume_data_ids: 简历数据ID列表
        """
        try:
            print(request.data)

            group_name = request.data.get('group_name')
            description = request.data.get('description', '')
            resume_data_ids = request.data.get('resume_data_ids', [])
            
            # 参数校验
            if not group_name:
                return Response(
                    {"error": "缺少参数: group_name"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not resume_data_ids or not isinstance(resume_data_ids, list):
                return Response(
                    {"error": "缺少参数或参数格式错误: resume_data_ids"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 获取简历数据
            resume_data_list = ResumeData.objects.filter(id__in=resume_data_ids)

            print("resume_data_list:", resume_data_list)
            
            # 检查是否所有简历数据都存在
            if len(resume_data_list) != len(resume_data_ids):
                existing_ids = [str(resume.id) for resume in resume_data_list]
                missing_ids = [rid for rid in resume_data_ids if rid not in existing_ids]
                return Response(
                    {"error": f"部分简历数据不存在，缺少的ID: {missing_ids}"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 检查是否为空列表
            if len(resume_data_list) == 0:
                return Response(
                    {"error": "至少需要一个简历数据"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 检查所有简历是否属于同一岗位
            # 获取第一个简历的岗位信息作为基准
            first_resume = resume_data_list[0]
            base_position_title = first_resume.position_title
            base_position_details = first_resume.position_details
            
            # 检查其他简历是否与第一个简历的岗位信息一致
            mismatched_resumes = []
            for resume_data in resume_data_list[1:]:
                if (resume_data.position_title != base_position_title or 
                    resume_data.position_details != base_position_details):
                    mismatched_resumes.append({
                        "resume_id": str(resume_data.id),
                        "resume_position_title": resume_data.position_title,
                        "base_position_title": base_position_title
                    })
            
            if mismatched_resumes:
                print("不属于同一岗位")
                return Response(
                    {
                        "error": "所有简历必须属于同一岗位",
                        "mismatched_resumes": mismatched_resumes,
                        "first_resume_id": str(first_resume.id)
                    }, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 计算岗位信息哈希值
            import hashlib
            import json
            
            position_info_str = json.dumps({
                "position_title": base_position_title,
                "position_details": base_position_details
            }, sort_keys=True)
            
            position_hash = hashlib.sha256(position_info_str.encode('utf-8')).hexdigest()
            
            # 检查是否已存在相同的岗位哈希值的简历组
            from .models import ResumeGroup
            existing_group = ResumeGroup.objects.filter(position_hash=position_hash).first()
            
            if existing_group:
                # 如果已存在该岗位的简历组，则直接使用该组
                resume_group = existing_group
            else:
                # 创建新的简历组
                resume_group = ResumeGroup.objects.create(
                    position_title=base_position_title,
                    position_details=base_position_details,
                    position_hash=position_hash,
                    group_name=group_name,
                    description=description,
                    resume_count=len(resume_data_list)
                )
            
            # 将简历数据关联到简历组
            for resume_data in resume_data_list:
                resume_data.group = resume_group
                resume_data.save()
            
            # 更新简历组中的简历数量
            resume_group.resume_count = resume_data_list.count()
            resume_group.save()
            
            return Response({
                "message": "简历组创建成功",
                "group_id": str(resume_group.id),
                "group_name": resume_group.group_name,
                "resume_count": resume_group.resume_count
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {"error": f"创建简历组时发生错误: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResumeGroupListAPIView(APIView):
    """
    简历组列表API - 支持分页查询
    """

    def get(self, request, format=None):
        """
        获取简历组列表，支持分页
        查询参数：
        - page: 页码，默认为1
        - page_size: 每页数量，默认为10，最大50
        - position_title: 岗位名称（可选，用于筛选）
        - include_resumes: 是否包含简历信息，默认为false
        """
        try:
            # 获取查询参数
            page = int(request.GET.get('page', 1))
            page_size = min(int(request.GET.get('page_size', 10)), 50)
            position_title = request.GET.get('position_title', None)
            include_resumes = request.GET.get('include_resumes', 'false').lower() == 'true'
            
            # 构建查询
            groups = ResumeGroup.objects.all().order_by('-created_at')
            
            # 根据岗位名称筛选
            if position_title:
                groups = groups.filter(position_title__icontains=position_title)
            
            # 分页
            start = (page - 1) * page_size
            end = start + page_size
            paginated_groups = groups[start:end]
            
            # 构建响应数据
            groups_data = []
            for group in paginated_groups:
                # 获取关联的简历数据数量
                resume_count = group.resumes.count()
                
                group_data = {
                    "id": str(group.id),
                    "group_name": group.group_name,
                    "position_title": group.position_title,
                    "description": group.description,
                    "resume_count": resume_count,
                    "created_at": group.created_at.isoformat()
                }
                
                # 如果需要包含简历信息
                if include_resumes:
                    resumes = group.resumes.all()
                    resume_data = []
                    for resume in resumes:
                        resume_data.append({
                            "id": str(resume.id),
                            "candidate_name": resume.candidate_name,
                            "position_title": resume.position_title,
                            "screening_score": resume.screening_score,
                            "screening_summary": resume.screening_summary,
                            "resume_content": resume.resume_content,
                            "created_at": resume.created_at.isoformat(),
                            "report_md_url": resume.report_md_file.url if resume.report_md_file else None,
                            "report_json_url": resume.report_json_file.url if resume.report_json_file else None,
                        })
                    group_data["resumes"] = resume_data
                
                groups_data.append(group_data)
            
            return JsonResponse({
                "groups": groups_data,
                "total": groups.count(),
                "page": page,
                "page_size": page_size
            })
            
        except Exception as e:
            return Response(
                {"error": f"查询简历组时发生错误: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AddResumeToGroupAPIView(APIView):
    """
    向现有简历组添加新简历API
    """

    def post(self, request, format=None):
        """
        向指定简历组添加新简历
        请求参数：
        - group_id: 简历组ID
        - resume_data_id: 简历数据ID
        """
        try:
            group_id = request.data.get('group_id')
            resume_data_id = request.data.get('resume_data_id')
            
            # 参数校验
            if not group_id:
                return Response(
                    {"error": "缺少参数: group_id"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not resume_data_id:
                return Response(
                    {"error": "缺少参数: resume_data_id"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 获取简历组
            try:
                resume_group = ResumeGroup.objects.get(id=group_id)
            except ResumeGroup.DoesNotExist:
                return Response(
                    {"error": "简历组不存在"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 获取简历数据
            try:
                resume_data = ResumeData.objects.get(id=resume_data_id)
            except ResumeData.DoesNotExist:
                return Response(
                    {"error": "简历数据不存在"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 检查简历是否已经属于该组
            if resume_data.group == resume_group:
                return Response(
                    {"error": "简历数据已属于该简历组"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 检查简历是否与简历组属于同一岗位
            if (resume_data.position_title != resume_group.position_title or 
                resume_data.position_details != resume_group.position_details):
                return Response(
                    {
                        "error": "简历与简历组不属于同一岗位",
                        "resume_position_title": resume_data.position_title,
                        "group_position_title": resume_group.position_title
                    }, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 将简历数据关联到简历组
            resume_data.group = resume_group
            resume_data.save()
            
            # 更新简历组中的简历数量
            resume_group.resume_count = resume_group.resumes.count()
            resume_group.save()
            
            return Response({
                "message": "简历成功添加到简历组",
                "group_id": str(resume_group.id),
                "group_name": resume_group.group_name,
                "resume_count": resume_group.resume_count
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": f"添加简历到简历组时发生错误: {str(e)}"}, 
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
                            "id": str(resume_data.id),  # 添加ID字段
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
