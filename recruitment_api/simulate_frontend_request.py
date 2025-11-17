import os
import sys
import json

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from resume_screening.screening_manage import run_resume_screening_from_payload

def simulate_frontend_request():
    """
    模拟前端提交岗位信息和简历数据进行初筛
    """
    print("开始模拟前端请求...")
    
    # 模拟前端提交的岗位信息
    position_data = {
        "position": "前端开发工程师",
        "required_skills": ["HTML", "JavaScript", "CSS"],
        "optional_skills": ["Vue.js", "React", "Angular"],
        "min_experience": 2,
        "education": ["本科", "硕士"],
        "certifications": ["前端工程师证书"],
        "salary_range": [12000, 25000],
        "project_requirements": {
            "min_projects": 3,
            "team_lead_experience": True
        }
    }
    
    # 模拟前端提交的简历数据
    resumes_data = [
        {
            "name": "张三简历.txt",
            "content": """姓名：张三
应聘职位：前端开发工程师
联系方式：zhangsan@example.com

教育背景：
2016.09 - 2020.06  XX大学  计算机科学与技术 本科

工作经历：
2020.07 - 至今  XX科技有限公司  前端开发工程师
- 负责公司官网和后台管理系统的前端开发
- 使用Vue.js框架开发多个企业级应用
- 参与团队代码评审和技术分享

技能：
- 精通HTML/CSS/JavaScript
- 熟练使用Vue.js框架
- 熟悉Webpack构建工具
- 了解前端性能优化

项目经验：
项目一：企业官网重构
- 使用Vue.js重构公司官网，提升用户体验
- 优化页面加载速度，减少30%的加载时间

项目二：后台管理系统
- 独立完成整个后台管理系统的前端开发
- 实现权限控制、数据可视化等功能""",
            "metadata": {
                "size": 1024,
                "type": "text/plain"
            }
        },
        {
            "name": "李四简历.txt",
            "content": """姓名：李四
应聘职位：前端开发工程师
联系方式：lisi@example.com

教育背景：
2018.09 - 2022.06  XX理工大学  软件工程 本科

工作经历：
2022.07 - 至今  XX互联网公司  初级前端工程师
- 参与公司产品的日常维护和功能开发
- 协助团队完成前端页面的实现

技能：
- 熟悉HTML/CSS基础
- 了解JavaScript基础语法
- 了解Vue.js框架

项目经验：
项目：公司官网维护
- 负责官网部分内容更新和bug修复
- 协助完成页面样式调整""",
            "metadata": {
                "size": 512,
                "type": "text/plain"
            }
        }
    ]
    
    print("提交的岗位信息:")
    print(json.dumps(position_data, ensure_ascii=False, indent=2))
    
    print("\n提交的简历数量:", len(resumes_data))
    for i, resume in enumerate(resumes_data):
        print(f"简历 {i+1}: {resume['name']}")
    
    # 调用简历初筛函数处理
    print("\n开始处理简历初筛...")
    try:
        results = run_resume_screening_from_payload(
            position=position_data,
            resumes=resumes_data,
            run_chat=True  # 设置为False以避免实际调用LLM，仅测试文件生成流程
        )
        
        print("\n处理完成，生成的报告:")
        for candidate_name, result in results.items():
            print(f"- {candidate_name}:")
            if isinstance(result, str) and result.startswith("报告已保存到"):
                print(f"  {result}")
            else:
                print(f"  生成了 {len(result)} 字符的报告内容")
                
        # 检查生成的文件
        print("\n检查生成的文件...")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        resumes_dir = os.path.join(base_dir, 'resume_screening', 'resumes')
        
        if os.path.exists(resumes_dir):
            files = os.listdir(resumes_dir)
            md_files = [f for f in files if f.endswith('.md')]
            json_files = [f for f in files if f.endswith('.json')]
            
            print(f"生成的MD报告文件 ({len(md_files)} 个):")
            for f in md_files:
                print(f"  - {f}")
                
            print(f"生成的JSON结果文件 ({len(json_files)} 个):")
            for f in json_files:
                print(f"  - {f}")
        else:
            print("未找到生成的文件目录")
            
    except Exception as e:
        print(f"处理过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    simulate_frontend_request()