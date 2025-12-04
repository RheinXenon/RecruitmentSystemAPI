"""
简历筛选模块API测试
"""

import json
import uuid
from django.test import TestCase, Client

from resume_screening.models import ResumeData, ResumeGroup, ResumeScreeningTask


class ResumeDataTestCase(TestCase):
    """简历数据模型测试"""
    
    def setUp(self):
        """测试前准备"""
        self.client = Client()
    
    def test_create_resume_data(self):
        """测试创建简历数据"""
        resume = ResumeData.objects.create(
            candidate_name='测试候选人',
            position_title='测试岗位',
            position_details={'requirements': ['技能1', '技能2']},
            resume_content='这是测试简历内容',
            resume_file_hash=f'test_{uuid.uuid4().hex[:16]}'
        )
        
        self.assertIsNotNone(resume.id)
        self.assertEqual(resume.candidate_name, '测试候选人')
        self.assertEqual(resume.position_title, '测试岗位')
    
    def test_resume_data_with_screening_results(self):
        """测试带筛选结果的简历数据"""
        resume = ResumeData.objects.create(
            candidate_name='张三',
            position_title='Python开发',
            position_details={'requirements': ['Python', 'Django']},
            resume_content='张三的简历...',
            resume_file_hash=f'test_{uuid.uuid4().hex[:16]}',
            screening_score={'overall': 85, 'skills': 90},
            screening_summary='候选人技术能力强，推荐进入面试'
        )
        
        self.assertEqual(resume.screening_score['overall'], 85)
        self.assertIn('推荐', resume.screening_summary)
    
    def test_resume_data_unique_hash(self):
        """测试简历哈希唯一性约束"""
        hash_value = f'unique_hash_{uuid.uuid4().hex[:8]}'
        
        ResumeData.objects.create(
            candidate_name='候选人1',
            position_title='岗位1',
            position_details={},
            resume_content='内容1',
            resume_file_hash=hash_value
        )
        
        # 相同哈希值应该抛出异常
        with self.assertRaises(Exception):
            ResumeData.objects.create(
                candidate_name='候选人2',
                position_title='岗位2',
                position_details={},
                resume_content='内容2',
                resume_file_hash=hash_value
            )


class ResumeGroupTestCase(TestCase):
    """简历组模型测试"""
    
    def test_create_resume_group(self):
        """测试创建简历组"""
        group = ResumeGroup.objects.create(
            position_title='高级开发工程师',
            position_details={'level': 'senior', 'team': '研发部'},
            position_hash=f'pos_hash_{uuid.uuid4().hex[:16]}',
            group_name='2024年研发招聘批次1'
        )
        
        self.assertIsNotNone(group.id)
        self.assertEqual(group.status, 'pending')
        self.assertEqual(group.resume_count, 0)
    
    def test_resume_group_with_resumes(self):
        """测试简历组关联简历"""
        group = ResumeGroup.objects.create(
            position_title='测试岗位',
            position_details={},
            position_hash=f'pos_hash_{uuid.uuid4().hex[:16]}',
            group_name='测试组'
        )
        
        # 创建多个简历并关联到组
        for i in range(3):
            ResumeData.objects.create(
                candidate_name=f'候选人{i+1}',
                position_title='测试岗位',
                position_details={},
                resume_content=f'简历内容{i+1}',
                resume_file_hash=f'hash_{uuid.uuid4().hex[:16]}',
                group=group
            )
        
        # 更新组的简历数量
        group.resume_count = group.resumes.count()
        group.save()
        
        self.assertEqual(group.resume_count, 3)
        self.assertEqual(group.resumes.count(), 3)
    
    def test_group_status_transitions(self):
        """测试简历组状态转换"""
        group = ResumeGroup.objects.create(
            position_title='测试岗位',
            position_details={},
            position_hash=f'pos_hash_{uuid.uuid4().hex[:16]}',
            group_name='测试组'
        )
        
        # 初始状态
        self.assertEqual(group.status, 'pending')
        
        # 状态转换
        group.status = 'interview_analysis'
        group.save()
        group.refresh_from_db()
        self.assertEqual(group.status, 'interview_analysis')
        
        group.status = 'completed'
        group.save()
        group.refresh_from_db()
        self.assertEqual(group.status, 'completed')


class ResumeScreeningTaskTestCase(TestCase):
    """简历筛选任务模型测试"""
    
    def test_create_task(self):
        """测试创建筛选任务"""
        task = ResumeScreeningTask.objects.create(
            status='pending',
            progress=0,
            total_steps=5
        )
        
        self.assertIsNotNone(task.id)
        self.assertEqual(task.status, 'pending')
        self.assertEqual(task.progress, 0)
    
    def test_task_progress_update(self):
        """测试任务进度更新"""
        task = ResumeScreeningTask.objects.create(
            status='running',
            progress=0,
            total_steps=4
        )
        
        # 模拟进度更新
        for step in range(1, 5):
            task.current_step = step
            task.progress = int((step / task.total_steps) * 100)
            task.save()
        
        task.refresh_from_db()
        self.assertEqual(task.current_step, 4)
        self.assertEqual(task.progress, 100)
    
    def test_task_failure(self):
        """测试任务失败状态"""
        task = ResumeScreeningTask.objects.create(
            status='running',
            progress=50
        )
        
        task.status = 'failed'
        task.error_message = '处理简历时发生错误'
        task.save()
        
        task.refresh_from_db()
        self.assertEqual(task.status, 'failed')
        self.assertIsNotNone(task.error_message)


class ResumeDataQueryTestCase(TestCase):
    """简历数据查询测试"""
    
    def setUp(self):
        """创建测试数据"""
        self.position_title = 'Python开发工程师'
        
        # 创建多个简历
        for i in range(5):
            ResumeData.objects.create(
                candidate_name=f'候选人{i+1}',
                position_title=self.position_title,
                position_details={'level': 'senior' if i % 2 == 0 else 'junior'},
                resume_content=f'简历内容{i+1}',
                resume_file_hash=f'query_hash_{uuid.uuid4().hex[:16]}',
                screening_score={'overall': 60 + i * 8}
            )
    
    def test_filter_by_position(self):
        """测试按岗位筛选"""
        resumes = ResumeData.objects.filter(position_title=self.position_title)
        self.assertEqual(resumes.count(), 5)
    
    def test_filter_by_candidate_name(self):
        """测试按候选人姓名筛选"""
        resume = ResumeData.objects.filter(candidate_name='候选人3').first()
        self.assertIsNotNone(resume)
        self.assertEqual(resume.candidate_name, '候选人3')
    
    def test_order_by_created_at(self):
        """测试按创建时间排序"""
        resumes = ResumeData.objects.all().order_by('-created_at')
        # 默认排序应该是最新的在前
        self.assertEqual(resumes.first().candidate_name, '候选人5')
