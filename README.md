# Memos AI 个人笔记智能问答助手

## 项目概述

这是一个基于个人 Memos 笔记的智能问答助手，能够理解你的问题并仅根据你的笔记内容给出准确回答。

## 功能特点

- **智能问答**：基于语义搜索 + LLM 生成准确回答
- **知识同步**：自动同步 Memos 笔记的增删改
- **本地部署**：数据完全本地，保护隐私
- **增量更新**：只处理变动的笔记，高效同步

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone [项目地址]
cd memos-ai

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入你的配置
nano .env
```

### 3. 首次运行

```bash
# 首次同步所有笔记
python scripts/sync.py --full-sync

# 启动问答服务
python -m app.main
```

访问 http://localhost:8000 开始使用

## 配置说明

### 环境变量 (.env)

```bash
# OpenAI API 配置
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1

# 数据库配置
MEMOS_DB_PATH=./memos_prod.db
VECTOR_DB_PATH=./vector_db

# 模型配置
EMBEDDING_MODEL=all-MiniLM-L6-v2
LLM_MODEL=gpt-3.5-turbo

# 搜索配置
MAX_SEARCH_RESULTS=5

# 同步配置
SYNC_INTERVAL_HOURS=1
```

### 定时同步

#### Linux/macOS

```bash
# 添加定时任务
crontab -e

# 每小时同步一次
0 * * * * /path/to/memos-ai/scripts/auto_sync.sh >> /path/to/memos-ai/logs/sync.log 2>&1
```

#### Windows

使用任务计划程序，每小时运行：
```bash
python scripts/sync.py
```

## 使用指南

### 1. 问答界面

- 打开浏览器访问 http://localhost:8000
- 在输入框中输入关于你笔记的问题
- 系统会基于你的笔记内容给出回答

### 2. 同步笔记

#### 手动同步
```bash
# 增量同步（只处理变动的笔记）
python scripts/sync.py

# 全量同步（重新索引所有笔记）
python scripts/sync.py --full-sync
```

#### 自动同步
- 已配置定时任务的用户无需手动操作
- 系统会自动检测笔记变化并更新索引

## 项目结构

```
memos-ai/
├── app/
│   ├── api/           # API 路由
│   ├── core/          # 核心配置
│   ├── models/        # 数据模型
│   ├── services/      # 业务逻辑
│   ├── static/        # 静态文件
│   ├── templates/     # HTML 模板
│   └── main.py        # FastAPI 应用入口
├── scripts/
│   ├── sync.py        # 同步脚本
│   └── auto_sync.sh   # 自动同步脚本
├── requirements.txt   # 依赖列表
├── .env.example       # 环境变量模板
└── README.md          # 项目文档
```

## 故障排除

### 常见问题

1. **找不到 memos_prod.db**
   - 确保 Memos 数据库文件在当前目录
   - 检查 MEMOS_DB_PATH 配置是否正确

2. **OpenAI API 错误**
   - 检查 OPENAI_API_KEY 是否正确
   - 确认 API 余额充足
   - 检查网络连接

3. **同步失败**
   - 检查数据库文件权限
   - 确认 Python 环境正确
   - 查看错误日志

### 调试模式

```bash
# 启动调试模式
python -m app.main --reload

# 查看同步日志
python scripts/sync.py --verbose
```

## 技术栈

- **后端**: FastAPI + SQLAlchemy
- **向量搜索**: FAISS + Sentence Transformers
- **LLM**: OpenAI GPT-3.5/4
- **数据库**: SQLite (Memos)
- **前端**: 原生 HTML/CSS/JS

## 安全说明

- 所有数据处理都在本地完成
- 不会上传你的笔记内容到第三方
- API 密钥仅用于调用 LLM 服务
- 建议定期备份向量数据库

## 更新日志

### v1.0.0
- 基础问答功能
- 自动同步功能
- 增量更新机制
- Web 界面

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License