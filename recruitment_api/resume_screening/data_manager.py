import os
import hashlib
import json
from django.core.files.base import ContentFile
from .models import ResumeData, ResumeScreeningTask, ScreeningReport


def calculate_file_hash(file_content):
    """
    计算文件内容的SHA256哈希值
    
    Args:
        file_content (str or bytes): 文件内容
        
    Returns:
        str: 文件的SHA256哈希值
    """
    if isinstance(file_content, str):
        file_content = file_content.encode('utf-8')
    
    sha256_hash = hashlib.sha256()
    sha256_hash.update(file_content)
    return sha256_hash.hexdigest()


def save_resume_screening_data(task: ResumeScreeningTask, 
                              position_data: dict, 
                              candidate_name: str, 
                              resume_content: str,
                              md_report_content: str,
                              json_report_content: str) -> ResumeData:
    """
    保存简历筛选数据到统一数据表中
    
    Args:
        task (ResumeScreeningTask): 筛选任务对象
        position_data (dict): 岗位信息
        candidate_name (str): 候选人姓名
        resume_content (str): 简历内容
        md_report_content (str): Markdown格式的报告内容
        json_report_content (str): JSON格式的报告内容
        
    Returns:
        ResumeData: 保存的简历数据对象
    """
    # 计算简历文件哈希值，用于唯一标识
    resume_hash = calculate_file_hash(resume_content)
    
    # 检查是否已存在相同简历
    try:
        existing_data = ResumeData.objects.get(resume_file_hash=resume_hash)
        # 如果已存在，更新相关信息
        existing_data.position_title = position_data.get('position', '未知岗位')
        existing_data.position_details = position_data
        existing_data.screening_score = extract_scores_from_json_report(json_report_content)
        existing_data.screening_summary = extract_summary_from_md_report(md_report_content)
        existing_data.task = task
        existing_data.save()
        return existing_data
    except ResumeData.DoesNotExist:
        # 如果不存在，则创建新记录
        pass
    
    # 创建新的简历数据记录
    resume_data = ResumeData(
        position_title=position_data.get('position', '未知岗位'),
        position_details=position_data,
        candidate_name=candidate_name,
        resume_content=resume_content,
        resume_file_hash=resume_hash,
        task=task
    )
    
    # 提取评分和总结信息
    resume_data.screening_score = extract_scores_from_json_report(json_report_content)
    resume_data.screening_summary = extract_summary_from_md_report(md_report_content)
    
    # 保存到数据库
    resume_data.save()
    
    # 保存报告文件
    if md_report_content:
        md_filename = f"{candidate_name}_简历初筛报告_{resume_hash[:8]}.md"
        resume_data.report_md_file.save(
            md_filename, 
            ContentFile(md_report_content.encode('utf-8'))
        )
    
    if json_report_content:
        json_filename = f"{candidate_name}_简历初筛报告_{resume_hash[:8]}.json"
        resume_data.report_json_file.save(
            json_filename, 
            ContentFile(json_report_content.encode('utf-8'))
        )
    
    # 保存后再次保存以确保文件关联正确
    resume_data.save()
    
    return resume_data


def extract_scores_from_json_report(json_report_content: str) -> dict:
    """
    从JSON报告中提取评分信息
    
    Args:
        json_report_content (str): JSON格式的报告内容
        
    Returns:
        dict: 评分信息
    """
    try:
        if isinstance(json_report_content, str):
            report_data = json.loads(json_report_content)
        else:
            report_data = json_report_content
            
        return report_data.get('scores', {})
    except (json.JSONDecodeError, AttributeError):
        return {}


def extract_summary_from_md_report(md_report_content: str) -> str:
    """
    从Markdown报告中提取总结信息
    
    Args:
        md_report_content (str): Markdown格式的报告内容
        
    Returns:
        str: 报告总结
    """
    try:
        # 简单提取总结部分，实际可以根据报告结构进行更复杂的提取
        lines = md_report_content.split('\n')
        summary_lines = []
        in_summary = False
        
        for line in lines:
            if '最终建议' in line or '综合评分' in line:
                in_summary = True
            
            if in_summary:
                summary_lines.append(line)
                
            if in_summary and len(summary_lines) > 10:  # 限制摘要长度
                break
                
        return '\n'.join(summary_lines) if summary_lines else md_report_content[:500]
    except Exception:
        return md_report_content[:500]


def get_or_create_screening_report(task: ResumeScreeningTask, 
                                  candidate_name: str, 
                                  md_file_path: str) -> ScreeningReport:
    """
    获取或创建筛选报告记录
    
    Args:
        task (ResumeScreeningTask): 筛选任务对象
        candidate_name (str): 候选人姓名
        md_file_path (str): MD文件路径
        
    Returns:
        ScreeningReport: 筛选报告对象
    """
    # 检查是否已存在报告记录
    try:
        report = ScreeningReport.objects.get(
            task=task,
            original_filename__icontains=candidate_name
        )
        return report
    except ScreeningReport.DoesNotExist:
        pass
    
    # 创建新的报告记录
    if os.path.exists(md_file_path):
        with open(md_file_path, 'rb') as f:
            md_filename = os.path.basename(md_file_path)
            report = ScreeningReport.objects.create(
                task=task,
                original_filename=md_filename,
            )
            # 保存MD文件
            report.md_file.save(md_filename, f)
            return report
    
    return None


def get_resume_data_by_hash(resume_hash: str) -> ResumeData:
    """
    根据简历哈希值获取简历数据
    
    Args:
        resume_hash (str): 简历文件哈希值
        
    Returns:
        ResumeData: 简历数据对象
    """
    try:
        return ResumeData.objects.get(resume_file_hash=resume_hash)
    except ResumeData.DoesNotExist:
        return None


def get_resume_data_by_candidate(candidate_name: str) -> list:
    """
    根据候选人姓名获取简历数据列表
    
    Args:
        candidate_name (str): 候选人姓名
        
    Returns:
        list: 简历数据对象列表
    """
    return ResumeData.objects.filter(candidate_name__icontains=candidate_name)


def get_resume_data_by_position(position_title: str) -> list:
    """
    根据岗位名称获取简历数据列表
    
    Args:
        position_title (str): 岗位名称
        
    Returns:
        list: 简历数据对象列表
    """
    return ResumeData.objects.filter(position_title__icontains=position_title)