# 简历初筛任务模块说明

## 概述

本模块提供简历初筛功能，包括：
1. **招聘标准加载** - 从 JSON 文件读取岗位需求
2. **量化标准生成** - 生成或读取 Markdown 格式的评分标准
3. **Autogen 群聊评审** - 使用 AI Agent 进行多维度评审
4. **报告生成和保存** - 将结果保存为本地文件和数据库记录

## 核心类和函数

### ResumeScreeningManager 类

管理招聘标准和报告的生成类，不涉及数据库操作，只处理文件I/O。

#### 主要方法：

**1. `load_recruitment_criteria()`**
- 从 `position_settings/migrations/recruitment_criteria.json` 加载招聘标准
- 返回: 包含 `position`, `required_skills`, `salary_range` 等的字典

**2. `get_or_generate_quantification_standard()`**
- 智能加载或生成量化评分标准
- 如果 `resume_screening/migrations/本岗位招聘量化评分标准.md` 存在，则读取
- 否则从 JSON 标准生成并保存
- 返回: 包含 `weights`, `scoring_rules`, `criteria` 等的字典

**3. `save_screening_report()`**
- 将筛选报告保存到本地文件
- 生成 Markdown 报告和 JSON 数据文件
- 返回: 包含文件路径的字典

## 文件路径说明

### 输入文件

- **招聘标准 JSON**: `recruitment_api/position_settings/migrations/recruitment_criteria.json`
  - 包含：职位、技能要求、薪资范围、学历要求等

### 输出文件
- **量化标准 MD**: `resume_screening/migrations/本岗位招聘量化评分标准.md`
  - 自动生成（如果不存在）
  - 包含详细的评分规则和权重配置

- **筛选报告**: `resume_screening/resumes/{候选人名}/`
  - `{候选人名}_简历初筛结果.md` - Markdown 格式的对话记录
  - `{候选人名}_评审数据.json` - 结构化的评分和建议数据

## 使用示例

### 1. 在 views.py 中调用处理

```python
from .screening_manage import run_resume_screening_from_payload

class ResumeScreeningAPIView(APIView):
    def post(self, request):
        # 解析数据
        position_data, resumes_data = parse_position_resumes_json(request.data)
        
        # 直接处理简历筛选
        results = run_resume_screening_from_payload(
            position=position_data,
            resumes=resumes_data,
            run_chat=False  # 设置为False以避免实际调用LLM
        )
```

### 2. 获取任务状态

前端可以通过手动刷新获取任务状态：
```
GET /api/screening/tasks/{task_id}/status/
```

## 配置说明

### Django Settings

需要在 `settings.py` 中配置文件存储：

```python
# 媒体文件配置
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
```

## 数据库模型关系

```
ResumeScreeningTask (任务表)
├── id: UUID
├── status: CharField (pending, running, completed, failed)
├── progress: IntegerField (0-100)
├── error_message: TextField
└── created_at: DateTime

ScreeningReport (报告表)
├── id: UUID
├── task: ForeignKey(ResumeScreeningTask)
├── md_file: FileField (MD报告文件)
├── original_filename: CharField
└── created_at: DateTime
```

## 监控和维护

### 监控任务进度
```python
# 手动查询任务状态
GET /api/screening/tasks/{task_id}/status/

# 响应示例：
{
    "task_id": "xxx",
    "status": "completed",
    "progress": 100,
    "current_step": 5,
    "total_steps": 5
}
```

## API 端点速查

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/screening/` | POST | 提交简历筛选任务 |
| `/api/screening/tasks/{task_id}/status/` | GET | 查询任务状态 |
| `/api/screening/reports/{report_id}/download/` | GET | 下载筛选报告 |

## 常见问题

**Q: 为什么量化标准文件没有生成？**
A: 检查 migrations 目录是否存在且有写入权限，检查日志查看具体错误

**Q: 报告文件保存到哪里了？**
A: 默认保存到 `resume_screening/resumes/` 目录，同时复制到数据库 FileField

**Q: 如何修改报告格式？**
A: 编辑 `ResumeScreeningManager._generate_markdown_report()` 方法
