"""
面试辅助API视图
人在回路的面试官AI助手
"""

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.core.files.base import ContentFile

import json
import logging
import uuid
from datetime import datetime

from .models import InterviewAssistSession, InterviewQARecord
from .services.interview_assistant import InterviewAssistant
from resume_screening.models import ResumeData

logger = logging.getLogger(__name__)


# ============ 会话管理 ============

@method_decorator(csrf_exempt, name='dispatch')
class SessionView(View):
    """面试辅助会话视图"""
    
    def post(self, request):
        """创建面试辅助会话"""
        try:
            data = json.loads(request.body)
            
            resume_data_id = data.get('resume_data_id')
            interviewer_name = data.get('interviewer_name', '面试官')
            job_config = data.get('job_config', {})
            company_config = data.get('company_config', {})
            
            if not resume_data_id:
                return JsonResponse({
                    'status': 'error',
                    'message': '缺少必要参数: resume_data_id'
                }, status=400)
            
            # 获取简历数据
            try:
                resume_data = ResumeData.objects.get(id=resume_data_id)
            except ResumeData.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': f'简历数据不存在: {resume_data_id}'
                }, status=404)
            
            # 如果没有提供岗位配置，从简历数据中获取
            if not job_config:
                job_config = {
                    'title': resume_data.position_title,
                    'description': '',
                    'requirements': resume_data.position_details or {}
                }
            
            # 创建会话
            session = InterviewAssistSession.objects.create(
                resume_data=resume_data,
                interviewer_name=interviewer_name,
                job_config=job_config,
                company_config=company_config,
                status='active'
            )
            
            # 构建简历摘要
            resume_summary = self._extract_resume_summary(resume_data)
            
            return JsonResponse({
                'status': 'success',
                'message': '面试辅助会话已创建',
                'data': {
                    'session_id': str(session.id),
                    'candidate_name': resume_data.candidate_name,
                    'position_title': job_config.get('title', resume_data.position_title),
                    'status': session.status,
                    'created_at': session.created_at.isoformat(),
                    'resume_summary': resume_summary
                }
            }, status=201)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': '请求数据格式错误，应为有效的JSON格式'
            }, status=400)
        except Exception as e:
            logger.error(f"创建面试会话时出错: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'创建会话失败: {str(e)}'
            }, status=500)
    
    def get(self, request, session_id=None):
        """获取会话详情"""
        if not session_id:
            return JsonResponse({
                'status': 'error',
                'message': '缺少会话ID'
            }, status=400)
        
        try:
            session = InterviewAssistSession.objects.get(id=session_id)
            
            # 获取问答记录数量
            qa_count = session.qa_records.count()
            
            response_data = {
                'session_id': str(session.id),
                'candidate_name': session.resume_data.candidate_name,
                'position_title': session.job_config.get('title', ''),
                'interviewer_name': session.interviewer_name,
                'status': session.status,
                'current_round': session.current_round,
                'qa_count': qa_count,
                'question_pool_count': len(session.question_pool),
                'resume_highlights': session.resume_highlights,
                'created_at': session.created_at.isoformat(),
                'updated_at': session.updated_at.isoformat()
            }
            
            if session.status == 'completed' and session.final_report:
                response_data['has_final_report'] = True
                response_data['final_report_summary'] = session.final_report.get(
                    'overall_assessment', {}
                ).get('summary', '')
            
            return JsonResponse({
                'status': 'success',
                'data': response_data
            })
            
        except InterviewAssistSession.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': '会话不存在'
            }, status=404)
        except Exception as e:
            logger.error(f"获取会话详情时出错: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'获取会话详情失败: {str(e)}'
            }, status=500)
    
    def delete(self, request, session_id=None):
        """结束/删除会话"""
        if not session_id:
            return JsonResponse({
                'status': 'error',
                'message': '缺少会话ID'
            }, status=400)
        
        try:
            session = InterviewAssistSession.objects.get(id=session_id)
            
            # 标记为已完成而非删除
            session.status = 'completed'
            session.save()
            
            return JsonResponse({
                'status': 'success',
                'message': '会话已结束'
            })
            
        except InterviewAssistSession.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': '会话不存在'
            }, status=404)
    
    def _extract_resume_summary(self, resume_data: ResumeData) -> dict:
        """提取简历摘要"""
        summary = {
            'candidate_name': resume_data.candidate_name,
            'position_title': resume_data.position_title,
        }
        
        # 从筛选报告中提取信息
        if resume_data.screening_score:
            summary['screening_score'] = resume_data.screening_score
        
        if resume_data.screening_summary:
            summary['screening_summary'] = resume_data.screening_summary[:200]
        
        return summary


# ============ 问题生成 ============

@method_decorator(csrf_exempt, name='dispatch')
class GenerateQuestionsView(View):
    """生成候选问题视图"""
    
    def post(self, request, session_id):
        """生成候选问题"""
        try:
            session = InterviewAssistSession.objects.get(id=session_id)
            
            if session.status != 'active':
                return JsonResponse({
                    'status': 'error',
                    'message': '会话已结束，无法生成问题'
                }, status=400)
            
            data = json.loads(request.body) if request.body else {}
            
            categories = data.get('categories', ['简历相关', '专业能力', '行为面试'])
            candidate_level = data.get('candidate_level', 'senior')
            count_per_category = data.get('count_per_category', 2)
            focus_on_resume = data.get('focus_on_resume', True)
            
            # 初始化面试助手
            assistant = InterviewAssistant(
                llm_client=self._get_llm_client(),
                job_config=session.job_config,
                company_config=session.company_config
            )
            
            all_questions = []
            interest_points = []
            
            # 1. 基于简历生成问题
            if focus_on_resume and session.resume_data.resume_content:
                resume_result = assistant.generate_resume_based_questions(
                    resume_content=session.resume_data.resume_content,
                    count=count_per_category
                )
                all_questions.extend(resume_result.get('questions', []))
                interest_points = resume_result.get('interest_points', [])
            
            # 2. 基于技能分类生成问题
            for category in categories:
                if category != '简历相关':
                    skill_questions = assistant.generate_skill_based_questions(
                        category=category,
                        candidate_level=candidate_level,
                        count=count_per_category
                    )
                    all_questions.extend(skill_questions)
            
            # 保存到会话
            session.question_pool = all_questions
            session.resume_highlights = interest_points
            session.save()
            
            return JsonResponse({
                'status': 'success',
                'message': f'已生成{len(all_questions)}个候选问题',
                'data': {
                    'session_id': str(session.id),
                    'question_pool': all_questions,
                    'resume_highlights': interest_points
                }
            })
            
        except InterviewAssistSession.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': '会话不存在'
            }, status=404)
        except Exception as e:
            logger.error(f"生成问题时出错: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'生成问题失败: {str(e)}'
            }, status=500)
    
    def _get_llm_client(self):
        """获取LLM客户端（可扩展）"""
        # TODO: 从配置中获取LLM客户端
        # 当前返回None，使用mock数据
        return None


# ============ 记录问答并评估 ============

@method_decorator(csrf_exempt, name='dispatch')
class RecordQAView(View):
    """记录问答并评估视图"""
    
    def post(self, request, session_id):
        """记录问答并获取评估"""
        try:
            session = InterviewAssistSession.objects.get(id=session_id)
            
            if session.status != 'active':
                return JsonResponse({
                    'status': 'error',
                    'message': '会话已结束'
                }, status=400)
            
            data = json.loads(request.body)
            
            question_data = data.get('question', {})
            answer_data = data.get('answer', {})
            
            if not question_data.get('content') or not answer_data.get('content'):
                return JsonResponse({
                    'status': 'error',
                    'message': '缺少问题或回答内容'
                }, status=400)
            
            # 更新轮次
            session.current_round += 1
            round_number = session.current_round
            
            # 初始化面试助手
            assistant = InterviewAssistant(
                llm_client=self._get_llm_client(),
                job_config=session.job_config,
                company_config=session.company_config
            )
            
            # 评估回答
            evaluation = assistant.evaluate_answer(
                question=question_data['content'],
                answer=answer_data['content'],
                target_skills=question_data.get('expected_skills', []),
                difficulty=question_data.get('difficulty', 5)
            )
            
            # 生成追问建议
            followup_suggestions = []
            followup_recommendation = {
                'should_followup': evaluation.get('should_followup', False),
                'reason': evaluation.get('followup_reason', ''),
                'suggested_followups': []
            }
            
            if evaluation.get('should_followup'):
                followup_result = assistant.generate_followup_suggestions(
                    original_question=question_data['content'],
                    answer=answer_data['content'],
                    evaluation=evaluation,
                    target_skill=question_data.get('expected_skills', [''])[0] if question_data.get('expected_skills') else None
                )
                followup_suggestions = followup_result.get('followup_suggestions', [])
                followup_recommendation['suggested_followups'] = followup_suggestions
                followup_recommendation['hr_hint'] = followup_result.get('hr_hint', '')
            
            # 创建问答记录
            qa_record = InterviewQARecord.objects.create(
                session=session,
                round_number=round_number,
                question=question_data['content'],
                question_source=question_data.get('source', 'hr_custom'),
                question_category=question_data.get('category', ''),
                expected_skills=question_data.get('expected_skills', []),
                question_difficulty=question_data.get('difficulty', 5),
                related_interest_point=question_data.get('interest_point'),
                answer=answer_data['content'],
                answer_recorded_at=timezone.now(),
                answer_duration_seconds=answer_data.get('duration_seconds'),
                evaluation=evaluation,
                followup_suggestions=followup_suggestions
            )
            
            session.save()
            
            return JsonResponse({
                'status': 'success',
                'message': '问答已记录，评估完成',
                'data': {
                    'round_number': round_number,
                    'qa_record_id': str(qa_record.id),
                    'evaluation': evaluation,
                    'followup_recommendation': followup_recommendation,
                    'hr_action_hints': self._generate_hr_hints(evaluation)
                }
            })
            
        except InterviewAssistSession.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': '会话不存在'
            }, status=404)
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': '请求数据格式错误'
            }, status=400)
        except Exception as e:
            logger.error(f"记录问答时出错: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'记录问答失败: {str(e)}'
            }, status=500)
    
    def _get_llm_client(self):
        """获取LLM客户端"""
        return None
    
    def _generate_hr_hints(self, evaluation: dict) -> list:
        """生成HR操作提示"""
        hints = []
        
        score = evaluation.get('normalized_score', 50)
        confidence = evaluation.get('confidence_level', 'uncertain')
        should_followup = evaluation.get('should_followup', False)
        
        if should_followup:
            hints.append("建议追问具体细节以验证真实能力")
        
        if confidence == 'overconfident':
            hints.append("候选人可能存在夸大，建议深入追问")
        elif confidence == 'uncertain':
            hints.append("候选人表现不够确定，可考虑追问或跳过")
        
        if score < 50:
            hints.append("该回答得分较低，可考虑记录问题点")
        elif score >= 80:
            hints.append("回答质量较好，可继续下一问题")
        
        if not hints:
            hints.append("可选择追问或继续下一问题")
        
        return hints


# ============ 生成追问建议 ============

@method_decorator(csrf_exempt, name='dispatch')
class GenerateFollowupView(View):
    """生成追问建议视图"""
    
    def post(self, request, session_id):
        """生成追问建议"""
        try:
            session = InterviewAssistSession.objects.get(id=session_id)
            
            data = json.loads(request.body)
            
            original_question = data.get('original_question', '')
            original_answer = data.get('original_answer', '')
            target_skill = data.get('target_skill', '')
            evaluation = data.get('evaluation', {})
            
            if not original_question or not original_answer:
                return JsonResponse({
                    'status': 'error',
                    'message': '缺少原始问题或回答'
                }, status=400)
            
            assistant = InterviewAssistant(
                llm_client=self._get_llm_client(),
                job_config=session.job_config,
                company_config=session.company_config
            )
            
            result = assistant.generate_followup_suggestions(
                original_question=original_question,
                answer=original_answer,
                evaluation=evaluation,
                target_skill=target_skill
            )
            
            return JsonResponse({
                'status': 'success',
                'data': result
            })
            
        except InterviewAssistSession.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': '会话不存在'
            }, status=404)
        except Exception as e:
            logger.error(f"生成追问建议时出错: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'生成追问建议失败: {str(e)}'
            }, status=500)
    
    def _get_llm_client(self):
        return None


# ============ 获取问答历史 ============

@method_decorator(csrf_exempt, name='dispatch')
class QAHistoryView(View):
    """问答历史视图"""
    
    def get(self, request, session_id):
        """获取问答历史"""
        try:
            session = InterviewAssistSession.objects.get(id=session_id)
            
            qa_records = session.qa_records.all().order_by('round_number')
            
            records_data = []
            score_trend = []
            
            for record in qa_records:
                record_data = {
                    'round': record.round_number,
                    'question': record.question,
                    'question_source': record.question_source,
                    'question_category': record.question_category,
                    'answer': record.answer,
                    'evaluation': record.evaluation,
                    'followup_suggestions': record.followup_suggestions,
                    'was_followed_up': record.was_followed_up,
                    'created_at': record.created_at.isoformat()
                }
                records_data.append(record_data)
                
                if record.evaluation:
                    score_trend.append(record.evaluation.get('normalized_score', 50))
            
            # 计算统计数据
            overall_stats = self._calculate_stats(qa_records)
            
            return JsonResponse({
                'status': 'success',
                'data': {
                    'session_id': str(session.id),
                    'candidate_name': session.resume_data.candidate_name,
                    'total_rounds': session.current_round,
                    'qa_records': records_data,
                    'score_trend': score_trend,
                    'overall_stats': overall_stats
                }
            })
            
        except InterviewAssistSession.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': '会话不存在'
            }, status=404)
        except Exception as e:
            logger.error(f"获取问答历史时出错: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'获取问答历史失败: {str(e)}'
            }, status=500)
    
    def _calculate_stats(self, qa_records) -> dict:
        """计算统计数据"""
        if not qa_records:
            return {
                'avg_score': 0,
                'followup_count': 0,
                'strong_areas': [],
                'weak_areas': []
            }
        
        scores = []
        dimension_totals = {}
        dimension_counts = {}
        followup_count = 0
        
        for record in qa_records:
            if record.was_followed_up:
                followup_count += 1
            
            if record.evaluation:
                scores.append(record.evaluation.get('normalized_score', 50))
                
                dim_scores = record.evaluation.get('dimension_scores', {})
                for dim, score in dim_scores.items():
                    if dim not in dimension_totals:
                        dimension_totals[dim] = 0
                        dimension_counts[dim] = 0
                    dimension_totals[dim] += score
                    dimension_counts[dim] += 1
        
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # 计算各维度平均分
        dimension_avgs = {}
        for dim in dimension_totals:
            dimension_avgs[dim] = dimension_totals[dim] / dimension_counts[dim]
        
        # 找出强项和弱项
        strong_areas = [dim for dim, avg in dimension_avgs.items() if avg >= 3]
        weak_areas = [dim for dim, avg in dimension_avgs.items() if avg <= 2]
        
        return {
            'avg_score': round(avg_score, 1),
            'followup_count': followup_count,
            'strong_areas': strong_areas,
            'weak_areas': weak_areas,
            'dimension_averages': {k: round(v, 2) for k, v in dimension_avgs.items()}
        }


# ============ 生成最终报告 ============

@method_decorator(csrf_exempt, name='dispatch')
class GenerateReportView(View):
    """生成最终报告视图"""
    
    def post(self, request, session_id):
        """生成最终评估报告"""
        try:
            session = InterviewAssistSession.objects.get(id=session_id)
            
            data = json.loads(request.body) if request.body else {}
            
            include_conversation_log = data.get('include_conversation_log', True)
            hr_notes = data.get('hr_notes', '')
            
            # 获取问答记录
            qa_records = session.qa_records.all().order_by('round_number')
            
            if not qa_records.exists():
                return JsonResponse({
                    'status': 'error',
                    'message': '没有问答记录，无法生成报告'
                }, status=400)
            
            # 准备问答数据
            qa_data = []
            for record in qa_records:
                qa_data.append({
                    'round_number': record.round_number,
                    'question': record.question,
                    'answer': record.answer,
                    'evaluation': record.evaluation,
                    'was_followed_up': record.was_followed_up
                })
            
            # 初始化面试助手
            assistant = InterviewAssistant(
                llm_client=self._get_llm_client(),
                job_config=session.job_config,
                company_config=session.company_config
            )
            
            # 生成报告
            report = assistant.generate_final_report(
                candidate_name=session.resume_data.candidate_name,
                interviewer_name=session.interviewer_name,
                qa_records=qa_data,
                hr_notes=hr_notes
            )
            
            # 保存报告到会话
            session.final_report = report
            session.status = 'completed'
            
            # 生成报告文件
            report_content = self._format_report_as_markdown(
                session, report, qa_data if include_conversation_log else None
            )
            filename = f"面试辅助报告_{session.resume_data.candidate_name}_{session.id}.md"
            session.report_file.save(filename, ContentFile(report_content.encode('utf-8')))
            
            session.save()
            
            return JsonResponse({
                'status': 'success',
                'message': '评估报告生成成功',
                'data': {
                    'report': report,
                    'report_file_url': session.report_file.url if session.report_file else None
                }
            })
            
        except InterviewAssistSession.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': '会话不存在'
            }, status=404)
        except Exception as e:
            logger.error(f"生成报告时出错: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'生成报告失败: {str(e)}'
            }, status=500)
    
    def _get_llm_client(self):
        return None
    
    def _format_report_as_markdown(self, session, report: dict, qa_data: list = None) -> str:
        """将报告格式化为Markdown"""
        lines = []
        
        lines.append("# 面试辅助评估报告\n")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"**候选人**: {session.resume_data.candidate_name}\n")
        lines.append(f"**应聘职位**: {session.job_config.get('title', '')}\n")
        lines.append(f"**面试官**: {session.interviewer_name}\n")
        lines.append("\n---\n")
        
        # 整体评估
        overall = report.get('overall_assessment', {})
        lines.append("## 整体评估\n")
        lines.append(f"- **推荐分数**: {overall.get('recommendation_score', 0)}/100\n")
        lines.append(f"- **推荐结论**: {overall.get('recommendation', '待定')}\n")
        lines.append(f"- **评估总结**: {overall.get('summary', '')}\n")
        lines.append("\n")
        
        # 维度分析
        dimensions = report.get('dimension_analysis', {})
        if dimensions:
            lines.append("## 维度分析\n")
            lines.append("| 维度 | 分数 | 评价 |\n")
            lines.append("|------|------|------|\n")
            for dim, data in dimensions.items():
                lines.append(f"| {dim} | {data.get('score', 0)} | {data.get('comment', '')} |\n")
            lines.append("\n")
        
        # 技能评估
        skills = report.get('skill_assessment', [])
        if skills:
            lines.append("## 技能评估\n")
            for skill in skills:
                lines.append(f"- **{skill.get('skill', '')}**: {skill.get('level', '')} - {skill.get('evidence', '')}\n")
            lines.append("\n")
        
        # 亮点和问题
        highlights = report.get('highlights', [])
        if highlights:
            lines.append("## 亮点\n")
            for h in highlights:
                lines.append(f"- {h}\n")
            lines.append("\n")
        
        red_flags = report.get('red_flags', [])
        if red_flags:
            lines.append("## 需关注的问题\n")
            for r in red_flags:
                lines.append(f"- ⚠️ {r}\n")
            lines.append("\n")
        
        # 建议
        next_steps = report.get('suggested_next_steps', [])
        if next_steps:
            lines.append("## 建议后续步骤\n")
            for step in next_steps:
                lines.append(f"1. {step}\n")
            lines.append("\n")
        
        # 问答记录
        if qa_data:
            lines.append("---\n")
            lines.append("## 问答记录\n")
            for qa in qa_data:
                lines.append(f"\n### 第{qa['round_number']}轮\n")
                lines.append(f"**问题**: {qa['question']}\n\n")
                lines.append(f"**回答**: {qa['answer']}\n\n")
                if qa.get('evaluation'):
                    eval_data = qa['evaluation']
                    lines.append(f"**评分**: {eval_data.get('normalized_score', 0):.1f}/100\n")
                    lines.append(f"**反馈**: {eval_data.get('feedback', '')}\n")
        
        return "".join(lines)
