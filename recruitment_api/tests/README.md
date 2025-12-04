# 后端测试脚本

本目录包含后端API的测试脚本。

## 文件说明

| 文件 | 说明 |
|------|------|
| `test_interview_assist.py` | 面试辅助模块的Django单元测试 |
| `test_resume_screening.py` | 简历筛选模块的Django单元测试 |
| `test_api_client.py` | 独立API测试客户端脚本 |

## 运行Django单元测试

在项目根目录(`recruitment_api`)下运行：

```bash
# 运行所有测试
python manage.py test tests

# 运行特定模块测试
python manage.py test tests.test_interview_assist
python manage.py test tests.test_resume_screening

# 运行特定测试类
python manage.py test tests.test_interview_assist.SessionViewTests

# 运行特定测试方法
python manage.py test tests.test_interview_assist.SessionViewTests.test_create_session_success

# 显示详细输出
python manage.py test tests --verbosity=2
```

## 运行API客户端测试

这个脚本用于测试已启动的后端服务：

```bash
# 确保后端服务已启动
python manage.py runserver

# 在另一个终端运行测试
cd tests

# 完整流程测试（需要提供有效的resume_data_id）
python test_api_client.py <resume_data_id>

# 错误处理测试
python test_api_client.py --errors
```

### 获取resume_data_id

可以通过Django shell获取：

```bash
python manage.py shell
```

```python
from resume_screening.models import ResumeData
# 获取第一个简历的ID
resume = ResumeData.objects.first()
print(resume.id)
```

## 测试覆盖的API端点

### 面试辅助模块 (`/interview-assist/`)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/sessions/` | POST | 创建面试会话 |
| `/sessions/<id>/` | GET | 获取会话详情 |
| `/sessions/<id>/` | DELETE | 结束会话 |
| `/sessions/<id>/generate-questions/` | POST | 生成候选问题 |
| `/sessions/<id>/record-qa/` | POST | 记录问答并评估 |
| `/sessions/<id>/generate-followup/` | POST | 生成追问建议 |
| `/sessions/<id>/history/` | GET | 获取问答历史 |
| `/sessions/<id>/generate-report/` | POST | 生成最终报告 |

### 简历筛选模块

测试了`ResumeData`、`ResumeGroup`、`ResumeScreeningTask`等模型的CRUD操作。

## 测试数据

Django单元测试会自动创建和清理测试数据，使用独立的测试数据库。

API客户端测试需要依赖已有的数据库数据。

## 注意事项

1. Django单元测试使用测试数据库，不会影响开发数据库
2. API客户端测试会操作真实数据库，请谨慎使用
3. 确保数据库迁移已完成：`python manage.py migrate`
