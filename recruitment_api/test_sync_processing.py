import os
import sys
import django
from django.conf import settings

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 配置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recruitment_api.settings')
django.setup()

def test_sync_processing():
    """
    测试同步处理功能
    """
    print("开始测试同步处理功能...")
    
    # 模拟Django请求数据
    from resume_screening.screening_manage import parse_position_resumes_json
    
    # 创建测试数据
    test_data = {
        "position": {
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
        },
        "resumes": [
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
            }
        ]
    }
    
    # 解析数据
    position_data, resumes_data = parse_position_resumes_json(test_data)
    print(f"解析岗位数据: {position_data.get('position')}")
    print(f"解析简历数量: {len(resumes_data)}")
    
    print("测试完成。")

if __name__ == "__main__":
    test_sync_processing()