"""
API客户端测试脚本
可独立运行，用于测试已启动的后端服务
"""

import requests
import json
import time
from typing import Optional


class APITestClient:
    """API测试客户端"""
    
    def __init__(self, base_url: str = 'http://127.0.0.1:8000'):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def _request(self, method: str, path: str, data: dict = None) -> dict:
        """发送HTTP请求"""
        url = f"{self.base_url}{path}"
        
        try:
            if method == 'GET':
                response = self.session.get(url)
            elif method == 'POST':
                response = self.session.post(url, json=data)
            elif method == 'DELETE':
                response = self.session.delete(url)
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            return {
                'status_code': response.status_code,
                'data': response.json() if response.content else None
            }
        except requests.exceptions.ConnectionError:
            return {'error': '无法连接到服务器，请确保后端服务已启动'}
        except json.JSONDecodeError:
            return {'error': '响应不是有效的JSON格式', 'raw': response.text}


class InterviewAssistAPITests:
    """面试辅助API测试"""
    
    def __init__(self, client: APITestClient):
        self.client = client
        self.base_path = '/interview-assist'
        self.created_sessions = []  # 记录创建的会话ID，用于清理
    
    def test_health_check(self) -> dict:
        """测试服务连接"""
        print("\n[测试] 服务连接检查...")
        result = self.client._request('GET', '/admin/')
        
        if 'error' in result:
            print(f"  ❌ 失败: {result['error']}")
            return {'success': False, 'error': result['error']}
        
        print(f"  ✅ 服务正常运行")
        return {'success': True}
    
    def test_create_session(self, resume_data_id: str, interviewer_name: str = '测试面试官') -> dict:
        """测试创建会话"""
        print(f"\n[测试] 创建面试会话...")
        
        result = self.client._request('POST', f'{self.base_path}/sessions/', {
            'resume_data_id': resume_data_id,
            'interviewer_name': interviewer_name,
            'job_config': {
                'title': '测试岗位',
                'requirements': ['技能1', '技能2']
            }
        })
        
        if result.get('status_code') == 201:
            session_id = result['data']['data']['session_id']
            self.created_sessions.append(session_id)
            print(f"  ✅ 成功创建会话: {session_id}")
            return {'success': True, 'session_id': session_id, 'data': result['data']}
        else:
            print(f"  ❌ 创建失败: {result}")
            return {'success': False, 'result': result}
    
    def test_get_session(self, session_id: str) -> dict:
        """测试获取会话详情"""
        print(f"\n[测试] 获取会话详情: {session_id}...")
        
        result = self.client._request('GET', f'{self.base_path}/sessions/{session_id}/')
        
        if result.get('status_code') == 200:
            print(f"  ✅ 获取成功")
            return {'success': True, 'data': result['data']}
        else:
            print(f"  ❌ 获取失败: {result}")
            return {'success': False, 'result': result}
    
    def test_generate_questions(self, session_id: str) -> dict:
        """测试生成问题"""
        print(f"\n[测试] 生成候选问题...")
        
        result = self.client._request('POST', f'{self.base_path}/sessions/{session_id}/generate-questions/', {
            'categories': ['简历相关', '专业能力', '行为面试'],
            'candidate_level': 'senior',
            'count_per_category': 2
        })
        
        if result.get('status_code') == 200:
            question_count = len(result['data']['data'].get('question_pool', []))
            print(f"  ✅ 生成了 {question_count} 个问题")
            return {'success': True, 'data': result['data']}
        else:
            print(f"  ❌ 生成失败: {result}")
            return {'success': False, 'result': result}
    
    def test_record_qa(self, session_id: str, question: str, answer: str) -> dict:
        """测试记录问答"""
        print(f"\n[测试] 记录问答...")
        
        result = self.client._request('POST', f'{self.base_path}/sessions/{session_id}/record-qa/', {
            'question': {
                'content': question,
                'source': 'hr_custom',
                'category': '测试类别',
                'expected_skills': ['技能1'],
                'difficulty': 5
            },
            'answer': {
                'content': answer,
                'duration_seconds': 60
            }
        })
        
        if result.get('status_code') == 200:
            round_num = result['data']['data'].get('round_number')
            score = result['data']['data'].get('evaluation', {}).get('normalized_score', 'N/A')
            print(f"  ✅ 第{round_num}轮问答已记录，评分: {score}")
            return {'success': True, 'data': result['data']}
        else:
            print(f"  ❌ 记录失败: {result}")
            return {'success': False, 'result': result}
    
    def test_get_qa_history(self, session_id: str) -> dict:
        """测试获取问答历史"""
        print(f"\n[测试] 获取问答历史...")
        
        result = self.client._request('GET', f'{self.base_path}/sessions/{session_id}/history/')
        
        if result.get('status_code') == 200:
            qa_count = len(result['data']['data'].get('qa_records', []))
            print(f"  ✅ 获取成功，共 {qa_count} 条记录")
            return {'success': True, 'data': result['data']}
        else:
            print(f"  ❌ 获取失败: {result}")
            return {'success': False, 'result': result}
    
    def test_generate_followup(self, session_id: str, question: str, answer: str) -> dict:
        """测试生成追问建议"""
        print(f"\n[测试] 生成追问建议...")
        
        result = self.client._request('POST', f'{self.base_path}/sessions/{session_id}/generate-followup/', {
            'original_question': question,
            'original_answer': answer,
            'target_skill': '项目管理',
            'evaluation': {'normalized_score': 65}
        })
        
        if result.get('status_code') == 200:
            print(f"  ✅ 生成成功")
            return {'success': True, 'data': result['data']}
        else:
            print(f"  ❌ 生成失败: {result}")
            return {'success': False, 'result': result}
    
    def test_generate_report(self, session_id: str, hr_notes: str = '') -> dict:
        """测试生成报告"""
        print(f"\n[测试] 生成最终报告...")
        
        result = self.client._request('POST', f'{self.base_path}/sessions/{session_id}/generate-report/', {
            'include_conversation_log': True,
            'hr_notes': hr_notes
        })
        
        if result.get('status_code') == 200:
            print(f"  ✅ 报告生成成功")
            return {'success': True, 'data': result['data']}
        else:
            print(f"  ❌ 生成失败: {result}")
            return {'success': False, 'result': result}
    
    def test_delete_session(self, session_id: str) -> dict:
        """测试结束会话"""
        print(f"\n[测试] 结束会话...")
        
        result = self.client._request('DELETE', f'{self.base_path}/sessions/{session_id}/')
        
        if result.get('status_code') == 200:
            print(f"  ✅ 会话已结束")
            return {'success': True}
        else:
            print(f"  ❌ 结束失败: {result}")
            return {'success': False, 'result': result}


def run_full_flow_test(resume_data_id: str, base_url: str = 'http://127.0.0.1:8000'):
    """运行完整流程测试"""
    print("=" * 60)
    print("面试辅助API完整流程测试")
    print("=" * 60)
    
    client = APITestClient(base_url)
    tests = InterviewAssistAPITests(client)
    
    # 1. 健康检查
    health = tests.test_health_check()
    if not health.get('success'):
        print("\n❌ 服务未启动，测试终止")
        return
    
    # 2. 创建会话
    session_result = tests.test_create_session(resume_data_id, '测试面试官')
    if not session_result.get('success'):
        print("\n❌ 创建会话失败，测试终止")
        return
    
    session_id = session_result['session_id']
    
    # 3. 获取会话详情
    tests.test_get_session(session_id)
    
    # 4. 生成问题
    tests.test_generate_questions(session_id)
    
    # 5. 记录多轮问答
    qa_pairs = [
        ('请介绍一下你最近参与的项目', '我最近参与了一个电商平台的后端开发，负责订单系统的设计和实现...'),
        ('你是如何解决高并发问题的', '我们采用了消息队列、缓存和数据库分库分表等方案...'),
        ('团队协作中遇到的最大挑战是什么', '曾经遇到过需求变更频繁的情况，我们通过敏捷开发和持续沟通来解决...')
    ]
    
    for q, a in qa_pairs:
        tests.test_record_qa(session_id, q, a)
        time.sleep(0.5)  # 避免请求过快
    
    # 6. 获取问答历史
    tests.test_get_qa_history(session_id)
    
    # 7. 生成追问建议
    tests.test_generate_followup(session_id, qa_pairs[0][0], qa_pairs[0][1])
    
    # 8. 生成报告
    tests.test_generate_report(session_id, '候选人整体表现良好，技术能力扎实')
    
    # 9. 最终验证会话状态
    tests.test_get_session(session_id)
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


def run_error_handling_tests(base_url: str = 'http://127.0.0.1:8000'):
    """运行错误处理测试"""
    print("=" * 60)
    print("错误处理测试")
    print("=" * 60)
    
    client = APITestClient(base_url)
    tests = InterviewAssistAPITests(client)
    
    import uuid
    fake_session_id = str(uuid.uuid4())
    fake_resume_id = str(uuid.uuid4())
    
    print("\n[测试] 访问不存在的会话...")
    result = tests.test_get_session(fake_session_id)
    expected = result.get('result', {}).get('status_code') == 404
    print(f"  {'✅ 正确返回404' if expected else '❌ 未正确处理'}")
    
    print("\n[测试] 使用不存在的简历ID创建会话...")
    result = tests.test_create_session(fake_resume_id)
    expected = result.get('result', {}).get('status_code') == 404
    print(f"  {'✅ 正确返回404' if expected else '❌ 未正确处理'}")
    
    print("\n" + "=" * 60)
    print("错误处理测试完成")
    print("=" * 60)


if __name__ == '__main__':
    import sys
    
    print("""
使用方法:
  python test_api_client.py <resume_data_id>        # 运行完整流程测试
  python test_api_client.py --errors                # 运行错误处理测试
  python test_api_client.py --help                  # 显示帮助

示例:
  python test_api_client.py 12345678-1234-1234-1234-123456789012
    """)
    
    if len(sys.argv) < 2:
        print("请提供resume_data_id参数或使用 --errors 运行错误测试")
        sys.exit(1)
    
    if sys.argv[1] == '--errors':
        run_error_handling_tests()
    elif sys.argv[1] == '--help':
        pass  # 已显示帮助
    else:
        resume_data_id = sys.argv[1]
        run_full_flow_test(resume_data_id)
