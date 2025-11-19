import threading
import time
import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from .models import VideoAnalysis
from resume_screening.models import ResumeData
import uuid


def simulate_video_analysis(video_analysis_id):
    """
    模拟视频分析过程的函数
    这个函数会在后台线程中运行，模拟视频分析过程
    """
    try:
        # 等待一段时间模拟分析过程（5-10秒）
        time.sleep(random.randint(1, 2))
        
        # 获取视频分析记录
        video_analysis = VideoAnalysis.objects.get(id=video_analysis_id)
        
        # 生成模拟的分析结果
        video_analysis.fraud_score = round(random.uniform(0.05, 0.3), 3)  # 欺诈评分
        video_analysis.neuroticism_score = round(random.uniform(0.2, 0.8), 3)  # 神经质评分
        video_analysis.extraversion_score = round(random.uniform(0.3, 0.9), 3)  # 外倾性评分
        video_analysis.openness_score = round(random.uniform(0.4, 0.95), 3)  # 开放性评分
        video_analysis.agreeableness_score = round(random.uniform(0.5, 0.95), 3)  # 宜人性评分
        video_analysis.conscientiousness_score = round(random.uniform(0.6, 0.98), 3)  # 尽责性评分
        video_analysis.confidence_score = round(random.uniform(0.8, 0.99), 3)  # 置信度评分
        
        # 生成模拟摘要
        video_analysis.summary = f"模拟分析完成。候选人表现出较强的{'外倾性' if video_analysis.extraversion_score > 0.7 else '尽责性'}特征。"
        
        # 更新状态为完成
        video_analysis.status = 'completed'
        
        # 保存分析结果
        video_analysis.save()
        
    except VideoAnalysis.DoesNotExist:
        # 视频分析记录不存在，记录错误但不抛出异常
        pass
    except Exception as e:
        # 如果出现异常，更新状态为失败
        try:
            video_analysis = VideoAnalysis.objects.get(id=video_analysis_id)
            video_analysis.status = 'failed'
            video_analysis.error_message = f"模拟分析过程中发生错误: {str(e)}"
            video_analysis.save()
        except VideoAnalysis.DoesNotExist:
            pass


class VideoAnalysisAPIView(APIView):
    """
    视频分析API - 接收视频数据并保存到数据库
    """

    def post(self, request, format=None):
        """
        接收视频数据并创建视频分析记录
        请求参数：
        - video_file: 视频文件
        - candidate_name: 候选人姓名
        - position_applied: 应聘岗位
        - resume_data_id: 简历数据ID（可选，用于关联简历数据）
        - video_name: 视频名称（可选，默认为文件名）
        """
        try:
            # 获取请求数据
            video_file = request.FILES.get('video_file')
            candidate_name = request.data.get('candidate_name')
            position_applied = request.data.get('position_applied')
            resume_data_id = request.data.get('resume_data_id')
            video_name = request.data.get('video_name', video_file.name if video_file else None)
            
            # 参数校验
            if not video_file:
                return Response(
                    {"error": "缺少参数: video_file"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not candidate_name:
                return Response(
                    {"error": "缺少参数: candidate_name"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not position_applied:
                return Response(
                    {"error": "缺少参数: position_applied"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not video_name:
                return Response(
                    {"error": "无法确定视频名称"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 如果提供了简历数据ID，验证其存在性
            resume_data = None
            if resume_data_id:
                try:
                    resume_data = ResumeData.objects.get(id=resume_data_id)
                except ResumeData.DoesNotExist:
                    return Response(
                        {"error": "指定的简历数据不存在"}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            # 创建视频分析记录
            video_analysis = VideoAnalysis.objects.create(
                video_name=video_name,
                video_file=video_file,
                file_size=video_file.size if video_file else None,
                candidate_name=candidate_name,
                position_applied=position_applied,
                status='pending'
            )
            
            # 如果提供了简历数据ID且存在，则建立关联
            if resume_data:
                print("简历数据ID且存在，则建立关联")
                resume_data.video_analysis = video_analysis
                resume_data.save()
            
            # 启动模拟分析线程
            print("启动线程")
            analysis_thread = threading.Thread(
                target=simulate_video_analysis,
                args=(video_analysis.id,)
            )
            analysis_thread.daemon = True  # 设置为守护线程
            analysis_thread.start()
            
            # 返回成功响应
            response_data = {
                "message": "视频数据接收成功，分析已在后台开始",
                "video_id": str(video_analysis.id),
                "video_name": video_analysis.video_name,
                "candidate_name": video_analysis.candidate_name,
                "position_applied": video_analysis.position_applied,
                "status": video_analysis.status,
                "created_at": video_analysis.created_at.isoformat()
            }
            
            # 如果关联了简历数据，添加相关信息
            if resume_data:
                response_data["resume_data_id"] = str(resume_data.id)
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {"error": f"处理视频数据时发生错误: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VideoAnalysisStatusAPIView(APIView):
    """
    视频分析状态查询API
    """

    def get(self, request, video_id, format=None):
        """
        根据视频ID查询分析状态和结果
        """
        try:
            # 获取视频分析记录
            try:
                video_analysis = VideoAnalysis.objects.get(id=video_id)
            except VideoAnalysis.DoesNotExist:
                return Response(
                    {"error": "视频分析记录不存在"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 构建响应数据
            response_data = {
                "video_id": str(video_analysis.id),
                "video_name": video_analysis.video_name,
                "candidate_name": video_analysis.candidate_name,
                "position_applied": video_analysis.position_applied,
                "status": video_analysis.status,
                "created_at": video_analysis.created_at.isoformat()
            }
            
            # 如果有分析结果，添加到响应中
            if video_analysis.status == 'completed':
                response_data.update({
                    "analysis_result": video_analysis.analysis_result,
                    "summary": video_analysis.summary,
                    "confidence_score": video_analysis.confidence_score
                })
            
            # 如果分析失败，添加错误信息
            if video_analysis.status == 'failed' and video_analysis.error_message:
                response_data["error_message"] = video_analysis.error_message
            
            return JsonResponse(response_data)
            
        except Exception as e:
            return Response(
                {"error": f"查询视频分析状态时发生错误: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VideoAnalysisUpdateAPIView(APIView):
    """
    视频分析结果更新API - 用于更新视频分析结果
    """

    def post(self, request, video_id, format=None):
        """
        更新视频分析结果
        请求参数：
        - fraud_score: 欺诈评分 (0-1)
        - neuroticism_score: 神经质评分 (0-1)
        - extraversion_score: 外倾性评分 (0-1)
        - openness_score: 开放性评分 (0-1)
        - agreeableness_score: 宜人性评分 (0-1)
        - conscientiousness_score: 尽责性评分 (0-1)
        - summary: 分析摘要（可选）
        - confidence_score: 置信度评分（可选）
        - status: 状态（可选，默认为completed）
        """
        try:
            # 获取视频分析记录
            try:
                video_analysis = VideoAnalysis.objects.get(id=video_id)
            except VideoAnalysis.DoesNotExist:
                return Response(
                    {"error": "视频分析记录不存在"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 获取请求数据
            fraud_score = request.data.get('fraud_score')
            neuroticism_score = request.data.get('neuroticism_score')
            extraversion_score = request.data.get('extraversion_score')
            openness_score = request.data.get('openness_score')
            agreeableness_score = request.data.get('agreeableness_score')
            conscientiousness_score = request.data.get('conscientiousness_score')
            summary = request.data.get('summary')
            confidence_score = request.data.get('confidence_score')
            status_value = request.data.get('status', 'completed')
            
            # 更新分析结果
            if fraud_score is not None:
                video_analysis.fraud_score = float(fraud_score)
            
            if neuroticism_score is not None:
                video_analysis.neuroticism_score = float(neuroticism_score)
            
            if extraversion_score is not None:
                video_analysis.extraversion_score = float(extraversion_score)
            
            if openness_score is not None:
                video_analysis.openness_score = float(openness_score)
            
            if agreeableness_score is not None:
                video_analysis.agreeableness_score = float(agreeableness_score)
            
            if conscientiousness_score is not None:
                video_analysis.conscientiousness_score = float(conscientiousness_score)
            
            if summary is not None:
                video_analysis.summary = summary
                
            if confidence_score is not None:
                video_analysis.confidence_score = float(confidence_score)
            
            # 更新状态
            video_analysis.status = status_value
            
            # 保存更新
            video_analysis.save()
            
            # 构建响应数据
            response_data = {
                "message": "视频分析结果更新成功",
                "video_id": str(video_analysis.id),
                "status": video_analysis.status,
                "analysis_result": video_analysis.analysis_result
            }
            
            # 如果有关联的简历数据，添加相关信息
            if hasattr(video_analysis, 'linked_resume_data') and video_analysis.linked_resume_data:
                response_data["resume_data_id"] = str(video_analysis.linked_resume_data.id)
            
            # 返回成功响应
            return Response(response_data, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {"error": "评分值必须是有效的数字"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"更新视频分析结果时发生错误: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VideoAnalysisListAPIView(APIView):
    """
    视频分析列表API - 支持分页查询
    """

    def get(self, request, format=None):
        """
        获取视频分析列表，支持分页和筛选
        查询参数：
        - page: 页码，默认为1
        - page_size: 每页数量，默认为10，最大50
        - candidate_name: 候选人姓名（可选，用于筛选）
        - position_applied: 应聘岗位（可选，用于筛选）
        - status: 状态（可选，用于筛选）
        """
        try:
            # 获取查询参数
            page = int(request.GET.get('page', 1))
            page_size = min(int(request.GET.get('page_size', 10)), 50)
            candidate_name = request.GET.get('candidate_name', None)
            position_applied = request.GET.get('position_applied', None)
            status_filter = request.GET.get('status', None)
            
            # 构建查询
            queryset = VideoAnalysis.objects.all().order_by('-created_at')
            
            # 根据候选人姓名筛选
            if candidate_name:
                queryset = queryset.filter(candidate_name__icontains=candidate_name)
                
            # 根据应聘岗位筛选
            if position_applied:
                queryset = queryset.filter(position_applied__icontains=position_applied)
                
            # 根据状态筛选
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            # 分页
            start = (page - 1) * page_size
            end = start + page_size
            paginated_queryset = queryset[start:end]
            
            # 构建响应数据
            video_list = []
            for video in paginated_queryset:
                video_data = {
                    "video_id": str(video.id),
                    "video_name": video.video_name,
                    "candidate_name": video.candidate_name,
                    "position_applied": video.position_applied,
                    "status": video.status,
                    "confidence_score": video.confidence_score,
                    "created_at": video.created_at.isoformat()
                }
                
                # 如果分析已完成，添加分析结果
                if video.status == 'completed':
                    video_data["analysis_result"] = video.analysis_result
                    
                video_list.append(video_data)
            
            return JsonResponse({
                "videos": video_list,
                "total": queryset.count(),
                "page": page,
                "page_size": page_size
            })
            
        except Exception as e:
            return Response(
                {"error": f"查询视频分析列表时发生错误: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )