"""
面试辅助核心服务
迁移自HRM1的InterviewerAgent，适配人在回路模式
"""

import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .prompts import InterviewPrompts

logger = logging.getLogger(__name__)


@dataclass
class QuestionSuggestion:
    """问题建议数据类"""
    id: str
    question: str
    category: str
    difficulty: int
    expected_skills: List[str]
    source: str  # resume_based, skill_based
    interest_point: Optional[Dict] = None


class InterviewAssistant:
    """
    面试辅助服务类
    提供问题生成、回答评估、追问建议等核心功能
    """
    
    def __init__(self, llm_client=None, job_config: Dict = None, company_config: Dict = None):
        """
        初始化面试辅助服务
        
        Args:
            llm_client: LLM客户端实例（需要实现chat_with_json_response方法）
            job_config: 岗位配置
            company_config: 公司配置
        """
        self.llm_client = llm_client
        self.job_config = job_config or {}
        self.company_config = company_config or {}
        self.prompts = InterviewPrompts()
    
    def generate_resume_based_questions(
        self, 
        resume_content: str,
        count: int = 3
    ) -> Dict[str, Any]:
        """
        基于简历生成针对性问题（保留HRM1的核心亮点功能）
        
        Args:
            resume_content: 简历内容
            count: 生成问题数量
            
        Returns:
            包含interest_points和questions的字典
        """
        logger.info("正在基于简历生成针对性问题...")
        
        # 构建系统提示词
        system_prompt = self._build_system_prompt()
        
        # 构建用户消息
        user_message = InterviewPrompts.RESUME_BASED_QUESTION_PROMPT.format(
            resume_content=resume_content,
            job_title=self.job_config.get("title", ""),
            job_description=self.job_config.get("description", ""),
            job_requirements=json.dumps(
                self.job_config.get("requirements", {}), 
                ensure_ascii=False, 
                indent=2
            )
        )
        
        try:
            if self.llm_client:
                result = self.llm_client.chat_with_json_response(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.7
                )
            else:
                # 无LLM时返回模拟数据
                result = self._get_mock_resume_questions(resume_content)
            
            # 处理结果
            interest_points = result.get("interest_points", [])
            questions = result.get("questions", [])[:count]
            
            logger.info(f"识别到 {len(interest_points)} 个兴趣点，生成 {len(questions)} 个问题")
            
            return {
                "interest_points": interest_points,
                "questions": questions
            }
            
        except Exception as e:
            logger.error(f"基于简历生成问题失败: {e}")
            return {"interest_points": [], "questions": []}
    
    def generate_skill_based_questions(
        self,
        category: str,
        candidate_level: str = "senior",
        count: int = 2
    ) -> List[Dict]:
        """
        基于技能要求生成问题
        
        Args:
            category: 问题类别
            candidate_level: 候选人级别
            count: 问题数量
            
        Returns:
            问题列表
        """
        logger.info(f"正在生成{category}类问题...")
        
        system_prompt = self._build_system_prompt()
        
        required_skills = self.job_config.get("requirements", {}).get("required_skills", [])
        
        user_message = InterviewPrompts.SKILL_BASED_QUESTION_PROMPT.format(
            job_title=self.job_config.get("title", ""),
            candidate_level=candidate_level,
            question_category=category,
            required_skills=", ".join(required_skills)
        )
        
        try:
            if self.llm_client:
                result = self.llm_client.chat_with_json_response(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.7
                )
                questions = result.get("questions", [])[:count]
            else:
                questions = self._get_mock_skill_questions(category, count)
            
            return questions
            
        except Exception as e:
            logger.error(f"生成技能问题失败: {e}")
            return []
    
    def evaluate_answer(
        self,
        question: str,
        answer: str,
        target_skills: List[str] = None,
        difficulty: int = 5
    ) -> Dict[str, Any]:
        """
        评估候选人回答（保留HRM1的多维度评分+浅层检测）
        
        Args:
            question: 问题内容
            answer: 候选人回答
            target_skills: 目标技能
            difficulty: 问题难度
            
        Returns:
            评估结果
        """
        logger.info("正在评估候选人回答...")
        
        if target_skills is None:
            target_skills = []
        
        # 先进行浅层回答检测
        shallow_detection = self.detect_shallow_answer(answer, target_skills)
        
        system_prompt = self._build_system_prompt()
        
        user_message = InterviewPrompts.ANSWER_EVALUATION_PROMPT.format(
            question=question,
            answer=answer,
            target_skills=", ".join(target_skills) if target_skills else "综合能力",
            difficulty=difficulty
        )
        
        try:
            if self.llm_client:
                evaluation = self.llm_client.chat_with_json_response(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.3
                )
            else:
                evaluation = self._get_mock_evaluation(answer, shallow_detection)
            
            # 合并浅层检测结果
            if "shallow_answer_signals" not in evaluation:
                evaluation["shallow_answer_signals"] = shallow_detection.get("signals", [])
            
            # 确保有标准化分数
            if "normalized_score" not in evaluation:
                dimension_scores = evaluation.get("dimension_scores", {})
                evaluation["normalized_score"] = self._calculate_normalized_score(dimension_scores)
            
            # 生成分数解释
            evaluation["score_interpretation"] = self._get_score_interpretation(
                evaluation["normalized_score"]
            )
            
            logger.info(f"评估完成: {evaluation['normalized_score']:.1f}/100")
            
            return evaluation
            
        except Exception as e:
            logger.error(f"评估失败: {e}")
            return self._get_default_evaluation()
    
    def detect_shallow_answer(
        self, 
        answer: str, 
        target_skills: List[str]
    ) -> Dict[str, Any]:
        """
        检测回答是否浮于表面（迁移自HRM1的detect_shallow_answer）
        
        Args:
            answer: 候选人回答
            target_skills: 目标技能
            
        Returns:
            检测结果
        """
        signals = []
        suspicion_score = 0
        
        # 从prompts获取词汇表
        high_level_terms = InterviewPrompts.HIGH_LEVEL_TERMS
        vague_words = InterviewPrompts.VAGUE_WORDS
        weakness_indicators = InterviewPrompts.WEAKNESS_INDICATORS
        empty_phrases = InterviewPrompts.EMPTY_PHRASES
        concrete_evidence = InterviewPrompts.CONCRETE_EVIDENCE
        technical_metrics = InterviewPrompts.TECHNICAL_METRICS
        
        answer_lower = answer.lower()
        answer_length = len(answer)
        
        # 信号1：使用高级术语
        has_high_level_term = any(term in answer_lower for term in high_level_terms)
        high_level_count = sum(1 for term in high_level_terms if term in answer_lower)
        
        # 信号2：模糊词汇数量
        vague_count = sum(1 for word in vague_words if word in answer)
        
        # 信号3：露怯关键词
        has_weakness = any(phrase in answer for phrase in weakness_indicators)
        
        # 信号4：具体性检测
        has_numbers = any(char.isdigit() for char in answer)
        has_example = any(word in answer for word in concrete_evidence)
        has_metrics = any(word in answer_lower for word in technical_metrics)
        
        # 信号5：空话套话
        empty_count = sum(1 for phrase in empty_phrases if phrase in answer)
        
        # === 综合判断 ===
        
        # 1. 高级术语但缺乏深度
        if has_high_level_term and answer_length < 200:
            if not has_numbers and not has_example:
                signals.append("使用高级术语但缺乏具体细节")
                suspicion_score += 3
        
        # 2. 多个高级术语但回答很短
        if high_level_count >= 3 and answer_length < 150:
            signals.append(f"提到{high_level_count}个技术概念但回答过短")
            suspicion_score += 2
        
        # 3. 模糊词汇过多
        if vague_count >= 3:
            signals.append(f"使用{vague_count}个不确定词汇")
            suspicion_score += 2
        elif vague_count >= 2 and answer_length < 150:
            signals.append(f"回答短且使用{vague_count}个模糊词")
            suspicion_score += 1
        
        # 4. 回答过短
        if answer_length < 60:
            signals.append(f"回答过短（仅{answer_length}字）")
            suspicion_score += 3
        elif answer_length < 100:
            signals.append(f"回答较短（{answer_length}字）")
            suspicion_score += 1
        
        # 5. 提到技术但无具体数据
        if has_high_level_term and not has_numbers and not has_metrics:
            signals.append("提到技术概念但缺少量化指标")
            suspicion_score += 2
        
        # 6. 缺乏具体示例
        if has_high_level_term and not has_example and answer_length < 150:
            signals.append("缺乏具体示例或案例说明")
            suspicion_score += 2
        
        # 7. 明确承认不熟悉
        if has_weakness:
            signals.append("承认对该领域不够熟悉")
            suspicion_score += 2
        
        # 8. 空话套话多
        if empty_count >= 3:
            signals.append("包含较多空话套话")
            suspicion_score += 1
        
        # 判断是否可疑
        is_suspicious = suspicion_score >= 3
        
        # 确定建议追问的技能
        followup_skill = None
        if is_suspicious and target_skills:
            for skill in target_skills:
                if skill.lower() in answer_lower:
                    followup_skill = skill
                    break
            if not followup_skill:
                followup_skill = target_skills[0] if target_skills else None
        
        result = {
            "is_suspicious": is_suspicious,
            "signals": signals,
            "suspicion_score": suspicion_score,
            "followup_skill": followup_skill,
            "answer_length": answer_length,
            "has_concrete_evidence": has_example or has_numbers,
            "has_weakness_indicator": has_weakness
        }
        
        if is_suspicious:
            logger.warning(f"检测到可疑回答 (可疑度{suspicion_score}): {', '.join(signals)}")
        
        return result
    
    def generate_followup_suggestions(
        self,
        original_question: str,
        answer: str,
        evaluation: Dict,
        target_skill: str = None
    ) -> Dict[str, Any]:
        """
        生成追问建议（保留HRM1的智能追问逻辑）
        
        Args:
            original_question: 原始问题
            answer: 候选人回答
            evaluation: 评估结果
            target_skill: 目标技能
            
        Returns:
            追问建议
        """
        logger.info("正在生成追问建议...")
        
        system_prompt = self._build_system_prompt()
        
        # 准备评估反馈
        eval_feedback = f"评分: {evaluation.get('normalized_score', 0):.1f}/100\n"
        eval_feedback += f"信心水平: {evaluation.get('confidence_level', 'unknown')}\n"
        eval_feedback += f"反馈: {evaluation.get('feedback', '')}"
        
        shallow_signals = evaluation.get("shallow_answer_signals", [])
        
        user_message = InterviewPrompts.FOLLOWUP_GENERATION_PROMPT.format(
            original_question=original_question,
            answer=answer,
            evaluation_feedback=eval_feedback,
            target_skill=target_skill or "技术细节",
            shallow_signals=", ".join(shallow_signals) if shallow_signals else "无明显信号"
        )
        
        try:
            if self.llm_client:
                result = self.llm_client.chat_with_json_response(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.7
                )
            else:
                result = self._get_mock_followup_suggestions(target_skill, shallow_signals)
            
            return result
            
        except Exception as e:
            logger.error(f"生成追问建议失败: {e}")
            return {"followup_suggestions": [], "hr_hint": "生成追问建议时出错"}
    
    def generate_final_report(
        self,
        candidate_name: str,
        interviewer_name: str,
        qa_records: List[Dict],
        hr_notes: str = ""
    ) -> Dict[str, Any]:
        """
        生成最终评估报告
        
        Args:
            candidate_name: 候选人姓名
            interviewer_name: 面试官姓名
            qa_records: 问答记录列表
            hr_notes: HR备注
            
        Returns:
            评估报告
        """
        logger.info("正在生成最终评估报告...")
        
        # 格式化对话记录
        conversation_log = self._format_conversation_log(qa_records)
        
        # 计算统计数据
        total_rounds = len(qa_records)
        scores = [r.get("evaluation", {}).get("normalized_score", 50) for r in qa_records if r.get("evaluation")]
        avg_score = sum(scores) / len(scores) if scores else 50
        followup_count = sum(1 for r in qa_records if r.get("was_followed_up", False))
        
        system_prompt = self._build_system_prompt()
        
        user_message = InterviewPrompts.FINAL_REPORT_PROMPT.format(
            candidate_name=candidate_name,
            job_title=self.job_config.get("title", ""),
            interviewer_name=interviewer_name,
            job_requirements=json.dumps(
                self.job_config.get("requirements", {}), 
                ensure_ascii=False
            ),
            conversation_log=conversation_log,
            total_rounds=total_rounds,
            avg_score=f"{avg_score:.1f}",
            followup_count=followup_count,
            hr_notes=hr_notes or "无"
        )
        
        try:
            if self.llm_client:
                report = self.llm_client.chat_with_json_response(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=0.3
                )
            else:
                report = self._get_mock_report(candidate_name, avg_score)
            
            logger.info("最终报告生成成功")
            return report
            
        except Exception as e:
            logger.error(f"报告生成失败: {e}")
            return {
                "overall_assessment": {
                    "recommendation_score": int(avg_score),
                    "recommendation": "待定",
                    "summary": "报告生成失败，请查看原始问答记录"
                }
            }
    
    # ============ 辅助方法 ============
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        company_info = f"""
公司名称: {self.company_config.get('name', '未指定')}
行业: {self.company_config.get('industry', '未指定')}
公司规模: {self.company_config.get('size', '未指定')}
"""
        
        job_requirements = f"""
职位名称: {self.job_config.get('title', '未指定')}
职位描述: {self.job_config.get('description', '未指定')}
核心要求: {json.dumps(self.job_config.get('requirements', {}), ensure_ascii=False)}
"""
        
        return InterviewPrompts.ASSISTANT_SYSTEM_PROMPT.format(
            job_title=self.job_config.get('title', '未指定职位'),
            company_info=company_info,
            job_requirements=job_requirements
        )
    
    def _calculate_normalized_score(self, dimension_scores: Dict) -> float:
        """计算标准化分数（0-100）"""
        if not dimension_scores:
            return 50.0
        
        # 维度权重
        weights = {
            "technical_depth": 0.25,
            "practical_experience": 0.25,
            "answer_specificity": 0.15,
            "logical_clarity": 0.15,
            "honesty": 0.10,
            "communication": 0.10
        }
        
        total_score = 0
        total_weight = 0
        
        for dim, weight in weights.items():
            if dim in dimension_scores:
                # 1-4分转换为0-100分
                score = (dimension_scores[dim] - 1) / 3 * 100
                total_score += score * weight
                total_weight += weight
        
        if total_weight > 0:
            return total_score / total_weight
        return 50.0
    
    def _get_score_interpretation(self, score: float) -> Dict:
        """获取分数解释"""
        if score >= 85:
            return {"level": "优秀", "recommendation": "强烈推荐"}
        elif score >= 70:
            return {"level": "良好", "recommendation": "推荐"}
        elif score >= 55:
            return {"level": "中等", "recommendation": "待定/需进一步验证"}
        elif score >= 40:
            return {"level": "较弱", "recommendation": "谨慎考虑"}
        else:
            return {"level": "不足", "recommendation": "不推荐"}
    
    def _format_conversation_log(self, qa_records: List[Dict]) -> str:
        """格式化对话记录"""
        formatted = []
        for record in qa_records:
            round_num = record.get("round_number", 0)
            question = record.get("question", "")
            answer = record.get("answer", "")
            evaluation = record.get("evaluation", {})
            
            formatted.append(f"\n【第{round_num}轮】")
            formatted.append(f"问题: {question}")
            formatted.append(f"回答: {answer}")
            
            if evaluation:
                score = evaluation.get("normalized_score", 0)
                feedback = evaluation.get("feedback", "")
                formatted.append(f"评分: {score:.1f}/100")
                formatted.append(f"反馈: {feedback}")
        
        return "\n".join(formatted)
    
    def _get_default_evaluation(self) -> Dict:
        """获取默认评估结果"""
        return {
            "dimension_scores": {
                "technical_depth": 2,
                "practical_experience": 2,
                "answer_specificity": 2,
                "logical_clarity": 2,
                "honesty": 3,
                "communication": 2
            },
            "normalized_score": 50.0,
            "score_interpretation": {"level": "中等", "recommendation": "待定"},
            "feedback": "评估失败，使用默认分数",
            "confidence_level": "uncertain",
            "shallow_answer_signals": [],
            "should_followup": False,
            "followup_reason": "",
            "followup_direction": ""
        }
    
    # ============ Mock数据方法（无LLM时使用）============
    
    def _get_mock_resume_questions(self, resume_content: str) -> Dict:
        """模拟基于简历的问题生成"""
        return {
            "interest_points": [
                {
                    "point": "项目经验描述",
                    "reason": "简历中提到的项目经验需要验证",
                    "skills_involved": ["项目管理", "技术实现"],
                    "risk_level": "medium"
                }
            ],
            "questions": [
                {
                    "id": "q1",
                    "question": "请详细介绍一下您简历中提到的核心项目经验",
                    "target": "项目经验",
                    "category": "简历相关",
                    "difficulty": 6,
                    "expected_skills": ["项目经验"],
                    "source": "resume_based",
                    "interest_point_ref": "项目经验描述"
                }
            ]
        }
    
    def _get_mock_skill_questions(self, category: str, count: int) -> List[Dict]:
        """模拟技能问题生成"""
        return [
            {
                "id": f"sq{i+1}",
                "question": f"请介绍一下您在{category}方面的经验",
                "category": category,
                "difficulty": 5,
                "expected_skills": [category],
                "source": "skill_based"
            }
            for i in range(count)
        ]
    
    def _get_mock_evaluation(self, answer: str, shallow_detection: Dict) -> Dict:
        """模拟评估结果"""
        # 基于浅层检测调整分数
        base_score = 60
        if shallow_detection.get("is_suspicious"):
            base_score -= shallow_detection.get("suspicion_score", 0) * 3
        if shallow_detection.get("has_concrete_evidence"):
            base_score += 10
        
        base_score = max(20, min(90, base_score))
        
        return {
            "dimension_scores": {
                "technical_depth": 2,
                "practical_experience": 2,
                "answer_specificity": 2 if not shallow_detection.get("has_concrete_evidence") else 3,
                "logical_clarity": 3,
                "honesty": 3,
                "communication": 3
            },
            "normalized_score": float(base_score),
            "feedback": "这是模拟评估结果，请配置LLM客户端以获得真实评估",
            "confidence_level": "uncertain" if shallow_detection.get("is_suspicious") else "genuine",
            "shallow_answer_signals": shallow_detection.get("signals", []),
            "should_followup": shallow_detection.get("is_suspicious", False),
            "followup_reason": "检测到回答可能浮于表面" if shallow_detection.get("is_suspicious") else "",
            "followup_direction": f"建议追问 {shallow_detection.get('followup_skill', '具体细节')}"
        }
    
    def _get_mock_followup_suggestions(self, target_skill: str, signals: List[str]) -> Dict:
        """模拟追问建议"""
        return {
            "followup_suggestions": [
                {
                    "id": "fq1",
                    "question": f"能否具体说说您在{target_skill or '这方面'}的实际项目经验？",
                    "strategy": "要求具体化",
                    "target_skill": target_skill or "综合能力",
                    "difficulty": 7,
                    "expected_outcome": "验证候选人的实际操作经验"
                }
            ],
            "hr_hint": "建议追问具体细节，观察候选人能否给出实际案例"
        }
    
    def _get_mock_report(self, candidate_name: str, avg_score: float) -> Dict:
        """模拟最终报告"""
        recommendation = "推荐" if avg_score >= 70 else "待定" if avg_score >= 55 else "不推荐"
        
        return {
            "overall_assessment": {
                "recommendation_score": int(avg_score),
                "recommendation": recommendation,
                "summary": f"这是{candidate_name}的模拟评估报告，请配置LLM以获得真实评估"
            },
            "dimension_analysis": {
                "technical_depth": {"score": int(avg_score), "comment": "模拟评估"},
                "practical_experience": {"score": int(avg_score), "comment": "模拟评估"},
                "answer_specificity": {"score": int(avg_score), "comment": "模拟评估"},
                "logical_clarity": {"score": int(avg_score), "comment": "模拟评估"},
                "honesty": {"score": int(avg_score), "comment": "模拟评估"},
                "communication": {"score": int(avg_score), "comment": "模拟评估"}
            },
            "skill_assessment": [],
            "red_flags": [],
            "highlights": [],
            "suggested_next_steps": ["配置LLM客户端以获得详细评估"],
            "detailed_feedback": "模拟报告，仅供参考"
        }
