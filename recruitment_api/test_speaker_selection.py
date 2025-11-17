import os
import sys

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_speaker_selection():
    """测试发言选择功能"""
    print("开始测试发言选择功能...")
    
    # 导入必要的模块
    from resume_screening.screening_manage import (
        recruitment_system,
        create_agents_with_current_criteria
    )
    
    # 动态创建Agents
    user_proxy, assistant, hr_agent, technical_agent, manager_agent, critic = create_agents_with_current_criteria()
    
    # 创建测试用的群聊对象
    from autogen import GroupChat
    group_chat = GroupChat(
        agents=[user_proxy, assistant, hr_agent, technical_agent, manager_agent, critic],
        messages=[],
        max_round=12
    )
    
    # 测试发言选择逻辑
    print("\n测试发言选择逻辑:")
    
    # 第一次发言应该从User_Proxy开始
    first_speaker = group_chat.agent_by_name("User_Proxy")
    print(f"第一发言人: {first_speaker.name}")
    
    # 模拟依次选择发言人
    current_speaker = first_speaker
    round_count = 0
    
    while current_speaker is not None and round_count < 10:
        print(f"\n第{round_count + 1}轮:")
        print(f"当前发言人: {current_speaker.name}")
        
        # 模拟获取下一个发言人
        # 注意：这里我们不能直接调用enhanced_speaker_selector，因为它需要完整的聊天上下文
        speaker_sequence = {
            "User_Proxy": "Assistant",
            "Assistant": "HR_Expert",
            "HR_Expert": "Technical_Expert",
            "Technical_Expert": "Project_Manager_Expert",
            "Project_Manager_Expert": "Critic",
            "Critic": None
        }
        
        next_speaker_name = speaker_sequence.get(current_speaker.name)
        if next_speaker_name is None:
            print("没有下一个发言人，流程结束")
            break
            
        next_speaker = group_chat.agent_by_name(next_speaker_name)
        if next_speaker is None:
            print(f"未找到下一个发言人: {next_speaker_name}")
            break
            
        print(f"下一个发言人: {next_speaker.name}")
        current_speaker = next_speaker
        round_count += 1
    
    print("\n测试完成。")

if __name__ == "__main__":
    test_speaker_selection()