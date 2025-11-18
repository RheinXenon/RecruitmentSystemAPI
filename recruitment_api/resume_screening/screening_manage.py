import os
import autogen
import json
import re
import json as json_module
import hashlib
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from typing import Dict, List, Any, Tuple, Optional
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


def parse_position_resumes_json(data: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    解析前端发送的岗位 + 多份简历 JSON 数据。

    期望格式：
    {
      "position": { ... },
      "resumes": [
         {"name": "ABD.txt", "content": "简历详细文本...", "metadata": {"size": 3375, "type": "text/plain"}},
         ...
      ]
    }

    返回：(position_dict, parsed_resumes_list)
    - position_dict: 原始的岗位对象（不会修改字段），调用方可进一步校验
    - parsed_resumes_list: 标准化后的简历列表，每项包含 `name`, `content`, `metadata`（至少含 `size` 和 `type`）

    如果格式不符合，将抛出 ValueError，错误信息为中文说明或字典形式的字段错误详情。
    """
    if not isinstance(data, dict):
        raise ValueError("请求体必须为 JSON 对象（dict）")

    position = data.get("position")
    resumes = data.get("resumes")

    errors: Dict[str, Any] = {}
    if position is None:
        errors["position"] = "缺少 'position' 字段"
    elif not isinstance(position, dict):
        errors["position"] = "'position' 必须为对象"

    if resumes is None:
        errors["resumes"] = "缺少 'resumes' 字段"
    elif not isinstance(resumes, list):
        errors["resumes"] = "'resumes' 必须为列表"

    if errors:
        raise ValueError(errors)

    parsed_resumes: List[Dict[str, Any]] = []
    for idx, item in enumerate(resumes):
        if not isinstance(item, dict):
            raise ValueError({"resumes": f"第 {idx} 项必须为对象"})

        name = item.get("name") or item.get("filename") or f"resume_{idx}"
        content = item.get("content")
        metadata = item.get("metadata", {}) or {}

        if content is None:
            raise ValueError({"resumes": f"第 {idx} 份简历缺少 'content' 字段"})

        if not isinstance(metadata, dict):
            metadata = {}

        size = metadata.get("size", 0)
        mtype = metadata.get("type", "text/plain")

        parsed_resumes.append({
            "name": name,
            "content": content,
            "metadata": {"size": size, "type": mtype}
        })

    return position, parsed_resumes


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
            # 解析实际的岗位信息文件路径
            actual_criteria_file = self._resolve_criteria_file_path()
            with open(actual_criteria_file, 'r', encoding='utf-8') as f:
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

    def _resolve_criteria_file_path(self):
        """解析岗位信息文件的实际路径"""
        # 如果是相对路径，则尝试在当前位置查找
        if not os.path.isabs(self.criteria_file):
            # 先尝试当前目录
            if os.path.exists(self.criteria_file):
                return self.criteria_file
            # 再尝试相对上级目录的路径
            relative_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                        "..", "position_settings", "migrations", "recruitment_criteria.json")
            if os.path.exists(relative_path):
                return relative_path
            # 再尝试直接相对路径
            direct_relative_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                              self.criteria_file)
            if os.path.exists(direct_relative_path):
                return direct_relative_path
        return self.criteria_file

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
            # 确保父目录存在（支持写入到子目录，例如 ./standards/）
            dirpath = os.path.dirname(filename) or '.'
            os.makedirs(dirpath, exist_ok=True)

            with open(filename, 'w', encoding='utf-8') as f:
                # Metadata
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
            
            # 同时保存对应的岗位信息JSON文件
            self._save_criteria_json(quantification_table, filename)
            return True

        except Exception as e:
            print(f"保存量化标准到MD文件时出错: {e}")
            return False
            
    def _save_criteria_json(self, quantification_table, md_filename):
        """保存量化标准对应的岗位信息JSON文件"""
        try:
            # 生成对应的JSON文件名
            base_name = os.path.splitext(md_filename)[0]
            json_filename = f"{base_name}_criteria.json"
            
            # 写入岗位信息
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(quantification_table['criteria'], f, ensure_ascii=False, indent=2)
                
            print(f"岗位信息(JSON格式)已保存到: {json_filename}")
        except Exception as e:
            print(f"保存岗位信息到JSON文件时出错: {e}")
    
    def _calculate_criteria_hash(self, criteria: Dict) -> str:
        """计算岗位信息的哈希值，用于比较一致性"""
        criteria_str = json.dumps(criteria, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(criteria_str.encode('utf-8')).hexdigest()
        
    def verify_criteria_consistency(self, target_criteria_file: str, md_file: str) -> bool:
        """验证量化评分标准是否与目标岗位信息文件一致"""
        try:
            # 解析实际的目标岗位信息文件路径
            actual_target_file = self._resolve_criteria_file_path_for_verification(target_criteria_file)
            
            # 读取目标岗位信息文件
            with open(actual_target_file, 'r', encoding='utf-8') as f:
                target_criteria = json.load(f)
            
            # 生成目标文件的哈希值
            target_hash = self._calculate_criteria_hash(target_criteria)
            
            # 尝试从关联的JSON文件读取量化标准对应的岗位信息
            base_name = os.path.splitext(md_file)[0]
            criteria_json_file = f"{base_name}_criteria.json"
            
            if os.path.exists(criteria_json_file):
                # 读取量化标准对应的岗位信息
                with open(criteria_json_file, 'r', encoding='utf-8') as f:
                    md_criteria = json.load(f)
                    
                # 生成量化标准文件的哈希值
                md_hash = self._calculate_criteria_hash(md_criteria)
                
                # 比较两个哈希值
                is_consistent = target_hash == md_hash
                if not is_consistent:
                    print(f"量化评分标准与岗位信息文件不一致: {actual_target_file}")
                    print(f"目标文件哈希: {target_hash}")
                    print(f"量化标准文件哈希: {md_hash}")
                else:
                    print("量化评分标准与岗位信息文件一致")
                    
                return is_consistent
            else:
                print(f"未找到量化标准对应的岗位信息文件: {criteria_json_file}")
                # 如果没有关联的JSON文件，则尝试从MD文件中提取信息进行比较
                # 这里简化处理，直接返回False
                return False
                
        except Exception as e:
            print(f"验证岗位信息一致性时出错: {e}")
            return False
    
    def _resolve_criteria_file_path_for_verification(self, target_criteria_file: str) -> str:
        """解析验证时使用的岗位信息文件路径"""
        # 如果是相对路径，则尝试在当前位置查找
        if not os.path.isabs(target_criteria_file):
            # 先尝试当前目录
            if os.path.exists(target_criteria_file):
                return target_criteria_file
            # 再尝试相对上级目录的路径
            relative_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                        "..", "position_settings", "migrations", "recruitment_criteria.json")
            if os.path.exists(relative_path):
                return relative_path
            # 再尝试直接相对路径
            direct_relative_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                              target_criteria_file)
            if os.path.exists(direct_relative_path):
                return direct_relative_path
        return target_criteria_file

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
    # 创建Metadata
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
# user_proxy = UserProxyAgent(
#     name="User_Proxy",
#     human_input_mode="TERMINATE",
#     max_consecutive_auto_reply=10,
#     code_execution_config=False,
#     system_message="""你代表企业招聘负责人。你的职责是：
#     1. 提供招聘标准文件路径和简历内容
#     2. 协调三个评审专家的评分工作
#     3. 汇总最终评分结果并做出招聘建议
#     回复 TERMINATE 表示评审完成。"""
# )

# # 2 助手代理 负责读取标准和生成量化表格
# assistant = AssistantAgent(
#     name="Assistant",
#     llm_config=llm_config,
#     system_message="""你是招聘系统协调员。你的职责是：
#     1. 读取并解析招聘标准文件
#     2. 生成量化评分表格
#     3. 将简历内容分发给三个评审专家，只需要向他们提出要求，但是你不需要说出他们的意见
#     请确保评分过程公正、标准统一。"""
# )

# # 3 HR代理
# hr_agent = AssistantAgent(
#     name="HR_Expert",
#     llm_config=llm_config,
#     system_message=f"""你是企业HR专家，专注于人才的综合素质评估。请根据以下标准进行评分：
#     {recruitment_system.quantification_table['scoring_rules']['hr_dimension']}

#     评分要点：
#     1. 工作经验匹配度（年限、行业相关性）
#     2. 学历背景和证书资质
#     3. 职业稳定性和发展潜力
#     4. 沟通表达能力和文化契合度

#     请对简历进行详细分析，给出0-100分的评分，并提供具体的评分理由。
#     在你自己评分的基础上，单独列出一行，在本岗位参考月薪资范围内给出你认为合适的薪资。
#     你只需要从你HR的角度提出意见和理由。
#     评分格式：HR评分：[分数]分，理由：[详细分析]，建议月薪：[建议薪资]"""
# )

# # 4 技术骨干代理
# technical_agent = AssistantAgent(
#     name="Technical_Expert",
#     llm_config=llm_config,
#     system_message=f"""你是技术评审专家，专注于技术能力评估。请根据以下标准进行评分：
#     {recruitment_system.quantification_table['scoring_rules']['technical_dimension']}

#     评分要点：
#     1. 技术技能栈的完整度和深度
#     2. 项目经验的技术复杂度和相关性
#     3. 技术成长潜力和学习能力
#     4. 问题解决能力和创新思维

#     请对简历进行详细技术分析，给出0-100分的评分，并提供具体的技术评价。
#     在你自己评分的基础上，单独列出一行，在本岗位参考月薪资范围内给出你认为合适的薪资。
#     你只需要从你技术骨干的角度提出意见和理由。
#     评分格式：技术评分：[分数]分，理由：[技术分析]，建议月薪：[建议薪资]"""
# )

# # 5 项目经理代理
# manager_agent = AssistantAgent(
#     name="Project_Manager_Expert",
#     llm_config=llm_config,
#     system_message=f"""你是项目经理专家，专注于项目管理能力评估。请根据以下标准进行评分：
#     {recruitment_system.quantification_table['scoring_rules']['manager_dimension']}

#     评分要点：
#     1. 项目管理经验和成果
#     2. 团队协作和沟通能力
#     3. 领导力和决策能力
#     4. 项目执行力和风险管理能力

#     请从项目管理角度分析简历，给出0-100分的评分，并提供具体的管理能力评价。
#     在你自己评分的基础上，单独列出一行，在本岗位参考月薪资范围内给出你认为合适的薪资。
#     你只需要从你项目经理的角度提出意见和理由。
#     评分格式：管理评分：[分数]分，理由：[管理能力分析]，建议月薪：[建议薪资]"""
# )

# # 6 评论员代理
# critic = AssistantAgent(
#     name="Critic",
#     llm_config=llm_config,
#     system_message=f"""你是综合评审专家。你的职责是：
#     1. 汇总三个专家的评分结果
#     2. 计算最终综合评分（满分100分）
#     3. 提供综合招聘建议
#     4. 指出候选人的优势和不足
#     5. 结合各专家给出的薪资建议，提出最终的建议月薪

#     请确保评分计算准确，建议合理。最终回复应包含：
#     - 各维度得分和综合得分
#     - 候选人优势分析
#     - 改进建议和面试重点
#     - 最终的招聘建议（推荐面试/备选/不匹配）
#     - 最终的建议月薪（如果最终的招聘建议是"不匹配"，则不需要提供月薪建议）

#     回复 APPROVE 表示评审完成。
    
#     量化评分标准如下：
#     职位：{recruitment_system.quantification_table['position']}
#     必备技能：{', '.join(recruitment_system.quantification_table['criteria'].get('required_skills', []))}
#     最低经验：{recruitment_system.quantification_table['criteria'].get('min_experience', 2)}年
#     参考月薪资：{recruitment_system.quantification_table['criteria'].get('salary_range', [8000, 20000])[0]}~{recruitment_system.quantification_table['criteria'].get('salary_range', [8000, 20000])[1]}元"""
# )

termination_condition = TextMentionTermination("APPROVE") | TextMentionTermination("TERMINATE") | MaxMessageTermination(
    20)


# 全局变量用于存储当前任务对象
current_task = None

def set_current_task(task):
    """设置当前任务对象"""
    global current_task
    current_task = task

# 自定义发言选择函数
def enhanced_speaker_selector(last_speaker: autogen.Agent, groupchat: GroupChat):
    """
    发言选择函数，包含错误处理和调试信息
    """
    # 确保last_speaker有效
    if last_speaker is None:
        # 第一次发言从User_Proxy开始
        next_speaker = groupchat.agent_by_name("User_Proxy") or groupchat.agents[0]
    else:
        # 定义发言顺序
        speaker_sequence = {
            "User_Proxy": "Assistant",
            "Assistant": "HR_Expert",
            "HR_Expert": "Technical_Expert",
            "Technical_Expert": "Project_Manager_Expert",
            "Project_Manager_Expert": "Critic",
            "Critic": None  # 结束对话
        }

        # 获取下一个发言者名称
        next_speaker_name = speaker_sequence.get(last_speaker.name)

        # 如果没有下一个发言者，结束对话
        if next_speaker_name is None:
            print("评审流程结束")
            next_speaker = None
        else:
            # 在群聊中查找下一个发言者
            next_speaker = groupchat.agent_by_name(next_speaker_name)
            
            # 如果找不到下一个发言者，返回None
            if next_speaker is None:
                print(f"警告: 未找到下一个发言人 {next_speaker_name}")

    current_sequence = ["User_Proxy", "Assistant", "HR_Expert", "Technical_Expert", "Project_Manager_Expert", "Critic"]
    print(f"发言进度: {current_sequence}")
    
    # 更新当前任务的发言者信息
    if current_task:
        if last_speaker:
            current_task.current_speaker = last_speaker.name
        else:
            current_task.current_speaker = "开始"
        current_task.save()
    
    if last_speaker and next_speaker:
        print(f"当前: {last_speaker.name} -> 下一个: {next_speaker.name}")
    elif last_speaker:
        print(f"当前: {last_speaker.name} -> 结束")
    else:
        print("开始 -> User_Proxy")

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
            # 改进的HR评分提取正则表达式，能处理多种格式包括粗体标记
            hr_score_match = re.search(r'HR评分[：:]\s*\**([0-9.]+)\**分', content)
            if hr_score_match:
                result["scores"]["hr_score"] = float(hr_score_match.group(1))
            else:
                # 备用方案：更宽松的匹配模式
                hr_score_match = re.search(r'(?i)hr.*?评分[^\d]{0,10}([0-9.]+)分', content, re.DOTALL)
                if hr_score_match:
                    result["scores"]["hr_score"] = float(hr_score_match.group(1))

            # 提取HR薪资建议
            hr_salary_match = re.search(r'建议月薪[：:]\s*\**([0-9\-~～～～]+)\**', content)
            if hr_salary_match:
                result["salary_suggestions"]["hr_suggestion"] = hr_salary_match.group(1)

            # 保存HR评语（去除评分格式部分）
            hr_comment = re.sub(r'HR评分[：:]\s*\**[0-9.]+\**分.*?理由[：:]\s*', '', content, flags=re.DOTALL)
            hr_comment = re.sub(r'建议月薪[：:]\s*\**[0-9\-~～～～]+\**.*', '', hr_comment, flags=re.DOTALL)
            result["review_comments"]["hr_comments"] = hr_comment.strip()

        # 提取技术专家的评分和评语
        elif speaker == "Technical_Expert":
            # 改进的技术评分提取正则表达式
            tech_score_match = re.search(r'技术评分[：:]\s*\**([0-9.]+)\**分', content)
            if tech_score_match:
                result["scores"]["technical_score"] = float(tech_score_match.group(1))
            else:
                # 备用方案
                tech_score_match = re.search(r'(?i)技术.*?评分[^\d]{0,10}([0-9.]+)分', content, re.DOTALL)
                if tech_score_match:
                    result["scores"]["technical_score"] = float(tech_score_match.group(1))

            # 提取技术薪资建议
            tech_salary_match = re.search(r'建议月薪[：:]\s*\**([0-9\-~～～～]+)\**', content)
            if tech_salary_match:
                result["salary_suggestions"]["technical_suggestion"] = tech_salary_match.group(1)

            # 保存技术评语
            tech_comment = re.sub(r'技术评分[：:]\s*\**[0-9.]+\**分.*?理由[：:]\s*', '', content, flags=re.DOTALL)
            tech_comment = re.sub(r'建议月薪[：:]\s*\**[0-9\-~～～～]+\**.*', '', tech_comment, flags=re.DOTALL)
            result["review_comments"]["technical_comments"] = tech_comment.strip()

        # 提取项目经理的评分和评语
        elif speaker == "Project_Manager_Expert":
            # 改进的管理评分提取正则表达式
            manager_score_match = re.search(r'管理评分[：:]\s*\**([0-9.]+)\**分', content)
            if manager_score_match:
                result["scores"]["manager_score"] = float(manager_score_match.group(1))
            else:
                # 备用方案
                manager_score_match = re.search(r'(?i)管理.*?评分[^\d]{0,10}([0-9.]+)分', content, re.DOTALL)
                if manager_score_match:
                    result["scores"]["manager_score"] = float(manager_score_match.group(1))

            # 提取管理薪资建议
            manager_salary_match = re.search(r'建议月薪[：:]\s*\**([0-9\-~～～～]+)\**', content)
            if manager_salary_match:
                result["salary_suggestions"]["manager_suggestion"] = manager_salary_match.group(1)

            # 保存管理评语
            manager_comment = re.sub(r'管理评分[：:]\s*\**[0-9.]+\**分.*?理由[：:]\s*', '', content, flags=re.DOTALL)
            manager_comment = re.sub(r'建议月薪[：:]\s*\**[0-9\-~～～～]+\**.*', '', manager_comment, flags=re.DOTALL)
            result["review_comments"]["manager_comments"] = manager_comment.strip()

        # 提取Critic的最终建议
        elif speaker == "Critic":
            # 改进的综合评分提取正则表达式
            comp_score_match = re.search(r'综合评分[：:]\s*\**([0-9.]+)\**分', content)
            if comp_score_match:
                result["scores"]["comprehensive_score"] = float(comp_score_match.group(1))
            else:
                # 备用方案
                comp_score_match = re.search(r'(?i)综合.*?评分[^\d]{0,10}([0-9.]+)分', content, re.DOTALL)
                if comp_score_match:
                    result["scores"]["comprehensive_score"] = float(comp_score_match.group(1))

            # 提取最终薪资建议
            final_salary_match = re.search(r'建议月薪[：:]\s*\**([0-9\-~～～～]+)\**', content)
            if final_salary_match:
                result["salary_suggestions"]["final_suggestion"] = final_salary_match.group(1)

            # 提取最终决策
            decision_patterns = [
                r'招聘建议[：:]\s*\***(推荐面试|备选|不匹配|建议面试|通过|不通过)\***',
                r'最终建议[：:]\s*\***(推荐面试|备选|不匹配|建议面试|通过|不通过)\***',
                r'决策[：:]\s*\***(推荐面试|备选|不匹配|建议面试|通过|不通过)\***'
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


def run_resume_screening(input_path: str = "origin_resumes", *, candidate_name: str = None, run_chat: bool = True):
    """
    封装后的简历初筛主流程。

    参数:
        input_path: 单个简历文件路径或包含简历文件的目录（默认 `origin_resumes`）
        candidate_name: 可选，指定候选人姓名（文件名不带扩展），当提供时将优先使用
        run_chat: 是否实际运行 Agent 群聊流程（默认为 True）。当无法调用外部 LLM 时可设置为 False，仅生成量化标准并保存阅读文件。

    返回:
        md_content (str): 生成的候选人简历初筛 Markdown 报告字符串（如果有）或量化标准 MD 路径信息
    """

    # 读取简历（支持单文件或目录）
    resumes_data = {}
    if os.path.isdir(input_path):
        resumes_data = read_resumes_from_folder(input_path)
    elif os.path.isfile(input_path):
        # 从单个文件读取
        name = os.path.splitext(os.path.basename(input_path))[0]
        with open(input_path, 'r', encoding='utf-8') as f:
            resumes_data = {name: f.read()}
    else:
        raise FileNotFoundError(f"输入路径不存在: {input_path}")

    if not resumes_data:
        raise ValueError("未找到任何简历内容。请检查输入路径。")

    # 确定候选人
    if candidate_name is None:
        candidate_name = next(iter(resumes_data))
    if candidate_name not in resumes_data:
        raise ValueError(f"指定的候选人 {candidate_name} 在输入路径中未找到")

    resume_text = resumes_data[candidate_name]

    # 校验量化评分标准与岗位信息的一致性
    criteria_file_path = os.path.join("..", "position_settings", "migrations", "recruitment_criteria.json")
    md_file_path = "本岗位招聘量化标准.md"
    
    if os.path.exists(md_file_path):
        is_consistent = recruitment_system.verify_criteria_consistency(criteria_file_path, md_file_path)
        if not is_consistent:
            print("检测到量化评分标准与岗位信息文件不一致，重新生成量化评分标准...")
            # 删除旧的量化标准文件
            if os.path.exists(md_file_path):
                os.remove(md_file_path)
            # 重新初始化RecruitmentSystem以重新生成量化标准
            recruitment_system.__init__(criteria_file=criteria_file_path, md_file=md_file_path)

    # 动态创建Agents以使用最新的量化标准
    user_proxy, assistant, hr_agent, technical_agent, manager_agent, critic = create_agents_with_current_criteria()

    # 创建群聊对象（保留原脚本创建逻辑）
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
        system_message=f"""你是一个高效的会议主持人，负责协调简历评审会议。请根据当前讨论进展，智能选择下一个最合适的发言人：

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

    请确保讨论有序进行，并在获得完整信息后适时终止会议。
    
    当前量化评分标准如下：
    职位：{recruitment_system.quantification_table['position']}
    必备技能：{', '.join(recruitment_system.quantification_table['criteria'].get('required_skills', []))}
    最低经验：{recruitment_system.quantification_table['criteria'].get('min_experience', 2)}年
    参考月薪资：{recruitment_system.quantification_table['criteria'].get('salary_range', [8000, 20000])[0]}~{recruitment_system.quantification_table['criteria'].get('salary_range', [8000, 20000])[1]}元"""
    )

    # 如果需要执行群聊流程，则启动
    if run_chat:
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

    # 保存结果（即使未实际运行群聊，也会生成/更新量化标准并写入文件夹）
    chat_messages = group_chat.messages if hasattr(group_chat, 'messages') else []
    # 确保 resumes 目录存在
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    resumes_dir = os.path.join(current_script_dir, 'resumes')
    os.makedirs(resumes_dir, exist_ok=True)

    md_filename = f"{candidate_name}简历初筛结果.md"
    save_conversation_to_md(chat_messages, md_filename)
    save_resume_to_json(chat_messages, candidate_name, f"{candidate_name}.json")

    # 只有在MD文件不存在时才需要保存量化标准
    if not os.path.exists("本岗位招聘量化标准.md"):
        recruitment_system.save_quantification_to_md(filename="本岗位招聘量化标准.md")
    else:
        print("量化标准文件已存在，跳过保存步骤。")

    # 返回生成的MD文件路径或内容
    final_md_path = os.path.join(resumes_dir, md_filename)
    try:
        with open(final_md_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        return md_content
    except Exception:
        return f"报告已保存到 {final_md_path}（文件无法读取）。"


def run_resume_screening_from_payload(position: Dict[str, Any], resumes: List[Dict[str, Any]], *, run_chat: bool = True) -> Dict[str, str]:
    """
    使用前端传来的岗位信息和已解析的简历列表生成初筛报告。

    参数:
      - position: 岗位信息字典（同前端格式）
      - resumes: 简历列表，每项包含 `name`, `content`, `metadata`
      - run_chat: 是否执行 Agent 聊天流程（默认 True）。如果环境无 LLM，可设为 False，仅生成/保存文件框架。

    返回:
      - 一个字典，key 为候选人名称（文件名不含扩展），value 为生成的 MD 文件路径或 MD 内容字符串（如果可读取）。
    """
    results = {}

    # 校验传入的岗位信息与本地量化标准文件的一致性
    md_file_path = "本岗位招聘量化标准.md"
    criteria_file_path = os.path.join("..", "position_settings", "migrations", "recruitment_criteria.json")
    
    if os.path.exists(md_file_path):
        is_consistent = recruitment_system.verify_criteria_consistency(criteria_file_path, md_file_path)
        if not is_consistent:
            print("检测到量化评分标准与岗位信息文件不一致，使用传入的岗位信息更新...")
    
    # 更新量化标准以匹配传入的岗位信息（不覆盖原文件，仅在内存中调整）
    if isinstance(position, dict):
        recruitment_system.quantification_table['criteria'] = position
        recruitment_system.quantification_table['position'] = position.get('position', recruitment_system.quantification_table.get('position'))
        recruitment_system.quantification_table['scoring_rules'] = recruitment_system.generate_scoring_rules(position)
        # 将内存中基于传入 position 生成的量化标准保存到 ./standards/<岗位>岗位量化评分标准.md
        try:
            # 清理岗位名以用于文件名
            pos_title = recruitment_system.quantification_table.get('position') or '未知岗位'
            import re as _re
            safe_title = _re.sub(r'[\\/:*?"<>|]', '_', str(pos_title))
            current_script_dir = os.path.dirname(os.path.abspath(__file__))
            standards_dir = os.path.join(current_script_dir, 'standards')
            os.makedirs(standards_dir, exist_ok=True)
            standards_filename = os.path.join(standards_dir, f"{safe_title}岗位量化评分标准.md")
            recruitment_system.save_quantification_to_md(filename=standards_filename)
        except Exception:
            # 保存标准失败不应阻塞流程，记录到控制台
            print("警告: 无法将岗位量化标准保存到 ./standards/，请检查权限或路径。")

    # 确保 resumes 目录存在
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    resumes_dir = os.path.join(current_script_dir, 'resumes')
    os.makedirs(resumes_dir, exist_ok=True)

    for item in resumes:
        name = item.get('name') or 'candidate'
        # 去掉扩展名作为候选人名称
        candidate_name = os.path.splitext(name)[0]
        resume_text = item.get('content', '')

        # 动态创建Agents以使用最新的量化标准
        user_proxy, assistant, hr_agent, technical_agent, manager_agent, critic = create_agents_with_current_criteria()

        # 创建群聊对象（与 run_resume_screening 保持一致）
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
            system_message=f"""你是一个高效的会议主持人，负责协调简历评审会议。请根据当前讨论进展，智能选择下一个最合适的发言人。
            
    当前量化评分标准如下：
    职位：{recruitment_system.quantification_table['position']}
    必备技能：{', '.join(recruitment_system.quantification_table['criteria'].get('required_skills', []))}
    最低经验：{recruitment_system.quantification_table['criteria'].get('min_experience', 2)}年
    参考月薪资：{recruitment_system.quantification_table['criteria'].get('salary_range', [8000, 20000])[0]}~{recruitment_system.quantification_table['criteria'].get('salary_range', [8000, 20000])[1]}元"""
        )

        if run_chat:
            user_proxy.initiate_chat(
                manager,
                message=f"""我们需要对一份求职简历进行综合评审。

招聘标准概述：
- 职位：{recruitment_system.quantification_table['position']}
- 必备技能：{', '.join(recruitment_system.quantification_table['criteria'].get('required_skills', []))}
- 最低经验：{recruitment_system.quantification_table['criteria'].get('min_experience', 2)}年
- 参考月薪资：{recruitment_system.quantification_table['criteria'].get('salary_range', [8000, 20000])[0]}~{recruitment_system.quantification_table['criteria'].get('salary_range', [8000, 20000])[1]}元

姓名：{candidate_name}

简历内容：
{resume_text}

请开始评审流程。"""
            )

        # 存储输出
        md_filename = f"{candidate_name}简历初筛结果.md"
        save_conversation_to_md(group_chat.messages if hasattr(group_chat, 'messages') else [], md_filename)
        save_resume_to_json(group_chat.messages if hasattr(group_chat, 'messages') else [], candidate_name, f"{candidate_name}.json")

        final_md_path = os.path.join(resumes_dir, md_filename)
        try:
            with open(final_md_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            results[candidate_name] = md_content
        except Exception:
            results[candidate_name] = f"报告已保存到 {final_md_path}（文件无法读取）。"

    return results


def create_agents_with_current_criteria():
    """根据当前量化标准动态创建Agents"""
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
        评分格式（显示评分的部分不要加任何格式）：HR评分：[分数]分，理由：[详细分析]，建议月薪：[建议薪资]"""
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
        评分格式（显示评分的部分不要加任何格式）：技术评分：[分数]分，理由：[技术分析]，建议月薪：[建议薪资]"""
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
        评分格式（显示评分的部分不要加任何格式）：管理评分：[分数]分，理由：[管理能力分析]，建议月薪：[建议薪资]"""
    )

    # 6 评论员代理
    critic = AssistantAgent(
        name="Critic",
        llm_config=llm_config,
        system_message=f"""你是综合评审专家。你的职责是：
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
        - 最终的建议月薪（如果最终的招聘建议是"不匹配"，则不需要提供月薪建议）

        请在你的发言开头给出综合评分，
        评分格式（显示评分的部分不要加任何格式）：综合评分：[分数]分
        
        量化评分标准如下：
        职位：{recruitment_system.quantification_table['position']}
        必备技能：{', '.join(recruitment_system.quantification_table['criteria'].get('required_skills', []))}
        最低经验：{recruitment_system.quantification_table['criteria'].get('min_experience', 2)}年
        参考月薪资：{recruitment_system.quantification_table['criteria'].get('salary_range', [8000, 20000])[0]}~{recruitment_system.quantification_table['criteria'].get('salary_range', [8000, 20000])[1]}元
        回复 APPROVE 表示评审完成。"""
    )
    
    return user_proxy, assistant, hr_agent, technical_agent, manager_agent, critic
