import json
import os
from typing import Dict, Any, Tuple

# 直接导入 Django 模型
from resume_screening.models import ResumeGroup, ResumeData
from video_analysis.models import VideoAnalysis


def load_recruitment_criteria(criteria_path="../position_settings/migrations/recruitment_criteria.json") -> Dict[str, Any]:
    """
    从指定路径加载招聘标准
    
    Args:
        criteria_path: 招聘标准文件路径
        
    Returns:
        招聘标准字典
    """
    try:
        with open(criteria_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # 如果找不到文件，返回默认值
        return {
            "position": "Python开发工程师",
            "required_skills": ["Python", "Django", "MySQL", "Linux"],
            "min_experience": 2,
            "education": ["本科", "硕士"]
        }


def load_candidates_data_by_group(group_id: str) -> Dict[str, Any]:
    """
    根据简历组ID加载候选人数据
    
    Args:
        group_id: 简历组ID
        
    Returns:
        候选人数据字典，键为候选人姓名，值为简历数据
    """
    try:
        # 获取简历组
        resume_group = ResumeGroup.objects.get(id=group_id)
        
        # 获取组内所有简历数据
        resumes = ResumeData.objects.filter(group=resume_group)
        
        # 构建候选人数据字典
        candidates = {}
        for resume in resumes:
            # 解析JSON报告内容
            json_content = {}
            if resume.json_report_content:
                try:
                    json_content = json.loads(resume.json_report_content)
                except json.JSONDecodeError:
                    pass
            
            candidates[resume.candidate_name] = {
                "position_title": resume.position_title,
                "resume_content": resume.resume_content,
                "screening_score": resume.screening_score,
                "screening_summary": resume.screening_summary,
                "final_recommendation": json_content.get("final_recommendation", {})
            }
            
        return candidates
    except ResumeGroup.DoesNotExist:
        print(f"未找到ID为 {group_id} 的简历组")
        return {}
    except Exception as e:
        print(f"加载候选人数据时发生错误: {e}")
        return {}


def load_personality_and_fraud_data(group_id: str) -> Tuple[Dict[str, Dict[str, float]], Dict[str, float]]:
    """
    根据简历组ID加载人格测试和欺诈检测数据
    
    Args:
        group_id: 简历组ID
        
    Returns:
        tuple: (人格测试分数字典, 欺诈检测分数字典)
    """

    big_five_scores = {}
    fraud_detection_scores = {}
    
    try:
        # 获取简历组
        resume_group = ResumeGroup.objects.get(id=group_id)
        
        # 获取组内所有简历数据
        resumes = ResumeData.objects.filter(group=resume_group)
        
        # 遍历简历数据，查找关联的视频分析记录
        for resume in resumes:
            # 检查是否有关联的视频分析记录
            if hasattr(resume, 'video_analysis') and resume.video_analysis:
                video_analysis = resume.video_analysis
                
                # 提取人格测试分数
                big_five_scores[resume.candidate_name] = {
                    'openness': video_analysis.openness_score or 0.0,
                    'conscientiousness': video_analysis.conscientiousness_score or 0.0,
                    'extraversion': video_analysis.extraversion_score or 0.0,
                    'agreeableness': video_analysis.agreeableness_score or 0.0,
                    'neuroticism': video_analysis.neuroticism_score or 0.0,
                }
                
                # 提取欺诈检测分数
                fraud_detection_scores[resume.candidate_name] = video_analysis.fraud_score or 0.0
                
    except ResumeGroup.DoesNotExist:
        print(f"未找到ID为 {group_id} 的简历组")
    except Exception as e:
        print(f"加载人格测试和欺诈检测数据时发生错误: {e}")
    
    return big_five_scores, fraud_detection_scores