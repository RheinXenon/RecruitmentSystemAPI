import os
import autogen
import json
import re
import json as json_module
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from typing import Dict, List, Any
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
import datetime

os.environ["PYTHONIOENCODING"] = "utf-8"

# 配置LLM模型列表
config_list = [
    {
        "model": "deepseek-ai/DeepSeek-V3.2-Exp",
        "api_key": "sk-inxgslqzyyrbzowtnowlgjfotvmvpldjyuiblkekxsypgeop",  # 配置API_KEY
        "base_url": "https://api.siliconflow.cn/v1",
        "temperature": 0,
    }
]

# LLM设置
llm_config = {
    "config_list": config_list,
    "seed": 42,
    "timeout": 120,
    "temperature": 0,
}

# 读取简历txt文件
def read_resumes_from_folder(folder_path):
    """
    读取文件夹中所有简历文件，从文件名提取姓名并返回文件内容

    参数:
        folder_path (str): 包含简历文件的文件夹路径

    返回:
        dict: 键为姓名，值为文件内容的字典
    """
    resumes = {}

    try:
        # 检查文件夹是否存在
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"文件夹不存在: {folder_path}")

        # 遍历文件夹中的所有文件
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)

            # 只处理文件，忽略子文件夹
            if os.path.isfile(file_path):
                # 从文件名提取姓名（去除扩展名）
                name = os.path.splitext(filename)[0]

                # 读取文件内容
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()

                resumes[name] = content

    except Exception as e:
        print(f"读取文件时出错: {e}")
        return {}

    return resumes


# 招聘标准管理和评分
class RecruitmentSystem:
    def __init__(self, criteria_file="recruitment_criteria.json", md_file="quantification_standard.md"):
        self.criteria_file = criteria_file
        self.md_file = md_file
        self.quantification_table = self.load_or_generate_quantification_table()

    def load_or_generate_quantification_table(self) -> Dict[str, Any]:
        """智能加载或生成量化表格：如果MD文件存在则直接读取，否则从JSON生成"""
        # 检查MD文件是否存在
        if os.path.exists(self.md_file):
            print(f"发现现有的量化标准文件: {self.md_file}，直接加载...")
            return self.load_quantification_from_md()
        else:
            print(f"未找到量化标准文件 {self.md_file}，从 {self.criteria_file} 生成新标准...")
            quantification_table = self.load_criteria()
            # 生成并保存MD文件
            self.save_quantification_to_md(quantification_table, self.md_file)
            return quantification_table

    def load_quantification_from_md(self) -> Dict[str, Any]:
        """从Markdown文件加载量化标准（主要提取关键信息）"""
        try:
            with open(self.md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 从MD内容中提取基本信息（简化解析）
            quantification = {
                "position": self.load_criteria().get("position", "Python开发工程师"),
                "weights": {"hr": 0.3, "technical": 0.4, "manager": 0.3},
                "criteria": self.load_criteria().get("criteria", {}),  # 回退到JSON标准
                "scoring_rules": self.generate_scoring_rules(self.load_criteria().get("criteria", {}))
            }

            # 尝试从MD文件中提取职位信息
            import re
            position_match = re.search(r'# (.+?)招聘量化标准', content)
            if position_match:
                quantification["position"] = position_match.group(1)

            print(f"已从 {self.md_file} 加载量化标准")
            return quantification

        except Exception as e:
            print(f"从MD文件加载失败: {e}，回退到JSON标准")
            return self.load_criteria()

    def load_criteria(self) -> Dict[str, Any]:
        """ 从JSON文件加载招聘标准并生成量化表格 """
        try:
            with open(self.criteria_file, 'r', encoding='utf-8') as f:
                criteria = json.load(f)

            print(criteria)

            # 生成量化评分表格
            quantification = {
                "position": criteria.get("position", "未知职位"),
                "weights": {
                    "hr": 0.3,
                    "technical": 0.4,
                    "manager": 0.3
                },
                "criteria": criteria,
                "scoring_rules": self.generate_scoring_rules(criteria)
            }
            return quantification
        except FileNotFoundError:
            # 默认招聘标准（如果文件不存在）
            default_criteria = {
                "position": "Python开发工程师",
                "required_skills": ["Python", "Django", "MySQL", "Linux"],
                "optional_skills": ["Redis", "Docker", "Vue.js", "AI"],
                "min_experience": 2,
                "education": ["本科", "硕士"],
                "certifications": [],
                "salary_range": [8000, 20000],
                "project_requirements": {
                    "min_projects": 2,
                    "team_lead_experience": True
                }
            }
            return {
                "position": default_criteria["position"],
                "weights": {"hr": 0.3, "technical": 0.4, "manager": 0.3},
                "criteria": default_criteria,
                "scoring_rules": self.generate_scoring_rules(default_criteria)
            }

    def generate_scoring_rules(self, criteria: Dict) -> Dict[str, List]:
        """根据招聘标准生成详细的评分规则"""
        rules = {
            "hr_dimension": [
                {"item": "工作经验", "max_score": 30, "rule": f"≥{criteria.get('min_experience', 2)}年经验"},
                {"item": "学历背景", "max_score": 25, "rule": f"学历要求: {', '.join(criteria.get('education', []))}"},
                {"item": "证书资质", "max_score": 20, "rule": "相关专业证书"},
                {"item": "职业稳定性", "max_score": 25, "rule": "工作经历连续性"}
            ],
            "technical_dimension": [
                {"item": "必备技能", "max_score": 40,
                 "rule": f"掌握: {', '.join(criteria.get('required_skills', []))}"},
                {"item": "附加技能", "max_score": 30,
                 "rule": f"加分项: {', '.join(criteria.get('optional_skills', []))}"},
                {"item": "技术深度", "max_score": 30, "rule": "项目经验和技术理解深度"}
            ],
            "manager_dimension": [
                {"item": "项目管理", "max_score": 35,
                 "rule": f"至少{criteria.get('project_requirements', {}).get('min_projects', 2)}个完整项目"},
                {"item": "团队协作", "max_score": 30, "rule": "团队合作和沟通能力"},
                {"item": "领导能力", "max_score": 35,
                 "rule": "团队领导经验" if criteria.get('project_requirements', {}).get('team_lead_experience',
                                                                                        True) else "项目参与经验"}
            ]
        }
        return rules

    def save_quantification_to_md(self, quantification_table=None, filename=None):
        """将量化标准保存为md格式"""
        if quantification_table is None:
            quantification_table = self.quantification_table
        if filename is None:
            filename = self.md_file

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                # Markdown标题和元信息
                f.write(f"# {quantification_table['position']}招聘量化标准\n\n")
                f.write(f"**生成时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"**源文件**: {self.criteria_file}\n\n")

                # 权重表格
                f.write("## 权重分配\n\n")
                f.write("| 维度 | 权重 | 说明 |\n")
                f.write("|------|------|------|\n")
                weights = quantification_table['weights']
                dimension_names = {'hr': 'HR维度', 'technical': '技术维度', 'manager': '管理维度'}
                for dimension, weight in weights.items():
                    f.write(f"| {dimension_names.get(dimension, dimension)} | {weight * 100}% |  |\n")
                f.write("\n")

                # 详细评分规则
                f.write("## 评分细则\n\n")
                scoring_rules = quantification_table['scoring_rules']

                for dimension, rules in scoring_rules.items():
                    f.write(f"### {dimension_names.get(dimension, dimension)}评分标准\n\n")
                    f.write("| 评分项目 | 满分 | 评分规则 |\n")
                    f.write("|----------|------|----------|\n")
                    for rule in rules:
                        f.write(f"| {rule['item']} | {rule['max_score']}分 | {rule['rule']} |\n")
                    f.write("\n")

                # 招聘要求汇总
                f.write("## 职位要求汇总\n\n")
                criteria = quantification_table['criteria']
                for key, value in criteria.items():
                    if key == 'required_skills':
                        f.write(f"**必备技能**: {', '.join(value)}\n\n")
                    elif key == 'optional_skills':
                        f.write(f"**加分技能**: {', '.join(value)}\n\n")
                    elif key == 'min_experience':
                        f.write(f"**最低工作经验**: {value}年\n\n")
                    elif key == 'education':
                        f.write(f"**学历要求**: {', '.join(value)}\n\n")
                    elif key == 'project_requirements':
                        f.write("**项目经验要求**:\n")
                        for req_key, req_value in value.items():
                            f.write(f"- {req_key}: {req_value}\n")
                        f.write("\n")

            print(f"量化标准(Markdown格式)已保存到: {filename}")
            return True

        except Exception as e:
            print(f"保存量化标准到MD文件时出错: {e}")
            return False

    def calculate_comprehensive_score(self, scores: Dict[str, float]) -> float:
        """计算综合评分（满分100分）"""
        comprehensive_score = 0
        for dimension, weight in self.quantification_table["weights"].items():
            comprehensive_score += scores.get(dimension, 0) * weight
        return round(comprehensive_score, 2)


# 文件保存功能
def save_conversation_to_md(conversation_history, filename="recruitment_review.md"):
    """
    将对话历史保存到md文件
    """
    # 创建Markdown内容
    md_content = "# 企业招聘简历评审报告\n\n"
    md_content += "## 评审记录\n\n"

    for i, message in enumerate(conversation_history):
        speaker = message.get('name', 'Unknown')
        content = message.get('content', '')

        md_content += f"### {speaker}的发言\n\n"
        md_content += f"{content}\n\n"
        md_content += "---\n\n"  # 分隔线

    # 写入文件
    # 获取当前脚本文件所在的目录
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    # 组合最终的文件路径
    final_filename = os.path.join(current_script_dir, 'resumes', filename)

    with open(final_filename, 'w', encoding='utf-8') as f:  # 指定utf-8编码
        f.write(md_content)

    print(f"对话记录已保存到 {final_filename}")


recruitment_system = RecruitmentSystem(
    criteria_file="recruitment_criteria.json",
    md_file="本岗位招聘量化标准.md"
)

# 创建智能体（Agents）
# 1 用户代理
user_proxy = UserProxyAgent(
    name="User_Proxy",
    human_input_mode="TERMINATE",
    max_consecutive_auto_reply=10,
    code_execution_config=False,
    system_message="""你代表企业招聘负责人。你的职责是：
    1. 提供招聘标准文件路径和简历内容
    2. 协调三个评审专家的评分工作
    3. 汇总最终评分结果并做出招聘建议
    回复 TERMINATE 表示评审完成。"""
)

# 2 助手代理 负责读取标准和生成量化表格
assistant = AssistantAgent(
    name="Assistant",
    llm_config=llm_config,
    system_message="""你是招聘系统协调员。你的职责是：
    1. 读取并解析招聘标准文件
    2. 生成量化评分表格
    3. 将简历内容分发给三个评审专家，只需要向他们提出要求，但是你不需要说出他们的意见
    请确保评分过程公正、标准统一。"""
)

# 3 HR代理
hr_agent = AssistantAgent(
    name="HR_Expert",
    llm_config=llm_config,
    system_message=f"""你是企业HR专家，专注于人才的综合素质评估。请根据以下标准进行评分：
    {recruitment_system.quantification_table['scoring_rules']['hr_dimension']}

    评分要点：
    1. 工作经验匹配度（年限、行业相关性）
    2. 学历背景和证书资质
    3. 职业稳定性和发展潜力
    4. 沟通表达能力和文化契合度

    请对简历进行详细分析，给出0-100分的评分，并提供具体的评分理由。
    在你自己评分的基础上，单独列出一行，在本岗位参考月薪资范围内给出你认为合适的薪资。
    你只需要从你HR的角度提出意见和理由。
    评分格式：HR评分：[分数]分，理由：[详细分析]，建议月薪：[建议薪资]"""
)

# 4 技术骨干代理
technical_agent = AssistantAgent(
    name="Technical_Expert",
    llm_config=llm_config,
    system_message=f"""你是技术评审专家，专注于技术能力评估。请根据以下标准进行评分：
    {recruitment_system.quantification_table['scoring_rules']['technical_dimension']}

    评分要点：
    1. 技术技能栈的完整度和深度
    2. 项目经验的技术复杂度和相关性
    3. 技术成长潜力和学习能力
    4. 问题解决能力和创新思维

    请对简历进行详细技术分析，给出0-100分的评分，并提供具体的技术评价。
    在你自己评分的基础上，单独列出一行，在本岗位参考月薪资范围内给出你认为合适的薪资。
    你只需要从你技术骨干的角度提出意见和理由。
    评分格式：技术评分：[分数]分，理由：[技术分析]，建议月薪：[建议薪资]"""
)

# 5 项目经理代理
manager_agent = AssistantAgent(
    name="Project_Manager_Expert",
    llm_config=llm_config,
    system_message=f"""你是项目经理专家，专注于项目管理能力评估。请根据以下标准进行评分：
    {recruitment_system.quantification_table['scoring_rules']['manager_dimension']}

    评分要点：
    1. 项目管理经验和成果
    2. 团队协作和沟通能力
    3. 领导力和决策能力
    4. 项目执行力和风险管理能力

    请从项目管理角度分析简历，给出0-100分的评分，并提供具体的管理能力评价。
    在你自己评分的基础上，单独列出一行，在本岗位参考月薪资范围内给出你认为合适的薪资。
    你只需要从你项目经理的角度提出意见和理由。
    评分格式：管理评分：[分数]分，理由：[管理能力分析]，建议月薪：[建议薪资]"""
)

# 6 评论员代理
critic = AssistantAgent(
    name="Critic",
    llm_config=llm_config,
    system_message="""你是综合评审专家。你的职责是：
    1. 汇总三个专家的评分结果
    2. 计算最终综合评分（满分100分）
    3. 提供综合招聘建议
    4. 指出候选人的优势和不足
    5. 结合各专家给出的薪资建议，提出最终的建议月薪

    请确保评分计算准确，建议合理。最终回复应包含：
    - 各维度得分和综合得分
    - 候选人优势分析
    - 改进建议和面试重点
    - 最终的招聘建议（推荐面试/备选/不匹配）
    - 最终的建议月薪（如果最终的招聘建议是“不匹配”，的不需要提供月薪建议）

    回复 APPROVE 表示评审完成。"""
)


termination_condition = TextMentionTermination("APPROVE") | TextMentionTermination("TERMINATE") | MaxMessageTermination(20)


# 自定义发言选择函数
def enhanced_speaker_selector(last_speaker: autogen.Agent, groupchat: GroupChat):
    """
    发言选择函数，包含错误处理和调试信息
    """
    # 确保last_speaker有效
    if last_speaker is None:
        return user_proxy  # 第一次发言从User_Proxy开始

    # 定义发言顺序
    speaker_sequence = {
        user_proxy: assistant,
        assistant: hr_agent,
        hr_agent: technical_agent,
        technical_agent: manager_agent,
        manager_agent: critic,
        critic: None  # 结束对话
    }

    # 获取下一个发言者
    next_speaker = speaker_sequence.get(last_speaker)

    # 验证下一个发言者是否在群聊中
    if next_speaker and next_speaker not in groupchat.agents:
        print(f"警告: {next_speaker.name} 不在群聊Agent列表中")
        return None

    current_sequence = [
        user_proxy.name, assistant.name, hr_agent.name,
        technical_agent.name, manager_agent.name, critic.name
    ]
    print(f"发言进度: {current_sequence}")
    print(f"当前: {last_speaker.name} -> 下一个: {getattr(next_speaker, 'name', 'END')}")

    return next_speaker


# 终止条件判断
def is_termination_msg(content):
    """检查终止消息"""
    if not content:
        return False
    content_str = str(content).lower()
    termination_keywords = ['approve', 'terminate', '任务完成', '评审结束']
    return any(keyword in content_str for keyword in termination_keywords)


def extract_scores_and_comments(conversation_history):
    """从对话历史中提取评分、评语和建议"""
    result = {
        "scores": {
            "hr_score": 0.0,
            "technical_score": 0.0,
            "manager_score": 0.0,
            "comprehensive_score": 0.0
        },
        "salary_suggestions": {
            "hr_suggestion": "",
            "technical_suggestion": "",
            "manager_suggestion": "",
            "final_suggestion": ""
        },
        "review_comments": {
            "hr_comments": "",
            "technical_comments": "",
            "manager_comments": ""
        },
        "final_recommendation": {
            "decision": "",
            "reasons": ""
        }
    }

    # 从对话中提取各专家的评分和建议
    for message in conversation_history:
        content = message.get('content', '')
        speaker = message.get('name', '')

        # 提取HR专家的评分和评语
        if speaker == "HR_Expert":
            # 提取HR评分
            hr_score_match = re.search(r'HR评分[：:]?\s*([0-9.]+)分', content)
            if hr_score_match:
                result["scores"]["hr_score"] = float(hr_score_match.group(1))

            # 提取HR薪资建议
            hr_salary_match = re.search(r'建议月薪[：:]?\s*([0-9\-~～～～]+)', content)
            if hr_salary_match:
                result["salary_suggestions"]["hr_suggestion"] = hr_salary_match.group(1)

            # 保存HR评语（去除评分格式部分）
            hr_comment = re.sub(r'HR评分[：:]?\s*[0-9.]+分.*?理由[：:]?\s*', '', content, flags=re.DOTALL)
            hr_comment = re.sub(r'建议月薪[：:]?\s*[0-9\-~～～～]+.*', '', hr_comment, flags=re.DOTALL)
            result["review_comments"]["hr_comments"] = hr_comment.strip()

        # 提取技术专家的评分和评语
        elif speaker == "Technical_Expert":
            # 提取技术评分
            tech_score_match = re.search(r'技术评分[：:]?\s*([0-9.]+)分', content)
            if tech_score_match:
                result["scores"]["technical_score"] = float(tech_score_match.group(1))

            # 提取技术薪资建议
            tech_salary_match = re.search(r'建议月薪[：:]?\s*([0-9\-~～～～]+)', content)
            if tech_salary_match:
                result["salary_suggestions"]["technical_suggestion"] = tech_salary_match.group(1)

            # 保存技术评语
            tech_comment = re.sub(r'技术评分[：:]?\s*[0-9.]+分.*?理由[：:]?\s*', '', content, flags=re.DOTALL)
            tech_comment = re.sub(r'建议月薪[：:]?\s*[0-9\-~～～～]+.*', '', tech_comment, flags=re.DOTALL)
            result["review_comments"]["technical_comments"] = tech_comment.strip()

        # 提取项目经理的评分和评语
        elif speaker == "Project_Manager_Expert":
            # 提取管理评分
            manager_score_match = re.search(r'管理评分[：:]?\s*([0-9.]+)分', content)
            if manager_score_match:
                result["scores"]["manager_score"] = float(manager_score_match.group(1))

            # 提取管理薪资建议
            manager_salary_match = re.search(r'建议月薪[：:]?\s*([0-9\-~～～～]+)', content)
            if manager_salary_match:
                result["salary_suggestions"]["manager_suggestion"] = manager_salary_match.group(1)

            # 保存管理评语
            manager_comment = re.sub(r'管理评分[：:]?\s*[0-9.]+分.*?理由[：:]?\s*', '', content, flags=re.DOTALL)
            manager_comment = re.sub(r'建议月薪[：:]?\s*[0-9\-~～～～]+.*', '', manager_comment, flags=re.DOTALL)
            result["review_comments"]["manager_comments"] = manager_comment.strip()

        # 提取Critic的最终建议
        elif speaker == "Critic":
            # 提取综合评分
            comp_score_match = re.search(r'综合评分[：:]?\s*([0-9.]+)分', content)
            if comp_score_match:
                result["scores"]["comprehensive_score"] = float(comp_score_match.group(1))

            # 提取最终薪资建议
            final_salary_match = re.search(r'建议月薪[：:]?\s*([0-9\-~～～～]+)', content)
            if final_salary_match:
                result["salary_suggestions"]["final_suggestion"] = final_salary_match.group(1)

            # 提取最终决策
            decision_patterns = [
                r'招聘建议[：:]?\s*(推荐面试|备选|不匹配|建议面试|通过|不通过)',
                r'最终建议[：:]?\s*(推荐面试|备选|不匹配|建议面试|通过|不通过)',
                r'决策[：:]?\s*(推荐面试|备选|不匹配|建议面试|通过|不通过)'
            ]

            for pattern in decision_patterns:
                decision_match = re.search(pattern, content)
                if decision_match:
                    result["final_recommendation"]["decision"] = decision_match.group(1)
                    break

            # 保存决策理由（整个Critic的发言作为理由）
            result["final_recommendation"]["reasons"] = content

    return result


def save_resume_to_json(conversation_history, candidate_name="张三", filename="recruitment_results.json"):
    """将简历评审结果保存为JSON格式"""

    # 提取评分和评论信息
    extracted_data = extract_scores_and_comments(conversation_history)

    # 构建完整的JSON结构
    resume_data = {
        "file_name": "招聘评审结果.md",
        "name": candidate_name,
        "scores": extracted_data["scores"],
        "salary_suggestions": extracted_data["salary_suggestions"],
        "review_comments": extracted_data["review_comments"],
        "final_recommendation": extracted_data["final_recommendation"],
        "conversation_history": conversation_history
    }

    # 计算综合评分（如果Critic没有提供）
    if resume_data["scores"]["comprehensive_score"] == 0:
        scores = resume_data["scores"]
        comprehensive_score = (
                scores["hr_score"] * recruitment_system.quantification_table["weights"]["hr"] +
                scores["technical_score"] * recruitment_system.quantification_table["weights"]["technical"] +
                scores["manager_score"] * recruitment_system.quantification_table["weights"]["manager"]
        )
        resume_data["scores"]["comprehensive_score"] = round(comprehensive_score, 2)

    # 保存到JSON文件

    # 获取当前脚本文件所在的目录
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    # 组合最终的文件路径
    final_filename = os.path.join(current_script_dir, 'resumes', filename)

    try:
        with open(final_filename, 'w', encoding='utf-8') as f:
            json_module.dump(resume_data, f, ensure_ascii=False, indent=2)
        print(f"简历评审结果已保存到 {final_filename}")
        return True
    except Exception as e:
        print(f"保存JSON文件时出错: {e}")
        return False


# 读取简历
folder_path = "origin_resumes"
resumes_data = read_resumes_from_folder(folder_path)

candidate_name = next(iter(resumes_data))
resume_text = resumes_data[candidate_name]

# 创建群聊
group_chat = GroupChat(
    agents=[user_proxy, assistant, hr_agent, technical_agent, manager_agent, critic],
    messages=[],
    max_round=12,
    speaker_selection_method=enhanced_speaker_selector,
)

manager = GroupChatManager(
    groupchat=group_chat,
    llm_config=llm_config,
    is_termination_msg=is_termination_msg,
    system_message="""你是一个高效的会议主持人，负责协调简历评审会议。请根据当前讨论进展，智能选择下一个最合适的发言人：
    
    评审流程建议：
    1. 首先由Assistant介绍简历概要和招聘标准
    2. 然后依次请HR专家、技术骨干、项目经理从各自专业角度评审
    3. 每个专家发言后，可以安排Critic进行阶段性总结
    4. 最后组织讨论，形成综合评分
    
    选择发言人的原则：
    - 确保每个专家都有公平的发言机会
    - 根据当前讨论的技术深度、管理角度或HR维度，选择最相关的专家
    - 保持讨论的节奏和效率，避免单个角色过度发言
    - 当出现分歧时，可以安排相关专家进行补充说明
    
    请确保讨论有序进行，并在获得完整信息后适时终止会议。"""
)

# 开始对话
print("启动企业招聘简历智能筛选系统...")
print(f"招聘职位: {recruitment_system.quantification_table['position']}")
print(f"量化标准文件: {'已存在' if os.path.exists('本岗位招聘量化标准.md') else '新生成'}")

user_proxy.initiate_chat(
    manager,
    message=f"""我们需要对一份求职简历进行综合评审。

招聘标准概述：
- 职位：{recruitment_system.quantification_table['position']}
- 必备技能：{', '.join(recruitment_system.quantification_table['criteria'].get('required_skills', []))}
- 最低经验：{recruitment_system.quantification_table['criteria'].get('min_experience', 2)}年
- 参考月薪资：{recruitment_system.quantification_table['criteria'].get('salary_range', [8000, 20000])[0]}~{recruitment_system.quantification_table['criteria'].get('salary_range', [8000, 20000])[1]}元

请按以下流程进行：
1. Assistant首先读取并解析招聘标准，生成量化评分表
2. 将简历内容分发给HR专家、技术专家、项目经理专家分别评审
3. 每位专家依次从自己的角度发言，对这份简历提出自己的看法
4. 每位专家从各自维度进行评分（0-100分）
5. Critic专家汇总评分，计算综合得分并提供招聘建议

姓名：{candidate_name}

简历内容：
{resume_text}

请开始评审流程。"""
)

print("招聘评审流程已结束。")

# 保存结果
chat_messages = group_chat.messages if hasattr(group_chat, 'messages') else []
save_conversation_to_md(chat_messages, f"{candidate_name}简历初筛结果.md")

# 保存到json文件
save_resume_to_json(chat_messages, candidate_name, f"{candidate_name}.json")

# 只有在MD文件不存在时才需要保存量化标准
if not os.path.exists("本岗位招聘量化标准.md"):
    recruitment_system.save_quantification_to_md(filename="本岗位招聘量化标准.md")
else:
    print("量化标准文件已存在，跳过保存步骤。")


# 打印量化标准摘要
print("\n" + "=" * 50)
print("量化评分标准摘要：")
print("=" * 50)
print(f"职位: {recruitment_system.quantification_table['position']}")
for dimension, rules in recruitment_system.quantification_table['scoring_rules'].items():
    print(f"\n{dimension.upper()}维度：")
    for rule in rules:
        print(f"  - {rule['item']}: 满分{rule['max_score']}分 ({rule['rule']})")
print(f"\n权重分配：HR{recruitment_system.quantification_table['weights']['hr'] * 100}%，"
      f"技术{recruitment_system.quantification_table['weights']['technical'] * 100}%，"
      f"管理{recruitment_system.quantification_table['weights']['manager'] * 100}%")