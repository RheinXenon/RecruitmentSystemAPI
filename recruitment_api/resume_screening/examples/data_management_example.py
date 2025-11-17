"""
简历数据管理功能示例脚本
演示如何使用新的ResumeData模型和data_manager模块
"""

import os
import django
import sys

# 添加项目路径到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 配置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recruitment_api.settings')
django.setup()

from resume_screening.models import ResumeScreeningTask, ScreeningReport, ResumeData
from resume_screening.data_manager import (
    save_resume_screening_data, 
    get_resume_data_by_hash, 
    get_resume_data_by_candidate,
    get_resume_data_by_position,
    calculate_file_hash
)


def example_usage():
    """
    演示数据管理功能的使用方法
    """
    print("=== 简历数据管理功能演示 ===\n")
    
    # 示例数据
    position_data = {
        "position": "高级Python开发工程师",
        "required_skills": ["Python", "Django", "MySQL", "Linux"],
        "optional_skills": ["Redis", "Docker", "Vue.js"],
        "min_experience": 3,
        "education": ["本科", "硕士"],
        "salary_range": [12000, 25000]
    }
    
    candidate_name = "张三"
    resume_content = """
    姓名：张三
    联系方式：138****1234 | zhangsan@email.com
    
    工作经验：
    1. 高级Python开发工程师 | ABC科技有限公司 | 2020.03 - 至今
       - 负责后端API开发和维护
       - 使用Django框架开发企业级应用
       - 参与系统架构设计和优化
    
    2. Python开发工程师 | XYZ软件公司 | 2018.06 - 2020.02
       - 参与CRM系统的开发
       - 负责数据库设计和优化
    """
    
    md_report_content = """
    # 企业招聘简历评审报告
    
    ## 评审记录
    
    ### HR_Expert的发言
    HR评分：85分，理由：候选人具备3年以上的Python开发经验，学历符合要求，职业稳定性较好。
    
    ### Technical_Expert的发言
    技术评分：90分，理由：技术栈完整，熟悉Django框架，有实际项目经验。
    
    ### Project_Manager_Expert的发言
    管理评分：75分，理由：有团队协作经验，但缺乏项目管理经验。
    
    ### Critic的发言
    综合评分：83.5分，最终建议：推荐面试，建议月薪：15000-18000元。
    """
    
    json_report_content = """
    {
      "name": "张三",
      "scores": {
        "hr_score": 85.0,
        "technical_score": 90.0,
        "manager_score": 75.0,
        "comprehensive_score": 83.5
      },
      "final_recommendation": {
        "decision": "推荐面试",
        "reasons": "综合能力较强，符合岗位要求"
      }
    }
    """
    
    # 计算简历哈希值
    resume_hash = calculate_file_hash(resume_content)
    print(f"简历文件哈希值: {resume_hash}\n")
    
    # 检查是否已存在相同简历
    existing_data = get_resume_data_by_hash(resume_hash)
    if existing_data:
        print(f"已存在相同的简历数据，ID: {existing_data.id}")
        return
    
    # 创建模拟任务和报告
    task = ResumeScreeningTask.objects.create(
        status='completed',
        progress=100,
        total_steps=1,
        current_step=1
    )
    
    # 保存到统一数据管理表
    print("保存简历筛选数据...")
    resume_data = save_resume_screening_data(
        task=task,
        position_data=position_data,
        candidate_name=candidate_name,
        resume_content=resume_content,
        md_report_content=md_report_content,
        json_report_content=json_report_content
    )
    
    print(f"数据保存成功，ID: {resume_data.id}")
    print(f"岗位名称: {resume_data.position_title}")
    print(f"候选人姓名: {resume_data.candidate_name}")
    print(f"综合评分: {resume_data.screening_score.get('comprehensive_score', 0) if resume_data.screening_score else 0}")
    print(f"创建时间: {resume_data.created_at}")
    print(f"简历哈希: {resume_data.resume_file_hash}")
    
    # 演示查询功能
    print("\n=== 查询功能演示 ===")
    
    # 按候选人姓名查询
    candidate_results = get_resume_data_by_candidate("张三")
    print(f"按候选人姓名查询到 {candidate_results.count()} 条记录")
    
    # 按岗位名称查询
    position_results = get_resume_data_by_position("Python开发")
    print(f"按岗位名称查询到 {position_results.count()} 条记录")
    
    # 按哈希值查询
    hash_result = get_resume_data_by_hash(resume_hash)
    if hash_result:
        print(f"按哈希值查询成功，ID: {hash_result.id}")
    
    print("\n=== 文件存储演示 ===")
    if resume_data.report_md_file:
        print(f"MD报告文件已保存: {resume_data.report_md_file.name}")
    if resume_data.report_json_file:
        print(f"JSON报告文件已保存: {resume_data.report_json_file.name}")


if __name__ == "__main__":
    example_usage()