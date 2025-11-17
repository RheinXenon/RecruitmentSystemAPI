import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from resume_screening.screening_manage import RecruitmentSystem

def test_recruitment_system():
    print("测试RecruitmentSystem类...")
    
    # 获取正确的绝对路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    criteria_file_path = os.path.join(base_dir, 'position_settings', 'migrations', 'recruitment_criteria.json')
    md_file_path = os.path.join(base_dir, '本岗位招聘量化标准.md')
    
    print(f"岗位信息文件路径: {criteria_file_path}")
    print(f"量化标准文件路径: {md_file_path}")
    
    # 检查文件是否存在
    print(f"岗位信息文件是否存在: {os.path.exists(criteria_file_path)}")
    print(f"量化标准文件是否存在: {os.path.exists(md_file_path)}")
    
    # 创建RecruitmentSystem实例
    rs = RecruitmentSystem(
        criteria_file="../position_settings/migrations/recruitment_criteria.json",
        md_file=md_file_path
    )
    
    # 输出基本信息
    print(f"职位: {rs.quantification_table['position']}")
    print(f"评分标准维度: {list(rs.quantification_table['scoring_rules'].keys())}")
    print(f"岗位要求键: {list(rs.quantification_table['criteria'].keys())}")
    
    # 测试哈希计算
    criteria_hash = rs._calculate_criteria_hash(rs.quantification_table['criteria'])
    print(f"岗位信息哈希值: {criteria_hash}")
    
    # 测试一致性验证
    is_consistent = rs.verify_criteria_consistency(
        "../position_settings/migrations/recruitment_criteria.json",
        md_file_path
    )
    print(f"与岗位信息文件一致性: {is_consistent}")
    
    print("测试完成。")

if __name__ == "__main__":
    test_recruitment_system()