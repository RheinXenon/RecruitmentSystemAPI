import os
import sys
import json

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_consistency_fix():
    """测试一致性修复功能"""
    print("开始测试一致性修复功能...")
    
    # 导入必要的模块
    from resume_screening.screening_manage import (
        recruitment_system, 
        run_resume_screening_from_payload
    )
    
    # 显示初始量化标准
    print("初始量化标准:")
    print(f"职位: {recruitment_system.quantification_table['position']}")
    print(f"必备技能: {recruitment_system.quantification_table['criteria'].get('required_skills', [])}")
    
    # 创建测试岗位数据
    test_position = {
        "position": "高级Python开发工程师",
        "required_skills": ["Python", "Django", "FastAPI", "PostgreSQL"],
        "optional_skills": ["Redis", "Docker", "Kubernetes", "AWS"],
        "min_experience": 5,
        "education": ["本科", "硕士"],
        "certifications": ["AWS认证", "Oracle认证"],
        "salary_range": [20000, 40000],
        "project_requirements": {
            "min_projects": 5,
            "team_lead_experience": True
        }
    }
    
    # 运行一次简历筛选
    print("\n运行简历筛选...")
    results = run_resume_screening_from_payload(
        position=test_position,
        resumes=[{
            "name": "李四简历.txt",
            "content": "李四的简历内容...",
            "metadata": {"size": 1000, "type": "text/plain"}
        }],
        run_chat=False
    )
    
    # 检查更新后的量化标准
    print("\n更新后的量化标准:")
    print(f"职位: {recruitment_system.quantification_table['position']}")
    print(f"必备技能: {recruitment_system.quantification_table['criteria']['required_skills']}")
    print(f"最低经验: {recruitment_system.quantification_table['criteria']['min_experience']}年")
    
    print("\n测试完成。")

if __name__ == "__main__":
    test_consistency_fix()