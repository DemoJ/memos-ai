# Memos AI 个人笔记智能问答助手

## 项目概述

这是一个基于个人 Memos 笔记的智能问答助手，能够理解你的问题并仅根据你的笔记内容给出准确回答。

## 更新说明
经实际实验后，在线向量模型api消耗较小，故全部改为使用在线向量模型api，以减小打包大小。

如需要本地向量模型，之前的代码已经备份到：https://github.com/DemoJ/memos-ai-cpu


## 功能特点

- **智能问答**：基于语义搜索 + LLM 生成准确回答
- **知识同步**：自动同步 Memos 笔记的增删改
- **数据本地**：Memos 数据库和向量索引存储在本地，保护隐私
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
# --- 必需配置 ---

# OpenAI API 配置 (用于语言模型)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo

# 在线 Embedding 服务配置 (用于向量化)
# 兼容 OpenAI Embedding API 格式
EMBEDDING_API_URL=your_embedding_api_url_here
EMBEDDING_API_KEY=your_embedding_api_key_here
EMBEDDING_MODEL=your_embedding_model_name # 例如: bge-m3

# --- 可选配置 ---

# 数据库路径
MEMOS_DB_PATH=./memos_prod.db
VECTOR_DB_PATH=./vector_db

# 搜索结果数量
MAX_SEARCH_RESULTS=5

# 自动同步间隔 (小时)
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
- **向量搜索**: FAISS + 在线 Embedding 服务
- **LLM**: OpenAI GPT-3.5/4
- **数据库**: SQLite (Memos)
- **前端**: 原生 HTML/CSS/JS

## 安全说明

- Memos 数据库和生成的向量索引完全存储在本地。
- 笔记内容会发送至你配置的在线 Embedding 服务以生成向量。
- 笔记内容和相关向量会发送至你配置的 LLM 服务（如 OpenAI）以生成回答。
- API 密钥完全由你本地保管，仅用于调用你指定的 API 服务。
- 建议定期备份向量数据库

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 特别致谢

X-AIO提供API额度供本项目研究使用，特别感谢！

X - All in one ：基于分布式AI算力的 LLM API 平台

官网地址：https://www.x-aio.com

## 许可证

MIT License