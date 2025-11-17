import os
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from resume_screening.models import ResumeScreeningTask, ScreeningReport, ResumeData
from resume_screening.data_manager import save_resume_screening_data, calculate_file_hash


class Command(BaseCommand):
    help = '迁移现有简历数据到统一数据表'

    def add_arguments(self, parser):
        parser.add_argument(
            '--resume-dir',
            type=str,
            default='resumes',
            help='简历文件目录路径'
        )

    def handle(self, *args, **options):
        resume_dir = options['resume_dir']
        if not os.path.isabs(resume_dir):
            resume_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                '..',
                resume_dir
            )
        
        self.stdout.write(f'开始迁移目录: {resume_dir}')
        
        # 获取所有已完成的任务
        completed_tasks = ResumeScreeningTask.objects.filter(status='completed')
        self.stdout.write(f'找到 {completed_tasks.count()} 个已完成任务')
        
        migrated_count = 0
        for task in completed_tasks:
            # 获取任务相关的报告
            reports = ScreeningReport.objects.filter(task=task)
            
            for report in reports:
                try:
                    # 从文件名提取候选人姓名
                    candidate_name = report.original_filename.replace('简历初筛结果.md', '')
                    
                    # 尝试查找对应的JSON文件
                    json_filename = f"{candidate_name}.json"
                    json_file_path = os.path.join(resume_dir, json_filename)
                    
                    # 尝试查找原始简历文件（假设存在）
                    resume_content = self.find_resume_content(candidate_name, resume_dir)
                    
                    # 读取报告内容
                    md_report_content = ""
                    if report.md_file and os.path.exists(report.md_file.path):
                        with open(report.md_file.path, 'r', encoding='utf-8') as f:
                            md_report_content = f.read()
                    
                    json_report_content = ""
                    if os.path.exists(json_file_path):
                        with open(json_file_path, 'r', encoding='utf-8') as f:
                            json_report_content = f.read()
                    
                    # 创建假的岗位信息（因为旧数据中没有保存）
                    position_data = {
                        "position": "未知岗位",
                        "required_skills": [],
                        "min_experience": 0
                    }
                    
                    # 保存到统一数据表
                    resume_data = save_resume_screening_data(
                        task=task,
                        position_data=position_data,
                        candidate_name=candidate_name,
                        resume_content=resume_content,
                        md_report_content=md_report_content,
                        json_report_content=json_report_content
                    )
                    
                    self.stdout.write(
                        f'成功迁移 {candidate_name} 的数据，ID: {resume_data.id}'
                    )
                    migrated_count += 1
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'迁移 {report.original_filename} 时出错: {str(e)}'
                        )
                    )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'数据迁移完成，共迁移 {migrated_count} 条记录'
            )
        )

    def find_resume_content(self, candidate_name, resume_dir):
        """
        尝试查找原始简历内容
        """
        # 常见的简历文件名模式
        possible_names = [
            f"{candidate_name}.txt",
            f"{candidate_name}简历.txt",
            f"{candidate_name}_简历.txt",
            f"{candidate_name}.md",
            f"{candidate_name}简历.md"
        ]
        
        for name in possible_names:
            file_path = os.path.join(resume_dir, name)
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return f.read()
                except Exception:
                    continue
        
        return "无法找到原始简历内容"