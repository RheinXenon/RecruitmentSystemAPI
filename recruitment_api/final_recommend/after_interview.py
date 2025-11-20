import os
import json
import autogen
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from typing import Dict, List, Any, Tuple
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
import datetime

# 导入数据准备模块
from .data_preparation import (
    load_recruitment_criteria,
    load_candidates_data_by_group,
    load_personality_and_fraud_data
)

# 配置LLM模型
config_list = [
    {
        "model": "deepseek-ai/DeepSeek-V3.2-Exp",
        "api_key": "sk-inxgslqzyyrbzowtnowlgjfotvmvpldjyuiblkekxsypgeop",
        "base_url": "https://api.siliconflow.cn/v1",
        "temperature": 0,
    }
]

llm_config = {
    "config_list": config_list,
    "seed": 42,
    "timeout": 120,
    "temperature": 0,
}


class RecruitmentSystem:
    """简化的招聘标准管理系统"""

    def __init__(self, criteria_file="../position_settings/migrations/recruitment_criteria.json"):
        self.criteria_file = criteria_file
        self.criteria = self.load_criteria()

    def load_criteria(self) -> Dict[str, Any]:
        """加载招聘标准"""
        return load_recruitment_criteria(self.criteria_file)


def read_candidate_data(group_id: str) -> Dict[str, Any]:
    """根据简历组ID读取候选人数据"""
    return load_candidates_data_by_group(group_id)


def generate_candidate_info(candidates_data, big_five_scores, fraud_scores):
    """生成候选人信息字符串"""
    candidate_infos = []
    for name, resume in candidates_data.items():
        info = f"""
候选人：{name}
简历信息：{resume.get("final_recommendation", "").get("reasons", "")}

大五人格测试结果：
- 开放性: {big_five_scores.get(name, {}).get('openness', 'N/A')}
- 尽责性: {big_five_scores.get(name, {}).get('conscientiousness', 'N/A')}  
- 外倾性: {big_five_scores.get(name, {}).get('extraversion', 'N/A')}
- 宜人性: {big_five_scores.get(name, {}).get('agreeableness', 'N/A')}
- 神经质: {big_five_scores.get(name, {}).get('neuroticism', 'N/A')}

欺诈检测得分: {fraud_scores.get(name, 'N/A')}（0.6以下为安全范围）
{"=" * 50}
"""
        candidate_infos.append(info)
    return "\n".join(candidate_infos)


def run_interview_evaluation(group_id: str, progress_callback=None) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    运行面试后评估流程的主要函数
    
    Args:
        group_id: 简历组ID
        progress_callback: 进度回调函数，用于报告当前发言者和对话轮数
        
    Returns:
        评估对话消息列表和发言者列表
    """
    # 初始化招聘系统
    recruitment_system = RecruitmentSystem()

    # 读取候选人数据
    candidates_data = read_candidate_data(group_id)

    # 加载人格测试和欺诈检测数据
    big_five_scores, fraud_detection_scores = load_personality_and_fraud_data(group_id)

    # 生成候选人信息
    candidate_info_text = generate_candidate_info(candidates_data, big_five_scores, fraud_detection_scores)

    # 创建智能体
    user_proxy = UserProxyAgent(
        name="招聘负责人",
        human_input_mode="TERMINATE",
        max_consecutive_auto_reply=10,
        code_execution_config=False,
        system_message="""你是企业招聘负责人，负责协调面试后评估流程。你的职责：
    1. 启动评估流程并提供所有候选人信息
    2. 确保专家按流程评审"""
    )

    assistant = AssistantAgent(
        name="评估协调员",
        llm_config=llm_config,
        system_message="""你是评估流程协调员。职责：
    1. 接收候选人资料并分发给各位专家
    2. 确保信息传递完整准确
    3. 协调评估流程顺利进行"""
    )

    hr_agent = AssistantAgent(
        name="HR专家",
        llm_config=llm_config,
        system_message=f"""你是HR专家，负责综合素质评估。评估维度：
    1. 工作经验与岗位匹配度（重点关注{recruitment_system.criteria.get('min_experience', 2)}年以上经验）
    2. 学历背景与证书资质
    3. 职业稳定性与发展潜力
    4. 人格特质分析：尽责性(可靠性)、宜人性(团队合作)、神经质(情绪稳定性)

    请对每位候选人：
    - 分析HR维度的适配性
    - 考虑人格测试结果和欺诈风险
    - 推荐1-2名候选人（实际招聘人数的1.5倍）
    - 给出具体推荐理由

    注意，你只能提出你的建议和想法，你不可以直接决定最终推荐

    输出格式：HR推荐：[候选人名单]，理由：[详细分析]"""
    )

    technical_agent = AssistantAgent(
        name="技术专家",
        llm_config=llm_config,
        system_message=f"""你是技术专家，负责技术能力评估。技术标准：
    必备技能：{', '.join(recruitment_system.criteria.get('required_skills', []))}

    评估重点：
    1. 技术栈匹配度和深度
    2. 项目经验的技术复杂度
    3. 问题解决能力和技术成长性
    4. 人格特质：开放性(创新能力)、尽责性(代码质量)

    请对每位候选人：
    - 分析技术能力与岗位匹配度
    - 评估技术描述的真实性（参考欺诈得分）
    - 推荐1-2名技术最合适的候选人
    - 提供技术层面的详细评价

    注意，你只能提出你的建议和想法，你不可以直接决定最终推荐

    输出格式：技术推荐：[候选人名单]，理由：[技术分析]"""
    )

    manager_agent = AssistantAgent(
        name="项目经理专家",
        llm_config=llm_config,
        system_message="""你是项目管理专家，评估项目管理能力。关注点：
    1. 项目管理经验和成果
    2. 团队协作与沟通能力  
    3. 领导力与决策能力
    4. 人格特质：外倾性(沟通)、宜人性(合作)、神经质(抗压)

    请对每位候选人：
    - 分析项目管理能力匹配度
    - 评估项目经验真实性
    - 推荐1-2名项目管理最合适的候选人
    - 提供管理能力详细评价

    注意，你只能提出你的建议和想法，你不可以直接决定最终推荐

    输出格式：管理推荐：[候选人名单]，理由：[管理能力分析]"""
    )

    critic_agent = AssistantAgent(
        name="综合评审专家",
        llm_config=llm_config,
        system_message="""你是综合评审专家，职责：
    第一轮：
    1. 汇总三位专家的推荐名单
    2. 分析各候选人综合竞争力
    3. 提供初步招聘建议

    第二轮：
    1. 组织专家讨论确定最终人选
    2. 为每位候选人生成详细评估报告
    3. 提供招聘顺位排序推荐

    最终的评估报告输出要求：
    - 清晰的候选人对比分析（用表格呈现）
    - 人格特质对工作适应性评估
    - 欺诈风险提示
    - 具体的岗位适配性分析
    - 明确的招聘推荐顺位

    最终确认格式：招聘顺位推荐：[姓名1] > [姓名2] > [姓名3]
    所有流程确认结束后打印APPROVE代表对话结束
    """
    )

    # 存储发言者序列
    speakers = []

    # 发言顺序管理
    def speaker_selector(last_speaker: autogen.Agent, groupchat: GroupChat):
        """智能发言选择器"""
        speaker_sequence = [
            user_proxy,  # 0: 启动流程
            assistant,  # 1: 分发资料
            hr_agent,  # 2: HR评估
            technical_agent,  # 3: 技术评估
            manager_agent,  # 4: 管理评估
            critic_agent,  # 5: 第一轮汇总
            critic_agent,  # 6: 启动第二轮讨论
            hr_agent,  # 7: HR深入讨论
            technical_agent,  # 8: 技术深入讨论
            manager_agent,  # 9: 管理深入讨论
            critic_agent  # 10: 最终总结
        ]

        current_step = len(groupchat.messages)
        print(f"当前对话轮次: {current_step}, 上一发言: {last_speaker.name if last_speaker else '无'}")

        if current_step < len(speaker_sequence):
            next_speaker = speaker_sequence[current_step]
            print(f"下一发言者: {next_speaker.name}")
            
            # 记录发言者
            speakers.append(next_speaker.name)
            
            # 调用进度回调函数通知当前发言者和对话轮数
            if progress_callback:
                progress_callback(next_speaker.name, current_step + 1)
                
            return next_speaker

        return None

    # 终止条件
    def is_termination_msg(content):
        """检查终止消息"""
        if not content:
            return False
        content_str = str(content).lower()
        return any(keyword in content_str for keyword in ['APPROVE'])

    # 创建群聊
    group_chat = GroupChat(
        agents=[user_proxy, assistant, hr_agent, technical_agent, manager_agent, critic_agent],
        messages=[],
        max_round=12,
        speaker_selection_method=speaker_selector,
    )

    manager = GroupChatManager(
        groupchat=group_chat,
        llm_config=llm_config,
        is_termination_msg=is_termination_msg,
    )

    # 启动评估流程
    print("启动面试后综合评估系统...")
    print(f"招聘职位: {recruitment_system.criteria.get('position', 'Python开发工程师')}")
    print(f"候选人数量: {len(candidates_data)}")

    user_proxy.initiate_chat(
        manager,
        message=f"""## 面试后综合评估任务

    ### 评估背景
    经过初筛和面试环节，现需要对候选人进行最终评估。

    **招聘职位**：{recruitment_system.criteria.get('position', 'Python开发工程师')}
    **需求人数**：1人
    **核心要求**：{', '.join(recruitment_system.criteria.get('required_skills', []))}，{recruitment_system.criteria.get('min_experience', 2)}年以上经验

    ### 候选人信息
    {len(candidates_data)}位候选人已完成面试，具体信息如下：
    {candidate_info_text}

    ### 评估流程
    **第一轮：专家独立评估**
    1. HR专家：综合素养、文化契合度、人格特质适配性
    2. 技术专家：技术能力、项目经验、专业技能匹配度  
    3. 项目经理专家：管理能力、团队协作、领导潜力
    4. 每位专家推荐1-2名候选人（需求1.5倍）

    **第二轮：综合讨论决策**
    1. 综合评审专家汇总分析
    2. 专家团队讨论确定最终人选
    3. 生成详细评估报告和招聘顺位推荐

    请按流程开始评估。"""
    )

    # 返回对话消息和发言者列表
    return group_chat.messages, speakers


# 以下代码仅用于测试目的，实际使用时应通过views.py调用run_interview_evaluation函数
if __name__ == "__main__":
    # 读取候选人数据 (示例使用组ID，实际应从前端传入)
    group_id = "4e2a2033-9ef4-45ca-b7b0-6c8e3eba93cd"  # 这应该从前端获取
    
    # 运行评估流程
    messages, speakers = run_interview_evaluation(group_id)
    
    # 打印结果
    if messages:
        print("评估流程已完成，最后一条消息:")
        print(messages[-1])
    
    print("面试后综合评估流程已完成！")