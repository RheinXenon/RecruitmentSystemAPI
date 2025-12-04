# Recruitment System API

基于 Django 5.0 的招聘系统后端 API，提供简历筛选、视频分析、岗位设置和最终推荐等功能。

---

## 📁 项目结构

```
RecruitmentSystemAPI/
├── recruitment_api/                # Django 项目根目录
│   ├── manage.py                   # Django 管理命令入口
│   ├── db.sqlite3                  # SQLite 数据库
│   │
│   ├── recruitment_api/            # 项目配置模块
│   │   ├── settings.py             # Django 配置
│   │   ├── urls.py                 # 主路由配置
│   │   ├── celery.py               # Celery 异步任务配置
│   │   ├── wsgi.py                 # WSGI 入口
│   │   └── asgi.py                 # ASGI 入口
│   │
│   ├── position_settings/          # 岗位设置模块
│   │   ├── views.py                # 岗位招聘标准 API
│   │   ├── migrations/             # 数据库迁移 & 配置文件
│   │   └── ...
│   │
│   ├── resume_screening/           # 简历初筛模块
│   │   ├── views.py                # 简历筛选 API
│   │   ├── screening_manage.py     # 筛选业务逻辑
│   │   ├── data_manager.py         # 数据管理
│   │   ├── group_status_manager.py # 简历组状态管理
│   │   ├── models.py               # 数据模型
│   │   ├── serializers.py          # 序列化器
│   │   ├── consumers.py            # WebSocket 消费者
│   │   ├── resumes/                # 简历存储目录
│   │   ├── standards/              # 筛选标准配置
│   │   └── ...
│   │
│   ├── video_analysis/             # 视频分析模块
│   │   ├── views.py                # 视频分析 API
│   │   ├── models.py               # 数据模型
│   │   ├── videos/                 # 视频存储目录
│   │   └── ...
│   │
│   ├── final_recommend/            # 最终推荐模块
│   │   ├── views.py                # 面试评估 API
│   │   ├── after_interview.py      # 面试后评估逻辑
│   │   ├── data_preparation.py     # 数据准备
│   │   ├── models.py               # 数据模型
│   │   └── ...
│   │
│   ├── interview_assist/           # 面试辅助模块 (人在回路)
│   │   ├── views.py                # 面试辅助 API
│   │   ├── models.py               # 数据模型 (Session, QARecord)
│   │   ├── urls.py                 # 路由配置
│   │   ├── admin.py                # Admin 配置
│   │   └── services/               # 核心服务
│   │       ├── interview_assistant.py  # 面试辅助服务
│   │       └── prompts.py          # Prompt 模板
│   │
│   └── screening_reports/          # 筛选报告存储目录
│       └── 2025/                   # 按年份归档
```

---

## 🔧 API 标准

### 通用规范

| 项目 | 说明 |
|------|------|
| **基础URL** | `http://localhost:8000` |
| **数据格式** | JSON (`Content-Type: application/json`) |
| **文件上传** | `multipart/form-data` |
| **认证方式** | 当前无认证（开发阶段） |

### 响应格式

**成功响应：**
```json
{
  "status": "success",
  "message": "操作成功",
  "data": { ... }
}
```

**错误响应：**
```json
{
  "status": "error",
  "message": "错误描述"
}
```

**异步任务响应：**
```json
{
  "status": "submitted",
  "message": "任务已提交，正在后台处理",
  "task_id": "uuid-string"
}
```

### HTTP 状态码

| 状态码 | 含义 |
|--------|------|
| `200` | 请求成功 |
| `202` | 异步任务已接受 |
| `400` | 请求参数错误 |
| `404` | 资源不存在 |
| `500` | 服务器内部错误 |

---

## 📡 API 接口列表

### 1. 岗位设置 (`/position-settings/`)

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/position-settings/` | 获取招聘标准配置 |
| `POST` | `/position-settings/` | 更新招聘标准配置 |

---

### 2. 简历初筛 (`/resume-screening/`)

#### 筛选任务

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/resume-screening/screening/` | 提交简历筛选任务 |
| `GET` | `/resume-screening/tasks/<task_id>/status/` | 查询任务状态 |
| `GET` | `/resume-screening/tasks-history/` | 获取任务历史记录 |

#### 报告管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/resume-screening/reports/<report_id>/download/` | 下载筛选报告 |
| `GET` | `/resume-screening/reports/<report_id>/detail/` | 获取报告详情 |

#### 数据管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/resume-screening/data/` | 获取简历数据列表 |

#### 简历分组

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/resume-screening/groups/` | 获取简历组列表 |
| `POST` | `/resume-screening/groups/create/` | 创建简历组 |
| `GET` | `/resume-screening/groups/<group_id>/` | 获取分组详情 |
| `POST` | `/resume-screening/groups/add-resume/` | 添加简历到分组 |
| `POST` | `/resume-screening/groups/remove-resume/` | 从分组移除简历 |
| `POST` | `/resume-screening/groups/set-status/` | 设置分组状态 |

#### 简历-视频关联

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/resume-screening/link-resume-to-video/` | 关联简历与视频 |
| `POST` | `/resume-screening/unlink-resume-from-video/` | 解除简历与视频关联 |

---

### 3. 视频分析 (`/video-analysis/`)

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/video-analysis/` | 提交视频分析任务 |
| `GET` | `/video-analysis/<video_id>/status/` | 查询分析状态 |
| `PUT` | `/video-analysis/<video_id>/update/` | 更新分析结果 |
| `GET` | `/video-analysis/list/` | 获取视频分析列表 |

**视频分析返回字段：**
- `fraud_score` - 欺诈评分
- `neuroticism_score` - 神经质评分
- `extraversion_score` - 外倾性评分
- `openness_score` - 开放性评分
- `agreeableness_score` - 宜人性评分
- `conscientiousness_score` - 尽责性评分
- `confidence_score` - 置信度评分
- `summary` - 分析摘要

---

### 4. 最终推荐 (`/final-recommend/`)

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/final-recommend/interview-evaluation/` | 启动面试后评估任务 |
| `GET` | `/final-recommend/interview-evaluation/<task_id>/` | 查询评估任务状态 |
| `GET` | `/final-recommend/interview-evaluation/?group_id=<id>` | 按分组查询最新任务 |
| `DELETE` | `/final-recommend/interview-evaluation/<task_id>/delete/` | 删除评估任务 |
| `GET` | `/final-recommend/download-report/<file_path>` | 下载评估报告 |

---

### 5. 面试辅助 (`/interview-assist/`) 🆕

人在回路的面试官AI助手，为真人HR提供面试问题建议、回答评估和追问建议。

#### 会话管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/interview-assist/sessions/` | 创建面试辅助会话 |
| `GET` | `/interview-assist/sessions/<session_id>/` | 获取会话详情 |
| `DELETE` | `/interview-assist/sessions/<session_id>/` | 结束会话 |

#### 问题生成

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/interview-assist/sessions/<session_id>/generate-questions/` | 生成候选问题（基于简历+岗位） |
| `POST` | `/interview-assist/sessions/<session_id>/generate-followup/` | 生成追问建议 |

#### 问答记录与评估

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/interview-assist/sessions/<session_id>/record-qa/` | 记录问答并获取AI评估 |
| `GET` | `/interview-assist/sessions/<session_id>/history/` | 获取问答历史 |

#### 报告生成

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/interview-assist/sessions/<session_id>/generate-report/` | 生成最终评估报告 |

**核心功能：**
- 🎯 **基于简历的问题生成** - 自动识别简历中的兴趣点，生成针对性问题
- 🔍 **浅层回答检测** - 识别"不懂装懂"的回答信号
- 💡 **智能追问建议** - 基于回答质量提供追问建议
- 📊 **多维度评估** - 技术深度、实践经验、诚实度等6个维度评分
- 📝 **最终报告生成** - 自动生成面试评估报告

---

## 🚀 快速开始

### 安装依赖

```bash
cd recruitment_api
pip install -r requirements.txt
```

### 数据库迁移

```bash
python manage.py migrate
```

### 启动开发服务器

```bash
python manage.py runserver
```

服务器默认运行在 `http://localhost:8000`

---

## 📝 示例请求

### 提交简历筛选

```bash
curl -X POST http://localhost:8000/resume-screening/screening/ \
  -H "Content-Type: application/json" \
  -d '{
    "position": {
      "title": "软件工程师",
      "requirements": ["Python", "Django"]
    },
    "resumes": [
      {"name": "候选人A.pdf", "content": "简历内容..."}
    ]
  }'
```

### 查询任务状态

```bash
curl http://localhost:8000/resume-screening/tasks/<task_id>/status/
```

### 上传视频分析

```bash
curl -X POST http://localhost:8000/video-analysis/ \
  -F "video_file=@interview.mp4" \
  -F "candidate_name=张三" \
  -F "position_applied=软件工程师"
```

---

## 📊 数据模型概览

| 模块 | 主要模型 |
|------|----------|
| `resume_screening` | `ResumeScreeningTask`, `ScreeningReport`, `ResumeData`, `ResumeGroup` |
| `video_analysis` | `VideoAnalysis` |
| `final_recommend` | `InterviewEvaluationTask` |
| `interview_assist` | `InterviewAssistSession`, `InterviewQARecord` |

---

## 🛠️ 技术栈

- **框架**: Django 5.0 + Django REST Framework
- **数据库**: SQLite (开发) / 可切换其他数据库
- **异步任务**: Celery (可选)
- **实时通信**: Django Channels (WebSocket)
