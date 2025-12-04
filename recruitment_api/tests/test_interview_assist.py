"""
面试辅助模块API测试
"""

import json
import uuid
from django.test import TestCase, Client
from django.urls import reverse

from interview_assist.models import InterviewAssistSession, InterviewQARecord
from resume_screening.models import ResumeData


class InterviewAssistTestCase(TestCase):
    """面试辅助模块基础测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.client = Client()
        
        # 创建测试用简历数据
        self.resume_data = ResumeData.objects.create(
            candidate_name='张三',
            position_title='高级Python开发工程师',
            position_details={
                'requirements': ['5年以上Python开发经验', '熟悉Django框架'],
                'skills': ['Python', 'Django', 'PostgreSQL']
            },
            resume_content='张三，5年Python开发经验，精通Django和Flask框架。曾在某大厂担任技术负责人。',
            resume_file_hash=f'test_hash_{uuid.uuid4().hex[:16]}'
        )
        
        self.base_url = '/interview-assist'
    
    def tearDown(self):
        """测试后清理"""
        InterviewQARecord.objects.all().delete()
        InterviewAssistSession.objects.all().delete()
        ResumeData.objects.all().delete()


class SessionViewTests(InterviewAssistTestCase):
    """会话管理API测试"""
    
    def test_create_session_success(self):
        """测试成功创建会话"""
        response = self.client.post(
            f'{self.base_url}/sessions/',
            data=json.dumps({
                'resume_data_id': str(self.resume_data.id),
                'interviewer_name': '李面试官',
                'job_config': {
                    'title': '高级Python开发工程师',
                    'requirements': ['5年Python经验']
                }
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('session_id', data['data'])
        self.assertEqual(data['data']['candidate_name'], '张三')
    
    def test_create_session_missing_resume_id(self):
        """测试缺少resume_data_id参数"""
        response = self.client.post(
            f'{self.base_url}/sessions/',
            data=json.dumps({
                'interviewer_name': '李面试官'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('resume_data_id', data['message'])
    
    def test_create_session_invalid_resume_id(self):
        """测试无效的resume_data_id"""
        response = self.client.post(
            f'{self.base_url}/sessions/',
            data=json.dumps({
                'resume_data_id': str(uuid.uuid4()),  # 不存在的ID
                'interviewer_name': '李面试官'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_create_session_invalid_json(self):
        """测试无效JSON格式"""
        response = self.client.post(
            f'{self.base_url}/sessions/',
            data='invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_get_session_detail(self):
        """测试获取会话详情"""
        # 先创建会话
        session = InterviewAssistSession.objects.create(
            resume_data=self.resume_data,
            interviewer_name='李面试官',
            job_config={'title': '高级Python开发工程师'},
            status='active'
        )
        
        response = self.client.get(f'{self.base_url}/sessions/{session.id}/')
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['data']['session_id'], str(session.id))
        self.assertEqual(data['data']['candidate_name'], '张三')
    
    def test_get_session_not_found(self):
        """测试获取不存在的会话"""
        fake_id = uuid.uuid4()
        response = self.client.get(f'{self.base_url}/sessions/{fake_id}/')
        
        self.assertEqual(response.status_code, 404)
    
    def test_delete_session(self):
        """测试结束会话"""
        session = InterviewAssistSession.objects.create(
            resume_data=self.resume_data,
            interviewer_name='李面试官',
            job_config={'title': '高级Python开发工程师'},
            status='active'
        )
        
        response = self.client.delete(f'{self.base_url}/sessions/{session.id}/')
        
        self.assertEqual(response.status_code, 200)
        
        # 验证状态已变更
        session.refresh_from_db()
        self.assertEqual(session.status, 'completed')


class GenerateQuestionsViewTests(InterviewAssistTestCase):
    """问题生成API测试"""
    
    def setUp(self):
        super().setUp()
        self.session = InterviewAssistSession.objects.create(
            resume_data=self.resume_data,
            interviewer_name='李面试官',
            job_config={'title': '高级Python开发工程师'},
            status='active'
        )
    
    def test_generate_questions_success(self):
        """测试成功生成问题"""
        response = self.client.post(
            f'{self.base_url}/sessions/{self.session.id}/generate-questions/',
            data=json.dumps({
                'categories': ['简历相关', '专业能力'],
                'candidate_level': 'senior',
                'count_per_category': 2
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('question_pool', data['data'])
    
    def test_generate_questions_empty_body(self):
        """测试空请求体生成问题（使用默认参数）"""
        response = self.client.post(
            f'{self.base_url}/sessions/{self.session.id}/generate-questions/',
            data='',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
    
    def test_generate_questions_session_completed(self):
        """测试已结束会话不能生成问题"""
        self.session.status = 'completed'
        self.session.save()
        
        response = self.client.post(
            f'{self.base_url}/sessions/{self.session.id}/generate-questions/',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_generate_questions_session_not_found(self):
        """测试会话不存在"""
        fake_id = uuid.uuid4()
        response = self.client.post(
            f'{self.base_url}/sessions/{fake_id}/generate-questions/',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)


class RecordQAViewTests(InterviewAssistTestCase):
    """记录问答API测试"""
    
    def setUp(self):
        super().setUp()
        self.session = InterviewAssistSession.objects.create(
            resume_data=self.resume_data,
            interviewer_name='李面试官',
            job_config={'title': '高级Python开发工程师'},
            status='active'
        )
    
    def test_record_qa_success(self):
        """测试成功记录问答"""
        response = self.client.post(
            f'{self.base_url}/sessions/{self.session.id}/record-qa/',
            data=json.dumps({
                'question': {
                    'content': '请介绍一下你最近参与的项目？',
                    'source': 'hr_custom',
                    'category': '项目经验',
                    'expected_skills': ['项目管理', '团队协作'],
                    'difficulty': 5
                },
                'answer': {
                    'content': '我最近参与了一个电商平台的后端重构项目...',
                    'duration_seconds': 120
                }
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('evaluation', data['data'])
        self.assertIn('round_number', data['data'])
        self.assertEqual(data['data']['round_number'], 1)
    
    def test_record_qa_missing_content(self):
        """测试缺少问题或回答内容"""
        response = self.client.post(
            f'{self.base_url}/sessions/{self.session.id}/record-qa/',
            data=json.dumps({
                'question': {'content': '问题内容'},
                'answer': {}  # 缺少content
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_record_qa_session_completed(self):
        """测试已结束会话不能记录问答"""
        self.session.status = 'completed'
        self.session.save()
        
        response = self.client.post(
            f'{self.base_url}/sessions/{self.session.id}/record-qa/',
            data=json.dumps({
                'question': {'content': '问题'},
                'answer': {'content': '回答'}
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
    
    def test_record_multiple_qa(self):
        """测试多轮问答记录"""
        for i in range(3):
            response = self.client.post(
                f'{self.base_url}/sessions/{self.session.id}/record-qa/',
                data=json.dumps({
                    'question': {'content': f'问题{i+1}'},
                    'answer': {'content': f'回答{i+1}'}
                }),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['data']['round_number'], i + 1)
        
        # 验证记录数量
        self.assertEqual(self.session.qa_records.count(), 3)


class GenerateFollowupViewTests(InterviewAssistTestCase):
    """追问建议生成API测试"""
    
    def setUp(self):
        super().setUp()
        self.session = InterviewAssistSession.objects.create(
            resume_data=self.resume_data,
            interviewer_name='李面试官',
            job_config={'title': '高级Python开发工程师'},
            status='active'
        )
    
    def test_generate_followup_success(self):
        """测试成功生成追问建议"""
        response = self.client.post(
            f'{self.base_url}/sessions/{self.session.id}/generate-followup/',
            data=json.dumps({
                'original_question': '请介绍一下你的项目经验',
                'original_answer': '我参与过多个项目...',
                'target_skill': '项目管理',
                'evaluation': {'normalized_score': 60}
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
    
    def test_generate_followup_missing_params(self):
        """测试缺少必要参数"""
        response = self.client.post(
            f'{self.base_url}/sessions/{self.session.id}/generate-followup/',
            data=json.dumps({
                'original_question': '问题'
                # 缺少original_answer
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)


class QAHistoryViewTests(InterviewAssistTestCase):
    """问答历史API测试"""
    
    def setUp(self):
        super().setUp()
        self.session = InterviewAssistSession.objects.create(
            resume_data=self.resume_data,
            interviewer_name='李面试官',
            job_config={'title': '高级Python开发工程师'},
            status='active',
            current_round=2
        )
        
        # 创建问答记录
        for i in range(2):
            InterviewQARecord.objects.create(
                session=self.session,
                round_number=i + 1,
                question=f'问题{i+1}',
                answer=f'回答{i+1}',
                evaluation={'normalized_score': 70 + i * 10}
            )
    
    def test_get_qa_history_success(self):
        """测试成功获取问答历史"""
        response = self.client.get(
            f'{self.base_url}/sessions/{self.session.id}/history/'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['data']['qa_records']), 2)
        self.assertEqual(data['data']['total_rounds'], 2)
        self.assertIn('score_trend', data['data'])
        self.assertIn('overall_stats', data['data'])
    
    def test_get_qa_history_empty(self):
        """测试空问答历史"""
        new_session = InterviewAssistSession.objects.create(
            resume_data=self.resume_data,
            interviewer_name='王面试官',
            job_config={'title': '测试岗位'},
            status='active'
        )
        
        response = self.client.get(
            f'{self.base_url}/sessions/{new_session.id}/history/'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['data']['qa_records']), 0)


class GenerateReportViewTests(InterviewAssistTestCase):
    """报告生成API测试"""
    
    def setUp(self):
        super().setUp()
        self.session = InterviewAssistSession.objects.create(
            resume_data=self.resume_data,
            interviewer_name='李面试官',
            job_config={'title': '高级Python开发工程师'},
            status='active',
            current_round=2
        )
        
        # 创建问答记录
        for i in range(2):
            InterviewQARecord.objects.create(
                session=self.session,
                round_number=i + 1,
                question=f'问题{i+1}',
                answer=f'回答{i+1}',
                evaluation={
                    'normalized_score': 75,
                    'dimension_scores': {'专业能力': 4, '沟通表达': 3}
                }
            )
    
    def test_generate_report_success(self):
        """测试成功生成报告"""
        response = self.client.post(
            f'{self.base_url}/sessions/{self.session.id}/generate-report/',
            data=json.dumps({
                'include_conversation_log': True,
                'hr_notes': '候选人表现积极'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertIn('report', data['data'])
        
        # 验证会话状态已变更为completed
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, 'completed')
    
    def test_generate_report_no_qa_records(self):
        """测试没有问答记录时无法生成报告"""
        new_session = InterviewAssistSession.objects.create(
            resume_data=self.resume_data,
            interviewer_name='王面试官',
            job_config={'title': '测试岗位'},
            status='active'
        )
        
        response = self.client.post(
            f'{self.base_url}/sessions/{new_session.id}/generate-report/',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)


class IntegrationTests(InterviewAssistTestCase):
    """完整流程集成测试"""
    
    def test_full_interview_flow(self):
        """测试完整面试流程"""
        # 1. 创建会话
        response = self.client.post(
            f'{self.base_url}/sessions/',
            data=json.dumps({
                'resume_data_id': str(self.resume_data.id),
                'interviewer_name': '李面试官'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        session_id = response.json()['data']['session_id']
        
        # 2. 生成问题
        response = self.client.post(
            f'{self.base_url}/sessions/{session_id}/generate-questions/',
            data=json.dumps({'count_per_category': 2}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # 3. 记录多轮问答
        for i in range(3):
            response = self.client.post(
                f'{self.base_url}/sessions/{session_id}/record-qa/',
                data=json.dumps({
                    'question': {'content': f'面试问题{i+1}'},
                    'answer': {'content': f'候选人回答{i+1}'}
                }),
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 200)
        
        # 4. 获取问答历史
        response = self.client.get(
            f'{self.base_url}/sessions/{session_id}/history/'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['data']['qa_records']), 3)
        
        # 5. 生成报告
        response = self.client.post(
            f'{self.base_url}/sessions/{session_id}/generate-report/',
            data=json.dumps({'hr_notes': '面试表现良好'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # 6. 验证会话状态
        response = self.client.get(f'{self.base_url}/sessions/{session_id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data']['status'], 'completed')
