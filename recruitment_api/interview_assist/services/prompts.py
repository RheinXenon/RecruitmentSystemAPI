"""
面试辅助Prompt模板
迁移自HRM1的interviewer_prompts.py和resume_prompts.py
适配人在回路的辅助模式
"""


class InterviewPrompts:
    """面试辅助Prompt集合"""
    
    # ============ 系统提示词 ============
    
    ASSISTANT_SYSTEM_PROMPT = """你是一位经验丰富的面试辅助AI，正在协助HR面试{job_title}职位的候选人。

# 公司信息
{company_info}

# 职位要求
{job_requirements}

# 你的职责
1. 根据候选人简历和职位要求，提供专业、有针对性的面试问题建议
2. 分析候选人的回答，识别潜在的"不懂装懂"或回答浮于表面的情况
3. 在需要时提供追问建议，帮助HR深入了解候选人的真实能力
4. 最终给出客观的评估报告

# 工作模式
- 你是辅助角色，最终决策由HR做出
- 提供多个候选问题供HR选择
- 给出清晰的评估依据和追问建议
"""

    # ============ 问题生成 ============
    
    RESUME_BASED_QUESTION_PROMPT = """基于以下候选人简历，识别值得深入探讨的兴趣点，并生成面试问题建议。

# 候选人简历
{resume_content}

# 职位要求
职位名称: {job_title}
职位描述: {job_description}
核心要求: {job_requirements}

# 任务

请识别出2-3个**值得深入探讨的兴趣点**，并针对这些点生成面试问题。

兴趣点选择原则：
1. 简历中提到的高级技术或复杂项目（可能存在夸大）
2. 与职位核心要求高度相关的技能描述
3. 看起来很厉害但描述模糊的经历
4. 使用了"精通"、"专家级"等词汇的技能
5. 项目成就中的量化指标（如"性能提升X倍"）

# 输出格式

请以JSON格式输出：

{{
  "interest_points": [
    {{
      "point": "兴趣点描述",
      "reason": "为什么关注这个点",
      "skills_involved": ["相关技能1", "相关技能2"],
      "risk_level": "high/medium/low"
    }}
  ],
  "questions": [
    {{
      "id": "q1",
      "question": "问题内容",
      "target": "针对简历中的哪个部分",
      "category": "简历相关",
      "difficulty": 7,
      "expected_skills": ["相关技能"],
      "source": "resume_based",
      "interest_point_ref": "关联的兴趣点描述"
    }}
  ]
}}
"""

    SKILL_BASED_QUESTION_PROMPT = """基于职位要求生成面试问题。

职位: {job_title}
候选人级别: {candidate_level}
问题类别: {question_category}
核心技能要求: {required_skills}

要求:
1. 生成2-3个该类别的问题
2. 问题难度应匹配候选人级别
3. 问题应该能有效考察相关技能
4. 避免太宽泛或太理论的问题
5. 优先考察实际经验和问题解决能力

请以JSON格式返回：
{{
  "questions": [
    {{
      "id": "sq1",
      "question": "问题内容",
      "category": "{question_category}",
      "difficulty": 5,
      "expected_skills": ["技能"],
      "source": "skill_based"
    }}
  ]
}}
"""

    # ============ 回答评估 ============
    
    ANSWER_EVALUATION_PROMPT = """请评估候选人的回答质量，特别注意识别**过度自信**和**不懂装懂**的信号。

问题: {question}
候选人回答: {answer}
考察技能: {target_skills}
问题难度: {difficulty}

## 评估维度 (每个维度1-4分)

### 1. 技术深度 (technical_depth)
- 1分: 仅知道概念名称,无法解释原理
- 2分: 理解基本原理,但缺乏深度
- 3分: 深入理解原理,能举实例
- 4分: 精通原理,能分析边界情况和trade-offs

### 2. 实践经验 (practical_experience)
- 1分: 无法提供具体项目细节
- 2分: 有项目但细节模糊
- 3分: 提供了具体的项目经验和数据
- 4分: 详细描述了复杂场景和解决方案

### 3. 回答具体性 (answer_specificity)
- 1分: 完全没有具体细节或数据
- 2分: 偶尔提到细节但不完整
- 3分: 包含多个具体参数、配置或代码
- 4分: 充满量化指标、架构图、代码示例

### 4. 逻辑清晰度 (logical_clarity)
- 1分: 混乱无条理
- 2分: 基本有条理
- 3分: 结构清晰
- 4分: 逻辑严密、层次分明

### 5. 诚实度 (honesty)
- 1分: 明显不懂装懂
- 2分: 有夸大倾向
- 3分: 比较诚实
- 4分: 准确认知自己的边界

### 6. 沟通能力 (communication)
- 1分: 表达不清
- 2分: 基本能说清楚
- 3分: 表达清晰
- 4分: 表达精准且有感染力

## 重点关注以下过度自信信号：
- 使用高级专业术语但缺乏具体细节
- 回答模糊、使用大量不确定词汇（"一般"、"差不多"、"应该"、"可能"）
- 主动承认"记不清"、"不太熟"但仍给出笼统回答
- 提到专业概念但没有具体数据、指标或案例示例
- 回答过短（<100字）但谈论复杂话题
- 缺乏对方案权衡的深入思考
- 无法给出实际工作中的具体问题和解决方案

## JSON返回格式

{{
  "dimension_scores": {{
    "technical_depth": 数字(1-4),
    "practical_experience": 数字(1-4),
    "answer_specificity": 数字(1-4),
    "logical_clarity": 数字(1-4),
    "honesty": 数字(1-4),
    "communication": 数字(1-4)
  }},
  "normalized_score": 数字(0-100),
  "feedback": "各维度的具体反馈，明确指出回答的优势和不足",
  "confidence_level": "genuine/uncertain/overconfident",
  "shallow_answer_signals": ["信号1", "信号2"],
  "should_followup": true/false,
  "followup_reason": "为什么需要/不需要追问",
  "followup_direction": "追问方向建议"
}}
"""

    # ============ 追问生成 ============
    
    FOLLOWUP_GENERATION_PROMPT = """基于候选人的回答，生成追问建议，以验证其真实能力水平。

原问题: {original_question}
候选人回答: {answer}
评估反馈: {evaluation_feedback}
追问目标技能: {target_skill}
可疑信号: {shallow_signals}

**追问策略：**
1. **要求具体化**：如果候选人提到技术概念，要求给出具体参数、指标、代码示例
2. **深入原理**：询问底层实现原理、工作机制、源码细节
3. **实战问题**：询问实际项目中遇到的具体问题和解决方案
4. **边界情况**：询问异常情况、性能瓶颈、容错处理
5. **技术对比**：要求对比不同方案的优劣、trade-off分析
6. **量化指标**：要求给出具体的性能数据、并发量、响应时间等

**追问问题类型示例：**
- "你提到了[技术概念]，能具体说说[具体参数/配置/实现细节]吗？"
- "这个方案在实际项目中遇到过什么性能问题？具体是怎么解决的？"
- "能画个架构图或写段伪代码来说明[技术点]吗？"
- "为什么选择[方案A]而不是[方案B]？各自的优缺点是什么？"
- "如果[极端场景]，你会怎么处理？"
- "这个优化前后的具体指标是多少？用什么工具测试的？"

请以JSON格式返回2-3个追问建议：

{{
  "followup_suggestions": [
    {{
      "id": "fq1",
      "question": "追问问题内容",
      "strategy": "追问策略类型",
      "target_skill": "目标技能",
      "difficulty": 8,
      "expected_outcome": "期望通过这个问题验证什么"
    }}
  ],
  "hr_hint": "给HR的提示：为什么建议追问，以及追问时应注意什么"
}}
"""

    # ============ 最终报告 ============
    
    FINAL_REPORT_PROMPT = """基于整场面试的问答记录，生成最终评估报告。

# 候选人信息
姓名: {candidate_name}
应聘职位: {job_title}
面试官: {interviewer_name}

# 职位要求
{job_requirements}

# 面试问答记录
{conversation_log}

# 评分统计
总轮次: {total_rounds}
平均分数: {avg_score}
追问次数: {followup_count}

# HR备注
{hr_notes}

请生成一份完整的面试评估报告，包含以下内容：

{{
  "overall_assessment": {{
    "recommendation_score": 数字(0-100),
    "recommendation": "强烈推荐/推荐/待定/不推荐",
    "summary": "整体评价总结，200字以内"
  }},
  "dimension_analysis": {{
    "technical_depth": {{"score": 0-100, "comment": "评价"}},
    "practical_experience": {{"score": 0-100, "comment": "评价"}},
    "answer_specificity": {{"score": 0-100, "comment": "评价"}},
    "logical_clarity": {{"score": 0-100, "comment": "评价"}},
    "honesty": {{"score": 0-100, "comment": "评价"}},
    "communication": {{"score": 0-100, "comment": "评价"}}
  }},
  "skill_assessment": [
    {{
      "skill": "技能名称",
      "level": "专家/高级/中级/初级/入门",
      "evidence": "判断依据"
    }}
  ],
  "red_flags": ["需要注意的问题点"],
  "highlights": ["候选人的亮点"],
  "suggested_next_steps": ["建议的后续步骤"],
  "detailed_feedback": "详细的评估说明，可以更长"
}}
"""

    # ============ 浅层回答检测词汇表 ============
    
    # 高级术语（如果提到但缺乏细节，可能是浅层理解）
    HIGH_LEVEL_TERMS = [
        "微服务", "分布式", "高并发", "高可用", "架构", "中台",
        "容器化", "kubernetes", "k8s", "docker", "云原生",
        "大数据", "机器学习", "深度学习", "算法优化",
        "性能优化", "缓存", "消息队列", "负载均衡"
    ]
    
    # 模糊词汇（大量使用可能表示不确定）
    VAGUE_WORDS = [
        "一般", "差不多", "应该", "可能", "大概",
        "好像", "似乎", "感觉", "不太确定", "记不太清"
    ]
    
    # 露怯关键词
    WEAKNESS_INDICATORS = [
        "不太熟悉", "了解不深", "接触不多", "没深入研究",
        "记不清了", "忘了具体", "大致是"
    ]
    
    # 空话套话
    EMPTY_PHRASES = [
        "根据实际情况", "具体问题具体分析", "要看场景",
        "这个要综合考虑", "主要还是要", "关键是要"
    ]
    
    # 具体性证据（有这些说明回答较具体）
    CONCRETE_EVIDENCE = [
        "比如", "例如", "具体来说", "实际上",
        "我们当时", "在项目中", "遇到过", "解决方案是"
    ]
    
    # 量化指标关键词
    TECHNICAL_METRICS = [
        "qps", "tps", "响应时间", "并发", "延迟",
        "吞吐量", "cpu", "内存", "数据量", "请求量"
    ]
