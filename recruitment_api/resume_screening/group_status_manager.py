from .models import ResumeGroup, ResumeData

def update_group_status_based_on_video_analysis(group_id):
    """
    根据组内所有简历数据的视频分析情况更新简历组状态
    
    Args:
        group_id: 简历组ID
        
    Returns:
        updated: 是否更新了状态
        new_status: 新状态值
    """
    try:
        # 获取简历组
        group = ResumeGroup.objects.get(id=group_id)
        
        # 获取组内所有简历数据
        resume_data_list = ResumeData.objects.filter(group=group)
        
        # 如果没有简历数据，保持原状态
        if not resume_data_list.exists():
            return False, group.status
        
        # 统计各种视频分析状态的数量
        pending_count = 0      # 待分析
        processing_count = 0   # 分析中
        completed_count = 0    # 已完成
        failed_count = 0       # 失败
        
        for resume_data in resume_data_list:
            if resume_data.video_analysis:
                status = resume_data.video_analysis.status
                if status == 'pending':
                    pending_count += 1
                elif status == 'running':
                    processing_count += 1
                elif status == 'completed':
                    completed_count += 1
                elif status == 'failed':
                    failed_count += 1
                else:
                    pending_count += 1  # 未知状态默认为待分析
            else:
                pending_count += 1  # 没有关联视频分析的也视为待分析
        
        # 根据视频分析状态决定组状态
        total_resumes = resume_data_list.count()
        new_status = group.status  # 默认保持原状态
        
        # 如果所有简历都没有视频分析或都是待分析状态，组状态为待分析
        if pending_count == total_resumes:
            new_status = 'pending'
        # 如果有任何一个在处理中，组状态为面试分析中
        elif processing_count > 0:
            new_status = 'interview_analysis'
        # 如果所有都完成了，组状态为已完成
        elif completed_count == total_resumes:
            new_status = 'interview_analysis_completed'
        # 如果有失败的且没有正在进行的，组状态为综合筛选中（需要人工干预）
        # elif failed_count > 0 and processing_count == 0:
        #     new_status = 'comprehensive_screening'
        # 其他情况保持为面试分析中
        else:
            new_status = 'interview_analysis'
        # TODO 需要在综合分析完成后修改状态判断逻辑
        
        # 如果状态改变了则更新
        if group.status != new_status:
            group.status = new_status
            group.save()
            return True, new_status
        else:
            return False, new_status
            
    except ResumeGroup.DoesNotExist:
        return False, None
    except Exception as e:
        # 出现异常时不更新状态
        return False, None